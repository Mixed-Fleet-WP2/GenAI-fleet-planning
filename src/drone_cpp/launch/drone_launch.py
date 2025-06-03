import os

from ament_index_python.packages import get_package_share_directory
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

from launch.event_handlers import OnShutdown, OnProcessExit, OnProcessIO

from launch.substitutions import (LaunchConfiguration,
    TextSubstitution,
    LocalSubstitution,
    EqualsSubstitution
)

from launch_ros.actions import Node
from launch.events import Shutdown
from launch.events.process import ProcessExited, ProcessIO
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource

def cancel_launch(event:ProcessExited, *args):
    
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
        default_value='',
        description='Namespace for the drone'
    )

    declare_use_namespace = DeclareLaunchArgument(
        name='use_namespace',
        default_value='False',
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
        default_value=os.path.join(pkg_share, 'config', 'nav2_config.yaml'),
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
            on_exit=cancel_launch
        )
    )

    # Get the launch directory
    #robot_sdf = os.path.join(pkg_share, 'models', 'x500_lidar_2d', 'model.sdf')
    robot_sdf = os.path.join(pkg_share, 'models', 'x3', 'model.sdf')
    bringup_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(nav_launch_dir, 'launch', 'bringup_launch.py')),
        launch_arguments={
            'namespace': namespace,
            'use_namespace': use_namespace,
            'slam': slam,
            'map': map_yaml_file,
            'use_sim_time': use_sim_time,
            'params_file': nav_params_file,
            'autostart': autostart,
            'use_composition': use_composition,
            'use_respawn': use_respawn,
        }.items(),
    )
   
    # At the moment there is a bug where processes started with shell=True are not shut down by launch
    # this is why the launch file from ros_gz_sim package is not used

    # See: https://github.com/ros2/launch/issues/757
    # and https://github.com/ros2/launch/issues/545
    gazebo_client = ExecuteProcess(
            #cmd=['gz','sim','-v4', '-g', '--force-version', '8', '--render-engine', 'ogre'],
            cmd=['gz','sim','-v4', '-g', '--force-version', '8'],
            name='gazebo',
            output='screen',
            shell=False,
            condition=IfCondition(EqualsSubstitution(use_gz, True))
        )

    world = os.path.join(pkg_share, 'worlds', 'default.sdf')
    
    # -s flag means server only
    gazebo_server = ExecuteProcess(
        cmd=['gz', 'sim', '-r', '-s', world],
        output='screen',
        condition=IfCondition(EqualsSubstitution(use_gz, True))
    )

    spawn_model = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        namespace='',
        parameters=[{'use_sim_time':True}],
        arguments=[
            '-name', 'drone',
            '-file', robot_sdf,
            '-x', TextSubstitution(text=str(2.0)), '-y', TextSubstitution(text=str(0.0)), '-z', TextSubstitution(text=str(0.0)),
            '-R', TextSubstitution(text=str(0.0)), '-P', TextSubstitution(text=str(0.0)), '-Y', TextSubstitution(text=str(0.0))
            ]
    )

    drone_controller = Node(
        package='drone_cpp',
        executable='drone_node',
        parameters=[{'use_sim_time':True}],
        namespace=''
    )

    shutdown_handler = RegisterEventHandler(
            OnShutdown(
                on_shutdown=[LogInfo(
                    msg=['The launch had to be aborted for the following reason: ',
                        LocalSubstitution('event.reason')]
                )]
            )
        )

    #This points to /forklift_sim/install/forklift_controller/share/
    #Because we go up one directory to get to the share directory
    set_env_vars_resources = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH', os.path.abspath(os.path.join(pkg_share, '..')))
    
    set_env_vars_resources2 = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH', os.path.join(pkg_share, 'models'))
    
    

    ld = LaunchDescription()


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
    ld.add_action(declare_namespace)
    ld.add_action(declare_use_sim_time)
    ld.add_action(declare_use_namespace)
    ld.add_action(declare_slam)
    ld.add_action(declare_nav_params_file)
    ld.add_action(declare_autostart)
    ld.add_action(declare_use_composition)
    ld.add_action(declare_use_respawn)
    ld.add_action(declare_map_yaml_file)
    

    ld.add_action(set_env_vars_resources)
    ld.add_action(set_env_vars_resources2)
    ld.add_action(gazebo_server)
    ld.add_action(gazebo_client)
    ld.add_action(spawn_model)
    ld.add_action(shutdown_handler)
    #ld.add_action(drone_controller)

    #ld.add_action(bringup_cmd)




    return ld


#https://robotics.stackexchange.com/questions/101307/how-to-access-the-runtime-value-of-a-launchconfiguration-instance-within-custom

#https://github.com/ros2/launch/blob/e1d12d595f2a7af7341fd685ea53ad302ea49d60/launch/launch/events/process/running_process_event.py#L29

#https://github.com/ros2/launch/blob/e1d12d595f2a7af7341fd685ea53ad302ea49d60/launch/launch/events/process/process_exited.py#L22

#SHUTDOWN definition
#https://github.com/ros2/launch/blob/e1d12d595f2a7af7341fd685ea53ad302ea49d60/launch/launch/events/shutdown.py#L33


