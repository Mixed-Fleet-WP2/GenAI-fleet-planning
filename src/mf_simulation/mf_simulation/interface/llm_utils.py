import os

import yaml
from dotenv import load_dotenv
from jinja2 import Environment, PackageLoader
from database import Database
from pydantic import BaseModel, ValidationError
from typing import NewType, Any, Optional
from openai import OpenAI
from anthropic import Anthropic
from anthropic.types import Message, ContentBlock
from enum import Enum
from typing import Literal

class LLMModel(Enum):
    def __init__(self, plain_name:str, model_name:str):
        self.plain_name = plain_name
        self.model_name = model_name

#https://stackoverflow.com/questions/29503339/how-to-get-all-values-from-python-enum-class
class GPTModel(LLMModel):
    GPT_3_5 = ("GPT 3.5", "gpt-3.5-turbo")
    GPT_4_1_MINI = ("GPT 4.1 Mini", "gpt-4.1-mini")
    GPT_4_1_NANO = ("GPT 4.1 Nano", "gpt-4.1-nano")
    GPT_4_1 = ("GPT 4.1","gpt-4.1")
    GPT_4o_MINI = ("GPT 4o Mini", "gpt-4o-mini")
    GPT_4o = ("GPT 4o", "gpt-4o")
    
    #Implicitly, the __init__ of LLModel is called

class ClaudeModel(LLMModel):
    CLAUDE_OPUS_4 = ("Opus 4", "claude-opus-4-20250514")
    CLAUDE_SONNET_4 = ("Sonnet 4", "claude-sonnet-4-20250514")
    CLAUDE_3_7_SONNET = ("Sonnet 3.7", "claude-3-7-sonnet-20250219")
    CLAUDE_3_5_HAIKU = ("Haiku 3.5", "claude-3-5-haiku-20241022")

class LLamaModel(LLMModel):
    LLAMA_3_70B = ("LLama3 70B", "llama3-70b-8192")
    LLAMA_3_8B = ("LLama3 8B", "llama3-8b-8192")
    LLAMA_3_3_70B = ("LLama3.3 70B", "llama-3.3-70b-versatile")
    LLAMA_3_1_8B = ("LLama3.1 8B", "llama-3.1-8b-instant")


SCRIPT_PATH = os.path.realpath(os.path.dirname(__file__))
API_KEY_ENV_PATH = os.path.join(SCRIPT_PATH, ".env")
load_dotenv(API_KEY_ENV_PATH)

STRUCTURAL_NOT_SUPPORTED = ["gpt-3.5-turbo"]

type AIModel = GPTModel | ClaudeModel | LLamaModel

MODELS: dict[str, list[AIModel]] = {
    "OpenAI": list(GPTModel),
    "Claude": list(ClaudeModel),
    "LLama": list(LLamaModel)
}


LLM_ROLE = "You are a central controller responsible for managing a multi-robot system."

#https://stackoverflow.com/questions/1319615/how-do-i-declare-custom-exceptions-in-modern-python

class LLMError(Exception):
    pass

# See example: # https://docs.pydantic.dev/2.3/usage/types/dicts_mapping/#typeddict
ActionID = NewType("ActionID", int)

class Action(BaseModel):
    action_id: ActionID
    executing_robot: str
    command: str
    command_arguments: list[Optional[str]]
    prerequisites: list[int]
    reasoning: str

    def to_format(self, format: Literal["json", "yaml"] ="json"):
        if format == "json":
            return self.model_dump_json(indent=2)
        else:
            return yaml.dump(self.model_dump(), indent=2)

class Plan(BaseModel):
    actions: list[Action]
    
    def to_format(self, format: Literal["json", "yaml"] = "json"):
        if format == "json":
            return self.model_dump_json(indent=2)
        else:
            return yaml.dump(self.model_dump(), indent=2)


