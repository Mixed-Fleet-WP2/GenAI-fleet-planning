import json
from threading import Thread
import os

from rclpy.executors import MultiThreadedExecutor
import yaml
from controller import Controller
from dotenv import load_dotenv
from jinja2 import Environment, PackageLoader, FileSystemLoader



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

def populate_template(task:str):
    template_dir = os.path.abspath(os.path.join(SCRIPT_PATH, "templates"))
    # https://jinja.palletsprojects.com/en/stable/api/#jinja2.FileSystemLoader
    env = Environment(
        #loader=PackageLoader("mf_simulation")
        loader = FileSystemLoader(template_dir)
    )
    template = env.get_template("prompt.yaml")

    # https://jinja.palletsprojects.com/en/stable/api/#jinja2.Template.render
    robot_abilities_path = os.path.abspath(os.path.join(SCRIPT_PATH, "..", "config", "robot_primitives.yaml"))
    with open(robot_abilities_path) as f:
        robot_abilities = yaml.dump(yaml.safe_load(f), default_flow_style=None, indent=2)
        # None == If a mapping or sequence consist only of scalars it will use "Flow Style", otherwise "Block Style"
        # See: https://stackoverflow.com/questions/56542746/read-and-dump-bracket-list-from-and-to-yaml-with-python

    ready = template.render(robot_types=robot_abilities,
                            task_description=task
                            
                            )
    print(ready)

   
def generate_plan(task, model):
    populate_template(task)

def send_open_ai_request(task, model):
    pass