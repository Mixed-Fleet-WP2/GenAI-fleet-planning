from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node
import os
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory, get_package_prefix

def generate_launch_description():

    pkg_share = get_package_share_directory('state_bridge')

    mqtt_config_file = LaunchConfiguration('mqtt_config_file')
    gz_bridge_config_file = LaunchConfiguration('gz_bridge_config')


    declare_mqtt_config_file = DeclareLaunchArgument(
        name="mqtt_config_file",
        default_value=os.path.join(pkg_share, 'config', 'state_bridge_mqtt_bridge.yaml')
    )

    declare_gz_bridge_path = DeclareLaunchArgument(
        name="gz_bridge_config",
        default_value=os.path.join(pkg_share, 'config', 'state_bridge_ros_gz_bridge.yaml'),
        description="Path to gz bridge configuration"
    )

    mqtt_bridge = Node(
        name="global_mqtt_client",
        package='mqtt_client',
        executable='mqtt_client',
        output='screen',
        parameters=[mqtt_config_file]
    )

    state_bridge = Node(
        package='state_bridge',
        executable='state_bridge',
        output='screen'
    )

    gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name="global_gz_bridge",
        parameters=[
            {
                'config_file': gz_bridge_config_file,
                'expand_gz_topic_names': True,
                'use_sim_time': True,
            }
        ],
        output='screen',
    )


    ld = LaunchDescription()
    ld.add_action(declare_mqtt_config_file)
    ld.add_action(declare_gz_bridge_path)
    ld.add_action(gz_bridge)
    ld.add_action(mqtt_bridge)
    ld.add_action(state_bridge)

    return ld

