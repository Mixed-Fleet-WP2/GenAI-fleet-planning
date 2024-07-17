import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
from geometry_msgs.msg import Point
import json
import time
import collections

class Forklift(Node):

    def __init__(self):
        super().__init__('forklift_robot')
        self.publisher = self.create_publisher(Point, '/move', 50)
        self.json_commands = collections.deque()
        self.timer = None

    def rotate(self, angle):
        msg = Float64()
        msg.data = angle
        self.publisher.publish(msg)
        self.get_logger().info(f'Published angle: {angle}')
    
    def move(self, x,y):
        msg = Point()
        msg.y = y
        msg.x = x
        # Publish the message
        self.publisher.publish(msg)
        
        self.get_logger().info(f'Point: {x}, {y}')


    def load_json_commands(self):
        try:
            with open('test.json') as json_file:
                data = json.load(json_file)
                for item in data:
                    cmd_pair = (item["cmd"],item["args"])
                    self.json_commands.append(cmd_pair)
        except Exception as e:
            self.get_logger().error(f"Error loading JSON: {e}")

    def execute_commands(self):
        if not self.json_commands:
            self.get_logger().info("No commands to execute at this time")
            self.timer.cancel()
            return

        func_call, args = self.json_commands.popleft()
        if func_call == "rotate":
            self.get_logger().info("Rotate command")
            angle = float(args[0])
            self.rotate(angle)
        elif func_call == "move":
            self.get_logger().info("Move command")
            x = float(args[0])
            y = float(args[1])
            self.move(x, y)

    def start_execution(self):
        self.load_json_commands()
        time.sleep(2) #Timer needed so there is enought time to establish connections
        self.timer = self.create_timer(1.0, self.execute_commands)  # Timer to call execute_commands every 2 seconds

def main(args=None):
    rclpy.init(args=args)
    node = Forklift()

    try:
        node.start_execution()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
