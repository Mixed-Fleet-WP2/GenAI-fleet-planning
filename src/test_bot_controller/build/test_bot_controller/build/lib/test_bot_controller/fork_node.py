#!/usr/bin/env python3

import rclpy
from rclpy.node import Node

class ForkControlNode(Node):

    def __init__(self):
        super().__init__("fork_control_node")
        self.get_logger().info("Test")

def main(args=None):
    rclpy.init(args=args)
    node = ForkControlNode()

if __name__ == '__main__':
    main()