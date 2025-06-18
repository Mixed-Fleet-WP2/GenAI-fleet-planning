import paho.mqtt.client as mqtt
import base64
from pydantic import BaseModel
import json
from typing import Literal

class RobotStateUpdate(BaseModel):
    robot_name: str
    robot_position: list[float]
    robot_status: Literal["online", "offline"]
    timestamp: int

class Database():
    def __init__(self):
        
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.connect("localhost", 1883, 60)
    
    def __del__(self):
        self.mqtt_client.disconnect()

    def on_connect(self, client:mqtt.Client, userdata, flags, reason_code, properties):
        print(f"Connected to MQTT broker with result code {reason_code}")
        # Subscribe after connecting
        client.subscribe("robot_state_updates")
        
    def on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode('utf-8')
            payload_as_object = json.loads(payload)
            #print(f"Received: {payload_as_object}", flush=True)
            
            result = RobotStateUpdate.model_validate_json(payload)
            print(f"Received: {result.model_dump()}", flush=True)

            # Optional: Validate with Pydantic model
            # robot_state = RobotStateUpdate(**payload_as_object)
            # print(f"Validated: {robot_state}")
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
        except Exception as e:
            print(f"Error processing message: {e}")
    
    def start(self):

        try:
            self.mqtt_client.loop_forever()
            
        except KeyboardInterrupt:
            print("Stopping MQTT client...")
            self.mqtt_client.disconnect()

if __name__ == "__main__":
    db = Database()
    db.start()  # This keeps the script running