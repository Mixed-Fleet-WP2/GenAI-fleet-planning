import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from rclpy.duration import Duration
import tf_transformations


#https://roboticsbackend.com/rclpy-params-tutorial-get-set-ros2-params-with-python/#Get_params_one_by_one
class ExampleNavToPose(Node):
    def __init__(self):
        super().__init__('navigation_node')

        # Declare parameters
        self.declare_parameter('namespace', '')
        self.declare_parameter('x_pose', 0.0)
        self.declare_parameter('y_pose', 0.0)
        self.declare_parameter('z_pose', 0.0)
        self.declare_parameter('roll', 0.0)
        self.declare_parameter('pitch', 0.0)
        self.declare_parameter('yaw', 0.0)
       

        # Retrieve parameters
        namespace = self.get_parameter('namespace').get_parameter_value().string_value
        x_pose = self.get_parameter('x_pose').get_parameter_value().double_value
        y_pose = self.get_parameter('y_pose').get_parameter_value().double_value
        z_pose = self.get_parameter('z_pose').get_parameter_value().double_value
        roll = self.get_parameter('roll').get_parameter_value().double_value
        pitch = self.get_parameter('pitch').get_parameter_value().double_value
        yaw = self.get_parameter('yaw').get_parameter_value().double_value
      
        # Use the parameters as needed in your node
        self.get_logger().info(f'Namespace: {namespace}')
        self.get_logger().info(f'Initial Pose: x={x_pose}, y={y_pose}, z={z_pose}, roll={roll}, pitch={pitch}, yaw={yaw}')
      
        # Initialize the navigator
        self.navigator = BasicNavigator(namespace=namespace)
        quaternion = tf_transformations.quaternion_from_euler(roll, pitch, yaw)

        # Set the initial pose
        initial_pose = PoseStamped()
        initial_pose.header.frame_id = 'map'
        initial_pose.header.stamp = self.navigator.get_clock().now().to_msg()
        initial_pose.pose.position.x = x_pose
        initial_pose.pose.position.y = y_pose
        initial_pose.pose.position.z = z_pose
        initial_pose.pose.orientation.w = quaternion[3]
        initial_pose.pose.orientation.x = quaternion[0]
        initial_pose.pose.orientation.y = quaternion[1]
        initial_pose.pose.orientation.z = quaternion[2]
        print("SETTTING INITIAL POSE")
        self.navigator.setInitialPose(initial_pose)
        print("SETTTING INITIAL POSE DONE")

        
        # Activate navigation, if not autostarted. This should be called after setInitialPose()
        # or this will initialize at the origin of the map and update the costmap with bogus readings.
        # If autostart, you should `waitUntilNav2Active()` instead.
        #self.navigator.lifecycleStartup()

        # Wait for navigation to fully activate, since autostarting nav2
        self.navigator.waitUntilNav2Active()

        # If desired, you can change or load the map as well
        # navigator.changeMap('/path/to/map.yaml')

        # You may use the navigator to clear or obtain costmaps
        # navigator.clearAllCostmaps()  # also have clearLocalCostmap() and clearGlobalCostmap()
        # global_costmap = navigator.getGlobalCostmap()
        # local_costmap = navigator.getLocalCostmap()

        # Set a goal pose
        
        goal_pose = PoseStamped()
        goal_pose.header.frame_id = 'map'
        goal_pose.header.stamp = self.navigator.get_clock().now().to_msg()
        goal_pose.pose.position.x = -1.0
        goal_pose.pose.position.y = -1.6
        #Keep the orientation as is
        goal_pose.pose.orientation.w = quaternion[3]
        goal_pose.pose.orientation.x = quaternion[0]
        goal_pose.pose.orientation.y = quaternion[1]
        goal_pose.pose.orientation.z = quaternion[2]
        self.navigator.goToPose(goal_pose)

        # Monitor the navigation task
        self.monitor_navigation(namespace)

    def monitor_navigation(self, namespace):
        i = 0
        while not self.navigator.isTaskComplete():
            i += 1
            feedback = self.navigator.getFeedback()
            if feedback and i % 5 == 0:
                self.get_logger().info(
                    'Estimated time of arrival: '
                    + '{0:.0f}'.format(
                        Duration.from_msg(feedback.estimated_time_remaining).nanoseconds
                        / 1e9
                    )
                    + ' seconds.'
                )

                # Some navigation timeout to demo cancellation
                if Duration.from_msg(feedback.navigation_time) > Duration(seconds=600.0):
                    self.navigator.cancelTask()

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
        result = self.navigator.getResult()
        if result == TaskResult.SUCCEEDED:
            self.get_logger().info('Goal succeeded!')
        elif result == TaskResult.CANCELED:
            self.get_logger().info('Goal was canceled!')
        elif result == TaskResult.FAILED:
            self.get_logger().info('Goal failed!')
        else:
            self.get_logger().info('Goal has an invalid return status!')

        self.navigator.lifecycleShutdown()

def main(args=None):
    rclpy.init(args=args)
    node = ExampleNavToPose()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()