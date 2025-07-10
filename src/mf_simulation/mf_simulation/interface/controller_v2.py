import paho.mqtt.client as mqtt
import json
from threading import Thread, Lock, Condition
from typing import Optional
from mf_simulation.interface.llm_utils import Plan, Action
from dataclasses import dataclass
from typing import TypedDict
from enum import Enum
from PySide6.QtCore import SignalInstance
from queue import Queue

@dataclass
class ExecutableAction():
    command_arguments: dict[str, str | float]
    prerequisites: set[Optional[int]]
    command: str
    executing_robot: str

    def __remove_prerequisite(self, action_id: int) -> bool:
        """
        Args:
            action_id: The id of the action to be removed from prequisites
        Returns:
            True if there are no prequisites left after removal, False
            otherwise
        """
        self.prerequisites.discard(action_id)

        if len(self.prerequisites) == 0:
            return True
        else:
            return False


#https://stackoverflow.com/questions/24481852/serialising-an-enum-member-to-json
class FeedbackType(str, Enum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    CANCEL = "CANCELLED"

class RobotAction(TypedDict):
    action_id: int
    command_arguments: dict[str, str | float]

class Feedback(TypedDict):
    action_id: int
    type: FeedbackType
    message: str

def feedback_str_to_enum(curr_dict):

    curr_dict["action_id"] = FeedbackType(curr_dict["action_id"])
    return curr_dict

class Controller():

    def __init__(self):
        
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.connect("localhost")

        self.__progress_callback = None
        
        #Start the mqtt client in a separate thread
        self.mqtt_client.loop_start()
   
        self.received_feedback:SignalInstance | None = None

        self.__feedback_lock = Lock()
        
        self.mqtt_client.subscribe([("feedback", 2)])

        # Also runs in the same thread that is started with loop_start()
        # https://stackoverflow.com/questions/57925734/does-on-message-in-paho-mqtt-run-in-a-new-thread
        self.mqtt_client.on_message = self.on_message

        self.__completed_actions:set[int] = set()
        self.__actions: dict[int, ExecutableAction] = dict()
        self.condition = Condition()
        self.__waiting_feedbacks:Queue[Feedback] = Queue()
        self.__execution_done = Condition()


    def __del__(self):

        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
    
    def on_message(self, client, userdata, message:mqtt.MQTTMessage):

        print(f"Received message: {message.topic}: {message.payload}", flush=True)
        
        payload = json.loads(message.payload)
        topic = message.topic

        if topic == "feedback":
            payload:Feedback = json.loads(message.payload, object_hook=feedback_str_to_enum)
            self.__waiting_feedbacks.put(payload)
            

    def __process_feedback(self):
        
        #https://stackoverflow.com/questions/8158442/fair-semaphore-in-python
        while True:
            
            # Get a feedback item or block until available
            feedback: Feedback = self.__waiting_feedbacks.get()

            feedback_type = feedback["type"]
            
            if self.__progress_callback: 
                self.__progress_callback.emit(feedback["message"])
            
            if  feedback_type == FeedbackType.ERROR:
                with self.__execution_done:
                    self.__execution_done.notify()
                    return False
            
            if feedback_type == FeedbackType.SUCCESS:
                
                completed_action_id = feedback["action_id"]

                # Remove completed action
                del self.__actions[completed_action_id]

                # Remove the id of the action from each action
                # that it is prerequisite for
                for id, action in self.__actions.items():
                    action.prerequisites.discard(id)
                    if not action.prerequisites:
                        self.__run_action(action, id)
                    

    def run_plan(self, plan: Plan, feedback_signal: SignalInstance):

        self.__progress_callback = feedback_signal

        for action in plan.actions:
            
            prerequisites = action.prerequisites
            action_id = action.action_id

            pending_action = ExecutableAction(
                command_arguments=action.command_arguments,
                prerequisites=set(prerequisites),
                command=action.command,
                executing_robot=action.executing_robot
            )


            self.__actions[action_id] =  pending_action

            # Run actions that dont have precondition immediately
            if not action.prerequisites:
                self.__run_action(pending_action, action_id)


        plan_success = self.__process_feedback()

        # # Start the thread that processes feedback
        # Thread(target=self.__process_feedback).start()

        # # Sleep to wait for execution to complete.
        # # Feedback is received from another thread
        # with self.__execution_done:
        #     self.__execution_done.wait()

    def __run_action(self, action:ExecutableAction, action_id:int):
        """
        Run a generic action on a robot.

        :param robot: The robot to run the action on
        :param action: The action to run
        :param args: The arguments to the action
        :param prereqs: The prerequisites to the action
        """

        if not action.prerequisites:
            print("No prerequisites, publishing immediately", flush=True)
            payload_as_string = json.dumps(RobotAction(action_id=action_id, command_arguments=action.command_arguments))
            self.mqtt_client.publish(f"{action.executing_robot}/{action.command}", payload_as_string, qos=2)
            return True

        return False

                    
                
