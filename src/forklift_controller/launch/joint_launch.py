import os
from launch import LaunchDescription
from launch.actions import AppendEnvironmentVariable, DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


# Constants for paths to different files and folders
#package_name_description = 'Lorem Ipsum'
package_name = 'forklift_controller'
default_robot_name = 'forklift'
gazebo_launch_file_path = 'launch'
gazebo_models_path = 'models'
ros_gz_bridge_config_file_path = 'config/ros_gz_bridge.yaml'
urdf_file_path = 'urdf/robot.urdf.xacro'
world_file_path = 'worlds/empty.world'
gui_script_path = 'gui/control.py'
# Set the path to different files and folders.  
pkg_ros_gz_sim = FindPackageShare(package='ros_gz_sim').find('ros_gz_sim')  
pkg_root = FindPackageShare(package=package_name).find(package_name)

default_ros_gz_bridge_config_file_path = os.path.join(pkg_root, ros_gz_bridge_config_file_path) 
default_urdf_model_path = os.path.join(pkg_root, urdf_file_path)
gazebo_launch_file_path = os.path.join(pkg_root, gazebo_launch_file_path)   
gazebo_models_path = os.path.join(pkg_root, gazebo_models_path)
world_path = os.path.join(pkg_root, world_file_path)
gui_path = os.path.join(pkg_root, gui_script_path)



