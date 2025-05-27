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


def generate_launch_description():
    ld = LaunchDescription()
    
    # Get the launch directory
    pkg_root = get_package_share_directory('forklift_controller')
    robot_sdf = os.path.join(pkg_root, 'models', 'x500', 'model.sdf')

    #Gazebo server and client

    #-g flag means gui only
    gazebo_client = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('ros_gz_sim'),
                         'launch',
                         'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': ['-v4 -g']}.items(),
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

    #This points to /forklift_sim/install/forklift_controller/share/
    #Because we go up one directory to get to the share directory
    set_env_vars_resources = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH', os.path.abspath(os.path.join(pkg_root, '..')))
    
    set_env_vars_resources2 = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH', os.path.join(pkg_root, 'models'))

    # Create the launch description and populate
    ld.add_action(set_env_vars_resources)
    ld.add_action(set_env_vars_resources2)
    ld.add_action(gazebo_server)
    ld.add_action(gazebo_client)
    ld.add_action(spawn_model)

    return ld
