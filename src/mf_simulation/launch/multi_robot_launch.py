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
    OpaqueFunction,
)
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from mf_simulation.launch_utils.utils import create_robot_instances

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
    
    # Bridge clock only once, see: https://github.com/gazebosim/ros_gz/issues/591
    bridge_clock = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{'use_sim_time': True}],
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
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
    
    # -s flag means server only
    gazebo_server = ExecuteProcess(
        cmd=['gz', 'sim', '-r', '-s', world],
        output='screen',
    )
    
    set_env_vars_resources = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH', os.path.join(pkg_share, 'models'))
    
    # Create the launch description and populate
    ld = LaunchDescription()
    
     # Declare the launch options
    ld.add_action(declare_world_cmd)
    ld.add_action(declare_map_yaml_cmd)
    ld.add_action(declare_use_rviz_cmd)
    ld.add_action(declare_autostart_cmd)
    ld.add_action(declare_rviz_config_file_cmd)
    ld.add_action(declare_use_robot_state_pub_cmd)
    ld.add_action(declare_robots_file)
    ld.add_action(set_env_vars_resources)

    # Add Gazebo processes
    ld.add_action(gazebo_server)
    ld.add_action(gazebo_client)
    
    ld.add_action(bridge_clock)
    
   
    
    # Use OpaqueFunction to create robot instances after resolving the YAML path
    ld.add_action(OpaqueFunction(function=create_robot_instances))
    
    return ld