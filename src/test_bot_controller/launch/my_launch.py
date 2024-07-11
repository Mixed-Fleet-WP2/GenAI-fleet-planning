import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    # Specify the name of the package and path to URDF file within the package
    pkg_name = 'test_bot_controller'
    file_subpath = 'urdf/test.urdf'

    # Read the URDF file
    urdf_file = os.path.join(get_package_share_directory(pkg_name), file_subpath)
    with open(urdf_file, 'r') as infp:
        robot_description_raw = infp.read()

    # Configure the node
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description_raw}]  # add other parameters here if required
    ),
    node_robot_state_publisher = Node(
        package='test_bot_controller',
        executable='forklift',
        output='screen',
        parameters=[]  # add other parameters here if required
    )

    # Run the node
    return LaunchDescription([
        node_robot_state_publisher
    ])
