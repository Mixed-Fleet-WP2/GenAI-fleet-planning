# Copyright (c) 2023 LG Electronics.
# Copyright (c) 2024 Open Navigation LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
from pathlib import Path
import tempfile

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    AppendEnvironmentVariable,
    DeclareLaunchArgument,
    ExecuteProcess,
    GroupAction,
    IncludeLaunchDescription,
    LogInfo,
    OpaqueFunction,
    RegisterEventHandler,
)
from launch.conditions import IfCondition
from launch.event_handlers import OnShutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, TextSubstitution
from nav2_common.launch import ParseMultiRobotPose
from launch_ros.actions import Node
from launch import LaunchContext
#from launch_print import launch_print
#https://stackoverflow.com/questions/57426715/import-modules-in-package-in-ros2

def launch_print(context:LaunchContext, item:LaunchConfiguration):

    item_val = item.perform(context)

    print("THE VALUE OF THE ITEM IS: ", item_val)


def generate_launch_description():
    ld = LaunchDescription()
    """
    Bring up the multi-robots with given launch arguments.

    Launch arguments consist of robot name(which is namespace) and pose for initialization.
    Keep general yaml format for pose information.
    ex) robots:='robot1={x: 0.6, y: 1.0, yaw: 1.5707, z: 0.2}; robot2={x: 0.65, y: -1.6, yaw: 1.5707, z: 0.2}'
    ex) robots:='robot3={x: 1.0, y: 1.0, z: 1.0, roll: 0.0, pitch: 1.5707, yaw: 1.5707};
                 robot4={x: 1.0, y: 1.0, z: 1.0, roll: 0.0, pitch: 1.5707, yaw: 1.5707}'
    """
    # Get the launch directory
    pkg_root = get_package_share_directory('forklift_controller')
    bringup_dir = get_package_share_directory('nav2_bringup')
    launch_dir = os.path.join(bringup_dir, 'launch')
    sim_dir = get_package_share_directory('nav2_minimal_tb4_sim')
    urdf_path = os.path.join(pkg_root, 'urdf', 'robot.urdf.xacro')

    # Simulation settings
    world = LaunchConfiguration('world')

    # On this example all robots are launched with the same settings
    map_yaml_file = LaunchConfiguration('map')
    params_file = LaunchConfiguration('params_file')
    autostart = LaunchConfiguration('autostart')
    slam = LaunchConfiguration('slam')
    rviz_config_file = LaunchConfiguration('rviz_config')
    use_robot_state_pub = LaunchConfiguration('use_robot_state_pub')
    use_rviz = LaunchConfiguration('use_rviz')

    gui_script_path = 'gui/GUI.py'
    # Set the path to different files and folders.  

    gui_path = os.path.join(pkg_root, gui_script_path)
 
    # Declare the launch arguments
    declare_world_cmd = DeclareLaunchArgument(
        'world',
        #default_value=os.path.join(pkg_root, 'worlds', 'depot.sdf'),
        default_value=os.path.join(sim_dir, 'worlds', 'depot.sdf'),
        description='Full path to world file to load',
    )

    declare_map_yaml_cmd = DeclareLaunchArgument(
        'map',
        default_value=os.path.join(bringup_dir, 'maps', 'depot.yaml'),
        description='Full path to map file to load',
    )

    declare_params_file_cmd = DeclareLaunchArgument(
        'params_file',
        default_value=os.path.join(
            pkg_root, 'config', 'nav2_config.yaml'
        ),
        description='Full path to the ROS2 parameters file to use for all launched nodes',
    )

    declare_autostart_cmd = DeclareLaunchArgument(
        'autostart',
        default_value='true',
        description='Automatically startup the stacks',
    )

    declare_slam_cmd = DeclareLaunchArgument(
        'slam',
        default_value='False',
        description='Wheter to use slam',
    )

    declare_rviz_config_file_cmd = DeclareLaunchArgument(
        'rviz_config',
        default_value=os.path.join(bringup_dir, 'rviz', 'nav2_namespaced_view.rviz'),
        description='Full path to the RVIZ config file to use.',
    )

    declare_use_robot_state_pub_cmd = DeclareLaunchArgument(
        'use_robot_state_pub',
        default_value='True',
        description='Whether to start the robot state publisher',
    )

    declare_use_rviz_cmd = DeclareLaunchArgument(
        'use_rviz', default_value='False', description='Whether to start RVIZ'
    )

    declare_mqtt_config = DeclareLaunchArgument(
        'mqtt_config',
        default_value=os.path.join(pkg_root, 'config', 'forklift_mqtt_bridge.yaml'),
        description="Config file for the mqtt client"
    )

    # The SDF file for the world is a xacro file because we wanted to
    # conditionally load the SceneBroadcaster plugin based on wheter we're
    # running in headless mode. But currently, the Gazebo command line doesn't
    # take SDF strings for worlds, so the output of xacro needs to be saved into
    # a temporary file and passed to Gazebo.
    world_sdf = tempfile.mktemp(prefix='nav2_', suffix='.sdf')
    world_sdf_xacro = ExecuteProcess(
        cmd=['xacro', '-o', world_sdf, ['headless:=', 'false'], world])
    
    gazebo_server = ExecuteProcess(
        cmd=['gz', 'sim', '-r', '-s', world_sdf],
        output='screen'
    )

    remove_temp_sdf_file = RegisterEventHandler(event_handler=OnShutdown(
        on_shutdown=[
            OpaqueFunction(function=lambda _: os.remove(world_sdf))
        ]))

    gazebo_client = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('ros_gz_sim'),
                         'launch',
                         'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': ['-v4 -g ']}.items(),
    )

    #Bridge clock only once, see: https://github.com/gazebosim/ros_gz/issues/591
    bridge_clock = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{'use_sim_time':True}],
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
      )

    bridge_cube_pose = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{'use_sim_time':True}],
        arguments=['/model/cube/pose@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V'],
    )

    launch_gui_cmd = ExecuteProcess(
        cmd=['python3', gui_path],
        output='screen'
    )

    
    #robots_list = ParseMultiRobotPose('robots').value()
    robots_list = {
        'forklift_1': {'x': 0.0, 'y': 0.0, 'z': 0.3}
        }
    #'forklift_2': {'x': -3.0, 'y': -1.6, 'z': 0.2}
    
    # Define commands for launching the navigation instances
    bringup_cmd_group = []
    for robot_name in robots_list:
        init_pose = robots_list[robot_name]
        group = GroupAction(
            [
                LogInfo(
                    msg=[
                        'Launching namespace=',
                        robot_name,
                        ' init_pose=',
                        str(init_pose),
                    ]
                ),
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource(
                        os.path.join(launch_dir, 'rviz_launch.py')
                    ),
                    condition=IfCondition(use_rviz),
                    launch_arguments={
                        'namespace': TextSubstitution(text=robot_name),
                        'use_namespace': 'True',
                        'rviz_config': rviz_config_file,
                    }.items(),
                ),
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource(
                        os.path.join(pkg_root, 'launch', 'forklift_simulation_launch.py')
                    ),
                    launch_arguments={
                        'namespace': robot_name,
                        'use_namespace': 'True',
                        'map': map_yaml_file,
                        'use_sim_time': 'True',
                        'params_file': params_file,
                        'autostart': autostart,
                        'use_rviz': 'True',
                        'use_simulator': 'False', #Set this to false because we only want to launch one simulation instance
                        'headless': 'True', #Set this to True for the same reasons as above
                        'use_robot_state_pub': use_robot_state_pub,
                        'x_pose': TextSubstitution(text=str(init_pose['x'])),
                        'y_pose': TextSubstitution(text=str(init_pose['y'])),
                        'z_pose': TextSubstitution(text=str(init_pose['z'])),
                        'roll': TextSubstitution(text=str(0.0)),
                        'pitch': TextSubstitution(text=str(0.0)),
                        'yaw': TextSubstitution(text=str(0.0)),
                        'robot_name': TextSubstitution(text=robot_name),
                        'robot_sdf': urdf_path,
                        'slam' : slam,
                        'mqtt_config': LaunchConfiguration('mqtt_config')
                    }.items(),
                ),
            ]
        )

        bringup_cmd_group.append(group)

    
    set_env_vars_resources = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH', os.path.abspath(os.path.join(pkg_root, '..')))
    set_env_vars_resources2 = AppendEnvironmentVariable(
            'GZ_SIM_RESOURCE_PATH',
            str(Path(os.path.join(sim_dir)).parent.resolve()))
    
    # Create the launch description and populate
    ld.add_action(set_env_vars_resources)
    ld.add_action(set_env_vars_resources2)
    #ld.add_action(LogInfo(msg=['GZ_SIM_RESOURCE_PATH=', os.path.abspath(os.path.join(pkg_root, '..'))]))

    # Declare the launch options
    ld.add_action(declare_world_cmd)
    ld.add_action(declare_map_yaml_cmd)
    ld.add_action(declare_params_file_cmd)
    ld.add_action(declare_use_rviz_cmd)
    ld.add_action(declare_autostart_cmd)
    ld.add_action(declare_rviz_config_file_cmd)
    ld.add_action(declare_use_robot_state_pub_cmd)
    ld.add_action(declare_slam_cmd)
    ld.add_action(bridge_clock)

    # Add the actions to start gazebo, robots and simulations
    ld.add_action(world_sdf_xacro)
    ld.add_action(gazebo_client)
    ld.add_action(gazebo_server)
    ld.add_action(remove_temp_sdf_file)

    ld.add_action(declare_mqtt_config)
    ld.add_action(bridge_cube_pose)

    ld.add_action(OpaqueFunction(function=launch_print, args=[params_file]))

    for cmd in bringup_cmd_group:
        ld.add_action(cmd)
    
    ld.add_action(launch_gui_cmd)

    return ld
