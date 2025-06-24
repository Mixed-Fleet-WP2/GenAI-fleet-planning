from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node
import os
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory, get_package_prefix

def generate_launch_description():

    pkg_share = get_package_share_directory('state_bridge')

    mqtt_config_file = LaunchConfiguration('mqtt_config_file')


    declare_mqtt_config_file = DeclareLaunchArgument(
        name="mqtt_config_file",
        default_value=os.path.join(pkg_share, 'config', 'state_bridge_mqtt_bridge.yaml')
    )

    mqtt_bridge = Node(
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

    ld = LaunchDescription()
    ld.add_action(declare_mqtt_config_file)
    ld.add_action(mqtt_bridge)
    ld.add_action(state_bridge)


