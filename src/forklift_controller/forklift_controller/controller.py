
from rclpy.node import Node
import collections
from movement_interface.srv import CubePos
import movement_interface.action as mv
from rclpy.action import ActionClient
import xml.etree.ElementTree as ET
import os
from tf2_msgs.msg import TFMessage

class Controller(Node):

    def __init__(self, robots_in_network=[{"type":"Toyota 02-8FGF15","name":"forklift_1"},
                                          {"type":"Toyota 02-8FGF15","name":"forklift_2"}]):
        
        super().__init__('controller')
        

        script_dir = os.path.dirname(os.path.abspath(__file__))
        tree = ET.parse(os.path.join(script_dir, 'robots.xml'))
        root = tree.getroot()

        #Move a cube to a random position, should be maybe allocated
        #to launch file in the future
        self.robots_in_network = robots_in_network
        connections = {}
        self.cube_pos_x = None
        self.cube_pos_y = None
        

        self.subscription = self.create_subscription(
            TFMessage,
            '/model/cube/pose',  
            self.cube_pose_callback,
            10
        )
        
        self.cube_pos_req = CubePos.Request()

        for robot in self.robots_in_network:
            self.get_logger().info(f"Robot: {robot}")
            type = robot['type']
            name = robot['name']

            robot_node = root.find(f"./robot[@type='{type}']")

            #Go through all the primitives and create an action client for each
            for primitive in robot_node.findall('primitive'):
                primitive_name = primitive.attrib.get('name')
                primitive_class = getattr(mv, primitive_name, None)
                connections[f"{name}/{primitive_name}"] = ActionClient(self, primitive_class, f'{name}/{primitive_name}')
        
        #Assume that the robots in network are ready to accept commands, so no need to wait for services
        """
        while not self.pick_up_cli.wait_for_service(timeout_sec=1.0) and not self.move_client.wait_for_server(): #and not self.move_cli.wait_for_service(timeout_sec=1.0)
            self.get_logger().info('Services not available yet')
        """
    
    """

    """
    def run_action(self, robot:str, action_name:str, args:dict, uuid, prereqs:list = None):
        """
        Run a generic action on a robot.

        :param robot: The robot to run the action on
        :param action_name: The action to run
        :param args: The arguments to the action
        :param prereqs: The prerequisites to the action
        """

        move_client = self.connections[f"{robot}/{action_name}"]
        primitive_class = getattr(mv, action_name, None)
        goal_msg = primitive_class.Goal()

        #Attach named arguments to the goal message
        for arg in args[1:]:
            arg_value = args[arg]
            goal_msg[arg] = arg_value

        #If there are prerquisites, we need to wait for them
        if prereqs:
            #We do not get anything about the acceptance
            self.get_logger().info("SYNC ACTION")
            result = move_client.send_goal(goal_msg)
            if result is not None:
                self.get_logger().info('Result: {0}'.format(result.result.success))
            else:
                self.get_logger().error('Failed to get result from action server')
        
        #For non-blocking behaviour, callbacks are used (default behaviour)
        else:
             #Returns a future that can be waited (this future completes when action server accepts or rejects the request)
            self.send_goal_future = self.move_client.send_goal_async(goal_msg)
            #Callback fires when the future resolves
            self.send_goal_future.add_done_callback(self.goal_response_callback)

    #https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Writing-an-Action-Server-Client/Py.html#writing-an-action-server
    def goal_response_callback(self, future):
        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().info('Goal rejected')
            return
        
        self.get_logger().info("Goal accepted")
        
        #Returns a future that can be waited (this future completes when the action completes or is aborted)
        self.get_result_future = goal_handle.get_result_async()
        self.get_result_future.add_done_callback(
            lambda future: self.get_logger().info(f'Result: {future.result().result.success}')
        )
      
    def get_cube_pos(self):
        return self.cube_pos_x, self.cube_pos_y
    
    def cube_pose_callback(self, msg):
        self.cube_pos_x = msg.transforms[1].transform.translation.x
        self.cube_pos_y = msg.transforms[1].transform.translation.y


    