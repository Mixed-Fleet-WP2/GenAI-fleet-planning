# Copyright (c) 2018 Intel Corporation
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

"""
Example for spawning multiple robots in Gazebo.

This is an example on how to create a launch file for spawning multiple robots into Gazebo
and launch multiple instances of the navigation stack, each controlling one robot.
The robots co-exist on a shared environment and are controlled by independent nav stacks.
"""

import os
from pathlib import Path
import tempfile

from ament_index_python.packages import get_package_share_directory
import yaml

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
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, TextSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    # Get the launch directory
    nav_launch_dir = get_package_share_directory('nav2_launch')
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
        default_value='false',
        description='Automatically startup the stacks',
    )

    declare_rviz_config_file_cmd = DeclareLaunchArgument(
        'rviz_config',
        default_value=os.path.join(nav_launch_dir, 'rviz', 'nav2_namespaced_view.rviz'),
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

    declare_robots_file = DeclareLaunchArgument(
        'robots_file',
        default_value=os.path.join(pkg_share, 'config', 'robots_default.yaml')
    )

    #Bridge clock only once, see: https://github.com/gazebosim/ros_gz/issues/591
    bridge_clock = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{'use_sim_time':True}],
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
      )

    with open(robots_file, "r") as file:
        robots = yaml.safe_load(file)
    
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
    )

    # -s flag means server only
    gazebo_server = ExecuteProcess(
        cmd=['gz', 'sim', '-r', '-s', world],
        output='screen',
    )
   
    # Define commands for launching the navigation instances
    nav_instances_cmds = []
    for robot in robots:
        pkg = get_package_share_directory(robots["package"])
        nav2_params_file = os.path.join(pkg, 'config', robots["nav2_config"])
        launch_file = robot["launch_file"]
        start_pos = robot["starting_position"]
        start_orient = robot["starting_orientation"]

        group = GroupAction(
            [   

                IncludeLaunchDescription(
                PythonLaunchDescriptionSource(os.path.join(nav_launch_dir, "launch", "rviz_launch.py")),
                condition=IfCondition(use_rviz),
            launch_arguments={
                'namespace': robot,
                'use_sim_time':'True',
                'use_namespace': 'True',
                'rviz_config': rviz_config_file,
            }.items(),
                ),
                
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource(
                        os.path.join(pkg, 'launch', launch_file)
                    ),
                    launch_arguments={
                        'namespace': robot['name'],
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
                        'robot_name': TextSubstitution(text=robot["name"]),
                    }.items(),
                )
            ]
        )

        nav_instances_cmds.append(group)

    set_env_vars_resources = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH', os.path.join(pkg_share, 'models'))

    # Create the launch description and populate
    ld = LaunchDescription()

    ld.add_action(gazebo_server)
    ld.add_action(gazebo_client)

    ld.add_action(set_env_vars_resources)

    # Declare the launch options
    ld.add_action(declare_world_cmd)
    ld.add_action(declare_map_yaml_cmd)
    ld.add_action(declare_use_rviz_cmd)
    ld.add_action(declare_autostart_cmd)
    ld.add_action(declare_rviz_config_file_cmd)
    ld.add_action(declare_use_robot_state_pub_cmd)
    ld.add_action(bridge_clock)
   
    # Add the actions to start gazebo, robots and simulations
    ld.add_action(declare_robots_file)
    

    for simulation_instance_cmd in nav_instances_cmds:
        ld.add_action(simulation_instance_cmd)

    return ld
