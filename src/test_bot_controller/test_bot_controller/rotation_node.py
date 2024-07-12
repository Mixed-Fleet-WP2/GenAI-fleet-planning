import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from std_msgs.msg import Float64
from geometry_msgs.msg import Vector3
from functools import partial
import math
from collections import deque

class RotationNode(Node):
    def __init__(self):
        super().__init__("rotation_node")
        self.angle_to_turn = None
        self.target_angle = 0
        self.kp = 0.8  # Proportional gain
        self.create_subscription(Odometry, "/model/forklift/odometry", self.__get_rotation, 10)
        self.create_subscription(Float64, "/rotate", partial(self.handle_command, topic_name='/rotate'), 10)
        self.create_subscription(Vector3, "/move", partial(self.handle_command, topic_name='/move'))
        self.rotation_controller = self.create_publisher(Twist, "/cmd_vel", 10)
        self.current_yaw = None
        self.orientation_received = False
        self.rotation_complete = True
        self.init_yaw = None
        self.timer = None
        self.command_queue = deque()

    def handle_command(self, msg, topic_name):
        #Tähän pitää laittaa queue myös
        match topic_name:
            case "/rotate":
                self.__set_angle(msg)
            case "/move":
                pass
        
    def __euler_from_quaternion(self, x, y, z, w):
        t3 = +2.0 * (w * z + x * y)
        t4 = +1.0 - 2.0 * (y * y + z * z)
        return math.atan2(t3, t4)  # in radians

    def __get_rotation(self, msg):
        orientation_q = msg.pose.pose.orientation
        yaw = self.__euler_from_quaternion(orientation_q.x, orientation_q.y, orientation_q.z, orientation_q.w)
        self.current_yaw = round(yaw, 2)
        self.orientation_received = True

    def __set_angle(self, msg):
        self.get_logger().info("Rotation message received")
        self.command_queue.append(msg.data)
        if self.rotation_complete:
            self.__start_next_rotation()

    def __start_next_rotation(self):
        if self.command_queue:
            #Take the next command from the queue
            self.angle_to_turn = self.command_queue.popleft()
            #Update the position to the one received from gazebo
            self.init_yaw = self.current_yaw
            self.target_angle = self.init_yaw + math.radians(self.angle_to_turn)
            #We are now in progress of making a rotation
            self.rotation_complete = False
            #Needed if we allow for new rotations starting mid command, in this
            #we do not allow new rotation commands while old is executing
            """
            if self.timer is not None:
                self.timer.cancel()
            """
            #Start the rotation loop
            self.timer = self.create_timer(0.1, self.rotate)

    def rotate(self):
        if not self.orientation_received:
            return

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
            #if self.timer:
            self.timer.cancel()
            self.timer = None
            self.__start_next_rotation()
        else:
            msg.angular.z = self.kp * error
            self.rotation_controller.publish(msg)
            #self.get_logger().info(f"Target angle: {self.target_angle:.2f}, Current yaw: {self.current_yaw:.2f}, Error: {error:.2f}")

def main(args=None):
    rclpy.init(args=args)
    node = RotationNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
