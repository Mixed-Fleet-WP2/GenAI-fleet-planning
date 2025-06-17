import rclpy
import json
from threading import Thread
import os

from tkinter import ttk

from rclpy.executors import MultiThreadedExecutor
import yaml
from controller import Controller
from dotenv import load_dotenv

load_dotenv()

SCRIPT_PATH = os.path.realpath(__file__)

CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
OPEN_AI_API_KEY = os.getenv('OPEN_AI_API_KEY')

OPEN_AI_MODELS = ["gpt-3.5-turbo", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-4.1", "gpt-4o-mini", "gpt-4o"]
STRUCTURAL_NOT_SUPPORTED = ["gpt-3.5-turbo"]

MODELS = {"Open AI" : OPEN_AI_MODELS,
         "Anthtropic": ["test"]}

