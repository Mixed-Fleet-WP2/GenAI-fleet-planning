import xml.etree.ElementTree as ET
import os
import paho.mqtt.client as mqtt

import json
import threading
import re

class Controller():

    def __init__(self, robots_in_network=[{"type":"Toyota 02-8FGF15","name":"forklift_1"},
                                          {"type":"Toyota 02-8FGF15","name":"forklift_2"}]):
        

        self.mqtt_client = mqtt.Client()
        self.mqtt_client.connect("localhost")

        #Start the mqtt client in a separate thread
        self.mqtt_client.loop_start()
        self.condition = threading.Condition()

        self.received_feedback = None
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        tree = ET.parse(os.path.join(script_dir, 'robots.xml'))
        root = tree.getroot()

        #Move a cube to a random position, should be maybe allocated
        #to launch file in the future
        self.robots_in_network = robots_in_network
        self.connections = {}
        self.cube_pos_x = None
        self.cube_pos_y = None

        self.mqtt_client.subscribe([("feedback", 2)])
        self.mqtt_client.subscribe([("cube_pos", 2)])
        self.mqtt_client.on_message =self.on_message

        self.current_action_preconditions = []
        self.current_action_completed_preconditions = []
        

        #Assume that the robots in network are ready to accept commands, so no need to wait for services
    
    def __del__(self):

        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()

    def on_message(self, client, userdata, message):

        print(f"Received message: {message.topic}", flush=True)

        if message.topic == "cube_pos":
            print("Received cube pos", flush=True)
        
        decoded_message = message.payload.decode('utf-8')
        #Remove control characters from the message, as they are left for some unknown reason???
        cleaned_message:str = re.sub(r'[\x00-\x1F\x7F]', '', decoded_message)
  
        payload = json.loads(cleaned_message)

        if "error" in payload:
            print(f"Received error: {payload['error']}", flush=True)
            return
        else:
            #No prerequisites, so we can just return
            if self.current_action_preconditions == []:
                return
            else:
                #Push the completed action to the list
                self.current_action_completed_preconditions.append(payload['action_id'])
                if self.current_action_completed_preconditions == self.current_action_preconditions:
                    with self.condition:
                        self.condition.notify()

    def run_action(self, robot:str, action_name:str, args:dict, uuid, prereqs:list = None):
        """
        Run a generic action on a robot.

        :param robot: The robot to run the action on
        :param action_name: The action to run
        :param args: The arguments to the action
        :param prereqs: The prerequisites to the action
        """

        print(f"Running action {action_name} on robot {robot} with args {args}")
        payload = {}

        payload['args'] = args
        payload['action_id'] = uuid

        payload_as_string = json.dumps(payload)

        self.current_action_preconditions = prereqs

        print(f"Preconditions: {self.current_action_preconditions}")

        #If there are no prerequisites, we can just publish the message right away
        #instead of waiting the robot to complete previous actions
        if not prereqs:
            endpoint = f"{robot}/{action_name}"
            self.mqtt_client.publish(endpoint, payload_as_string, qos=2)
        else:
            #With automatically acquires the lock and releases it when the block is exited
            #(even on error)
            with self.condition:
                #Wait for previous actions to complete
                while self.current_action_completed_preconditions != self.current_action_preconditions:
                    self.condition.wait()
                    #Publish the message
                    self.mqtt_client.publish(f"{robot}/{action_name}", payload, qos=2)
                    break
                
    def get_cube_pos(self):
        return self.cube_pos_x, self.cube_pos_y
    
    def cube_pose_callback(self, msg):
        self.cube_pos_x = msg.transforms[1].transform.translation.x
        self.cube_pos_y = msg.transforms[1].transform.translation.y


"""

        for robot in self.robots_in_network:
            self.get_logger().info(f"Robot: {robot}")
            type = robot['type']
            name = robot['name']

            robot_node = root.find(f"./robot[@type='{type}']")

            if robot_node is None:
                self.get_logger().error(f"Robot type {type} not found in robots.xml")
            else:
                robot_node_str = ET.tostring(robot_node, encoding='unicode')
                self.get_logger().info(robot_node_str)
            primitive_list = robot_node.find('./primitives')
            self.get_logger().info(f"Primitive parent: {primitive_list}")
            primitives = primitive_list.findall('primitive')
            if primitives is None:
                self.get_logger().error(f"Primitives not found for robot {name}")


            #Go through all the primitives and create an action client for each
            for primitive in robot_node.find('./primitives').findall('primitive'):
                primitive_name = primitive.attrib.get('name')
                primitive_class = getattr(mv, primitive_name, None)
                self.get_logger().info(f"Primitive: {primitive_name}")
                self.connections[f"{name}/{primitive_name}"] = ActionClient(self, primitive_class, f'{name}/{primitive_name}')

"""