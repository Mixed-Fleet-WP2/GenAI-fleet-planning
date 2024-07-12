import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
import json

class Forklift(Node):

    def __init__(self):
        super().__init__('forklift_robot')
        self.publisher = self.create_publisher(Float64, '/rotate', 50)
        self.json_commands = []
        self.timer = None

    def rotate(self, angle):
        msg = Float64()
        msg.data = angle
        self.publisher.publish(msg)
        self.get_logger().info(f'Published angle: {angle}')

    def load_json_commands(self):
        try:
            with open('test.json') as json_file:
                data = json.load(json_file)
                self.json_commands = [(item['cmd'], item['args']) for item in data]
        except Exception as e:
            self.get_logger().error(f"Error loading JSON: {e}")

    def execute_commands(self):
        if not self.json_commands:
            self.get_logger().info("No commands to execute")
            if self.timer:
                self.timer.cancel()
            return

        func_call, args = self.json_commands.pop(0)
        if func_call == "rotate":
            self.get_logger().info("Rotate command")
            angle = float(args[0])
            self.rotate(angle)

        elif func_call == "move":
            self.get_logger().info("Move command")
            x = args[0]
            y = args[1]
            # Implement move functionality if needed
            # self.move(x, y)

    def start_execution(self):
        self.load_json_commands()
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
