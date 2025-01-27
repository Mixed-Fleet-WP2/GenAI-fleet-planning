import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist, PoseStamped
from std_msgs.msg import Bool
import numpy as np
from movement_interface.srv import MovementSuccess, Pickup, Drop, CubePos
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup
from tf2_msgs.msg import TFMessage
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from rclpy.duration import Duration
import tf_transformations
from tf2_ros import TransformListener, Buffer
from movement_interface.action import MoveToPoint
from rclpy.action import ActionServer, GoalResponse
from rclpy.action.server import ServerGoalHandle
import sys
from rclpy.time import Duration, Time
#import paho.mqtt.client as mqtt

from utils import move_object_to_point, reset_contact_sensor

# Specifies at which index in the pose
# array received from gazebo the cube is located

CUBE_WIDTH = 0.2
FORK_LENGTH = 0.3
FORK_PLATE_JOINT_ORIGIN_X = 0.38
FORK_PLATE_JOINT_ORIGIN_Y = 0
LEFT_FORK_VISUAL_ORIGIN_X = 0.15
LEFT_FORK_VISUAL_ORIGIN_Y = 0.05
# The height at which drop the "picked up cube onto the fork, could be in the future be replaced with an odometry value"
TELEPORT_HEIGHT = 0.2

class PrimitiveNode(Node):
    def __init__(self, node_name):

        move_object_to_point('cube', np.random.randint(3, 14), np.random.randint(3, 14), 0.5)

        # Use the namespace in the Node initialization
        # node_name = namespace but we cannot get it through
        #parameters, as the super constructor must be called first
        super().__init__(f"{node_name}_backend")

         # Declare parameters
        self.declare_parameter('namespace', '')
        self.declare_parameter('x_pose', 0.0)
        self.declare_parameter('y_pose', 0.0)
        self.declare_parameter('z_pose', 0.0)
        self.declare_parameter('roll', 0.0)
        self.declare_parameter('pitch', 0.0)
        self.declare_parameter('yaw', 0.0)

        #https://roboticsbackend.com/rclpy-params-tutorial-get-set-ros2-params-with-python/#Get_params_one_by_one
        namespace_p, x_pose_p, y_pose_p, z_pose_p, roll_p, pitch_p, yaw_p = self.get_parameters(['namespace','x_pose','y_pose','z_pose','roll','pitch','yaw'])

         # Retrieve parameters
        self.__namespace = namespace_p.get_parameter_value().string_value
        self.__x_pose = x_pose_p.get_parameter_value().double_value
        self.__y_pose = y_pose_p.get_parameter_value().double_value
        self.__z_pose= z_pose_p.get_parameter_value().double_value
        self.__roll = roll_p.get_parameter_value().double_value
        self.__pitch = pitch_p.get_parameter_value().double_value
        self.__yaw = yaw_p.get_parameter_value().double_value
        
        self.cube_pos_x = None
        self.cube_pos_y = None

        #Callbacks inside Reentrant groups may be executed in parallel, but things outside cannot not
        self.subscription_cb_group = ReentrantCallbackGroup()
        self.service_cb_group = ReentrantCallbackGroup()
        self.action_cb_group = ReentrantCallbackGroup()
        #self.create_subscription(Odometry, f"{self.__namespace}/odometry", self.__get_odom, 10)
        self.create_subscription(Bool, f"{self.__namespace}/touched", self.__detect_contact, 10)

        self.movement_server = ActionServer(self, MoveToPoint,  f'{self.__namespace}/move', self.move_callback, callback_group=self.action_cb_group)

        self.cube_pos_service = self.create_service(CubePos, 'cube_pos', self.send_cube_pos, callback_group=self.service_cb_group)
        self.pickup_srv = self.create_service(Pickup, f"{self.__namespace}/pick_up", self.pick_up, callback_group=self.service_cb_group) 
        self.drop_srv = self.create_service(Drop, f"{self.__namespace}/drop", self.drop, callback_group=self.service_cb_group)

        self.subscription = self.create_subscription(
            TFMessage,
            '/model/cube/pose',  
            self.cube_pose_callback,
            10
        )
        
        self.current_yaw = None
        self.current_x = None
        self.current_y = None
        self.current_z = None
        self.action_in_progress = False
        self.in_cube_contact = False

        self.current_quaternion_w = 0.0
        self.current_quaternion_x = 0.0
        self.current_quaternion_y = 0.0
        self.current_quaternion_z = 0.0
        self.odom_received = False
        self.__navigator = None

        self.__init_nav()

    def move_callback(self, goal_handle: ServerGoalHandle):
        x = goal_handle.request.x
        y = goal_handle.request.y
        self.get_logger().info("Moving to point")

        if x < -9 or y is None:
            self.get_logger().info("No target x coordinate provided")
            goal_handle.abort()
            return MoveToPoint.Result(success=False)

        return self.move(x,y, goal_handle)
        

    def __init_nav(self):
        # Initialize the navigator
        self.__navigator = BasicNavigator(namespace=self.__namespace)
        quaternion = tf_transformations.quaternion_from_euler(self.__roll, self.__pitch, self.__yaw)

        # Set the initial pose
        initial_pose = PoseStamped()
        initial_pose.header.frame_id = 'map'
        initial_pose.header.stamp = self.__navigator.get_clock().now().to_msg()
        initial_pose.pose.position.x = self.__x_pose
        initial_pose.pose.position.y = self.__y_pose
        initial_pose.pose.position.z = self.__z_pose
        initial_pose.pose.orientation.w = quaternion[3]
        initial_pose.pose.orientation.x = quaternion[0]
        initial_pose.pose.orientation.y = quaternion[1]
        initial_pose.pose.orientation.z = quaternion[2]

        self.__navigator.setInitialPose(initial_pose)
        # Activate navigation, if not autostarted. This should be called after setInitialPose()
        # or this will initialize at the origin of the map and update the costmap with bogus readings.
        # If autostart, you should `waitUntilNav2Active()` instead.
        #self.navigator.lifecycleStartup()

        # Wait for navigation to fully activate, since autostarting nav2
        self.__navigator.waitUntilNav2Active()

    def send_cube_pos(self, request, response):
        response.pos_vector[0] = self.cube_pos_x
        response.pos_vector[1] = self.cube_pos_y
        return response

    def pick_up(self, request, response):
        object = request.object
        self.pick_up_object(object)
        response.success = True
        return response
    
    def drop(self, request, response):
        object = request.object
        self.drop_object(object)
        response.success = True
        return response    

    def cube_pose_callback(self, msg):
        self.cube_pos_x = msg.transforms[1].transform.translation.x
        self.cube_pos_y = msg.transforms[1].transform.translation.y
        
    def move(self, x:float, y:float, goal_handle: ServerGoalHandle) -> MoveToPoint.Result:
        
        goal_pose = PoseStamped()
        goal_pose.header.frame_id = 'map'
        goal_pose.header.stamp = self.__navigator.get_clock().now().to_msg()
        goal_pose.pose.position.x = x
        goal_pose.pose.position.y = y
        #Keep the orientation as is
        """
        goal_pose.pose.orientation.w = quaternion[3]
        goal_pose.pose.orientation.x = quaternion[0]
        goal_pose.pose.orientation.y = quaternion[1]
        goal_pose.pose.orientation.z = quaternion[2]
        """
        self.__navigator.goToPose(goal_pose)

        # Monitor the navigation task
        return self.monitor_navigation(self.__namespace, goal_handle)

    def monitor_navigation(self, namespace: str, goal_handle: ServerGoalHandle) -> MoveToPoint.Result:
        
        tfbuffer = Buffer()
        listener = TransformListener(tfbuffer, self)

        while True:
            try:
                trans = tfbuffer.lookup_transform(f'{self.__namespace}/base_link', f'{self.__namespace}/base_link', Time(), Duration(seconds=10))
                self.get_logger().info(f"TRANSFORM IS NOW: {trans.transform.translation.x}")
            except Exception as e:
                self.get_logger().info(f"EXCEPTION: {e}")
            
        i = 0
        feedback_msg = MoveToPoint.Feedback()
        while not self.__navigator.isTaskComplete():
            i += 1
            feedback = self.__navigator.getFeedback()
            
            #Simulate arriving to pick up the cube
            if self.in_cube_contact:
                self.__navigator.cancelTask()
                goal_handle.succeed()
                return MoveToPoint.Result(success=True)
                
            if feedback and i % 5 == 0:
                feedback_msg.curr_pos = [feedback.current_pose.pose.position.x, feedback.current_pose.pose.position.y]
                goal_handle.publish_feedback(feedback_msg)
                self.get_logger().info(
                    'Estimated time of arrival: '
                    + '{0:.0f}'.format(
                        Duration.from_msg(feedback.estimated_time_remaining).nanoseconds
                        / 1e9
                    )
                    + ' seconds.'
                ) 

                #The feedback is: nav2_msgs.action.NavigateToPose_Feedback(current_pose=geometry_msgs.msg.PoseStamped(header=std_msgs.msg.Header(stamp=builtin_interfaces.msg.Time(sec=15, nanosec=876000000), frame_id='map'), pose=geometry_msgs.msg.Pose(position=geometry_msgs.msg.Point(x=0.20310853538829562, y=0.0591938412848921, z=0.15), orientation=geometry_msgs.msg.Quaternion(x=0.0, y=0.0, z=0.2484336233448129, w=0.9686489223613309))), navigation_time=builtin_interfaces.msg.Duration(sec=0, nanosec=0), estimated_time_remaining=builtin_interfaces.msg.

                # Some navigation timeout to demo cancellation
                if Duration.from_msg(feedback.navigation_time) > Duration(seconds=600.0):
                    self.__navigator.cancelTask()

                """
                # Some navigation request change to demo preemption
                if Duration.from_msg(feedback.navigation_time) > Duration(seconds=18.0):
                    goal_pose = PoseStamped()
                    goal_pose.header.frame_id = 'map'
                    goal_pose.header.stamp = self.navigator.get_clock().now().to_msg()
                    goal_pose.pose.position.x = 0.0
                    goal_pose.pose.position.y = 0.0
                    goal_pose.pose.orientation.w = 1.0
                    self.navigator.goToPose(goal_pose)
                """

        # Do something depending on the return code
        result = self.__navigator.getResult()
        if result == TaskResult.SUCCEEDED:
            self.pick_up_object('cube')
            goal_handle.succeed()
            return MoveToPoint.Result(success=True)
        #Nav failed, was canceled or other
        else:
            goal_handle.abort()
            return MoveToPoint.Result(success=False)

        #self.__navigator.lifecycleShutdown()
        
    """
    frame_local_pos_x: the x-coordinate of the origin of a frame specified in terms of the base link's 
    coordinate system. In Gazebo one can see the this coordinate by inspecting the link (if the link
    is not fixed)
    frame_local_y: the y-coordinate of the origin of a frame specified in terms of the base link's 
    coordinate system. In Gazebo one can see the this coordinate by inspecting the link (if the link
    is not fixed)
    offset_x: How much the returned x-coordinate should be offset to the
    x-direction (in the forklift's coordinate frame, not global) i.e. forward when looking towards the front
    offset_y: How much the returned y-coordinate should be offset to the
    y-direction (in the forklift's coordinate frame, not global) i.e. left when looking towards the front
    """

    def get_frame_pos_as_global(self, frame_local_pos_x, frame_local_pos_y, offset_x=0, offset_y=0):

        forklift_origin_global_x = self.current_x
        forklift_origin_global_y = self.current_y
        forklift_rotation_angle = self.current_yaw
        frame_local_position = np.array([frame_local_pos_x + offset_x, frame_local_pos_y + offset_y])

        # Transformation matrix to rotate the forlift's coordinate axis to the same
        # position as global axis
        rotation_matrix = np.array([
            [np.cos(forklift_rotation_angle), -np.sin(forklift_rotation_angle)],
            [np.sin(forklift_rotation_angle), np.cos(forklift_rotation_angle)]
        ])

        rotated_local_position = rotation_matrix.dot(frame_local_position)

        frame_global_pos_x = rotated_local_position[0] + forklift_origin_global_x
        frame_global_pos_y = rotated_local_position[1] + forklift_origin_global_y

        return frame_global_pos_x, frame_global_pos_y

    def pick_up_object(self, object):
        # 0.05 offset is to put the cube's origin between the 2 forks, otherwise it would be at the center of the left fork
        fork_center_x, fork_center_y = self.get_frame_pos_as_global(FORK_PLATE_JOINT_ORIGIN_X, FORK_PLATE_JOINT_ORIGIN_Y,
                                                                    LEFT_FORK_VISUAL_ORIGIN_X, LEFT_FORK_VISUAL_ORIGIN_Y - 0.05)
        # Movement to target is complete, pick up the target
        move_object_to_point('cube', fork_center_x, fork_center_y, TELEPORT_HEIGHT, self.current_quaternion_x,
                                  self.current_quaternion_y, self.current_quaternion_z, self.current_quaternion_w)

        cube_x, cube_y = self.cube_pos_x, self.cube_pos_y

        if abs(fork_center_x - cube_x) < 0.5 and abs(fork_center_y - cube_y) < 0.5:
            return True
        return False

    def drop_object(self, object):
        # Get the coordinates of a point right in front of the forklift, relative to the global frame
        x, y = self.get_frame_pos_as_global(FORK_PLATE_JOINT_ORIGIN_X, FORK_PLATE_JOINT_ORIGIN_Y,
                                            FORK_LENGTH + CUBE_WIDTH / 2, LEFT_FORK_VISUAL_ORIGIN_Y - 0.05)
        move_object_to_point('cube', x, y, TELEPORT_HEIGHT, self.current_quaternion_x, self.current_quaternion_y,
                                  self.current_quaternion_z, self.current_quaternion_w)
        self.in_cube_contact = False
        reset_contact_sensor()

    def __detect_contact(self, msg):
        self.in_cube_contact = msg.data
  
def main(args=None):

    node_name = sys.argv[1]

    rclpy.init(args=args)
    node = PrimitiveNode(node_name)
    # https://answers.ros.org/question/358343/rate-and-sleep-function-in-rclpy-library-for-ros2/
    #One is the default thread, another reserved for service callbacks and third for actions
    executor = MultiThreadedExecutor(num_threads=2)
    rclpy.spin(node, executor=executor)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()


"""
 # start the demo autonomy task
    demo_cmd = Node(
        package='forklift_controller',
        executable='navigation_node',
        emulate_tty=True,
        output='screen',
        parameters=[
            {'namespace': namespace,
             'x_pose': pose['x'],
             'y_pose': pose['y'],
             'z_pose': pose['z'],
             'roll': pose['R'],
             'pitch': pose['P'],
             'yaw': pose['Y'],
             }
        ]
    )
"""