import sys
import argparse

import paho.mqtt.client as mqtt
import os
import json 
import yaml

class MalformedPlanError(Exception):
    pass

def read_plan(plan_path: str):
    if not os.path.exists(plan_path):
        raise FileNotFoundError("The given file could not be found")

    with open(plan_path) as f:
        content = f.read()

    # Try JSON
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try YAML if JSON fails
    try:
        return yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise MalformedPlanError(
            "File is neither valid JSON nor YAML"
        ) from e

def send_plan(plan: dict, host: str="localhost", port: int=1883):

    mqtt_client = mqtt.Client()

    mqtt_client.connect(host, port)
    mqtt_client.loop_start()

    plan_stringified = json.dumps(plan)
    print("Sending a plan")
    result = mqtt_client.publish("/plan", payload=plan_stringified, qos=2)
    result.wait_for_publish()
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
  

def main():
    parser = argparse.ArgumentParser(
        description="Script that reads a robotic plan from a json/yaml file"
        "and sends it through an MQTT broker for execution in the simulation")
    
    parser.add_argument(
        "filename", 
        help="Path to the yaml/json file that " \
        "contains the plan to execute. See README" \
        " at the project root for the format",
        type=str)
    
    parser.add_argument(
        "-p", "--port",
        help="Port that the mqtt broker runs on",
        type=int,
        default=1883)
    
    parser.add_argument(
        "--host", 
        help="Broker hostname",
        default="localhost")
    
    args = parser.parse_args()
    plan = read_plan(args.filename)
    send_plan(plan, args.host, args.port)



if __name__ == "__main__":
    main()