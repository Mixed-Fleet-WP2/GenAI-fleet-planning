
from rclpy.node import Node
import collections
from movement_interface.srv import MovementSuccess, Pickup, Drop, CubePos
import threading

class Forklift(Node):

    def __init__(self, node_name):

        #Move a cube to a random position, should be maybe allocated
        #to launch file in the future
        
        super().__init__(node_name)
        self.move_cli = self.create_client(MovementSuccess, f'{node_name}/move')
        self.cube_pos_cli = self.create_client(CubePos, 'cube_pos')
        self.pick_up_cli = self.create_client(Pickup, f'{node_name}/pick_up')  
        self.drop_cli = self.create_client(Drop, f'{node_name}/drop')
        self.json_commands = collections.deque()
        self.move_req = MovementSuccess.Request()
        self.pick_up_req = Pickup.Request()
        self.drop_req = Drop.Request()
        self.cube_pos_req = CubePos.Request()
        
        while not self.move_cli.wait_for_service(timeout_sec=1.0) and not self.pick_up_cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Services not available yet')
        
    def move(self, x, y):
        #Populate the request object
        self.move_req.x = x
        self.move_req.y = y
        #Make a ROS2 service call
        return self.move_cli.call(self.move_req)

    def pick_up(self, object):
        self.pick_up_req.object = object
        return self.pick_up_cli.call(self.pick_up_req)

    def drop(self, object):
        self.drop_req.object = object
        return self.drop_cli.call(self.drop_req)

    def get_cube_pos(self):
        res = self.cube_pos_cli.call(self.cube_pos_req)
        x,y = res.pos_vector[0],res.pos_vector[1]
        self.get_logger().info(str(x))
        return x,y

    def execute_commands(self, commands):

        while commands:
            func_name, args = commands.popleft()
            
            if func_name == "move":
                self.get_logger().info("Move")

                x = float(args[0])
                y = float(args[1])

                response = self.move(x, y)
                was_success = bool(response.success)

                if not was_success:
                    raise Exception("Movement to point was not successful")

            elif func_name == "pick_up":
                self.get_logger().info("Pick up")
                object = args[0]
                response = self.pick_up(object)
                was_success = bool(response.success)

                if not was_success:
                    raise Exception("Picking up the object was not successful")
                
            elif func_name == "drop":
                self.get_logger().info("Drop")
                object = args[0]
                response = self.drop(object)
                was_success = bool(response.success)

                if not was_success:
                    raise Exception("Dropping the object was not successful")
        
        #Inform that all commands were executed
        self.get_logger().info("All commands executed")
    