class PromptGenerator():

    def __init__(self):
        self.db = Database()
        #template_dir = os.path.abspath(os.path.join(SCRIPT_PATH, "templates"))
        # https://jinja.palletsprojects.com/en/stable/api/#jinja2.FileSystemLoader
        self.env = Environment(
            loader=PackageLoader("mf_simulation.interface")
            #loader = FileSystemLoader(template_dir)
        )
        self.template_ = self.env.get_template("prompt.jinja")
        self.robot_abilities_path_ = os.path.join(SCRIPT_PATH,"robot_primitives.yaml")

        self.__open_ai_client = OpenAI(api_key=os.getenv('OPEN_AI_API_KEY'))
        self.__anthtropic_client = Anthropic(api_key=os.getenv('CLAUDE_API_KEY'))

    def __populate_template(self, task:str):
        
        try: 
            with open(self.robot_abilities_path_ ) as f:
                robot_abilities = yaml.dump(yaml.safe_load(f), default_flow_style=None, indent=2)
                # None == If a mapping or sequence consist only of scalars it will use "Flow Style", otherwise "Block Style"
                # See: https://stackoverflow.com/questions/56542746/read-and-dump-bracket-list-from-and-to-yaml-with-python

            robot_states = yaml.dump(self.db.get_robot_states(), default_flow_style=None, indent=2)
            object_states = yaml.dump(self.db.get_object_states(), default_flow_style=None, indent=2)

            filled_template = self.template_.render(robot_types=robot_abilities,
                                        task_description=task,
                                        robot_states=robot_states,
                                        object_states=object_states)
            
            return filled_template
        except Exception as e:
            raise LLMError("Filling out the prompt template failed")

    def generate_plan(self, task: str, model: GPTModel | ClaudeModel | LLamaModel) -> tuple[str, Plan]:
        """
        Generate an action plan for available robots using an llm that
        attempts to achieve a given task. 

        Args:
            task: task to generate the plan for
            model: Enum indicating the model to use
            format: format to return the prompt and plan in
        
        Returns:
            Json or yaml formatted tuple containing the prompt and plan (in this order).
        
        Raises:
            LLMApiError: An error occured when trying to get the response from the LLM API
            PromptCreationException: An error occured while trying to create a completed
                prompt for the task.
        """

        try:
            prompt:str = self.__populate_template(task)
     
            if isinstance(model, GPTModel):
                response = self.__send_open_ai_request(prompt, model.model_name)
            elif isinstance(model, ClaudeModel):
                response = self.__send_anthtropic_request(prompt, model.model_name)
            else:
                raise LLMError("Invalid model supplied")

            return prompt, response
        except LLMError:
            raise
            
    def __send_open_ai_request(self, content:str, model:str) -> Plan:
        """
        Send a reguest to the OpenAI api and receive a response

        Args:
            content: prompt to send the model
            model: OpenAI model to use

        Returns:
            The llm response
        
        Raises:
            LLMError: An error occured when trying to get the response from the API or
            parsing it failed
        """
        try:
            res = self.__open_ai_client.responses.parse(
                model=model,
                input=[
                    {"role": "system", "content": LLM_ROLE},
                    {"role": "user",
                    "content": content}
                ],
                text_format=Plan
            )
            
            plan: Plan | None = res.output_parsed
            
            if plan == None:
                raise LLMError("Failed to parse API response")
            
            return plan

        except LLMError:
            raise
        except Exception as e:
            raise LLMError("Error trying to get response from OpenAI API")
       
            
    def __send_anthtropic_request(self, content:str, model:str) -> Plan:
        
        print("GENERATING PLAN", flush=True)

        #https://docs.pydantic.dev/latest/concepts/json_schema/#generating-json-schema
        plan_schema: dict[str, Any] = Plan.model_json_schema()

        # https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview#json-mode
        try:
            res: Message = self.__anthtropic_client.messages.create(
                max_tokens=1024,
                tools=[{
                    "name": "plan_format", 
                    "description": "Format for a robotic plan",
                    "input_schema" : plan_schema
                }],
                tool_choice={"type": "tool", "name": "plan_format"},
                model=model,
                system=LLM_ROLE,
                messages=[{"role": "user", "content": content}]
            )

            res_content: ContentBlock = res.content[0]
            if res_content.type == "text":
                plan:str = res_content.text
            else:
                raise LLMError("Error parsing response from Anthropic API")

            validated_plan = self.__validate_output(plan)
            return validated_plan
        
        except LLMError:
            raise 
        except Exception as e:
            raise LLMError("Error trying to get response from Anthropic API", e)

    def __validate_output(self, output: str):
        
        try:
            return Plan.model_validate_json(output)
        except ValidationError:
            raise
            

