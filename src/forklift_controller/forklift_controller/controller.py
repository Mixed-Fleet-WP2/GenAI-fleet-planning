import xml.etree.ElementTree as ET
import os
import paho.mqtt.client as mqtt
from collections import deque

import json
import threading
import re

MODELS = ["pallet_1"]

class Controller():

    def __init__(self, robots_in_network=[{"type":"Toyota 02-8FGF15","name":"forklift_1"},
                                          {"type":"Toyota 02-8FGF15","name":"forklift_2"}]):
        

        self.mqtt_client = mqtt.Client()
        self.mqtt_client.connect("localhost")

        #Start the mqtt client in a separate thread
        self.mqtt_client.loop_start()
   
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

        for model in MODELS:
            #print(f"SUBSCRIBING {model}_pos", flush=True)
            self.mqtt_client.subscribe([(f"{model}_pos", 2)])

        
        self.mqtt_client.subscribe([("test", 2)])
        self.mqtt_client.on_message =self.on_message

        self.completed_tasks = set()  # Globally shared set of completed action_ids
        self.condition = threading.Condition()

        
        self.object_positions = {}
        

        #Assume that the robots in network are ready to accept commands, so no need to wait for services
    
    def __del__(self):

        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
    
    def __process_mqtt_msg(self, msg):
        #A hacky way to extract JSON from the payload but
        # something is wrong with the payload when it goes
        # through the MQTT broker and mqqtt-ros2-bridge
        start = msg.payload.find(b'{')
        end = msg.payload.rfind(b'}') + 1
        if start == -1 or end == -1:
            raise ValueError("JSON not found in payload")
        
        raw_payload = msg.payload[start:end]
        decoded_message = raw_payload.decode('utf-8')
        #print(f"Decoded message: {decoded_message}", flush=True)
        return json.loads(decoded_message)
    
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
            print(f"Processing position for {object}", flush=True)
            object_positions[object] = {}
            print(self.object_positions, flush=True)
            object_positions[object]['x'] = self.object_positions[object]['position']['x']
            object_positions[object]['y'] = self.object_positions[object]['position']['y']
            object_positions[object]['z'] = self.object_positions[object]['position']['z']

            object_positions[object]['quaternion_x'] = self.object_positions[object]['orientation']['x']
            object_positions[object]['quaternion_y'] = self.object_positions[object]['orientation']['y']
            object_positions[object]['quaternion_z'] = self.object_positions[object]['orientation']['z']
            object_positions[object]['quaternion_w'] = self.object_positions[object]['orientation']['w']
        
        return object_positions
    

    def on_message(self, client, userdata, message:mqtt.MQTTMessage):

        #Position messages names are always in the format <model>_pos
        if re.search(r".*_pos", message.topic) != None:
            #The first group (group 0) is the whole match, the second group (group 1) is the model name
            model_name = re.search(r"(.*)_pos", message.topic).group(1)
            #print(f"Received position message for {model_name}: {message.payload}", flush=True)
            pos_dict = self.__process_mqtt_msg(message)
            self.object_positions[model_name] = pos_dict
            return
        else:
            print(f"Received message: {message.topic}: {message.payload}", flush=True)
        
        payload = self.__process_mqtt_msg(message)

        if "error" in payload:
            print(f"Received error: {payload['error']}", flush=True)
            return

        if not payload or "action_id" not in payload:
            print(f"Ignoring message without valid action_id: {payload}")
            return

        action_id = int(payload['action_id'])

        with self.condition:
            print(f"[MQTT] Marking action {action_id} as completed.")
            self.completed_tasks.add(action_id)
            self.condition.notify_all()  # Notify all threads waiting on preconditions


    def run_action(self, robot:str, action_name:str, args:dict, uuid, prereqs:list = None):
        """
        Run a generic action on a robot.

        :param robot: The robot to run the action on
        :param action_name: The action to run
        :param args: The arguments to the action
        :param prereqs: The prerequisites to the action
        """

        print(f"Running action {action_name} on robot {robot} with args {args}")

        payload = {
            'args': args,
            'action_id': uuid
        }
        payload_as_string = json.dumps(payload)

        if not prereqs:
            print("No prerequisites, publishing immediately", flush=True)
            self.mqtt_client.publish(f"{robot}/{action_name}", payload_as_string, qos=2)
            return

        prereqs_set = set(prereqs)

        with self.condition:
            while not prereqs_set.issubset(self.completed_tasks):
                missing = prereqs_set - self.completed_tasks
                print(f"[{uuid}] Waiting for prerequisites: {missing}")
                self.condition.wait()

        print(f"[{uuid}] Prerequisites met. Publishing action.")
        self.mqtt_client.publish(f"{robot}/{action_name}", payload_as_string, qos=2)
                    
                
