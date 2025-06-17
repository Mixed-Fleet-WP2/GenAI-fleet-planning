from pydantic import BaseModel
from typing import Union, TypedDict, Dict, NewType

# See example: # https://docs.pydantic.dev/2.3/usage/types/dicts_mapping/#typeddict
ActionID = NewType("ActionID", int)

class Action(BaseModel):
    action_id: ActionID
    executing_robot: str
    command: str
    command_arguments: dict[str, Union[float, str]]
    prerequisites: list[ActionID]
    reasoning: str

class Plan(BaseModel):
    actions: list[Action]