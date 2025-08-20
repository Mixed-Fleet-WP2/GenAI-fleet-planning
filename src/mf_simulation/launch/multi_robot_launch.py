# type: ignore

#  Copyright (c) 2025 Elmeri Pohjois-Koivisto
#  Licensed under MIT, see LICENSES at the repository root for full license(s)

import os
from ament_index_python.packages import get_package_share_directory, get_packages_with_prefixes, get_package_prefix
from launch import LaunchDescription
from launch.actions import (
    AppendEnvironmentVariable,
    DeclareLaunchArgument,
    ExecuteProcess,
    OpaqueFunction,
    GroupAction,
    IncludeLaunchDescription,
)
from launch.substitutions import LaunchConfiguration,  TextSubstitution
from launch_ros.actions import Node, LoadComposableNodes
from launch.launch_description_sources import get_launch_description_from_python_launch_file, PythonLaunchDescriptionSource
from ros_gz_bridge.actions import RosGzBridge
from ros_gz_sim.actions import GzServer
from launch_ros.descriptions import ComposableNode
from launch.event_handlers import OnShutdown
import yaml
from launch.conditions import IfCondition, UnlessCondition
from nav2_common.launch import ReplaceString, RewrittenYaml
from launch_ros.descriptions import ParameterFile

def create_robot_instances(context, *args, **kwargs):
    """Function to create robot instances based on the robots YAML file"""
    
    robots_file_path = LaunchConfiguration('robots_file').perform(context)
    map_yaml_file = LaunchConfiguration('map').perform(context)
    autostart = LaunchConfiguration('autostart').perform(context)
    rviz_config_file = LaunchConfiguration('rviz_config').perform(context)
    use_rviz = LaunchConfiguration('use_rviz').perform(context)
    
    nav_launch_dir = get_package_share_directory('nav2_launch')
    
    with open(robots_file_path, "r") as file:
        robots:list[dict] = yaml.safe_load(file)["robots"]

    nav_instances_cmds = []
    
    for robot in robots:
        robot_name = robot["name"]
        robot_package = robot["package"]
        launch_file = robot["launch_file"]
        nav2_config = robot["nav2_config"]
        start_pos = robot.get("starting_position", [3.0, -1.0, 0.0])
        start_orient = robot.get("starting_orientation", [0.0, 0.0, 0.0])

        print("odom from file:", robot["use_pure_odom"], flush=True)

        use_pure_odom = robot.get("use_pure_odom", False)
        
        pkg = get_package_share_directory(robot_package)
        print("odom use is:", use_pure_odom, flush=True)
        nav2_params_file = os.path.join(pkg, 'config', nav2_config)
        
        group = GroupAction([  
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(os.path.join(nav_launch_dir, "launch", "rviz_launch.py")),
                condition=IfCondition(use_rviz),
                launch_arguments={
                    'namespace': robot_name,
                    'use_sim_time': 'True',
                    'use_namespace': 'True',
                    'rviz_config': rviz_config_file,
                }.items(),
            ),
            
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(pkg, 'launch', launch_file)
                ),
                launch_arguments={
                    'namespace': robot_name,
                    'use_namespace': 'True',
                    'map': map_yaml_file,
                    'use_sim_time': 'True',
                    'params_file': nav2_params_file,
                    'autostart': autostart,
                    'x_pose': TextSubstitution(text=str(start_pos[0])),
                    'y_pose': TextSubstitution(text=str(start_pos[1])),
                    'z_pose': TextSubstitution(text=str(start_pos[2])),
                    'roll': TextSubstitution(text=str(start_orient[0])),
                    'pitch': TextSubstitution(text=str(start_orient[1])),
                    'yaw': TextSubstitution(text=str(start_orient[2])),
                    'robot_name': TextSubstitution(text=robot_name),
                    'use_pure_odom': TextSubstitution(text=str(use_pure_odom))
                }.items(),
            ),  
                # Only publish static map->odom transform if the odom is ground truth and amcl is not used
                Node(
                    condition=IfCondition(str(use_pure_odom)),
                    package="tf2_ros",
                    executable="static_transform_publisher",
                    output="screen",
                    namespace=robot_name,
                    arguments=[
                        "--frame-id", "map",
                        "--child-frame-id", "odom"
                    ],
                    parameters=[{
                        "use_sim_time": True
                    }],
                    remappings = [('/tf', 'tf'), ('/tf_static', 'tf_static')]
                )
        ], scoped=True, forwarding=True)
        nav_instances_cmds.append(group)
            
    return nav_instances_cmds

