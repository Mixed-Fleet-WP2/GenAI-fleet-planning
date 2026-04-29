# type: ignore

#  Copyright (c) 2025 Elmeri Pohjois-Koivisto
#  Licensed under MIT, see LICENSES at the repository root for full license(s)

import os
import yaml
from ament_index_python.packages import get_package_share_directory, get_package_prefix
from launch import LaunchDescription
from launch.actions import (
    AppendEnvironmentVariable,
    DeclareLaunchArgument,
    ExecuteProcess,
    OpaqueFunction,
    GroupAction,
)
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, LoadComposableNodes
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ros_gz_bridge.actions import RosGzBridge
from ros_gz_sim.actions import GzServer
from launch_ros.descriptions import ComposableNode
from launch.conditions import IfCondition
from nav2_common.launch import ReplaceString


# ---------------------------------------------------------------------------
# Orchestrator-owned per-robot actions
# (Nav2, RSP, AMCL etc. are the robot container's responsibility)
# ---------------------------------------------------------------------------

def create_robot_instances(context, *args, **kwargs):
    robots_file_path = LaunchConfiguration('robots_file').perform(context)

    with open(robots_file_path) as f:
        robots: list[dict] = yaml.safe_load(f)["robots"]

    def make_robot_group(robot: dict) -> GroupAction:
        name          = robot["name"]
        use_pure_odom = str(robot.get("use_pure_odom", False))

        # The orchestrator's only per-robot responsibility is the static
        # map->odom transform when the robot uses ground-truth odometry
        # and therefore does not run AMCL.
        # Everything else (Nav2, RSP, AMCL, costmaps …) lives in the
        # robot's own container and its own launch file.
        return GroupAction(scoped=True, actions=[
            Node(
                condition=IfCondition(use_pure_odom),
                package='tf2_ros',
                executable='static_transform_publisher',
                namespace=name,
                output='screen',
                arguments=['--frame-id', 'map', '--child-frame-id', 'odom'],
                parameters=[{'use_sim_time': True}],
                # Keep TF inside the robot's namespace so it doesn't leak
                remappings=[('/tf', 'tf'), ('/tf_static', 'tf_static')],
            ),
        ])

    return [make_robot_group(r) for r in robots]


# ---------------------------------------------------------------------------
# Launch description
# ---------------------------------------------------------------------------

