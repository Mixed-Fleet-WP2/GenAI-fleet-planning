import xml.etree.ElementTree as ET
import os
import paho.mqtt.client as mqtt
from collections import deque

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
        self.mqtt_client.subscribe([("test", 2)])
        self.mqtt_client.on_message =self.on_message

        #Items are sets of prerequisites for each action,
        #preconditions are checked in the order they are added
        #Each set contains the prerequisites for a single action
        self.preconditions_queue = deque()
        
        self.object_positions = {}
        

        #Assume that the robots in network are ready to accept commands, so no need to wait for services
    
    def __del__(self):

        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
    
    def __process_mqtt_msg(self, msg: mqtt.MQTTMessage, debug: bool = False):
        decoded_message = str(msg.payload.decode('utf-8'))
        # Remove control characters from the message
        #cleaned_message = re.sub(r'[\x00-\x1F\x7F]', '', decoded_message)
        cleaned_message = re.sub(r'^[^\{]+', '', decoded_message)
        cleaned_message = re.sub(r'[^\}]+$', '', cleaned_message)
        
        if debug:
            print(f"Received message: {msg.payload}", flush=True)
            print(f"Decoded message: {decoded_message}", flush=True)
            print(f"Cleaned message: {cleaned_message}", flush=True)
        try:
            payload = json.loads(cleaned_message)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}", flush=True)
            payload = None
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
            if not self.preconditions_queue:
                print("No preconditions, returning", flush=True)
                return
            else:
                #The first set in the queue is the one that is waiting for feedback first
                first_waiting_action_preconditions:set = self.preconditions_queue[0]


                precondition_to_remove = int(payload['action_id'])

                #Only an action with the same ID can remove the precondition (only action itself may remove it), also non-existing action cannot be removed
                if payload['action_id'] == precondition_to_remove and precondition_to_remove in first_waiting_action_preconditions:

                    #Remove the action that was just completed from the set
                    first_waiting_action_preconditions.remove(int(payload['action_id']))
                    #If the set is empty, all actions have been completed
                    if not first_waiting_action_preconditions:
                        #Remove the set from the queue
                        self.preconditions_queue.popleft()
                        #print("All preconditions met, notifying the waiting thread", flush=True)
                        print("Preconditions after removal", flush=True)
                        print(self.preconditions_queue, flush=True)
                        #Notify the waiting thread that the preconditions have been met
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

        #Each activation record has a set of prerequisites
        preconditions_for_this_stack = None

        #Only if there are prerequisites, we need to add them to the queue
        if prereqs:
            print(f"Adding prerequisites {prereqs} to the queue", flush=True)
            #Multiple instances of this function may be running at the same time
            preconditions_for_this_stack = set(prereqs)
            #Add the preconditions to the queue (by reference)
            self.preconditions_queue.append(preconditions_for_this_stack)

        print("Preconditions queue is now", flush=True)
        print(self.preconditions_queue, flush=True)

        #If there are no prerequisites, we can just publish the message right away
        #instead of waiting the robot to complete previous actions
        if not prereqs:
            print("No prerequisites, publishing the message right away", flush=True)
            endpoint = f"{robot}/{action_name}"
            self.mqtt_client.publish(endpoint, payload_as_string, qos=2)
        else:
            print("Waiting for preconditions to be met", flush=True)
            #With automatically acquires the lock and releases it when the block is exited
            #(even on error)
            #print(f"THe payload is: {payload_as_string}", flush=True)
            with self.condition:
                #Wait for previous actions to complete (if the precondition set is empty, it means that all actions have been completed)
                #When feedback is received, the set is modified by removing the completed action and the condition is notified
                while len(preconditions_for_this_stack) > 0:
                    print(f"Waiting for {preconditions_for_this_stack}", flush=True)
                    self.condition.wait()
                    #Publish the message when the condition is notified
            self.mqtt_client.publish(f"{robot}/{action_name}", payload_as_string, qos=2)
                    
                
