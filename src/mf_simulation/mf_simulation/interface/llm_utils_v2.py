import os

import yaml
from dotenv import load_dotenv
from jinja2 import Environment, PackageLoader
from mf_simulation.interface.database import Database
from pydantic import BaseModel, ValidationError
from typing import  Literal
from openai import OpenAI
from anthropic import Anthropic
from anthropic.types import Message, ContentBlock
from enum import Enum
from types import MappingProxyType
from mf_simulation.interface.plan_format import PlanFromLLM, ActionFromLLM

import instructor

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
    LLAMA_3_1_8B = ("LLama3.1 8B", "llama-3.1-8B") # Local model with llama.cpp ONLY THAT WORKS
    LLAMA_3_2_8B = ("LLama3.2 8B", "llama-3.2-8b-instruct") # Local model with llama.cpp


SCRIPT_PATH = os.path.realpath(os.path.dirname(__file__))
API_KEY_ENV_PATH = os.path.join(SCRIPT_PATH, ".env")
load_dotenv(API_KEY_ENV_PATH)

STRUCTURAL_NOT_SUPPORTED = ["gpt-3.5-turbo"]

AIModel = GPTModel | ClaudeModel | LLamaModel

MODELS: MappingProxyType[Literal["OpenAI", "Claude", "LLama"], list[AIModel]] = MappingProxyType({
    "OpenAI": list(GPTModel),
    "Claude": list(ClaudeModel),
    "LLama": list(LLamaModel),
})


LLM_ROLE = "You are a central controller responsible for managing a multi-robot system."

#https://stackoverflow.com/questions/1319615/how-do-i-declare-custom-exceptions-in-modern-python

class LLMError(Exception):
    pass

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

    def generate_plan(self, task: str, model: GPTModel | ClaudeModel | LLamaModel, feedback_signal) -> tuple[str, PlanFromLLM]:
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
     
            if isinstance(model, (GPTModel, ClaudeModel, LLamaModel)):
                response: PlanFromLLM = self.__send_llm_request(prompt, model)
            else:
                raise LLMError("Invalid model supplied")

            return prompt, response
        except LLMError:
            raise
    
    def __send_llm_request(self, content:str, model: AIModel) -> PlanFromLLM:
        client = self.__create_client(model)

        try:
            response: PlanFromLLM = client.chat.completions.create(
                model=model.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": LLM_ROLE,
                    },
                    {
                        "role": "user",
                        "content": content,
                    }
                ],
                response_model=PlanFromLLM,
            )
            return response
        except ValidationError as ve:
            raise LLMError("Response from LLM did not match expected format") from ve
        except Exception as e:
            print("Exception when calling LLM API:", e, flush=True)
            raise LLMError("Error trying to get response from LLM API") from e
        
    def __create_client(self, model: AIModel) -> instructor.Instructor:

        base_url = None
        match model:
            case GPTModel():
                provider = "openai"
                api_key = os.getenv('OPEN_AI_API_KEY')
            case ClaudeModel():
                provider = "anthropic"
                api_key = os.getenv('CLAUDE_API_KEY')
            case LLamaModel():
                provider = "ollama"
                api_key = "not-required"
                base_url = "http://192.168.0.104:11434/v1"
            case _:
                raise LLMError("Invalid model supplied")
        
        if base_url is not None:
            print("Sending request to url:", base_url, flush=True)
            client = instructor.from_provider(
                f"{provider}/{model.model_name}",
                api_key=api_key,
                base_url=base_url,
                # This module already runs in a separate thread
                # so this can be sync
                async_client=False
            )
        else:
   
            client = instructor.from_provider(
                f"{provider}/{model.model_name}",
                api_key=api_key,
                async_client=False
            )
        return client
        

            

