import rclpy
from rclpy.node import Node

from std_msgs.msg import Float64



class Forklift(Node):

    def __init__(self):
            super().__init__('forklift_robot')

            # Create a publisher for the /rotate topic
            self.publisher = self.create_publisher(Float64, '/rotate', 10)

            
    def rotate(self, angle):
        msg = Float64()
        msg.data = angle
        # Publish the message
        self.publisher.publish(msg)
        
        self.get_logger().info(f'Published: {angle}')