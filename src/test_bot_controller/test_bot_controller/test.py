import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup
from std_srvs.srv import Empty
from std_msgs.msg import Int32
import time
import threading

class ServiceNode(Node):
    def __init__(self):
        super().__init__('mock_service_node')
        
        self.shared_data = None
        self.data_lock = threading.Lock()
        
        # Create a subscriber with its own callback group
        self.subscription_cb_group = ReentrantCallbackGroup()
        self.subscription = self.create_subscription(
            Int32,
            'test_topic',
            self.subscription_callback,
            10,
            callback_group=self.subscription_cb_group
        )

        # Create a service with its own callback group
        self.service_cb_group = ReentrantCallbackGroup()
        self.srv = self.create_service(
            Empty,
            'test_service',
            self.service_callback,
            callback_group=self.service_cb_group
        )

    def subscription_callback(self, msg):
        self.get_logger().info(f'Subscriber received: {msg.data}')
        # Safely update the shared variable

        self.shared_data = msg.data

    def service_callback(self, request, response):
        self.get_logger().info('Service callback started')
        while True:

            if self.shared_data == 1:
                break
            
            if self.shared_data is not None:
                self.get_logger().info(f'Processing: {self.shared_data}')
            else:
                self.get_logger().info('No data to process')
            
            time.sleep(1)
        
        self.get_logger().info('Service callback finished')
        return response

def main(args=None):
    rclpy.init(args=args)
    node = ServiceNode()
    
    # Use a MultiThreadedExecutor to allow concurrent callback processing
    executor = MultiThreadedExecutor(num_threads=4)
    rclpy.spin(node, executor=executor)
    
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
