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

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import AppendEnvironmentVariable, LogInfo
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, TextSubstitution
from launch.substitutions.command import Command
from launch.substitutions.find_executable import FindExecutable
from launch_ros.actions import Node
from launch.actions import OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnShutdown
from tempfile import NamedTemporaryFile, _TemporaryFileWrapper

import yaml

"""
Add a namespace to a mqtt config file. This is necessary because only the messages from the ros2 side are namespaced
and the mqtt messages are not. This function adds the namespace to the mqtt messages so that the mqtt client node
can subscribe to the correct topics.

param context: The context of the launch file
param namespace: The namespace to add to the mqtt config file
param base_file: The base mqtt config file to add the namespace to
param temp_file: A temporary file to write the namespaced topics to and pass to the mqtt client node

returns: A list containing the mqtt client node

Example of the structure of the base_file:

/**/*:
  ros__parameters:
    broker:
      host: localhost
      port: 1883
    bridge:
      ros2mqtt:
        ros_topics: 
          - feedback
          - /pingpong/ros
        /feedback:
          mqtt_topic: feedback
        /pingpong/ros:
          mqtt_topic: pingpong/ros
      mqtt2ros:
        mqtt_topics: 
          - move
          - drop
          - pick_up
          - ping/ros
        move:
          ros_topic: move
          ros_type: std_msgs/msg/Float32MultiArray
          primitive: true
        drop:
          ros_topic: drop
          ros_type: std_msgs/msg/String
          primitive: true
        pick_up:
          ros_topic: pick_up
          ros_type: std_msgs/msg/String
          primitive: true
        ping/ros:
          ros_topic: ping/ros
          primitive: true
"""

def add_namespace(context, namespace:LaunchConfiguration, base_file: LaunchConfiguration, temp_file: _TemporaryFileWrapper) -> list:

    try:

        yaml_file_path = base_file.perform(context)
        namespace = namespace.perform(context)
        #Temporary file is created in the create_launch_description function, only name is passed
        temp_file_name:str = temp_file.name

        with open(yaml_file_path, "r") as file:
            config = yaml.safe_load(file)

        # Iterate through bridge topics and add namespace
        bridge = config["/**/*"]["ros__parameters"]["bridge"]

        #Topic names for the mqtt messages (mqtt -> ros)
        mqtt_to_ros = bridge["mqtt2ros"]

        #Namespace the mqtt messages as ros2 system does not do this automatically
        for topic in list(mqtt_to_ros):
            
            if topic == "mqtt_topics":
                namespaced_topics = []
                topics = mqtt_to_ros["mqtt_topics"]
                for topic_mqtt in topics:
                    namespaced_topics.append(f"{namespace}/{topic_mqtt}") 
                mqtt_to_ros["mqtt_topics"] = namespaced_topics
            else:
                mqtt_to_ros[f"{namespace}/{topic}"] = mqtt_to_ros[topic]
                del mqtt_to_ros[topic]
            

        #Write namespaced topics to a temp file
        with open(temp_file.name, "w") as file:
            yaml.dump(config, file, default_flow_style=False)
        
        mqtt_bridge = Node(
            package='mqtt_client',
            executable='mqtt_client',
            namespace=namespace,
            output='screen',
            parameters=[temp_file_name]
            
        )
    except Exception as e:
        print("Error in add_namespace: ", e)
        return []
       
    return [mqtt_bridge]

def generate_launch_description():

     # Create the launch description and populate
    ld = LaunchDescription()

    pkg_root = get_package_share_directory('forklift_controller')

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
        default_value=os.path.join(pkg_root, 'config', 'forklift_mqtt_bridge.yaml'),
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
    
    mqtt_config_temp_file:_TemporaryFileWrapper = NamedTemporaryFile(mode='w+t', delete=False, suffix='.yaml')

    # Remove the temporary file when the launch file is shutdown
    remove_temp_mqtt_file = RegisterEventHandler(event_handler=OnShutdown(
        on_shutdown=[
            OpaqueFunction(function=lambda _: os.remove(mqtt_config_temp_file.name))
        ]))
    
    joint_gui = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        namespace=namespace,
        output='screen',
        parameters=[{
            'use_sim_time': True,
        }]
    )

    #ld.add_action(joint_gui)


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
            '-x', pose['x'], '-y', TextSubstitution(text="2.0"), '-z', pose['z'],
            '-R', pose['R'], '-P', pose['P'], '-Y', pose['Y']
            ]
    )

    ld.add_action(OpaqueFunction(function=add_namespace, args=[namespace, mqtt_config, mqtt_config_temp_file]))
    ld.add_action(declare_namespace_cmd)
    ld.add_action(declare_robot_name_cmd)
    ld.add_action(declare_robot_sdf_cmd)
    ld.add_action(declare_mqtt_config)
    ld.add_action(set_env_vars_resources)
 
    ld.add_action(bridge)
    
    ld.add_action(spawn_model)
    ld.add_action(remove_temp_mqtt_file)

   
    return ld


