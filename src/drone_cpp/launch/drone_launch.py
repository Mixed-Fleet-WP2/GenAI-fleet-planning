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
from launch.event_handlers import OnShutdown, OnProcessExit, OnProcessIO

from launch.substitutions import (LaunchConfiguration,
    TextSubstitution,
    LocalSubstitution,
    EqualsSubstitution,
    PathJoinSubstitution,
    EnvironmentVariable
)

from launch_ros.actions import Node
from launch.events import Shutdown
from launch.events.process import ProcessExited, ProcessIO
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.descriptions import ParameterFile
from nav2_common.launch import ReplaceString, RewrittenYaml
from mf_simulation.utils.launch_utils import launch_print


def cancel_launch(event:ProcessExited, context, *args):
    
    return_code = event.returncode

    if return_code == 1:
        return EmitEvent(event=Shutdown(
            reason='PX4 installation could not be built, are you sure it is installed?'
            )
        )


def generate_launch_description():
    
    nav_launch_dir = get_package_share_directory('nav2_launch')
    pkg_share = get_package_share_directory('drone_cpp')

    use_gz = LaunchConfiguration('use_gz')
    px4_path = LaunchConfiguration('px4_path')
    px4_airframe = LaunchConfiguration('px4_airframe')
    drone_name = LaunchConfiguration('drone_name')
    namespace = LaunchConfiguration('namespace')
    use_sim_time = LaunchConfiguration('use_sim_time')
    use_namespace = LaunchConfiguration('use_namespace')
    slam = LaunchConfiguration('slam')
    nav_params_file = LaunchConfiguration('nav_params_file')
    autostart = LaunchConfiguration('autostart')
    use_composition  = LaunchConfiguration('use_composition')
    use_respawn  = LaunchConfiguration('use_respawn')
    map_yaml_file = LaunchConfiguration('map_yaml_file')
    mqtt_config_file = LaunchConfiguration('mqtt_config_file')
    robot_sdf = LaunchConfiguration('robot_sdf')

    remappings = [('/tf', 'tf'), ('/tf_static', 'tf_static')]

    declare_px4_airframe = DeclareLaunchArgument(
        name='px4_airframe',
        default_value='4001',
        description='Airframe to be used for the drone'
    )

    declare_use_gz = DeclareLaunchArgument(
        name='use_gz',
        default_value='True',
        description='Wheter to use gz sim'
    )

    declare_px4_path = DeclareLaunchArgument(
        name='px4_path',
        default_value=os.path.join(os.path.expanduser('~'), 'PX4-Autopilot'),
        description='Path to px4 installation'
    )

    declare_drone_name = DeclareLaunchArgument(
        name='drone_name',
        default_value='drone',
        description='Name for the drone and also the name PX4 binds to in the simulation'
    )

    declare_namespace = DeclareLaunchArgument(
        name='namespace',
        default_value='drone_1',
        description='Namespace for the drone'
    )

    declare_use_namespace = DeclareLaunchArgument(
        name='use_namespace',
        default_value='True',
        description="Whether to use namespace for the drone"
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
        default_value=os.path.join(pkg_share, 'config', 'drone_nav2_config.yaml'),
        description="Path to drone's nav2 param file"
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
        default_value=os.path.join(pkg_share, 'models', 'x3_urdf_convr', 'model.sdf'),
        description="Path to the robot sdf/urdf"
    )

    declare_gz_bridge_path = DeclareLaunchArgument(
        name="gz_bridge_config",
        default_value=os.path.join(pkg_share, 'config', 'drone_ros_gz_bridge.yaml'),
        description="Path to gz bridge configuration"
    )

    declare_mqtt_config_file = DeclareLaunchArgument(
        name="mqtt_config_file",
        default_value=os.path.join(pkg_share, 'config', 'drone_mqtt_bridge.yaml')
    )
 
    px4_launch_file = 'drone_cpp.px4_build'

    #If the env parameter is not given, the process use the environment
    #variables from this context
    px4_launch = ExecuteProcess(
        cmd=['python3', '-m', px4_launch_file],
        output='screen',
        shell=False,
        
        #https://github.com/ros2/launch/blob/e1d12d595f2a7af7341fd685ea53ad302ea49d60/launch/launch/conditions/launch_configuration_equals.py#L54
    )

    #https://robotics.stackexchange.com/questions/89531/how-to-exit-from-a-ros2-lifecycle-launch-script
    #https://github.com/ros2/launch/blob/a89671962220c8691ea4f128717bca599c711cda/launch/examples/launch_counters.py#L96-L98
    #https://docs.ros.org/en/galactic/Tutorials/Intermediate/Launch/Using-Event-Handlers.html
    handler = RegisterEventHandler(
        OnProcessExit(
            target_action=px4_launch,
            on_exit=lambda e, context: cancel_launch(e)
        )
    )

    mqtt_config_file = ReplaceString(
        source_file=mqtt_config_file,
        replacements={'<robot_namespace>':('/', namespace)}
    )

    
    # Get the launch directory
    bringup_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(nav_launch_dir, 'launch', 'bringup_launch.py')),
        launch_arguments={
            'namespace': namespace,
            'use_namespace': use_namespace,
            'slam': slam,
            #'map': map_yaml_file,
            'use_sim_time': use_sim_time,
            'params_file': nav_params_file,
            'autostart': autostart,
            'use_composition': use_composition,
            'use_respawn': use_respawn,
        }.items(),
    )
   
    # This command returns the parsed sdf as a string

    # How to pass arguments to xacro: 
    # https://robotics.stackexchange.com/questions/85348/pass-parameters-to-xacro-from-launch-file-or-otherwise
    parsed_sdf= Command(['xacro', ' ', robot_sdf, ' namespace:=', namespace])
    
    spawn_model = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        namespace=namespace,
        parameters=[{'use_sim_time':True}],
        arguments=[
            '-name', 'drone',
            '-string', parsed_sdf,
            '-x', TextSubstitution(text=str(3.0)), '-y', TextSubstitution(text=str(0.0)), '-z', TextSubstitution(text=str(0.0)),
            '-R', TextSubstitution(text=str(0.0)), '-P', TextSubstitution(text=str(0.0)), '-Y', TextSubstitution(text=str(0.0))
            ]
    )
    
    run_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        namespace=namespace,
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time, 'robot_description': ParameterValue(
                parsed_sdf, value_type=str)}, # This was required because the robot_state_publisher was trying to parse the string as yaml. This was a problem
            # when the file included comments
        ],
        remappings=remappings,
    )
    
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        namespace=namespace,
        parameters=[
            {
                'config_file': os.path.join(pkg_share, 'config', 'drone_ros_gz_bridge.yaml'),
                'expand_gz_topic_names': True,
                'use_sim_time': True,
            }
        ],
        output='screen',
    )

    mqtt_bridge = Node(
        package='mqtt_client',
        executable='mqtt_client',
        namespace=namespace,
        output='screen',
        parameters=[mqtt_config_file]
    )

    drone_footprint_broadcaster = Node(
        package='drone_cpp',
        executable='drone_tf_publisher',
        name='drone_broadcaster',
        namespace=namespace,
        parameters=[{'use_sim_time': True}],
        remappings=remappings
    )

    # https://robotics.stackexchange.com/questions/99879/ros2-launch-how-to-concatenate-launchconfiguration-with-string
    drone_controller = Node(
        package='drone_cpp',
        name=namespace,
        #name=[namespace, TextSubstitution(text="_node")],
        executable='drone_controller',
        parameters=[{'use_sim_time':True}],
        namespace=namespace
    )

    shutdown_handler = RegisterEventHandler(
            OnShutdown(
                on_shutdown=[LogInfo(
                    msg=['The launch had to be aborted for the following reason: ',
                        LocalSubstitution('event.reason')]
                )]
            )
        )

    # This is so package:// and model:// is resolved in sdf files
    # When urdf is converted to sdf, the package:// is replaced with model://

    # Unlike resource finder (eg. in rviz) that resolves the package:// to share/package_name
    # gazebo uses model:// like a prefix to the path
    # This is why the path must be one higher
    set_env_vars_resources = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH', os.path.join(get_package_prefix('drone_cpp'), 'share'))
    
    

    ld = LaunchDescription()
    ld.add_action(LogInfo(msg=EnvironmentVariable(name='GZ_SIM_RESOURCE_PATH')))

    #ld.add_action(launch_print(os.path.join(get_package_prefix('drone_cpp'), 'share')))

    ld.add_action(declare_use_gz)
    ld.add_action(declare_px4_path)
    ld.add_action(declare_px4_airframe)
    ld.add_action(declare_drone_name)

    #https://docs.px4.io/main/en/sim_gazebo_gz/#usage-configuration-options
    ld.add_action(SetEnvironmentVariable('PX4_PATH', px4_path))
    ld.add_action(SetEnvironmentVariable('PX4_GZ_MODEL_NAME', drone_name))
    ld.add_action(SetEnvironmentVariable('PX4_SYS_AUTOSTART', px4_airframe))
    ld.add_action(SetEnvironmentVariable('PX4_GZ_STANDALONE', TextSubstitution(text='1')))

    ld.add_action(handler)
    #ld.add_action(px4_launch)
    ld.add_action(declare_robot_sdf)
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
    ld.add_action(declare_gz_bridge_path)
    
    ld.add_action(set_env_vars_resources)
 
    ld.add_action(shutdown_handler)

    ld.add_action(bridge)
    ld.add_action(mqtt_bridge)
    ld.add_action(drone_controller)

    ld.add_action(bringup_cmd)

    ld.add_action(spawn_model)
    ld.add_action(run_robot_state_publisher)
    ld.add_action(drone_footprint_broadcaster)

    return ld


#https://robotics.stackexchange.com/questions/101307/how-to-access-the-runtime-value-of-a-launchconfiguration-instance-within-custom

#https://github.com/ros2/launch/blob/e1d12d595f2a7af7341fd685ea53ad302ea49d60/launch/launch/events/process/running_process_event.py#L29

#https://github.com/ros2/launch/blob/e1d12d595f2a7af7341fd685ea53ad302ea49d60/launch/launch/events/process/process_exited.py#L22

#SHUTDOWN definition
#https://github.com/ros2/launch/blob/e1d12d595f2a7af7341fd685ea53ad302ea49d60/launch/launch/events/shutdown.py#L33