def generate_launch_description():
    # Get the launch directory
    nav_launch_dir = get_package_share_directory('nav2_launch')
    
    global_mqtt_config_file = LaunchConfiguration('mqtt_config_file')
    global_gz_bridge_config_file = LaunchConfiguration('gz_bridge_config')

    launch_dir = os.path.join(nav_launch_dir, 'launch')
    pkg_share = get_package_share_directory('mf_simulation')
    
    # Simulation settings
    world = LaunchConfiguration('world')
    # On this example all robots are launched with the same settings
    map_yaml_file = LaunchConfiguration('map')
    autostart = LaunchConfiguration('autostart')
    rviz_config_file = LaunchConfiguration('rviz_config')
    use_robot_state_pub = LaunchConfiguration('use_robot_state_pub')
    use_rviz = LaunchConfiguration('use_rviz')
    robots_file = LaunchConfiguration('robots_file')
    headless = LaunchConfiguration('headless')
    mqtt_port = LaunchConfiguration('mqtt_port')
    mqtt_host = LaunchConfiguration('mqtt_host')
    
    # Declare the launch arguments
    declare_world_cmd = DeclareLaunchArgument(
        'world',
        default_value=os.path.join(pkg_share, 'worlds', 'warehouse_spacious.sdf'),
        description='Full path to world file to load',
    )
    
    declare_map_yaml_cmd = DeclareLaunchArgument(
        'map',
        default_value=os.path.join(nav_launch_dir, 'maps', 'warehouse_spacious.yaml'),
        description='Full path to map file to load',
    )
    
    declare_autostart_cmd = DeclareLaunchArgument(
        'autostart',
        default_value='true',
        description='Automatically startup the stacks',
    )
    
    declare_rviz_config_file_cmd = DeclareLaunchArgument(
        'rviz_config',
        default_value=os.path.join(nav_launch_dir, 'config', 'nav2_namespaced_view.rviz'),
        description='Full path to the RVIZ config file to use.',
    )
    
    declare_use_robot_state_pub_cmd = DeclareLaunchArgument(
        'use_robot_state_pub',
        default_value='True',
        description='Whether to start the robot state publisher',
    )
    
    declare_use_rviz_cmd = DeclareLaunchArgument(
        'use_rviz', 
        default_value='True', 
        description='Whether to start RVIZ'
    )
    
    declare_robots_file = DeclareLaunchArgument(
        'robots_file',
        default_value=os.path.join(pkg_share, 'config', 'robots_default.yaml'),
        description='Full path to robots configuration YAML file'
    )


    declare_global_mqtt_config_file = DeclareLaunchArgument(
        name="mqtt_config_file",
        default_value=os.path.join(pkg_share, 'config', 'global_mqtt_bridge.yaml')
    )

    declare_global_gz_bridge_path = DeclareLaunchArgument(
        name="gz_bridge_config",
        default_value=os.path.join(pkg_share, 'config', 'global_ros_gz_bridge.yaml'),
        description="Path to gz bridge configuration"
    )

    declare_headless = DeclareLaunchArgument(
        name='headless',
        default_value='True',
        description="Whether to run the LLM gui or not"
    )

    declare_mqtt_port = DeclareLaunchArgument(
        name="mqtt_port",
        default_value='1883',
        description="Port for the MQTT broker"
    )

    declare_mqtt_host = DeclareLaunchArgument(
        name="mqtt_host",
        default_value='localhost',
        description="Host for the MQTT broker"
    )

    global_mqtt_config_file = ReplaceString(
        source_file=global_mqtt_config_file,
        replacements={
            '<hostname>':(mqtt_host),
            '<port>':(mqtt_port)}
    )
    
    # At the moment there is a bug where processes started with shell=True are not shut down by launch
    # this is why the launch file from ros_gz_sim package is not used
    # See: https://github.com/ros2/launch/issues/757
    # and https://github.com/ros2/launch/issues/545
    gazebo_client = ExecuteProcess(
        #cmd=['gz','sim','-v4', '-g', '--force-version', '8', '--render-engine', 'ogre'],
        cmd=['gz', 'sim', '-v4', '-g', '--force-version', '8'],
        name='gazebo',
        output='screen',
        shell=False,
    )


    start_headless_client = ExecuteProcess(
        cmd=['ros2', 'run', 'mf_simulation', 'json_client', mqtt_host, mqtt_port],
        name='mf_simulation_json_client',
        output='screen',
        shell=False,
        condition=IfCondition(headless)
    )


    start_interface = ExecuteProcess(
        cmd=['ros2', 'run', 'mf_simulation', 'interface'],
        name='mf_simulation_interface',
        output='screen',
        shell=False,
        condition=UnlessCondition(headless)
    )

    simulation_container = Node(
        name='sim_env_container',
        package='rclcpp_components',
        executable='component_container_mt',
        # arguments=["--use_multi_threaded_executor"],
        output='both'
    )


    # See https://github.com/gazebosim/ros_gz/blob/bba6783a85955e2719a0d11468d9a8a79223b0a7/ros_gz_sim/launch/ros_gz_sim.launch.py#L22 
    # for example of using GzServer action

    # GZServer implementation:
    # https://github.com/gazebosim/ros_gz/blob/bba6783a85955e2719a0d11468d9a8a79223b0a7/ros_gz_sim/ros_gz_sim/actions/gzserver.py#L236
    gazebo_server = GzServer(
        world_sdf_file=world,
        container_name='sim_env_container',
        create_own_container=str(False),
        use_composition= str(True),
    )

    # RosGzBridge implementation:
    # https://github.com/gazebosim/ros_gz/blob/bba6783a85955e2719a0d11468d9a8a79223b0a7/ros_gz_bridge/ros_gz_bridge/actions/ros_gz_bridge.py#L267

    # The node internally loads itself to the specified container so no need to make it below
    gz_bridge = RosGzBridge(
        bridge_name="global_gz_bridge",
        config_file=global_gz_bridge_config_file,
        container_name="sim_env_container",
        create_own_container=str(False),
        use_composition=str(True),
        # Fixes a bug with extra bridge params, see:
        # https://github.com/gazebosim/ros_gz/pull/775

        # In addition, allows us to start a service bridge by passing
        # extra params, because services cannot yet be defined with yaml
        # although ros_gz_bridge itself supports launching them

        extra_bridge_params=[{"bridge_names": ["service_bridge", "create_bridge", "delete_bridge"],
        "bridges.service_bridge.service_name": "/world/warehouse/set_pose",
        "bridges.service_bridge.ros_type_name": "ros_gz_interfaces/srv/SetEntityPose",
        "bridges.service_bridge.gz_req_type_name": "gz.msgs.Pose",
        "bridges.service_bridge.gz_rep_type_name": "gz.msgs.Boolean",
        "bridges.service_bridge.direction": "BIDIRECTIONAL",

        "bridges.create_bridge.service_name": "/world/warehouse/create",
        "bridges.create_bridge.ros_type_name": "ros_gz_interfaces/srv/SpawnEntity",
        "bridges.create_bridge.gz_req_type_name": "gz.msgs.EntityFactory",
        "bridges.create_bridge.gz_rep_type_name": "gz.msgs.Boolean",
        "bridges.create_bridge.direction": "BIDIRECTIONAL",

        "bridges.delete_bridge.service_name": "/world/warehouse/remove",
        "bridges.delete_bridge.ros_type_name": "ros_gz_interfaces/srv/DeleteEntity",
        "bridges.delete_bridge.gz_req_type_name": "gz.msgs.Entity",
        "bridges.delete_bridge.gz_rep_type_name": "gz.msgs.Boolean",
        "bridges.delete_bridge.direction": "BIDIRECTIONAL",


        }]
    )

    # Unused for now in favor of RosGzBridge- action
    # service_bridge = Node(
    #     name="service_bridge",
    #     package="ros_gz_bridge",
    #     executable="parameter_bridge",
    #     # These handle the parameters
    #     # https://github.com/gazebosim/ros_gz/blob/77522600db37d49a23e349c6e109b08caa621188/ros_gz_bridge/src/ros_gz_bridge.cpp#L36
    #     # https://github.com/gazebosim/ros_gz/blob/2b0f0a045bb232fab6aac59beeefe46bc7e082ab/ros_gz_bridge/src/bridge_config.cpp
    #     parameters=[{
    #         'config_file': global_gz_bridge_config_file
    #     } 
    #     ],
    #     # Pass the service bridge definition as plain arguments because the RosGzBridge doesnt support services
    #     # from yaml files when using the version from apt (as of 24.7.2025).
    #     # In the future, when changes are available, services can be listed in the yaml
    #     # See: https://github.com/gazebosim/ros_gz/commit/f69a10d73b3d32fdd4efaea40359a6b62a7f27b2 

    #     # This handles the arguments:
    #     # https://github.com/gazebosim/ros_gz/blob/2b0f0a045bb232fab6aac59beeefe46bc7e082ab/ros_gz_bridge/src/parameter_bridge.cpp
    #     arguments=["/world/warehouse/set_pose@ros_gz_interfaces/srv/SetEntityPose@gz.msgs.Pose@gz.msgs.Boolean"]
    # )

    # https://docs.ros.org/en/jazzy/How-To-Guides/Launching-composable-nodes.html

    # Load the the node that bridges gz->ros->mqtt into the same process
    load_composable_nodes = LoadComposableNodes(
        target_container='sim_env_container',
        composable_node_descriptions=[
            ComposableNode(
                package='mqtt_client',
                plugin='mqtt_client::MqttClient',
                name='global_mqtt_client',
                parameters=[global_mqtt_config_file],
                extra_arguments=[{'use_intra_process_comms': True}],
             ),
            ComposableNode(
                package='state_bridge',
                plugin='state_bridge::StateBridge',
                name='state_bridge_component',
                parameters=[{'use_sim_time': True}],
                extra_arguments=[{'use_intra_process_comms': True}],
            ),
        ]
    )


    set_env_vars_resources = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH', os.path.join(pkg_share, 'models'))
  
    
    # Create the launch description and populate
    ld = LaunchDescription()

    PKGS = ["forklift_cpp", "drone_cpp"]
    for pkg in PKGS:
        pkg_prefix = get_package_prefix(pkg)
        resource_path = os.path.join(pkg_prefix, 'share')
        ld.add_action(AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH', resource_path))
    
    #https://robotics.stackexchange.com/questions/98997/ros2-foxy-python-launch-argument-scope-when-nesting-launch-files
     # Declare the launch options

    ld.add_action(declare_global_mqtt_config_file)
    ld.add_action(declare_global_gz_bridge_path)
    
    ld.add_action(declare_world_cmd)
    ld.add_action(declare_map_yaml_cmd)
    ld.add_action(declare_use_rviz_cmd)
    ld.add_action(declare_autostart_cmd)
    ld.add_action(declare_rviz_config_file_cmd)
    ld.add_action(declare_use_robot_state_pub_cmd)
    ld.add_action(declare_robots_file)
    ld.add_action(declare_headless)
    ld.add_action(declare_mqtt_port)
    ld.add_action(declare_mqtt_host)
    ld.add_action(set_env_vars_resources)

    ld.add_action(simulation_container)
 
    ld.add_action(load_composable_nodes)

    #ld.add_action(gz_bridge)
    ld.add_action(gazebo_server)
    ld.add_action(gazebo_client)
    ld.add_action(start_interface)
    ld.add_action(start_headless_client)
    #ld.add_action(service_bridge)
    ld.add_action(gz_bridge)
    
    #ld.add_action(standalone_state_bridge)
    

    # Use OpaqueFunction to create robot instances after resolving the YAML path
    ld.add_action(OpaqueFunction(function=create_robot_instances))
    
    return ld