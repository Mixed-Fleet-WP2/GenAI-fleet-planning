#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
import math


class RotationNode(Node):
    def __init__(self):
        super().__init__("rotation_node")
        self.angle_to_turn = 90
        self.target_angle = 0
        self.kp = 1.0  # Proportional gain
        self.create_subscription(Odometry, "/model/forklift/odometry", self.__get_rotation, 10)
        self.rotation_controller = self.create_publisher(Twist, "/cmd_vel", 10)
        self.current_yaw = None
        self.orientation_received = False
        self.rotation_complete = True
        self.init_yaw = None
        self.timer = self.create_timer(0.1, self.rotate)

    def __euler_from_quaternion(self, x, y, z, w):
        """
        Convert a quaternion into euler angles (roll, pitch, yaw).
        roll is rotation around x in radians (counterclockwise)
        pitch is rotation around y in radians (counterclockwise)
        yaw is rotation around z in radians (counterclockwise)
        """
        
        t3 = +2.0 * (w * z + x * y)
        t4 = +1.0 - 2.0 * (y * y + z * z)
        yaw_z = math.atan2(t3, t4)

        return yaw_z  # in radians

    def __get_rotation(self, msg):
        orientation_q = msg.pose.pose.orientation
        yaw = self.__euler_from_quaternion(orientation_q.x, orientation_q.y, orientation_q.z, orientation_q.w)
        self.current_yaw = round(yaw, 2)
        self.orientation_received = True

    def rotate(self):

        if not self.orientation_received:
            return

        if self.rotation_complete:
            # Initialize rotation parameters
            self.init_yaw = self.current_yaw
            self.target_angle = self.init_yaw + math.radians(self.angle_to_turn)
            self.rotation_complete = False

        msg = Twist()
        error = self.target_angle - self.current_yaw


        """
        # Normalize error to be within -pi to pi
        if error > math.pi:
            error -= 2 * math.pi
        elif error < -math.pi:
            error += 2 * math.pi
        """


        if abs(error) < 0.01:  # Smaller threshold for rotation completion
            msg.angular.z = 0.0
            self.rotation_controller.publish(msg)
            self.get_logger().info(f"Rotation complete: {self.current_yaw:.2f} radians")
            self.rotation_complete = True
            # Optionally, reset the timer here if you want to continue doing other tasks
            msg.linear.x = 1.5
            self.rotation_controller.publish(msg)
            self.timer.cancel()
        else:
            # Decrease the turning velocity as we approach the target
            msg.angular.z = self.kp * error
            self.rotation_controller.publish(msg)
            self.get_logger().info(f"Target angle: {self.target_angle:.2f}, Current yaw: {self.current_yaw:.2f}, Error: {error:.2f}")

def main(args=None):
    rclpy.init(args=args)
    node = RotationNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