def generate_launch_description():
    nav_launch_dir = get_package_share_directory('nav2_launch')
    pkg_share      = get_package_share_directory('mf_simulation')

    # -----------------------------------------------------------------------
    # Launch arguments
    # -----------------------------------------------------------------------

    declare_world = DeclareLaunchArgument(
        'world',
        default_value=os.path.join(pkg_share, 'worlds', 'warehouse_spacious.sdf'),
        description='Full path to the Gazebo world SDF',
    )

    declare_map = DeclareLaunchArgument(
        'map',
        default_value=os.path.join(nav_launch_dir, 'maps', 'warehouse_spacious.yaml'),
        description='Full path to the Nav2 map YAML (used by robot containers via ROS params)',
    )

    declare_robots_file = DeclareLaunchArgument(
        'robots_file',
        default_value=os.path.join(pkg_share, 'config', 'robots_default.yaml'),
        description='Full path to robots configuration YAML',
    )

    declare_mqtt_config = DeclareLaunchArgument(
        name='mqtt_config_file',
        default_value=os.path.join(pkg_share, 'config', 'global_mqtt_bridge.yaml'),
    )

    declare_gz_bridge_config = DeclareLaunchArgument(
        name='gz_bridge_config',
        default_value=os.path.join(pkg_share, 'config', 'global_ros_gz_bridge.yaml'),
        description='Path to gz bridge configuration',
    )

    declare_mqtt_port = DeclareLaunchArgument(
        name='mqtt_port',
        default_value='1883',
        description='Port for the MQTT broker',
    )

    declare_mqtt_host = DeclareLaunchArgument(
        name='mqtt_host',
        default_value='localhost',
        description='Host for the MQTT broker',
    )

    # -----------------------------------------------------------------------
    # Substitutions
    # -----------------------------------------------------------------------

    world                    = LaunchConfiguration('world')
    mqtt_host                = LaunchConfiguration('mqtt_host')
    mqtt_port                = LaunchConfiguration('mqtt_port')
    global_gz_bridge_config  = LaunchConfiguration('gz_bridge_config')

    # Stamp hostname + port into the MQTT bridge config at launch time
    global_mqtt_config = ReplaceString(
        source_file=LaunchConfiguration('mqtt_config_file'),
        replacements={
            '<hostname>': mqtt_host,
            '<port>':     mqtt_port,
        },
    )

    # -----------------------------------------------------------------------
    # Gazebo
    #
    # We launch the server as a composable node inside a shared container so
    # that the gz<->ROS bridge runs in the same process (zero-copy).
    #
    # The GUI client is a separate process because:
    #   a) it is optional / usually not wanted inside Docker, and
    #   b) it cannot be a composable node.
    #
    # NOTE: When running in Docker with --network host the GUI client can be
    #       started on the host with just `gz sim -g` and it will connect to
    #       the server automatically via the GZ_IP / GZ_PARTITION env vars.
    # -----------------------------------------------------------------------

    simulation_container = Node(
        name='global_stuff_container',
        package='rclcpp_components',
        executable='component_container_mt',
        output='both',
    )

    # A separate client for processing
    # MQTT messages because there is no gui launched
    gazebo_headless_client = ExecuteProcess(
        cmd=['ros2', 'run', 'mf_simulation', 'json_client', mqtt_host, mqtt_port],
        name='mf_simulation_json_client',
        output='screen',
        shell=False,
    )

    # -----------------------------------------------------------------------
    # Gz <-> ROS bridge  (global topics + world services)
    # loaded to the shared
    # -----------------------------------------------------------------------

    gz_bridge = RosGzBridge(
        bridge_name='global_gz_bridge',
        config_file=global_gz_bridge_config,
        container_name='global_stuff_container',
        create_own_container=str(False),
        use_composition=str(True),
        extra_bridge_params=[{
            'bridge_names': ['service_bridge', 'create_bridge', 'delete_bridge'],

            'bridges.service_bridge.service_name':    '/world/warehouse/set_pose',
            'bridges.service_bridge.ros_type_name':   'ros_gz_interfaces/srv/SetEntityPose',
            'bridges.service_bridge.gz_req_type_name':'gz.msgs.Pose',
            'bridges.service_bridge.gz_rep_type_name':'gz.msgs.Boolean',
            'bridges.service_bridge.direction':        'BIDIRECTIONAL',

            'bridges.create_bridge.service_name':     '/world/warehouse/create',
            'bridges.create_bridge.ros_type_name':    'ros_gz_interfaces/srv/SpawnEntity',
            'bridges.create_bridge.gz_req_type_name': 'gz.msgs.EntityFactory',
            'bridges.create_bridge.gz_rep_type_name': 'gz.msgs.Boolean',
            'bridges.create_bridge.direction':         'BIDIRECTIONAL',

            'bridges.delete_bridge.service_name':     '/world/warehouse/remove',
            'bridges.delete_bridge.ros_type_name':    'ros_gz_interfaces/srv/DeleteEntity',
            'bridges.delete_bridge.gz_req_type_name': 'gz.msgs.Entity',
            'bridges.delete_bridge.gz_rep_type_name': 'gz.msgs.Boolean',
            'bridges.delete_bridge.direction':         'BIDIRECTIONAL',
        }],
    )

    # -----------------------------------------------------------------------
    # Composable nodes that share the simulation container process
    # -----------------------------------------------------------------------

    load_composable_nodes = LoadComposableNodes(
        target_container='global_stuff_container',
        composable_node_descriptions=[
            ComposableNode(
                package='mqtt_client',
                plugin='mqtt_client::MqttClient',
                name='global_mqtt_client',
                parameters=[global_mqtt_config],
                extra_arguments=[{'use_intra_process_comms': True}],
            ),
            ComposableNode(
                package='state_bridge',
                plugin='state_bridge::StateBridge',
                name='state_bridge_component',
                parameters=[{'use_sim_time': True}],
                extra_arguments=[{'use_intra_process_comms': True}],
            ),
        ],
    )

    # -----------------------------------------------------------------------
    # Environment — Gazebo model paths
    # -----------------------------------------------------------------------

    set_gz_resource_path = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH',
        os.path.join(pkg_share, 'models'),
    )

    # -----------------------------------------------------------------------
    # Assemble LaunchDescription
    # -----------------------------------------------------------------------

    ld = LaunchDescription()

    # Gazebo needs to find robot mesh/model assets from each robot package
    for pkg in ['forklift_cpp', 'drone_cpp']:
        ld.add_action(AppendEnvironmentVariable(
            'GZ_SIM_RESOURCE_PATH',
            os.path.join(get_package_prefix(pkg), 'share'),
        ))

    # Arguments
    ld.add_action(declare_world)
    ld.add_action(declare_map)
    ld.add_action(declare_robots_file)
    ld.add_action(declare_mqtt_config)
    ld.add_action(declare_gz_bridge_config)
    ld.add_action(declare_mqtt_port)
    ld.add_action(declare_mqtt_host)

    # Environment
    ld.add_action(set_gz_resource_path)

    # Simulation stack (order matters — container must exist before nodes load into it)
    ld.add_action(simulation_container)
    ld.add_action(gz_bridge)
    ld.add_action(load_composable_nodes)
    ld.add_action(gazebo_headless_client)

    # Per-robot orchestrator actions (static TF only — nav2 lives in robot containers)
    ld.add_action(OpaqueFunction(function=create_robot_instances))

    return ld