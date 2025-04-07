import rclpy
import json
from threading import Thread
import tkinter as tk
import requests
import os
import re

from rclpy.executors import MultiThreadedExecutor


from controller import Controller
from dotenv import load_dotenv

#path_to_env = os.path.expanduser('~/.forklift_controller/.env')
load_dotenv()

CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
OPEN_AI_API_KEY = os.getenv('OPEN_AI_API_KEY')

CLAUDE_MODELS = ["claude-3-sonnet-20240229", "claude-3-5-sonnet-20240620", "claude-3-opus-20240229", "claude-3-haiku-20240307"]
OPEN_AI_MODELS = ["gpt-4o-mini", "gpt-3.5-turbo", "gpt-4o"]
LLAMA_MODELS = ["llama3.1-405b","llama3.1-70b","llama3.1-8b","llama3-70b","llama3-8b", "llama2-13b"]


COMMON_PROMPT = """You control a fleet of robots and have access to following commands:
                - pick_up(object): makes a robot pick up an object specified as a string. Returns nothing
                - move(x,y): makes a robot move to the specified coordinates. Takes two integers, returns
                - drop(object): makes the robot drop an object in front of it, specified as a string. Returns nothing\n\n
                """

TASK_PROMPT = "\n\nYour tasks is: {task}"

FORMAT_INSTRUCTION = """\n\n
                        You should return the proposed instructions in a form following this example:
                        [
                        {"uuid": 1,
                        "executor": "robot_1",
                        "cmd": "cmd_name",
                        "args": {
                            "arg1": arg1,
                            "arg2": arg2,
                            "arg3": arg3
                        },
                        "reason": "Explain the reasoning behind command here"
                        },
                        {"uuid": 2,
                        "executor": "robot_2",
                        "cmd": "cmd_name2",
                        "args": {
                            "arg1": arg1,
                            "arg2": arg2,},
                        "prerequisite": [1]
                        "reason": "Explain the reasoning behind command 2 here"
                        
                        }
                        ...More commands
                    ]. 
                    Concrete example:
                    [
                        {"uuid": 1,
                        "executor": "drone_1",
                        "cmd": "inspect_area",
                        "args": {"x": 0, "y": 0},
                        "reason": "Inspect the area to find the object"
                        }
                    ]

                    Return only the JSON and say nothing else. Do not wrap json in a comment or do anything else
                    with it, just return plain json object. Do not add any other text or explanation. Follow the format strictly.

                    If there are no arguments, leave the array empty.
                    You may only use the functions that were given to
                    you and nothing else. Use only the functions
                    you deem necessary. If some action requires another to be completed before it can be started
                    use the 'prerequisite field" and insert the id of the prequisite action as an item 
                    in the array. If actions can be executed in parallel (for example two robots moving
                    at the same time), leave the array empty. In addition to the commands, 
                    explain the reasoning behind the commands and include
                    it in the JSON as string following the format specified before, do not insert comments
                    outside the JSON. 
                    """

