# Copyright (C) 2023 Open Source Robotics Foundation
# Copyright (C) 2024 Open Navigation LLC
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


from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import AppendEnvironmentVariable, LogInfo
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch.substitutions.command import Command
from launch.substitutions.find_executable import FindExecutable
from launch_ros.actions import Node
from launch.actions import OpaqueFunction

def print_path(context, *args, **kwargs):

    mqtt_file = LaunchConfiguration('mqtt_config').perform(context)
    print("HERE IT IS")
    print(f"The mqtt_config is: {mqtt_file}")



def generate_launch_description():

     # Create the launch description and populate
    ld = LaunchDescription()

    pkg_root = get_package_share_directory('forklift_controller')

    namespace = LaunchConfiguration('namespace')
    robot_name = LaunchConfiguration('robot_name')
    robot_sdf = LaunchConfiguration('robot_sdf')
    pose = {'x': LaunchConfiguration('x_pose', default='-2.00'),
            'y': LaunchConfiguration('y_pose', default='-0.50'),
            'z': LaunchConfiguration('z_pose', default='0.01'),
            'R': LaunchConfiguration('roll', default='0.00'),
            'P': LaunchConfiguration('pitch', default='0.00'),
            'Y': LaunchConfiguration('yaw', default='0.00')}
    
    declare_mqtt_config = DeclareLaunchArgument(
        'mqtt_config',
        default_value=os.path.join(pkg_root, 'config', 'mqtt_params.yaml'),
        description="Config file for the mqtt client"
    )

    # Declare the launch arguments
    declare_namespace_cmd = DeclareLaunchArgument(
        'namespace',
        default_value='',
        description='Top-level namespace')

    declare_robot_name_cmd = DeclareLaunchArgument(
        'robot_name',
        default_value='turtlebot3_waffle',
        description='name of the robot')

    declare_robot_sdf_cmd = DeclareLaunchArgument(
        'robot_sdf',
        default_value=os.path.join(pkg_root, 'urdf', 'robot.urdf.xacro'),
        description='Full path to robot sdf file to spawn the robot in gazebo')
    
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        namespace=namespace,
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

    mqtt_bridge = Node(
        package='mqtt_client',
        executable='mqtt_client',
        namespace=namespace,
        output='screen',
        parameters=[LaunchConfiguration('mqtt_config')
        ]
        
    )

    spawn_model = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        namespace=namespace,
        arguments=[
            '-name', robot_name,
            '-string', Command([
                FindExecutable(name='xacro'), ' ', 'namespace:=',
                LaunchConfiguration('namespace'), ' ', robot_sdf]),
            '-x', pose['x'], '-y', pose['y'], '-z', pose['z'],
            '-R', pose['R'], '-P', pose['P'], '-Y', pose['Y']]
    )

    set_env_vars_resources = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH', os.path.join(pkg_root, 'meshes'))
    
    ld.add_action(LogInfo(msg=f"The path is: {os.path.join(pkg_root, 'meshes')}"))

    ld.add_action(declare_namespace_cmd)
    ld.add_action(declare_robot_name_cmd)
    ld.add_action(declare_robot_sdf_cmd)
    ld.add_action(set_env_vars_resources)
 
    ld.add_action(bridge)
    ld.add_action(mqtt_bridge)

    ld.add_action(spawn_model)
    print_func = OpaqueFunction(function=print_path)
    ld.add_action(print_func)
    return ld


