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
    SetEnvironmentVariable
)

from launch.event_handlers import OnShutdown, OnProcessExit
from launch.substitutions import LaunchConfiguration, TextSubstitution, LocalSubstitution
from launch_ros.actions import Node
from launch.events import Shutdown
from launch.events.process import ProcessExited


def cancel_launch(event:ProcessExited, *args):
    
    return_code = event.returncode

    if return_code == 1:
        return EmitEvent(event=Shutdown(
            reason='PX4 installation could not be built, are you sure it is installed?'
            )
        )


def generate_launch_description():
   

    use_gz = LaunchConfiguration('use_gz')
    px4_path = LaunchConfiguration('px4_path')
    px4_airframe = LaunchConfiguration('px4_airframe')
    drone_name = LaunchConfiguration('drone_name')

    declare_px4_airframe = DeclareLaunchArgument(
        name='px4_airframe',
        default_value='4001',
        description='Airframe to be used for the drone'
    )


    declare_use_gz = DeclareLaunchArgument(
        name='use_gz',
        default_value='False',
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

    
    pkg_root = get_package_share_directory('forklift_controller')
    

    px4_launch_file = os.path.join(pkg_root, 'launch', 'px4_launch.py')

    #If the env parameter is not given, the process use the environment
    #variables from this context
    px4_launch = ExecuteProcess(
        cmd=['python3', px4_launch_file, use_gz],
        output='screen',
        shell=False,
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
    pkg_root = get_package_share_directory('forklift_controller')
    robot_sdf = os.path.join(pkg_root, 'models', 'x500_vision', 'model.sdf')

   
    # At the moment there is a bug where processes started with shell=True are not shut down by launch
    # this is why the launch file from ros_gz_sim package is not used

    # See: https://github.com/ros2/launch/issues/757
    # and https://github.com/ros2/launch/issues/545
    gazebo_client = ExecuteProcess(
            cmd=['gz','sim','-v4', '-g', '--force-version', '8'],
            name='gazebo',
            output='screen',
            shell=False
        )

    world = os.path.join(pkg_root, 'worlds', 'default.sdf')
    
    # -s flag means server only
    gazebo_server = ExecuteProcess(
        cmd=['gz', 'sim', '-r', '-s', world],
        output='screen'
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
            '-x', TextSubstitution(text=str(0.0)), '-y', TextSubstitution(text=str(0.0)), '-z', TextSubstitution(text=str(0.0)),
            '-R', TextSubstitution(text=str(0.0)), '-P', TextSubstitution(text=str(0.0)), '-Y', TextSubstitution(text=str(0.0))
            ]
    )

    drone_controller = Node(
        package='forklift_controller',
        executable='drone_controller',
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
        'GZ_SIM_RESOURCE_PATH', os.path.abspath(os.path.join(pkg_root, '..')))
    
    set_env_vars_resources2 = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH', os.path.join(pkg_root, 'models'))
    
    

    ld = LaunchDescription()


    ld.add_action(declare_use_gz)
    ld.add_action(declare_px4_path)
    ld.add_action(declare_px4_airframe)
    ld.add_action(declare_drone_name)

    #https://docs.px4.io/main/en/sim_gazebo_gz/#usage-configuration-options
    ld.add_action(SetEnvironmentVariable('PX4_PATH', px4_path))
    ld.add_action(SetEnvironmentVariable('PX4_GZ_MODEL', drone_name))
    ld.add_action(SetEnvironmentVariable('PX4_SYS_AUTOSTART', px4_airframe))

    ld.add_action(handler)
    ld.add_action(px4_launch)
    

    # Create the launch description and populate
    ld.add_action(set_env_vars_resources)
    ld.add_action(set_env_vars_resources2)
    ld.add_action(gazebo_server)
    ld.add_action(gazebo_client)
    ld.add_action(spawn_model)
    ld.add_action(shutdown_handler)

    ld.add_action(drone_controller)




    return ld


#https://robotics.stackexchange.com/questions/101307/how-to-access-the-runtime-value-of-a-launchconfiguration-instance-within-custom

#https://github.com/ros2/launch/blob/e1d12d595f2a7af7341fd685ea53ad302ea49d60/launch/launch/events/process/running_process_event.py#L29

#https://github.com/ros2/launch/blob/e1d12d595f2a7af7341fd685ea53ad302ea49d60/launch/launch/events/process/process_exited.py#L22

#SHUTDOWN definition
#https://github.com/ros2/launch/blob/e1d12d595f2a7af7341fd685ea53ad302ea49d60/launch/launch/events/shutdown.py#L33


