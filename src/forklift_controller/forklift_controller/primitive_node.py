import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Bool
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup
from tf2_msgs.msg import TFMessage
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from rclpy.duration import Duration
import tf_transformations
import sys
from rclpy.time import Duration
from std_msgs.msg import String
from MqttPayload import MqttPayload
import json
#https://answers.ros.org/question/409120/
import rosidl_runtime_py


from utils import move_object_to_point, reset_contact_sensor, get_pos_as_other_coord_frame

CUBE_WIDTH = 0.1
FORK_LENGTH = 0.3

class PrimitiveNode(Node):
    
    def __init__(self, node_name):
        
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
        self.publisher_cb_group = ReentrantCallbackGroup()

        self.create_subscription(String, "move", self.move_callback, 10, callback_group=self.subscription_cb_group)
        self.create_subscription(Bool, "touched", self.__detect_contact, 10)
        self.create_subscription(String, 'pick_up', self.pick_up_callback, 10, callback_group=self.subscription_cb_group)
        self.create_subscription(String, 'drop', self.drop_callback, 10, callback_group=self.subscription_cb_group)
        self.feedback_publisher = self.create_publisher(String, 'feedback', 10, callback_group=self.publisher_cb_group)
        self.cube_pos_publisher = self.create_publisher(String, '/cube_pos', 10, callback_group=self.publisher_cb_group)
        
        #Subscribe to the gazebo topic where the cube is published
        self.subscription = self.create_subscription(TFMessage,'/cube_pos_gz', self.cube_pose_callback, 10)
        
        self.__navigator = None
        self.__init_nav()

    
    def cube_pose_callback(self, msg):
        #Immediately forward the message to the mqtt bridge
        #Convert the message to an ordered dictionary
        msg_to_fwd = rosidl_runtime_py.convert.message_to_ordereddict(msg)
        msg_as_string = json.dumps(msg_to_fwd)
        msg = String()
        msg.data = msg_as_string
        self.cube_pos_publisher.publish(msg)
        
    def move_callback(self, msg):
        
        self.get_logger().info(f"The type of the msg is {type(msg)}")
        try:
            data = json.loads(msg.data)

            self.get_logger().info(f"Data: {data}")

            x = float(data["args"]["x"])
            y = float(data["args"]["y"])
            action_id = int(data["action_id"])

            self.move(x,y, action_id)
        except Exception as e:
            self.get_logger().error(f"Error: {e}")
            #self.feedback_publisher(MqttPayload("error", action_id, {"error": "Move failed, invalid arguments"}))


    def drop_callback(self, msg:String):

        try:
            data = json.loads(msg.data)

            self.get_logger().info(f"Data: {data}")

            object:str = data["args"]["object"]
            action_id:int = int(data["action_id"])

            return self.drop(object, action_id)
        except Exception as e:
            self.get_logger().error(f"Error: {e}")
            #self.feedback_publisher(MqttPayload("error", action_id, {"error": "Drop failed, invalid
    
    def pick_up_callback(self, msg:String):
        
        try:
            self.get_logger().info(f"The type of the msg is {type(msg)}")
            self.get_logger().info(f"The data is {msg.data}")

            data = json.loads(msg.data)
            self.get_logger().info(f"Data: {data}")

            object:str = data["args"]["object"]
            action_id:int = int(data["action_id"])

            self.get_logger().info(f"Object: {object}, action_id: {action_id}")

            return self.pick_up(object, action_id)
        except Exception as e:
            self.get_logger().error(f"Error: {e}")
            #self.feedback_publisher(MqttPayload("error", action_id, {"error": "Pick up failed, invalid arguments"}))

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

    def pick_up(self, object, action_id:int):
 
        x, y, z, orient_x, orient_y, orient_z, orient_w = get_pos_as_other_coord_frame(self, 'map', 'fork_1')
        
        move_object_to_point(object, x+0.15, y+0.05, z+0.1, orient_x, orient_y, orient_z, orient_w)

        payload = MqttPayload("success", action_id, {"success": "Pick up succeeded"})
        payload_as_string = str(payload)
        msg = String()
        msg.data = '{"payload_as_str": "test"}' 
        self.get_logger().info(f"The string representation of the payload is {payload_as_string}")

        self.feedback_publisher.publish(msg)

    def drop(self, object, action_id:int):
    
        x, y, z, orient_x, orient_y, orient_z, orient_w = get_pos_as_other_coord_frame(self, 'map', 'fork_1')

        #The transformation origin is the joint where the fork is attached to the forklift
        # The fork is 0.3 meters long and the cube is 0.2 meters wide
        # so in order to drop the cube in front of the fork, we need to move it 0.4 meters  
        # in the x axis (i.e. the fork length + the half of the cube width where the origin is)     
        pos_from_fork_start_to_end = x + FORK_LENGTH + CUBE_WIDTH

        move_object_to_point(object, pos_from_fork_start_to_end, y+0.05, z+0.1, orient_x, orient_y, orient_z, orient_w)
        payload = MqttPayload("success", action_id, {"success": "Drop succeeded"})
        payload_as_string = str(payload)
        self.feedback_publisher.publish(payload_as_string)

    def move(self, x:float, y:float, action_id:int):
        
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
        #return self.monitor_navigation(self.__namespace)
        return self.monitor_navigation(self)

    def monitor_navigation(self, action_id):

        self.get_logger().info("Monitoring navigation")
        
        i = 0
        while not self.__navigator.isTaskComplete():
            i += 1
            feedback = self.__navigator.getFeedback()
            

            """
            #Simulate arriving to pick up the cube
            if self.in_cube_contact:
                self.__navigator.cancelTask()
                return False
            """
                
            if feedback and i % 5 == 0:
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
            success_payload = MqttPayload("success", action_id, {"success": "Navigation succeeded"})
            self.feedback_publisher.publish(String(data=str(success_payload)))
        #Nav failed, was canceled or other
        else:
            error_payload = MqttPayload("error", action_id, {"error": "Navigation failed"})
            self.feedback_publisher.publish(String(data=str(error_payload)))
        #self.__navigator.lifecycleShutdown()
        
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

    for i in range(2):
        executor.remove_node(node)

    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

