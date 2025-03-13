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

        self.object_positions = {}
        

        #Assume that the robots in network are ready to accept commands, so no need to wait for services
    
    def __del__(self):

        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
    
    def __process_mqtt_msg(self, msg:mqtt.MQTTMessage, debug: bool = False):
        
        decoded_message = msg.payload.decode('utf-8')
        #Remove control characters from the message, as they are left for some unknown reason???
        cleaned_message:str = re.sub(r'[\x00-\x1F\x7F]', '', decoded_message)
        if debug:
            print(f"Cleaned message: {cleaned_message}", flush=True)
        payload = json.loads(cleaned_message)

        return payload
    
    def get_object_positions(self):
        """
        Get positions of all known objects in the environment. Simultaneously
        convert the complex TFMessage to a simple dict with only the necessary information
        to be used in prompting. The conversion happens only when the prompt is being
        created and not when the position message is received as it would
        hinder performance

        :return: A dict with object positions in the format:
        {
            "object_name": {
                "x": x_position,
                "y": y_position,
                "z": z_position,
                "quaternion_x": x_rotation,
                "quaternion_y": y_rotation,
                "quaternion_z": z_rotation,
                "quaternion_w": w_rotation
            }
        }	
        """
       
        object_positions = {}

        for object in self.object_positions:
            object_positions[object] = {}
            object_positions[object]['x'] = self.object_positions[object]['transforms'][1]['transform']['translation']['x']
            object_positions[object]['y'] = self.object_positions[object]['transforms'][1]['transform']['translation']['y']
            object_positions[object]['z'] = self.object_positions[object]['transforms'][1]['transform']['translation']['z']

            object_positions[object]['quaternion_x'] = self.object_positions[object]['transforms'][1]['transform']['rotation']['x']
            object_positions[object]['quaternion_y'] = self.object_positions[object]['transforms'][1]['transform']['rotation']['y']
            object_positions[object]['quaternion_z'] = self.object_positions[object]['transforms'][1]['transform']['rotation']['z']
            object_positions[object]['quaternion_w'] = self.object_positions[object]['transforms'][1]['transform']['rotation']['w']

        return object_positions
    

    def on_message(self, client, userdata, message:mqtt.MQTTMessage):

        if message.topic == "cube_pos":
            #Always replace the object positions with the latest ones (even if existing)
            pos_dict = self.__process_mqtt_msg(message) #This is a dict in format following
            #ros2 TFMessage. See: https://docs.ros.org/en/melodic/api/tf2_msgs/html/msg/TFMessage.html
            self.object_positions["cube"] = pos_dict
            return
        
        print(f"Received message on topic {message.topic}", flush=True)
        payload = self.__process_mqtt_msg(message, debug=True)

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
            print("Waiting for preconditions to be met", flush=True)
            #With automatically acquires the lock and releases it when the block is exited
            #(even on error)
            with self.condition:
                #Wait for previous actions to complete
                while self.current_action_completed_preconditions != self.current_action_preconditions:
                    self.condition.wait()
                    #Publish the message
                    self.mqtt_client.publish(f"{robot}/{action_name}", payload, qos=2)
                    break
                
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