def generate_launch_description():
 
  declare_robot_amount_cmd = DeclareLaunchArgument(
    name='robot_amount',
    default_value='2',
    description='The amount of robots to spawn')

  # Declare the launch arguments  
  declare_robot_name_cmd = DeclareLaunchArgument(
    name='robot_name',
    default_value=default_robot_name,
    description='The name for the robot')
  

  declare_simulator_cmd = DeclareLaunchArgument(
    name='headless',
    default_value='False',
    description='Display the Gazebo GUI if False, otherwise run in headless mode')
 
  declare_urdf_model_path_cmd = DeclareLaunchArgument(
    name='urdf_model', 
    default_value=default_urdf_model_path, 
    description='Absolute path to robot urdf file')
     
  declare_use_robot_state_pub_cmd = DeclareLaunchArgument(
    name='use_robot_state_pub',
    default_value='True',
    description='Whether to start the robot state publisher')
 
  declare_use_rviz_cmd = DeclareLaunchArgument(
    name='use_rviz',
    default_value='False',
    description='Whether to start RVIZ')
  
  declare_use_sim_time_cmd = DeclareLaunchArgument(
    name='use_sim_time',
    default_value='False',
    description='Use simulation (Gazebo) clock if true')
 
  declare_use_simulator_cmd = DeclareLaunchArgument(
    name='use_simulator',
    default_value='True',
    description='Whether to start Gazebo')
 
  declare_world_cmd = DeclareLaunchArgument(
    name='world',
    default_value=world_path,
    description='Full path to the world model file to load')
 
  declare_x_cmd = DeclareLaunchArgument(
    name='x',
    default_value='0.0',
    description='x component of initial position, meters')
 
  declare_y_cmd = DeclareLaunchArgument(
    name='y',
    default_value='0.0',
    description='y component of initial position, meters')
     
  declare_z_cmd = DeclareLaunchArgument(
    name='z',
    default_value='0.01',
    description='z component of initial position, meters')
     
  declare_roll_cmd = DeclareLaunchArgument(
    name='roll',
    default_value='0.0',
    description='roll angle of initial orientation, radians')
 
  declare_pitch_cmd = DeclareLaunchArgument(
    name='pitch',
    default_value='0.0',
    description='pitch angle of initial orientation, radians')
 
  declare_yaw_cmd = DeclareLaunchArgument(
    name='yaw',
    default_value='0.0',
    description='yaw angle of initial orientation, radians')

  #Create the variables for holding the values of given cmd line arguments
  
  #LaunchConfiguration on objekti, joka saa launchin aikana
  #arvon, joka annettiin komentoriviltä esim. alla "headless" on komentoriviparametri
  # Launch configuration variables specific to simulation
  headless = LaunchConfiguration('headless')
  robot_name = LaunchConfiguration('robot_name')
  urdf_model = LaunchConfiguration('urdf_model')
  use_robot_state_pub = LaunchConfiguration('use_robot_state_pub')
  use_sim_time = LaunchConfiguration('use_sim_time')
  use_simulator = LaunchConfiguration('use_simulator')
  world = LaunchConfiguration('world')
  use_rviz = LaunchConfiguration('use_rviz')
   
  # Set the default pose
  x = LaunchConfiguration('x')
  y = LaunchConfiguration('y')
  z = LaunchConfiguration('z')
  roll = LaunchConfiguration('roll')
  pitch = LaunchConfiguration('pitch')
  yaw = LaunchConfiguration('yaw')
  amount_of_robots = LaunchConfiguration('robot_amount')

  set_env_vars_resources = AppendEnvironmentVariable(
    'GZ_SIM_RESOURCE_PATH',
    gazebo_models_path)
  
  # Start Gazebo server
  start_gazebo_server_cmd = IncludeLaunchDescription(
    PythonLaunchDescriptionSource(
      os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')),
    condition=IfCondition(use_simulator),
    launch_arguments={'gz_args': ['-r -s -v4 ', world], 'on_exit_shutdown': 'true'}.items())
 
  # Start Gazebo client    
  start_gazebo_client_cmd = IncludeLaunchDescription(
    PythonLaunchDescriptionSource(
      os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')),
    launch_arguments={'gz_args': '-g -v4 '}.items()
    )
  

  # Launch RViz
  start_rviz_cmd = Node(
    condition=IfCondition(use_rviz),
    package='rviz2',
    executable='rviz2',
    name='rviz2',
    output='screen'
  )

  # Bridge ROS topics and Gazebo messages for establishing communication
  start_gazebo_ros_bridge_cmd = Node(
    package='ros_gz_bridge',
    executable='parameter_bridge',
    parameters=[{
      'config_file': default_ros_gz_bridge_config_file_path,
    }],
    output='screen'
  ) 

  start_fork_control_cmd = Node(
    package=package_name,
    executable="fork_node",
  )


  launch_gui_cmd = ExecuteProcess(
            cmd=['python3', gui_path],
            output='screen'
  )
     
  opfunc = OpaqueFunction(function = spawn_robot)
  ld = LaunchDescription()

  ld.add_action(start_fork_control_cmd)
  # Declare the launch options
  ld.add_action(declare_robot_amount_cmd)
  ld.add_action(declare_robot_name_cmd)
  ld.add_action(declare_simulator_cmd)
  ld.add_action(declare_urdf_model_path_cmd)
  ld.add_action(declare_use_robot_state_pub_cmd)  
  ld.add_action(declare_use_rviz_cmd) 
  ld.add_action(declare_use_sim_time_cmd)
  ld.add_action(declare_use_simulator_cmd)
  ld.add_action(declare_world_cmd)
 
  ld.add_action(declare_x_cmd)
  ld.add_action(declare_y_cmd)
  ld.add_action(declare_z_cmd)
  ld.add_action(declare_roll_cmd)
  ld.add_action(declare_pitch_cmd)
  ld.add_action(declare_yaw_cmd)  
 
  # Add any actions
  ld.add_action(set_env_vars_resources)
  ld.add_action(start_gazebo_server_cmd)
  ld.add_action(start_gazebo_client_cmd)
  #ld.add_action(start_robot_state_publisher_cmd)
  ld.add_action(start_rviz_cmd)
 
  #ld.add_action(start_gazebo_ros_spawner_cmd)
  ld.add_action(start_gazebo_ros_bridge_cmd)

  ld.add_action(launch_gui_cmd)
  ld.add_action(opfunc)

  return ld

#https://robotics.stackexchange.com/questions/104340/getting-the-value-of-launchargument-inside-python-launch-file
def spawn_robot(context):

    amount_of_robots = LaunchConfiguration('robot_amount').perform(context)
    urdf_model = LaunchConfiguration('urdf_model').perform(context)
    use_robot_state_pub = LaunchConfiguration('use_robot_state_pub')
    use_sim_time = LaunchConfiguration('use_sim_time')
    
    # List to store actions
    actions = []

    for i in range(int(amount_of_robots)):
        robot_name = f"forklift_{i+1}"
        x_pos = float(i)
        print(f"Spawning {robot_name} at x position {x_pos}")

        spawn_action = Node(
          package='ros_gz_sim',
          executable='create',
          arguments=[
            '-name', robot_name,
            '-topic', "robot_description",
            '-x', str(x_pos+1),
            '-y', '0.0',
            '-z', '0.01',
            '-R', '0',
            '-P', '0',
            '-Y', '0'
            ],
          output='screen',
          ) 
        
        bridge_cmd_vel_action = Node(
          package='ros_gz_bridge',
          executable='parameter_bridge',
          arguments=[f'{robot_name}/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist'],
        )

        bridge_container_contact_action = Node(
          package='ros_gz_bridge',
          executable='parameter_bridge',
          arguments=[f'{robot_name}/touched@std_msgs/msg/Bool[gz.msgs.Boolean'],
        )

        robot_description_content = ""
          # Subscribe to the joint states of the robot, and publish the 3D pose of each link.
        try:
          robot_description_content = ParameterValue(
          Command(['xacro ', urdf_model, ' robot_namespace:=',robot_name]),
          value_type=str
        )
        except Exception as e:
          print(e)
          exit()

        start_robot_state_publisher_cmd = Node(
          condition=IfCondition(use_robot_state_pub),
          package='robot_state_publisher',
          executable='robot_state_publisher',
          name=f'robot_state_publisher_{robot_name}',
          output='screen',
          parameters=[{
            'use_sim_time': use_sim_time, 
            'robot_description': robot_description_content,
            'frame_prefix': robot_name + "/"}],
          remappings=[('/tf', f'/{robot_name}/tf'),
                       ('/tf_static', f'/{robot_name}/tf_static')],
            )


        bridge_odometry_action = Node(
          package='ros_gz_bridge',
          executable='parameter_bridge',
          arguments=[f'{robot_name}/odometry@nav_msgs/msg/Odometry[gz.msgs.Odometry'],
        )

        execution_node_action = Node(
          package="forklift_controller",
          executable="primitive_node", #Corresponds to a name in setup.py
          arguments=[robot_name]
          )

        actions.append(start_robot_state_publisher_cmd)
        actions.append(spawn_action)
        actions.append(bridge_container_contact_action)
        actions.append(bridge_cmd_vel_action)
        actions.append(bridge_odometry_action)
        actions.append(execution_node_action)
    
    return actions
    



