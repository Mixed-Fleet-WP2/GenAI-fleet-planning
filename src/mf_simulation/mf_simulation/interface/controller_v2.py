import paho.mqtt.client as mqtt
import json
import threading
from pydantic import BaseModel
from typing import Optional
from mf_simulation.interface.llm_utils import Plan

class ExecutableAction(BaseModel):
    action_id: int
    args: dict[str, list[Optional[str]]]

class Controller():

    def __init__(self):
        
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.connect("localhost")

        #Start the mqtt client in a separate thread
        self.mqtt_client.loop_start()
   
        self.received_feedback = None
        
        self.mqtt_client.subscribe([("feedback", 2)])

        self.mqtt_client.on_message = self.on_message

        self.completed_tasks = set()  # Globally shared set of completed action_ids
        self.condition = threading.Condition()

        self.object_positions = {}
        
    
    def __del__(self):

        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
    
    def on_message(self, client, userdata, message:mqtt.MQTTMessage):

        print(f"Received message: {message.topic}: {message.payload}", flush=True)
        
        payload = message.payload

        if "error" in payload:
            print(f"Received error: {payload['error']}", flush=True)
            return

        if not payload or "action_id" not in payload:
            print(f"Ignoring message without valid action_id: {payload}")
            return

        action_id = int(payload['action_id'])

        with self.condition:
            print(f"Marking action {action_id} as completed.")
            self.completed_tasks.add(action_id)
            self.condition.notify_all()  # Notify all threads waiting on preconditions

    def run_plan(self, plan: Plan):
        pass


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
                    
                
