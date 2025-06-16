import os
from ament_index_python.packages import get_package_share_directory
import yaml
from launch.actions import (
    GroupAction,
    IncludeLaunchDescription,
    OpaqueFunction
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, TextSubstitution

def create_robot_instances(context, *args, **kwargs):
    """Function to create robot instances based on the robots YAML file"""
    
    robots_file_path = LaunchConfiguration('robots_file').perform(context)
    map_yaml_file = LaunchConfiguration('map').perform(context)
    print("THIS IS THE MAP", map_yaml_file, flush=True)
    autostart = LaunchConfiguration('autostart').perform(context)
    print("AUTOSTART", autostart, flush=True)
    rviz_config_file = LaunchConfiguration('rviz_config').perform(context)
    use_rviz = LaunchConfiguration('use_rviz').perform(context)
    
    nav_launch_dir = get_package_share_directory('nav2_launch')
    
    with open(robots_file_path, "r") as file:
        robots:list[dict] = yaml.safe_load(file)["robots"]

    nav_instances_cmds = []
    
    for robot in robots:
        robot_name = robot["name"]
        robot_package = robot["package"]
        launch_file = robot["launch_file"]
        nav2_config = robot["nav2_config"]
        start_pos = robot.get("starting_position", [0.0, 0.0, 0.0])
        start_orient = robot.get("starting_orientation", [0.0, 0.0, 0.0])
        
        pkg = get_package_share_directory(robot_package)

        nav2_params_file = os.path.join(pkg, 'config', nav2_config)
        
        group = GroupAction([  
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(os.path.join(nav_launch_dir, "launch", "rviz_launch.py")),
                condition=IfCondition(use_rviz),
                launch_arguments={
                    'namespace': robot_name,
                    'use_sim_time': 'True',
                    'use_namespace': 'True',
                    'rviz_config': rviz_config_file,
                }.items(),
            ),
            
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(pkg, 'launch', launch_file)
                ),
                launch_arguments={
                    'namespace': robot_name,
                    'use_namespace': 'True',
                    'map': map_yaml_file,
                    'use_sim_time': 'True',
                    'params_file': nav2_params_file,
                    'autostart': autostart,
                    'x_pose': TextSubstitution(text=str(start_pos[0])),
                    'y_pose': TextSubstitution(text=str(start_pos[1])),
                    'z_pose': TextSubstitution(text=str(start_pos[2])),
                    'roll': TextSubstitution(text=str(start_orient[0])),
                    'pitch': TextSubstitution(text=str(start_orient[1])),
                    'yaw': TextSubstitution(text=str(start_orient[2])),
                    'robot_name': TextSubstitution(text=robot_name),
                }.items(),
            )
        ])
        nav_instances_cmds.append(group)
            
    return nav_instances_cmds

def launch_print(launch_item:LaunchConfiguration):

    return OpaqueFunction(function=lambda context: print(launch_item.perform(context)))

