import paho.mqtt.client as mqtt
import base64
from pydantic import BaseModel, RootModel
import json
from typing import Literal, Union


# https://docs.pydantic.dev/latest/concepts/models/#rootmodel-and-custom-root-types
class RobotState(BaseModel):
    robot_position: list[float]
    robot_status: Literal["online", "offline"]
    timestamp: int

class RobotStateUpdate(RootModel):
    root: dict[str, RobotState]

class Database():
    def __init__(self):
        
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self.__on_connect
        self.mqtt_client.on_message = self.__on_message
        self.mqtt_client.connect("localhost", 1883, 60)
        self.state_data_ = {}
        self.mqtt_client.loop_start()  # Start the MQTT client loop in a separate thread
    
    def __del__(self):
        self.mqtt_client.disconnect()
        print("Connection terminated!")

    def __on_connect(self, client:mqtt.Client, userdata, flags, reason_code, properties):
        print(f"Connected to MQTT broker")
        client.subscribe("robot_state_updates")
        
    def __on_message(self, client:mqtt.Client, userdata, msg:mqtt.MQTTMessage):
        try:
            payload = msg.payload.decode('utf-8')
            state = RobotStateUpdate.model_validate_json(payload).model_dump()
            # https://docs.python.org/3/library/stdtypes.html#dict.update
            self.state_data_.update(state)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
        except Exception as e:
            print(f"Error processing message: {e}")
    
    
    def get_state(self, robot_name=None):
        """
        Get state information of robot(s).

        Args:
            robot_name (str, optional): Name of the robot whose state to get. Defaults to None.

        Returns:
            dict: A dictionary containing the state of the robot(s), for example:
            {
                "robot_1": {
                    "robot_position": [0.0, 0.0, 0.0],
                    "robot_status": "online",
                    "timestamp": 20
                }
            }
        """
        if not robot_name:
            return self.state_data_
        else:
            if robot_name in self.state_data_:
                return dict(robot_name=self.state_data_[robot_name])
            else:
                return {}
        
if __name__ == "__main__":
    db = Database()