class GUI:
    def __init__(self, root):

        self.object_states = {
                            "environment": {
                                "objects": ["cube"],
                                "locations": ["storage_area"],
                                "robots":["forklift_1", "forklift_2"],
                                "object_positions": {
                                "cube": None
                                },
                                "location_positions": {
                                "storage_area": (0, 0)
                                }
                            }
                        }

        
        self.json_instructions = {}

        self.controller:Controller = Controller()

        self.model = OPEN_AI_MODELS[0]
        self.root = root
        self.OPEN_AI_API_KEY = os.environ.get('OPEN_AI_KEY')
        self.CLAUDE_API_KEY = os.environ.get('CLAUDE_KEY')
        self.LLAMA_API_KEY = os.environ.get('LLAMA_KEY')

        self.prompt_label = tk.Label(root, text="Enter what you want the robot to do:")
        self.prompt_label.grid(row=0, columnspan=6, pady=(10, 10))

        self.header_input = tk.Label(root, text="Input:")
        self.header_input.grid(row=1, columnspan=2, column=0)

        self.header_prompt = tk.Label(root, text="Completed prompt:")
        self.header_prompt.grid(row=1, columnspan=2, column=2)

        self.header_output = tk.Label(root, text="The produced plan:")
        self.header_output.grid(row=1, columnspan=2, column=4)

        self.prompt_text = tk.Text(root, width=50, height=20)
        self.prompt_text.grid(row=2, columnspan=2)

        #Area for the completed prompt
        self.prompt_area = tk.Text(root,width=50, height=20)
        self.prompt_area.grid(sticky="N", column=2, row=2, columnspan=2)
        self.prompt_area.configure(state="disabled")

        self.response_area = tk.Text(root,width=50, height=20)
        self.response_area.grid(sticky="N", column=4, row=2, columnspan=2)
        self.response_area.configure(state="disabled")

         # Create the dropdown and place it in the left corner
        OPTIONS = OPEN_AI_MODELS + CLAUDE_MODELS + LLAMA_MODELS
        self.variable = tk.StringVar(root)
        self.variable.set(OPTIONS[0])  # Default value
        self.dropdown = tk.OptionMenu(root, self.variable, *OPTIONS, command=self.callback)
        self.dropdown.grid(row=3, column=0, sticky="w")
        
        self.btn_frame = tk.Frame(root)
        self.btn_frame.grid(row=3, column=2, columnspan=2)

        self.start_button = tk.Button(self.btn_frame, text="Create and initiate plan", command=self.get_ai_response)
        self.start_button.pack(anchor='center')
    
    def callback(self,selection):
        self.model = selection

    def get_ai_response(self):
        
        is_claude = False
        model_name = self.model

        object_pos_dict = self.controller.get_object_positions()
        self.object_states["environment"]["object_positions"] = object_pos_dict
       
        #Convert the object states to a string
        object_states_str = json.dumps(self.object_states)
        
        #Get the textual content of the input field
        task = self.prompt_text.get("1.0", "end-1c")
        task = TASK_PROMPT.format(task=task)
        
        instructions = COMMON_PROMPT +  object_states_str + task + FORMAT_INSTRUCTION
        
        #Courtesy of ChatGPT
        # Remove leading and trailing whitespace from each line
        text = "\n".join(line.strip() for line in instructions.splitlines())
        # Replace multiple spaces within lines with a single space
        text = "\n".join(re.sub(r'\s+', ' ', line) for line in text.splitlines())
        
        self.prompt_area.configure(state="normal")
        self.prompt_area.insert("1.0", text)
        self.prompt_area.configure(state="disable")
        
        if model_name in OPEN_AI_MODELS:
            api_key = OPEN_AI_API_KEY
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", 'content-type': 'application/json'}
        elif model_name in CLAUDE_MODELS:
            is_claude = True
            api_key = CLAUDE_API_KEY
            url = "https://api.anthropic.com/v1/messages"
            headers = {
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json'
            }
        elif model_name in LLAMA_MODELS:
            url = 'https://api.llama-api.com/chat/completions'
            api_key = self.LLAMA_API_KEY
            headers = {"Authorization": f"Bearer {api_key}", 'content-type': 'application/json'}
        else:
            err = f"Unsupported model {model_name}"
            return
        
        model = model_name
        
        data = {
            "max_tokens":1024,
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": f"{instructions}",
                },
            ],
        }

        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            res = response.json()
            
            #Claude's API follows a different request format, thus this is needed
            if is_claude:
                code = res['content'][0]['text']
            else:
                code = res['choices'][0]['message']['content']

            self.json_instructions = code
            self.parse_and_write_ai_response(code, model_name)
        else:
            raise Exception(f"Request failed with status code {response.status_code}: {response.text}")

    def parse_and_write_ai_response(self, response, model_name):

        #Write the output to gui
        header = f"Response written by {model_name}\n\n"
        self.response_area.configure(state="normal")
        self.response_area.insert("1.0", header + response)
        self.response_area.configure(state="disable")
       
        #Start execution on separate thread, because otherwise GUI doesn't have time to update the view
        execution_thread = Thread(target=self.start_execution, daemon=True)
        execution_thread.start()
        execution_thread.join

    def start_execution(self):

        commands = json.loads(self.json_instructions)

        for command in commands:
            executing_robot = command["executor"]
            command_name = command["cmd"]
            args:dict = command["args"]
            uuid = command["uuid"]
            prereguisites = command.get("prerequisite", None)

            thread = Thread(target=self.controller.run_action, args=(executing_robot, command_name, args, uuid, prereguisites), daemon=True)
            thread.start()
            #thread.join()

def main(args=None):

    #rclpy.init(args=args)

    #https://robotics.stackexchange.com/questions/106026/ros2-multi-nodes-each-on-a-thread-in-same-process
    #executor = MultiThreadedExecutor()

    root = tk.Tk()
    app = GUI(root)

    #Separate thread for the ROS2 node, so that the gui can run in the main thread
    #spin_thread = Thread(target=executor.spin, daemon=True)
    #spin_thread.start()

    #root.protocol("WM_DELETE_WINDOW", lambda: on_closing(root, spin_thread, executor))
    root.protocol("WM_DELETE_WINDOW", lambda: on_closing(root))
    root.mainloop()

#def on_closing(root, spin_thread:Thread, executor:MultiThreadedExecutor):
def on_closing(root):
    # Stop executor's spinning thread
    #executor.shutdown()
    #spin_thread.join() 

    #rclpy.shutdown()

    root.destroy()

if __name__ == '__main__':
    main()