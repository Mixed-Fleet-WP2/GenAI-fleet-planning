


# type: ignore
import os

from ament_index_python.packages import get_package_share_directory, get_package_prefix
from launch import LaunchDescription
from launch.actions import (
    AppendEnvironmentVariable,
    DeclareLaunchArgument,
)

from launch.actions import OpaqueFunction
from launch.substitutions.command import Command
from launch_ros.parameter_descriptions import ParameterValue
from launch.substitutions import LaunchConfiguration, TextSubstitution
from launch_ros.actions import Node
from ros_gz_bridge.actions import RosGzBridge
from launch.actions import ExecuteProcess


def generate_launch_description():

    pkg_share = get_package_share_directory('test_pkg')
    namespace = LaunchConfiguration('namespace')
    use_sim_time = LaunchConfiguration('use_sim_time')
    forklift_gz_bridge_config = LaunchConfiguration("forklift_gz_bridge_config")
    robot_sdf = LaunchConfiguration('robot_sdf')
    remappings = [('/tf', 'tf'), ('/tf_static', 'tf_static')]

    pose = {
        'x': TextSubstitution(text='0.0'),
        'y': TextSubstitution(text='0.0'),
        'z': TextSubstitution(text='0.0'),
        'roll': TextSubstitution(text='0.0'),
        'pitch': TextSubstitution(text='0.0'),
        'yaw': TextSubstitution(text='0.0'),
    }

    declare_use_gz = DeclareLaunchArgument(
        name='use_gz',
        default_value='True',
        description='Wheter to use gz sim'
    )

    declare_use_namespace = DeclareLaunchArgument(
        name='namespace',
        default_value='',
        description='Namespace for the robot'
    )

    declare_use_sim_time = DeclareLaunchArgument(
        name='use_sim_time',
        default_value='True',
        description='Whether to use simulation time'
    )

    declare_robot_sdf = DeclareLaunchArgument(
        name="robot_sdf",
        default_value=os.path.join(pkg_share, 'urdf', 'forklift.urdf.xacro'),
        description="Path to the robot sdf/urdf"
    )

    declare_forklift_gz_bridge_path = DeclareLaunchArgument(
        name="forklift_gz_bridge_config",
        default_value=os.path.join(pkg_share, 'config', 'forklift_ros_gz_bridge.yaml'),
        description="Path to gz bridge configuration"
    )

    # This command returns the parsed sdf as a string
    # How to pass arguments to xacro: 
    # https://robotics.stackexchange.com/questions/85348/pass-parameters-to-xacro-from-launch-file-or-otherwise
    parsed_urdf = Command(['xacro', ' ', robot_sdf, ' namespace:=', namespace])
    
    # See: https://github.com/gazebosim/ros_gz/pull/380

    def spawn_robot(context, *args, **kwargs):
        namespace_str = namespace.perform(context)
        urdf_str = parsed_urdf.perform(context)
        # Escape quotes inside the URDF for the shell command
        urdf_escaped = urdf_str.replace('"', '\\"')

        spawn = ExecuteProcess(
            cmd=[
                'ros2', 'service', 'call',
                '/world/empty/create',
                'ros_gz_interfaces/srv/SpawnEntity',
                '{'
                    'entity_factory: {'
                    f'name: "{namespace_str}", '
                    f'sdf: "{urdf_escaped}", '
                    'allow_renaming: true, '
                    'pose: {'
                        'position: {x: 0.0, y: 0.0, z: 0.0}, '
                        'orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}'
                    '}'
                    '}'
                '}'
            ],
            output='screen'
        )
        return [spawn]


    run_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        namespace=namespace,
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time, 'robot_description': ParameterValue(
                parsed_urdf, value_type=str)}, # This was required because the robot_state_publisher was trying to parse the string as yaml. This was a problem
            # when the file included comments
        ],
        remappings=remappings,
    )
    
    bridge= RosGzBridge(
       # container_name="sim_env_container",
        bridge_name=[namespace, "_bridge"],
        namespace=namespace,
        config_file=forklift_gz_bridge_config,
        use_composition=False,
        # Fixes a bug with extra bridge params, see:
        # https://github.com/gazebosim/ros_gz/pull/775
        
        #bridge_params=[ {
               #'expand_gz_topic_names': True,
                #'use_sim_time': True,
            #}]

         extra_bridge_params=[{"bridge_names": ["create_bridge"],
        "bridges.create_bridge.service_name": "/world/warehouse/create",
        "bridges.create_bridge.ros_type_name": "ros_gz_interfaces/srv/SpawnEntity",
        "bridges.create_bridge.gz_req_type_name": "gz.msgs.EntityFactory",
        "bridges.create_bridge.gz_rep_type_name": "gz.msgs.Boolean",
        "bridges.create_bridge.direction": "BIDIRECTIONAL",
        }]
    )

    # This is so package:// and model:// is resolved in sdf files
    # When urdf is converted to sdf, the package:// is replaced with model://

    # Unlike ros' resource finder that resolves the package:// to share/package_name
    # gazebo uses model:// like a prefix to the path
    # This is why the path must be one higher
    set_env_vars_resources = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH', os.path.join(get_package_prefix('test_pkg'), 'share'))

    ld = LaunchDescription()
    spawn_model = OpaqueFunction(function=spawn_robot)
    ld.add_action(declare_use_namespace)
    ld.add_action(declare_robot_sdf)
    ld.add_action(declare_use_gz)
    ld.add_action(declare_forklift_gz_bridge_path)
    ld.add_action(declare_use_sim_time)
    ld.add_action(run_robot_state_publisher)
    ld.add_action(set_env_vars_resources)
    ld.add_action(bridge)
    #ld.add_action(spawn_model)
    

    return ld





