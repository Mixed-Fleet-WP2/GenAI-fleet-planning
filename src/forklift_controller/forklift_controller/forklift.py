
from rclpy.node import Node
import collections
from movement_interface.srv import MovementSuccess, Pickup, Drop, CubePos
from movement_interface.action import MoveToPoint
from rclpy.action import ActionClient
from functools import partial
class Forklift(Node):

    def __init__(self, node_name):
            
        #Move a cube to a random position, should be maybe allocated
        #to launch file in the future
        
        super().__init__(f"{node_name}_api")
        self.cube_pos_cli = self.create_client(CubePos, 'cube_pos')
        self.pick_up_cli = self.create_client(Pickup, f'{node_name}/pick_up')  
        self.drop_cli = self.create_client(Drop, f'{node_name}/drop')
        self.json_commands = collections.deque()
        self.move_req = MovementSuccess.Request()
        self.pick_up_req = Pickup.Request()
        self.drop_req = Drop.Request()
        self.cube_pos_req = CubePos.Request()
        self.move_client = ActionClient(self, MoveToPoint, f'{node_name}_move')
        
        while not self.pick_up_cli.wait_for_service(timeout_sec=1.0) and not self.move_client.wait_for_server(): #and not self.move_cli.wait_for_service(timeout_sec=1.0)
            self.get_logger().info('Services not available yet')
    
    def move_action(self, x,y, is_sync=False):
        
        self.get_logger().info("Received client goal")
        goal_msg = MoveToPoint.Goal()
        goal_msg.x = x
        goal_msg.y = y

        if is_sync:
            #We do not get anything about the acceptance
            self.get_logger().info("SYNC ACTION")
            result = self.move_client.send_goal(goal_msg)
            if result is not None:
                self.get_logger().info('Result: {0}'.format(result.result.success))
            else:
                self.get_logger().error('Failed to get result from action server')
        
        #For non-blocking behaviour, callbacks are used
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
        
        self.get_logger().info("ASYNC ACTION")
        #Returns a future that can be waited (this future completes when the action completes or is aborted)
        self.get_result_future = goal_handle.get_result_async()
        self.get_result_future.add_done_callback(self.get_result_callback)
        """
        else:
            self.get_logger().info("SYNC ACTION")
            #https://docs.ros2.org/foxy/api/rclpy/api/actions.html
            #THIS SHOULD MAYBE BE MOVED OUTSIDE THE CALLBACK AND INTO A REGULAR FUNCTION AS PER: https://docs.ros2.org/foxy/api/rclpy/api/actions.html (Do not call this method in a callback or a deadlock may occur)
            result = goal_handle.get_result() #Synchronous version
            self.get_logger().info('Result: {0}'.format(result))
        """
        

    def get_result_callback(self, future):
        result = future.result().result
        self.get_logger().info('Result: {0}'.format(result.success))

    def pick_up(self, object):
        self.pick_up_req.object = object
        return self.pick_up_cli.call(self.pick_up_req)

    def drop(self, object):
        self.drop_req.object = object
        return self.drop_cli.call(self.drop_req)

    def get_cube_pos(self):
        res = self.cube_pos_cli.call(self.cube_pos_req)
        x,y = res.pos_vector[0],res.pos_vector[1]
        return x,y

    