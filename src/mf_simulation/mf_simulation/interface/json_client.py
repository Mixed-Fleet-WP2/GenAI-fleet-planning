from mf_simulation.interface.database import Database
from mf_simulation.interface.controller_v2 import Controller
import paho.mqtt.client as mqtt
import json
from mf_simulation.interface.plan_format import Plan
from pydantic import ValidationError
import sys
from threading import Thread
import os
from mf_simulation.interface.progress_notifier import ProgressNotifier



class JsonClient():

    def __init__(self):

        self.__controller = Controller()

        self.__mqtt_client = mqtt.Client()

        self.__mqtt_client.connect("153.1.162.49", 2883)

        self.__mqtt_client.subscribe([("/plan", 2)])
        self.__mqtt_client.on_message = self.on_message

        self.__mqtt_client.loop_forever()

        
    
    def __del__(self):

        self.__mqtt_client.loop_stop()
        self.__mqtt_client.disconnect()
    
    def on_message(self, client, userdata, message:mqtt.MQTTMessage):
        
        #payload = json.loads(message.payload)
        topic = message.topic
        payload = message.payload.decode()
        #print()
        #print(f"Decoded payload: {payload}", flush=True)

        if topic == "/plan":
            try:
                plan: Plan = Plan.model_validate_json(payload)
                print("MESSAGE RECEIVED", flush=True)
                return
                plan_thread = Thread(None, self.__controller.run_plan, args=[plan, ProgressNotifier()])
                plan_thread.start()

            except ValidationError as e:
                print(e, file=sys.stderr, flush=True)

def main():
    JsonClient()

if __name__ == "__main__":
    main()


"""
mosquitto_pub -h localhost -p 1883 -t "/plan" --repeat 1 --repeat-delay 1 -m '[{"executing_robot":"drone_1","command":"search","command_arguments":{},"action_id":2,"prerequisites":[]}]'

mosquitto_sub -h localhost -p 1883 -t "/plan"


"""