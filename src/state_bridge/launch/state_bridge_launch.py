from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node
import os
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory, get_package_prefix
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode
from ros_gz_bridge.actions import RosGzBridge


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

    # mqtt_bridge = Node(
    #     name="global_mqtt_client",
    #     package='mqtt_client',
    #     executable='mqtt_client',
    #     output='screen',
    #     parameters=[mqtt_config_file]
    # )

    state_bridge = Node(
        package='state_bridge',
        executable='state_bridge',
        output='screen'
    )

    gz_bridge1 = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name="globall_gz_bridge",
        parameters=[
            {
                'config_file': gz_bridge_config_file,
                'expand_gz_topic_names': True,
                'use_sim_time': True,
            }
        ],
        output='screen',
    )

    ros_gz_bridge_action = RosGzBridge(
        bridge_name="test_bridge",
        config_file=gz_bridge_config_file,
        container_name="sim_env_container",
        create_own_container=str(False),
        use_composition=str(True)
        #bridge_params=LaunchConfiguration('bridge_params'),
    )


    mqtt_bridge = ComposableNode(
        package="mqtt_client",
        plugin="mqtt_client::MqttClient",
        name="global_mqtt_client",
        parameters=[mqtt_config_file],
    )

    gz_bridge = ComposableNode(
        package="ros_gz_bridge",
        plugin="ros_gz_bridge::RosGzBridge",
        name="global_gz_bridge",
        parameters=[
            {
                'config_file': gz_bridge_config_file,
                'expand_gz_topic_names': True,
                'use_sim_time': True,
            }
        ],
    )
    # https://github.com/gazebosim/ros_gz/pull/528
    # https://github.com/gazebosim/ros_gz/blob/bba6783a85955e2719a0d11468d9a8a79223b0a7/ros_gz_bridge/ros_gz_bridge/actions/ros_gz_bridge.py#L35
    container = ComposableNodeContainer(
        name='sim_env_container',
        namespace='',
        package='rclcpp_components',
        executable='component_container',
        output='both',
        composable_node_descriptions= [
            mqtt_bridge,
        ],
        
    )


    ld = LaunchDescription()
    ld.add_action(declare_mqtt_config_file)
    ld.add_action(declare_gz_bridge_path)
    #ld.add_action(gz_bridge1)
    # ld.add_action(mqtt_bridge)
    ld.add_action(state_bridge)
    ld.add_action(container)
    ld.add_action(ros_gz_bridge_action)

    return ld

