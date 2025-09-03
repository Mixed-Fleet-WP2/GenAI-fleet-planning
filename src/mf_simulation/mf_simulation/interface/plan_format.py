import yaml
from pydantic import BaseModel
from typing import NewType,Literal, Optional

# See example: # https://docs.pydantic.dev/2.3/usage/types/dicts_mapping/#typeddict
ActionID = NewType("ActionID", int)

class Formattable(BaseModel):
    
    def to_format(self, format: Literal["json", "yaml"] ="json"):
        if format == "json":
            return self.model_dump_json(indent=2)
        else:
            return yaml.dump(self.model_dump(), indent=2)

class ActionFromLLM(BaseModel):
    action_id: int
    executing_robot: str
    command: str
    command_arguments: dict[str, str | float]
    prerequisites: list[int]
    reasoning: str

class PlanFromLLM(Formattable):
    actions: list[ActionFromLLM]
