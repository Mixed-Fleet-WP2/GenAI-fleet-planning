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
from launch.launch_context import LaunchContext

from launch_ros.actions import Node
from nav2_common.launch import RewrittenYaml

def rewrite_config():

    #Namespaces are added automatically by ros2
    mqtt_topics = ['move', 'pick_up', 'drop', 'ping', 'pong']

    mqtt_to_ros = []
    ros_to_mqtt = []

    for topic in mqtt_topics:
        mqtt_to_ros.append({
            "mqtt_topic": topic,
            "ros_topic": f"/{topic}"
        })

        ros_to_mqtt.append({
            "ros_topic": f"/{topic}",
            "mqtt_topic": topic
        })
    
    param_overrides = {
        'mqtt2ros': mqtt_to_ros,
        'ros2mqtt': ros_to_mqtt
    }
    print(param_overrides)
    return param_overrides

def generate_launch_description():

     # Create the launch description and populate
    ld = LaunchDescription()

    pkg_root = get_package_share_directory('forklift_controller')
    bringup_dir = get_package_share_directory('nav2_minimal_tb3_sim')

    namespace = LaunchConfiguration('namespace')
    robot_name = LaunchConfiguration('robot_name')
    robot_sdf = LaunchConfiguration('robot_sdf')
    pose = {'x': LaunchConfiguration('x_pose', default='-2.00'),
            'y': LaunchConfiguration('y_pose', default='-0.50'),
            'z': LaunchConfiguration('z_pose', default='0.01'),
            'R': LaunchConfiguration('roll', default='0.00'),
            'P': LaunchConfiguration('pitch', default='0.00'),
            'Y': LaunchConfiguration('yaw', default='0.00')}
    mqtt_config = LaunchConfiguration('mqtt_config')

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
        default_value=os.path.join(bringup_dir, 'urdf', 'gz_waffle.sdf.xacro'),
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

    """
    param_rewrites = {'ros2mqtt': {'ros_topic': '/cmd_vel', 'mqtt_topic': 'cmd_vel'}}
   
    context = LaunchContext()
    rewritten_yaml = RewrittenYaml(
        source_file=os.path.join(pkg_root, 'config', 'mqtt_params.yaml'),
        param_rewrites=param_rewrites,
        convert_types=True
    )

     # Perform the substitution to get the temporary file path
    rewritten_yaml_path = rewritten_yaml.perform(context)
    print(f"Temporary file path: {rewritten_yaml_path}")

    # Read and print the contents of the temporary file
    with open(rewritten_yaml_path, 'r') as file:
        rewritten_yaml_content = file.read()
        print(f"Rewritten YAML content:\n{rewritten_yaml_content}")

    mqtt_bridge = Node(
        package='mqtt_client',
        executable='mqtt_client',
        namespace=namespace,
        parameters=[rewritten_yaml]
    )
    """

    ld.add_action(LogInfo(msg="Spawning model"))
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
        'GZ_SIM_RESOURCE_PATH', os.path.join(bringup_dir, 'models'))
    set_env_vars_resources2 = AppendEnvironmentVariable(
            'GZ_SIM_RESOURCE_PATH',
            str(Path(os.path.join(bringup_dir)).parent.resolve()))

   
 
    ld.add_action(declare_namespace_cmd)
    ld.add_action(declare_robot_name_cmd)
    ld.add_action(declare_robot_sdf_cmd)
    ld.add_action(set_env_vars_resources)
    ld.add_action(set_env_vars_resources2)

    ld.add_action(bridge)
    #ld.add_action(mqtt_bridge)

    ld.add_action(spawn_model)
    return ld


