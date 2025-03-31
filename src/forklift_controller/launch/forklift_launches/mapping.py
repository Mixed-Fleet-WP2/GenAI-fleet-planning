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
from launch_ros.actions import Node
from launch.substitutions.command import Command
from launch.substitutions.find_executable import FindExecutable


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
    sim_dir = get_package_share_directory('nav2_minimal_tb3_sim')
    urdf_path = os.path.join(pkg_root, 'urdf', 'robot.urdf.xacro')

    # Simulation settings
    world = LaunchConfiguration('world')
    rviz_config_file = LaunchConfiguration('rviz_config')
    use_robot_state_pub = LaunchConfiguration('use_robot_state_pub')
    use_rviz = LaunchConfiguration('use_rviz')

    set_env_vars_resources = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH', os.path.join(pkg_root, 'models'))
    """
    set_env_vars_resources2 = AppendEnvironmentVariable(
            'GZ_SIM_RESOURCE_PATH',
            str(Path(os.path.join(sim_dir)).parent.resolve()))
    """
    ld.add_action(LogInfo(
        msg="GZ_SIM_RESOURCE_PATH: " +
        os.path.join(pkg_root, 'models')))
   
    # Create the launch description and populate
    ld.add_action(set_env_vars_resources)
    # Declare the launch arguments
    declare_world_cmd = DeclareLaunchArgument(
        'world',
        default_value=os.path.join(pkg_root, 'worlds', 'warehouse.world'),
        #default_value=os.path.join(sim_dir, 'worlds', 'tb3_sandbox.sdf.xacro'),
        description='Full path to world file to load',
    )

    declare_rviz_config_file_cmd = DeclareLaunchArgument(
        'rviz_config',
        default_value=os.path.join(bringup_dir, 'rviz', 'nav2_default_view.rviz'),
        description='Full path to the RVIZ config file to use.',
    )

    declare_use_robot_state_pub_cmd = DeclareLaunchArgument(
        'use_robot_state_pub',
        default_value='True',
        description='Whether to start the robot state publisher',
    )

    declare_use_rviz_cmd = DeclareLaunchArgument(
        'use_rviz', default_value='True', description='Whether to start RVIZ'
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

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[
            {
                'config_file': os.path.join(
                    pkg_root, 'config', 'turtlebot3_waffle_bridge.yaml'
                ),
                'expand_gz_topic_names': True,
                'use_sim_time': True,
            }
        ],
        output='screen',
    )

    #Bridge clock only once, see: https://github.com/gazebosim/ros_gz/issues/591
    bridge_clock = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{'use_sim_time':True}],
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
      )

    """
    bridge_cube_pose = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{'use_sim_time':True}],
        arguments=['/model/cube/pose@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V'],
    )
    """

    launch_rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        condition=IfCondition(use_rviz),
        parameters=[{'use_sim_time': True}],
        arguments=['-d', rviz_config_file],
    )

    parsed_urdf = Command(['xacro', ' ', urdf_path])
    
    
    start_robot_state_pub = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        condition=IfCondition(use_robot_state_pub),
        parameters=[{'use_sim_time': True, 'robot_description': parsed_urdf}],
    )

    spawn_model = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-name', 'test_bot',
            '-string', Command([FindExecutable(name='xacro'), ' ', urdf_path]),
            '-x', '0.0', '-y', '0.0', '-z', '0.0',
            '-R', '0.0', '-P', '0.0', '-Y', '0.0']
    )

    
    

    
    #ld.add_action(set_env_vars_resources2)

    # Declare the launch options
    ld.add_action(declare_world_cmd)
    ld.add_action(declare_use_rviz_cmd)
    ld.add_action(declare_rviz_config_file_cmd)
    ld.add_action(declare_use_robot_state_pub_cmd)
    ld.add_action(bridge_clock)

    # Add the actions to start gazebo, robots and simulations
    ld.add_action(world_sdf_xacro)
    ld.add_action(gazebo_client)
    ld.add_action(gazebo_server)
    ld.add_action(remove_temp_sdf_file)

    ld.add_action(launch_rviz)
    ld.add_action(start_robot_state_pub)
    ld.add_action(spawn_model)
    ld.add_action(bridge)


    #ld.add_action(bridge_cube_pose)

    return ld
