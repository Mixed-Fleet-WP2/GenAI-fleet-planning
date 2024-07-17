import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from std_msgs.msg import Float64
from geometry_msgs.msg import Point
from functools import partial
import math
from collections import deque
import threading
import subprocess

class RotationNode(Node):
    def __init__(self):
        super().__init__("rotation_node")
        self.angle_to_turn = None
        self.target_angle = 0
        self.kp = 0.9  # Proportional gain
        self.kp_movement = 0.5
        self.target_x  = 0.0
        self.target_y = 0.0

        self.create_subscription(Odometry, "/model/forklift/odometry", self.__get_odom, 10)
        self.create_subscription(Float64, "/rotate", partial(self.handle_command, topic_name="/rotate"), 10)
        self.create_subscription(Point, "/move", partial(self.handle_command, topic_name='/move'), 10)
        self.rotation_controller = self.create_publisher(Twist, "/cmd_vel", 10)
        self.current_yaw = None
        self.current_x = None
        self.current_y = None
        self.action_in_progress = False

        self.angle_diff_to_target = 0.0
        self.x_diff_to_target = 0.0
        self.y_diff_to_target = 0.0
        self.current_quaternion_w = 0.0

        self.current_quaternion_x = 0.0
        self.current_quaternion_y = 0.0
        self.current_quaternion_z = 0.0

        self.odom_received = False
        self.rotation_complete = True
        self.init_yaw = None
        self.timer = None
        self.move_timer = None
        self.command_queue = deque()

    def handle_command(self, msg, topic_name):
        #Append the received command
        self.command_queue.append((topic_name, msg))
         
    def __euler_from_quaternion(self, x, y, z, w):
        t3 = +2.0 * (w * z + x * y)
        t4 = +1.0 - 2.0 * (y * y + z * z)
        return math.atan2(t3, t4)

    def handle_cmds(self):
        if self.command_queue and self.odom_received and not self.action_in_progress:
            cmd = self.command_queue.popleft()
            msg_type, msg = cmd
            match msg_type:
                case "/rotate":
                    pass
                case "/move":
                    self.action_in_progress = True
                    # Adjust the target position
                    target_x = msg.x
                    target_y = msg.y
                    
                    # Calculate the x and y compontents of the vector that starts from the forklift and ends at the target
                    direction_vector_x_component = target_x - self.current_x
                    direction_vector_y_component = target_y - self.current_y
                    #Calculate the length of the sum vector (direct vector leading to target)
                    distance = math.hypot(direction_vector_x_component, direction_vector_y_component )
                    
                    # convert to the sum vector to unit vector
                    if distance > 0:
                        direction_vector_x_component  /= distance
                        direction_vector_y_component /= distance
                    
                    # Set the offset target by moving the real target away to the direction of the vector
                    self.target_x = target_x - 0.5 * direction_vector_x_component
                    self.target_y = target_y - 0.5 * direction_vector_y_component 

                    self.x_diff_to_target = self.target_x - self.current_x
                    self.y_diff_to_target = self.target_y - self.current_y
                    self.angle_diff_to_target = math.atan2(self.y_diff_to_target, self.x_diff_to_target)

                    # Rotate first to face the target
                    self.init_yaw = self.current_yaw
                    self.target_angle = self.init_yaw + (self.angle_diff_to_target - self.init_yaw)
                    self.rotation_complete = False

                    # Enter the rotation loop and rotate until facing the point
                    self.timer = self.create_timer(0.1, self.rotate)

                    # Start a new loop for the actual movement
                    self.move_timer = self.create_timer(0.1, self.move)

    def move(self):
        if not self.rotation_complete:
            return

        error_x = self.target_x - self.current_x
        error_y = self.target_y - self.current_y
        distance_error = math.hypot(error_x, error_y)
        msg = Twist()
        if distance_error < 0.08:
            msg.linear.x = 0.0
            self.rotation_controller.publish(msg)
            self.get_logger().info(f"Move complete, current location: ({self.current_x}, {self.current_y})")
            self.action_in_progress = False
            self.move_timer.cancel()
            self.move_timer = None
            
            teleop_location_x = self.current_x
            teleop_location_y = self.current_y
            z = 0.3
            cmd = [
            "gz", "service",
            "-s", "/world/default/set_pose",
            "--reqtype", "gz.msgs.Pose",
            "--reptype", "gz.msgs.Boolean",
            "--timeout", "300",
            "--req", (
                f'name: "cube", position: {{x: {teleop_location_x}, y: {teleop_location_y}, z: {z}}}, '
                f'orientation: {{x: {self.current_quaternion_x}, y: {self.current_quaternion_y}, '
                f'z: {self.current_quaternion_z}, w: {self.current_quaternion_w}}}'
                )
            ]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                self.get_logger().info(result.stdout)
                self.get_logger().info(result.stderr)
            except Exception as e:
                self.get_logger().info(e)

        else:
            #Multiplying by a small value results in slower linear movement
            msg.linear.x = self.kp_movement * distance_error
            self.rotation_controller.publish(msg)


    def __get_odom(self, msg):
        orientation_q = msg.pose.pose.orientation
        self.current_x = msg.pose.pose.position.x
        self.current_y = msg.pose.pose.position.y
        self.current_quaternion_x = orientation_q.x
        self.current_quaternion_y = orientation_q.y
        self.current_quaternion_z = orientation_q.z
        self.current_quaternion_w = orientation_q.w
        yaw = self.__euler_from_quaternion(orientation_q.x, orientation_q.y, orientation_q.z, orientation_q.w)
        self.current_yaw = round(yaw, 2)
        self.odom_received = True

    def rotate(self):
        error = self.target_angle - self.current_yaw
        if error > math.pi:
            error -= 2 * math.pi
        elif error < -math.pi:
            error += 2 * math.pi

        msg = Twist()
        if abs(error) < 0.01:  # Smaller threshold for rotation completion
            msg.angular.z = 0.0
            self.rotation_controller.publish(msg)
            self.get_logger().info(f"Rotation complete: {self.current_yaw:.2f} radians")
            self.rotation_complete = True
            if self.timer:
                self.get_logger().info(f"Cancelling timer")
                self.timer.cancel()
                self.timer = None
        else:
            msg.angular.z = self.kp * error
            self.rotation_controller.publish(msg)
            #self.get_logger().info(f"Target angle: {self.target_angle:.2f}, Current yaw: {self.current_yaw:.2f}, Error: {error:.2f}")

    
def main(args=None):
    rclpy.init(args=args)
    node = RotationNode()
    rate = node.create_rate(2)
    # https://answers.ros.org/question/358343/rate-and-sleep-function-in-rclpy-library-for-ros2/
    thread = threading.Thread(target=rclpy.spin, args=(node, ), daemon=True)
    thread.start()
    try:
        while rclpy.ok():
            node.handle_cmds()
            rate.sleep()
    except KeyboardInterrupt:
        pass

    rclpy.shutdown()

if __name__ == '__main__':
    main()
