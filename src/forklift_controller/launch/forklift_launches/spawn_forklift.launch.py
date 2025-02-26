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
from launch.actions import OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnShutdown
from nav2_common.launch import RewrittenYaml
import tempfile

import yaml

def add_namespace(context, yaml_file, namespace, ):

    print("THE YAML FILE IS: ", yaml_file)
    with open(yaml_file, "r") as file:
        config = yaml.safe_load(file)

    # Iterate through bridge topics and add namespace
    bridge = config["/**/*"]["ros__parameters"]["bridge"]

    ros_to_mqtt_topics = bridge["ros2mqtt"]["ros_topics"]

    #Topic names for the mqtt messages (mqtt -> ros)
    mqtt_to_ros_topics_mqtt_names = bridge["mqtt2ros"]["mqtt_topics"]
    print("THE TEMP FILE IS: ", yaml_file)

    namespaced_topics = []
    #Append namespaces to mqtt topics as that is not done by ros2 system
    for topic in mqtt_to_ros_topics_mqtt_names:
        namespaced_topics.append(f"{namespace}/{topic}") 

    bridge["mqtt2ros"]["mqtt_topics"] = namespaced_topics

    with open(f"modified_{yaml_file}", "w") as file:
        yaml.dump(config, file, default_flow_style=False)

    mqtt_bridge = Node(
        package='mqtt_client',
        executable='mqtt_client',
        namespace=namespace,
        output='screen',
        parameters=[yaml_file]
        
    )

    return mqtt_bridge

def generate_launch_description():

     # Create the launch description and populate
    ld = LaunchDescription()

    pkg_root = get_package_share_directory('forklift_controller')

    test_path = os.path.join(pkg_root, 'config', 'test.yaml')

    namespace = LaunchConfiguration('namespace')
    mqtt_config = LaunchConfiguration('mqtt_config')
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

    set_env_vars_resources = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH', os.path.join(pkg_root, 'meshes'))
    
    #ld.add_action(OpaqueFunction(function=add_namespace, args=[namespace, test_path]))

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

    ld.add_action(declare_namespace_cmd)
    ld.add_action(declare_robot_name_cmd)
    ld.add_action(declare_robot_sdf_cmd)
    ld.add_action(set_env_vars_resources)
 
    ld.add_action(bridge)

    ld.add_action(spawn_model)

   
    return ld


