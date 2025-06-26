import os
from ament_index_python.packages import get_package_share_directory, get_package_prefix, get_packages_with_prefixes
from launch import LaunchDescription
from launch.actions import (
    AppendEnvironmentVariable,
    DeclareLaunchArgument,
    ExecuteProcess,
    LogInfo,
    OpaqueFunction,
    GroupAction,
    IncludeLaunchDescription
)
from launch.substitutions import LaunchConfiguration, EnvironmentVariable, PathJoinSubstitution
from launch_ros.actions import Node, LoadComposableNodes
from mf_simulation.utils.launch_utils import create_robot_instances, launch_print
from launch.launch_description_sources import get_launch_description_from_python_launch_file, PythonLaunchDescriptionSource
from ros_gz_bridge.actions import RosGzBridge
from ros_gz_sim.actions import GzServer
from launch_ros.descriptions import ComposableNode


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
    
    # Declare the launch arguments
    declare_world_cmd = DeclareLaunchArgument(
        'world',
        default_value=os.path.join(pkg_share, 'worlds', 'warehouse.sdf'),
        description='Full path to world file to load',
    )
    
    declare_map_yaml_cmd = DeclareLaunchArgument(
        'map',
        default_value=os.path.join(nav_launch_dir, 'maps', 'warehouse.yaml'),
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
        default_value=os.path.join(pkg_share, 'config', 'state_bridge_mqtt_bridge.yaml')
    )

    declare_global_gz_bridge_path = DeclareLaunchArgument(
        name="gz_bridge_config",
        default_value=os.path.join(pkg_share, 'config', 'state_bridge_ros_gz_bridge.yaml'),
        description="Path to gz bridge configuration"
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

    interface_path = get_package_prefix('mf_simulation') + '/lib/python3.12/site-packages/mf_simulation/interface/interface.py'

    start_interface = ExecuteProcess(
        cmd=['python3', interface_path],
        name='mf_simulation_interface',
        output='screen',
        shell=False,
    )

    
    # # -s flag means server only
    # gazebo_server = ExecuteProcess(
    #     cmd=['gz', 'sim', '-r', '-s', world],
    #     output='screen',
    # )

    simulation_container = Node(
        name='sim_env_container',
        package='rclcpp_components',
        executable='component_container',
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
        use_composition=str(True)
    )

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
                name='state_bridge_exec',
                parameters=[{'use_sim_time': True}],
                extra_arguments=[{'use_intra_process_comms': True}],
            ),
        ]
    )

    set_env_vars_resources = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH', os.path.join(pkg_share, 'models'))
  

    pkgs = get_packages_with_prefixes()
    
    # Create the launch description and populate
    ld = LaunchDescription()

    for pkg in pkgs:
        pkg_prefix = pkgs[pkg]
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
    ld.add_action(set_env_vars_resources)

    ld.add_action(simulation_container)

    # Add Gazebo processes
    #ld.add_action(state_bridge)

    ld.add_action(load_composable_nodes)

    ld.add_action(gz_bridge)
    ld.add_action(gazebo_server)
    ld.add_action(gazebo_client)
    ld.add_action(start_interface)
    

    # Use OpaqueFunction to create robot instances after resolving the YAML path
    ld.add_action(OpaqueFunction(function=create_robot_instances))
    
    return ld