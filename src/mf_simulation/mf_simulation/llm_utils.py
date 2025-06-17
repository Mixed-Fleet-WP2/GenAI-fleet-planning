import json
from threading import Thread
import os

from tkinter import ttk

from rclpy.executors import MultiThreadedExecutor
import yaml
from controller import Controller
from dotenv import load_dotenv
from jinja2 import Environment, PackageLoader, FileSystemLoader

load_dotenv()

SCRIPT_PATH = os.path.realpath(os.path.dirname(__file__))

CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
OPEN_AI_API_KEY = os.getenv('OPEN_AI_API_KEY')

OPEN_AI_MODELS = ["gpt-3.5-turbo", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-4.1", "gpt-4o-mini", "gpt-4o"]
STRUCTURAL_NOT_SUPPORTED = ["gpt-3.5-turbo"]

MODELS = {"Open AI" : OPEN_AI_MODELS,
         "Anthtropic": ["test"]}

def populate_template():
    template_dir = os.path.abspath(os.path.join(SCRIPT_PATH, "templates"))
    # https://jinja.palletsprojects.com/en/stable/api/#jinja2.FileSystemLoader
    env = Environment(
        #loader=PackageLoader("mf_simulation")
        loader = FileSystemLoader(template_dir)
    )
    template = env.get_template("prompt.yaml")
    #https://jinja.palletsprojects.com/en/stable/api/#jinja2.Template.render
    robot_abilities_path = os.path.abspath(os.path.join(SCRIPT_PATH, "..", "config", "robot_primitives.yaml"))
    with open(robot_abilities_path) as f:
        #robot_abilities = f.read()
        content = yaml.safe_load(f)
        # None - If a mapping or sequence consist only of scalars it will use "Flow Style", otherwise "Block Style"
        # See: https://stackoverflow.com/questions/56542746/read-and-dump-bracket-list-from-and-to-yaml-with-python
        string = yaml.dump(content, default_flow_style=None, indent=2)

    ready = template.render(robot_types=string)
    print(ready)

   
def generate_plan(task, model):
    populate_template()

def send_open_ai_request(task, model):
    pass