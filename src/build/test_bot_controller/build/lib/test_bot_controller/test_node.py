#!/usr/bin/env python3
import rclpy
from rclpy.node import Node

class MyNode(Node):

    def __init__(self):
        super().__init__("first_node")
        self.get_logger().info("Hello with ROS2ededde")


def main(args=None):
    #Init communication with ros
    rclpy.init(args=args)
    
    node = MyNode()
    rclpy.spin(node)
    #Stop communication
    rclpy.shutdown()

if __name__ == '__main__':
    main()