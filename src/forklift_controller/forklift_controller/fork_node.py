#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64



class ForkControlNode(Node):
    

    def __init__(self):
        super().__init__("fork_control_node")
        self.fork_down = True

        self.fork_controller = self.create_publisher(Float64, "/fork_control", 10)
        self.timer = self.create_timer(3,self.send_lift_command)
    
    def send_lift_command(self):
        msg = Float64()
        if(self.fork_down):
            msg.data = 2.0
        else:
            msg.data = 0.7
        self.fork_down = not self.fork_down
        self.fork_controller.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = ForkControlNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
