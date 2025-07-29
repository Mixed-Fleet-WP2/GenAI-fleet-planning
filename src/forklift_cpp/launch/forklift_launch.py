# type: ignore

import os

from ament_index_python.packages import get_package_share_directory, get_package_prefix
from launch import LaunchDescription
from launch.actions import (
    AppendEnvironmentVariable,
    DeclareLaunchArgument,
    ExecuteProcess,
    LogInfo,
    RegisterEventHandler,
    EmitEvent,
    SetEnvironmentVariable,
    IncludeLaunchDescription
)

from launch.substitutions.command import Command
from launch_ros.parameter_descriptions import ParameterValue
from launch.event_handlers import OnShutdown

from launch.substitutions import (LaunchConfiguration,
    TextSubstitution,
    LocalSubstitution,
    EqualsSubstitution
)

from launch_ros.actions import Node
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.descriptions import ParameterFile
from nav2_common.launch import ReplaceString, RewrittenYaml
from ros_gz_bridge.actions import RosGzBridge


def generate_launch_description():
    
    nav_launch_dir = get_package_share_directory('nav2_launch')
    pkg_share = get_package_share_directory('forklift_cpp')

    robot_name = LaunchConfiguration('robot_name')
    namespace = LaunchConfiguration('namespace')
    use_sim_time = LaunchConfiguration('use_sim_time')
    use_namespace = LaunchConfiguration('use_namespace')
    slam = LaunchConfiguration('slam')
    nav_params_file = LaunchConfiguration('nav_params_file')
    autostart = LaunchConfiguration('autostart')
    use_composition  = LaunchConfiguration('use_composition')
    use_respawn  = LaunchConfiguration('use_respawn')
    map_yaml_file = LaunchConfiguration('map_yaml_file')
    forklift_mqtt_config_file = LaunchConfiguration('forklift_mqtt_config_file')
    forklift_gz_bridge_config = LaunchConfiguration("forklift_gz_bridge_config")
    robot_sdf = LaunchConfiguration('robot_sdf')

    remappings = [('/tf', 'tf'), ('/tf_static', 'tf_static')]

    pose = {
        'x': LaunchConfiguration('x_pose'),
        'y': LaunchConfiguration('y_pose'),
        'z': LaunchConfiguration('z_pose'),
        'roll': LaunchConfiguration('roll'),
        'pitch': LaunchConfiguration('pitch'),
        'yaw': LaunchConfiguration('yaw')
    }

    
    declare_use_gz = DeclareLaunchArgument(
        name='use_gz',
        default_value='True',
        description='Wheter to use gz sim'
    )

    declare_robot_name = DeclareLaunchArgument(
        name='robot_name',
        default_value='forklift',
        description='Name for the forklift'
    )

    declare_namespace = DeclareLaunchArgument(
        name='namespace',
        default_value='',
        description='Namespace for the forklift'
    )

    declare_use_namespace = DeclareLaunchArgument(
        name='use_namespace',
        default_value='True',
        description="Whether to use namespace for the forklift"
    )

    declare_use_sim_time = DeclareLaunchArgument(
        name='use_sim_time',
        default_value='True',
        description='Whether to use simulation time'
    )

    declare_slam = DeclareLaunchArgument(
        name='slam',
        default_value='False',
        description='Whether to use slam'
    )

    declare_nav_params_file = DeclareLaunchArgument(
        name='nav_params_file',
        default_value=os.path.join(pkg_share, 'config', 'forklift_nav2_config.yaml'),
        description="Path to forklift's nav2 param file"
    )

    declare_autostart = DeclareLaunchArgument(
        name='autostart',
        default_value='True',
        description='Whether to automatically start the nav2 stack'
    )

    declare_use_composition = DeclareLaunchArgument(
        name='use_composition',
        default_value='True',
        description='Whether to compose the nav2 nodes together into a single process'
    )
    
    declare_use_respawn = DeclareLaunchArgument(
        name='use_respawn',
        default_value='True',
        description='Whether to respawn the robot'
    )

    declare_map_yaml_file = DeclareLaunchArgument(
        name='map_yaml_file',
        default_value='',
        description='Absolute path to the map yaml file'
    )

    declare_robot_sdf = DeclareLaunchArgument(
        name="robot_sdf",
        default_value=os.path.join(pkg_share, 'urdf', 'robot.urdf.xacro'),
        description="Path to the robot sdf/urdf"
    )

    declare_forklift_gz_bridge_path = DeclareLaunchArgument(
        name="forklift_gz_bridge_config",
        default_value=os.path.join(pkg_share, 'config', 'forklift_ros_gz_bridge.yaml'),
        description="Path to gz bridge configuration"
    )

    declare_mqtt_config_file = DeclareLaunchArgument(
        name="forklift_mqtt_config_file",
        default_value=os.path.join(pkg_share, 'config', 'forklift_mqtt_bridge.yaml')
    )

    forklift_mqtt_config_file = ReplaceString(
        source_file=forklift_mqtt_config_file,
        replacements={'<robot_namespace>':('/', namespace)}
    )
    
    

    bringup_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(nav_launch_dir, 'launch', 'bringup_launch.py')),
        launch_arguments={
            'namespace': namespace,
            'use_namespace': use_namespace,
            'slam': slam,
            # Use the default
            #'map': map_yaml_file,
            'use_sim_time': use_sim_time,
            'params_file': nav_params_file,
            'autostart': autostart,
            'use_composition': use_composition,
            'use_respawn': use_respawn,
            **pose
        }.items(),
    )
   
    # This command returns the parsed sdf as a string
    # How to pass arguments to xacro: 
    # https://robotics.stackexchange.com/questions/85348/pass-parameters-to-xacro-from-launch-file-or-otherwise
    parsed_urdf = Command(['xacro', ' ', robot_sdf, ' namespace:=', namespace])
    
    spawn_model = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        namespace=namespace,
        parameters=[{'use_sim_time':True}],
        arguments=[
            '-name', namespace,
            '-string', parsed_urdf,
            '-x', pose['x'], '-y', pose['y'], '-z', pose['z'],
            '-R', pose['roll'], '-P', pose['pitch'], '-Y', pose['yaw']
            ]
    )

    run_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        namespace=namespace,
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time, 'robot_description': ParameterValue(
                parsed_urdf, value_type=str)}, # This was required because the robot_state_publisher was trying to parse the string as yaml. This was a problem
            # when the file included comments
        ],
        remappings=remappings,
    )
    
    bridge= RosGzBridge(
        container_name="sim_env_container",
        bridge_name=[namespace, "_bridge"],
        namespace=namespace,
        config_file=forklift_gz_bridge_config,
  
        # Fixes a bug with extra bridge params, see:
        # https://github.com/gazebosim/ros_gz/pull/775

        extra_bridge_params=[ {
                'expand_gz_topic_names': True,
                'use_sim_time': True,
            }]
    )

    mqtt_bridge = Node(
        package='mqtt_client',
        executable='mqtt_client',
        namespace=namespace,
        output='screen',
        parameters=[forklift_mqtt_config_file]
    )

    forklift_controller = Node(
        package="forklift_cpp",
        executable="forklift_controller",
        namespace=namespace,
        name=namespace,
        output='screen',
        parameters=[{'use_sim_time':True}],
        remappings=remappings
    )

    # This is so package:// and model:// is resolved in sdf files
    # When urdf is converted to sdf, the package:// is replaced with model://

    # Unlike resource finder that resolves the package:// to share/package_name
    # gazebo uses model:// like a prefix to the path
    # This is why the path must be one higher
    set_env_vars_resources = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH', os.path.join(get_package_prefix('forklift_cpp'), 'share'))

    ld = LaunchDescription()

    ld.add_action(declare_robot_sdf)
    ld.add_action(declare_use_gz)
    ld.add_action(declare_robot_name)
    ld.add_action(declare_forklift_gz_bridge_path)
    ld.add_action(declare_namespace)
    ld.add_action(declare_use_sim_time)
    ld.add_action(declare_use_namespace)
    ld.add_action(declare_slam)
    ld.add_action(declare_nav_params_file)
    ld.add_action(declare_autostart)
    ld.add_action(declare_use_composition)
    ld.add_action(declare_use_respawn)
    ld.add_action(declare_map_yaml_file)
    ld.add_action(declare_mqtt_config_file)
    ld.add_action(run_robot_state_publisher)
    
    ld.add_action(set_env_vars_resources)

    ld.add_action(bridge)
    ld.add_action(mqtt_bridge)

    ld.add_action(bringup_cmd)
    ld.add_action(spawn_model)
    ld.add_action(forklift_controller)

    return ld





