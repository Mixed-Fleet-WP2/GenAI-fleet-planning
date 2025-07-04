import json
from threading import Thread
import os

import yaml
from controller import Controller
from dotenv import load_dotenv
from jinja2 import Environment, PackageLoader, FileSystemLoader
from database import Database
from pydantic import BaseModel
from typing import Union, TypedDict, Dict, NewType, Any, Optional
from openai import OpenAI


SCRIPT_PATH = os.path.realpath(os.path.dirname(__file__))
API_KEY_ENV_PATH = os.path.join(SCRIPT_PATH, ".env")
load_dotenv(API_KEY_ENV_PATH)

CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
OPEN_AI_API_KEY = os.getenv('OPEN_AI_API_KEY')

OPEN_AI_MODELS = ["gpt-3.5-turbo", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-4.1", "gpt-4o-mini", "gpt-4o"]
STRUCTURAL_NOT_SUPPORTED = ["gpt-3.5-turbo"]

MODELS = {"Open AI" : OPEN_AI_MODELS,
         "Anthtropic": ["test"],
         "Meta": ["llama3-70b-8192", "llama3-8b-8192", "llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
        }


# See example: # https://docs.pydantic.dev/2.3/usage/types/dicts_mapping/#typeddict
ActionID = NewType("ActionID", int)

class Action(BaseModel):
    action_id: ActionID
    executing_robot: str
    command: str
    command_arguments: list[Optional[str]]
    prerequisites: list[int]
    reasoning: str

class Plan(BaseModel):
    actions: list[Action]


class PromptGenerator():

    def __init__(self):
        self.db = Database()
        template_dir = os.path.abspath(os.path.join(SCRIPT_PATH, "templates"))
        # https://jinja.palletsprojects.com/en/stable/api/#jinja2.FileSystemLoader
        self.env = Environment(
            loader=PackageLoader("mf_simulation.interface")
            #loader = FileSystemLoader(template_dir)
        )
        self.template_ = self.env.get_template("prompt.jinja")
        self.robot_abilities_path_ = os.path.abspath(os.path.join(SCRIPT_PATH,
                                                                 "..",
                                                                "config", 
                                                                "robot_primitives.yaml"))

        self.open_ai_client = OpenAI(api_key=os.getenv('OPEN_AI_API_KEY'))

        self.plan_json_ = ""
        self.plan_yaml_ = ""

    def populate_template_(self, task:str):
    
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

   
    def generate_plan(self, task: str, model: str="gpt-4o-mini") -> tuple[str, str]:
        """
        Generate an action plan for available robots using an llm that
        attempts to achieve a given task. 

        Args:
            task: task to generate the plan for
            model: llm model to use
            format: format to return the prompt and plan in
        
        Returns:
            Json or yaml formatted tuple containing the prompt and plan (in this order)
        """

        prompt = self.populate_template_(task)
        
  
        if model in OPEN_AI_MODELS:
            response = self.send_open_ai_request(prompt, model)
        
        res_obj = response.model_dump()
       
        return prompt, response
            
    def send_open_ai_request(self, content, model):
        
        res = self.open_ai_client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": "You are a central controller responsible for managing a multi-robot system."},
                {"role": "user",
                 "content": content}
            ],
            text_format=Plan
        )
        return res.output_parsed


