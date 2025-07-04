import paho.mqtt.client as mqtt
from pydantic import BaseModel, RootModel
import json
from typing import Literal


class RobotState(BaseModel):
    robot_position: list[float]
    robot_status: Literal["online", "offline"]
    timestamp: int

class ObjectState(BaseModel):
    x: float
    y: float
    z: float
    roll: float
    pitch: float
    yaw: float

# https://docs.pydantic.dev/latest/concepts/models/#rootmodel-and-custom-root-types
class RobotStateUpdate(RootModel):
    root: dict[str, RobotState]

class ObjectStateUpdate(RootModel):
    root: dict[str, ObjectState]

class Database():
    def __init__(self):
        
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self.__on_connect
        self.mqtt_client.on_message = self.__on_message
        self.mqtt_client.connect("localhost", 1883, 60)
        self.robot_state_data_ = {}
        self.object_state_data_ = {}
        self.mqtt_client.loop_start()  # Start the MQTT client loop in a separate thread
    
    def __del__(self):
        self.mqtt_client.disconnect()
        print("Connection terminated!")

    def __on_connect(self, client:mqtt.Client, userdata, flags, reason_code, properties):
        print(f"Connected to MQTT broker")
        client.subscribe("robot_state_updates")
        client.subscribe("object_state_updates")
        
    def __on_message(self, client:mqtt.Client, userdata, msg:mqtt.MQTTMessage):
        try:
            payload = msg.payload.decode('utf-8')
            if msg.topic == "robot_state_updates":
                state = RobotStateUpdate.model_validate_json(payload).model_dump()
                # https://docs.python.org/3/library/stdtypes.html#dict.update
                self.robot_state_data_.update(state)
            elif msg.topic == "object_state_updates":
                state = ObjectStateUpdate.model_validate_json(payload).model_dump()
                self.object_state_data_.update(state)
            else:
                print(f"Unknown topic: {msg.topic}")
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
        except Exception as e:
            print(f"Error processing message: {e}")
    
    
    def get_robot_states(self, robot_name: str | None =None):
        """
        Get state information of robot(s). 
        If no robot name is specified, get state of all robots.

        Args:
            robot_name (str, optional): Name of the robot whose state to get. Defaults to None.

        Returns:
            dict: A dictionary containing the state of the robot(s). 
            Empty if no robot corresponding to robot_name is found or no robots exist. for example:
            {
                "robot_1": {
                    "robot_position": [0.0, 0.0, 0.0],
                    "robot_status": "online",
                    "timestamp": 20
                }
            }
        

        """
        if not robot_name:
            return self.robot_state_data_
        else:
            if robot_name in self.robot_state_data_:
                return dict(robot_name=self.robot_state_data_[robot_name])
            else:
                return {}
    
    def get_object_states(self, object_name: str | None = None):
        """
        Get state information of the objects in the environment.
        If no object name is specified, get state of all objects.

        Args:
            object_name (str | None): Name of the object whose state to get. Defaults to None.
        
        Returns:
            dict: A dictionary containing the state of the objects(s). 
            Empty if no object corresponding to object_name is found or no known objects exist. for example:
            {
                "pallet_1": {
                    "x": 2.0,
                    "y": 0.0,
                    "z": 0.0,
                    "roll": 0.0,
                    "pitch": 0.0,
                    "yaw": 0.0
                }
            }
            
        """

        if not object_name:
            return self.object_state_data_
        else:
            if object_name in self.object_state_data_:
                return dict(object_name=self.object_state_data_[object_name])
            else:
                return {}


if __name__ == "__main__":
    db = Database()
