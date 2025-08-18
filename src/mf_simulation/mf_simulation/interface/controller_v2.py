import paho.mqtt.client as mqtt
import json
from typing import Optional
from mf_simulation.interface.plan_format import Plan, PlanFromLLM, Action, ActionFromLLM
from dataclasses import dataclass
from typing import TypedDict
from enum import Enum
from PySide6.QtCore import SignalInstance
from queue import Queue

# Used with no plan gui
from mf_simulation.interface.progress_notifier import ProgressNotifier

@dataclass
class ExecutableAction():
    command_arguments: dict[str, str | float]
    prerequisites: set[Optional[int]]
    command: str
    executing_robot: str
    action_id: int
    # Write feedback to file or the gui (if using llm)
    feedback_signal: SignalInstance | ProgressNotifier
    input_from_action_id: Optional[int] = None

    def remove_prerequisite(self, action_id: int) -> bool:
        """
        Args:
            action_id: The id of the action to be removed from prequisites
        Returns:
            True if there are no prerequisites left after removal, False
            otherwise
        """
        self.prerequisites.discard(action_id)

        if len(self.prerequisites) == 0:
            return True
        else:
            return False
    
    def run(self, client: mqtt.Client):
        """
        Run a robot action by publishing to the relevant mqtt topic

        Args:
            client: The mqtt client instance used to publish the action
        Returns:
            None
        """
        
        action_json = json.dumps({
            "action_id": self.action_id,
            "command_arguments": self.command_arguments
        })
        topic = f"{self.executing_robot}/{self.command}"
        self.feedback_signal.emit(f"Running action with id of {self.action_id} on topic {topic}")
        client.publish(topic, action_json)


#https://stackoverflow.com/questions/24481852/serialising-an-enum-member-to-json
class FeedbackType(str, Enum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    CANCEL = "CANCELLED"

class Feedback(TypedDict):
    action_id: int
    type: FeedbackType
    message: str
    # Must be at least empty
    return_value: dict[str, float|int|str]

def feedback_str_to_enum(curr_dict):

    # Handle nested dicts
    if "type" in curr_dict:
        curr_dict["type"] = FeedbackType(curr_dict["type"])
    return curr_dict

class Controller():

    def __init__(self):
        
        self.__return_vals = {}
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.connect("localhost")

        self.__progress_callback: SignalInstance | ProgressNotifier
        
        #Start the mqtt client in a separate thread
        self.mqtt_client.loop_start()
   
        self.received_feedback: SignalInstance | None = None

        self.mqtt_client.subscribe([("feedback", 2)])

        # Also runs in the same thread that is started with loop_start()
        # https://stackoverflow.com/questions/57925734/does-on-message-in-paho-mqtt-run-in-a-new-thread
        self.mqtt_client.on_message = self.on_message

        self.__actions: dict[int, ExecutableAction] = dict()
    
        self.__waiting_feedbacks: Queue[Feedback] = Queue()
  
    def __del__(self):

        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
    
    def on_message(self, client, userdata, message:mqtt.MQTTMessage):
        
        payload = json.loads(message.payload)
        topic = message.topic

        if topic == "feedback":
            #print("RECEIVED FEEDBACK!!!", flush=True)
            # object hook allows specifying how certain strings should be converted
            # to python types. In this case enums
            payload:Feedback = json.loads(message.payload, object_hook=feedback_str_to_enum)
            #print("FEEDBACK IS: ", payload, flush=True)
            # Add a processable item to a feedback queue
            self.__waiting_feedbacks.put(payload)
            

    def __process_feedback(self):
        
        #https://stackoverflow.com/questions/8158442/fair-semaphore-in-python
        while True:
            
            # Get a feedback item or block until available
            feedback: Feedback = self.__waiting_feedbacks.get()
            feedback_type = feedback["type"]
            
            self.__progress_callback.emit(feedback["message"])
            
            if  feedback_type == FeedbackType.ERROR:
                    return False
            
            if feedback_type == FeedbackType.SUCCESS:
                
                completed_action_id = feedback["action_id"]

                # Add the return value if it is not empty (guaranteed to be at least empty by the c++ backend):
                return_value = feedback["return_value"]
                if return_value:
                    self.__return_vals[completed_action_id] = return_value

                #print("Return values after success: ", self.__return_vals, flush=True)
                # Remove completed action from all actions
                print("Removing action id: ", completed_action_id, flush=True)
                del self.__actions[completed_action_id]
                
                # All actions have been completed
                if not self.__actions:
                    self.__progress_callback.emit("The plan has been completed successfully!")
                    return True

                # Remove the id of the completed action from each action
                # that it is prerequisite for
                for id, action in self.__actions.items():
                    print("REMOVING PREREQS", flush=True)
                    if action.remove_prerequisite(completed_action_id):
                        # If action args should become from another action's return value,
                        # get the stored return value and replace arguments:
                        if action.input_from_action_id:
                            print("USING ACTION WITH ARGS: ", self.__return_vals[completed_action_id], flush=True)
                            action.command_arguments = self.__return_vals[completed_action_id]
                        action.run(self.mqtt_client)
                    

    def run_plan(self, plan: Plan | PlanFromLLM, feedback_signal: SignalInstance | ProgressNotifier):
        
        if feedback_signal:
            self.__progress_callback = feedback_signal

        self.__progress_callback.emit("Running plan")

        for action in plan.actions:
            prerequisites = action.prerequisites
            action_id = action.action_id

            pending_action = ExecutableAction(
                command_arguments=action.command_arguments,
                prerequisites=set(prerequisites),
                command=action.command,
                executing_robot=action.executing_robot,
                action_id=action_id,
                feedback_signal=feedback_signal,
                #ActionFromLLM does not have the input_from_action_id and for Action the default is None
                input_from_action_id= action.input_from_action_id if type(action) == Action else None
            )

            print("Adding an action with id of: ", action_id, flush=True)
            self.__actions[action_id] =  pending_action

            # Run actions that dont have precondition immediately
            if not action.prerequisites:
                pending_action.run(self.mqtt_client)


        plan_success = self.__process_feedback()

        if plan_success:
            feedback_signal.emit("Success: All actions completed")
        else:
            feedback_signal.emit("Failure: The plan could not be completed")



                    
                
