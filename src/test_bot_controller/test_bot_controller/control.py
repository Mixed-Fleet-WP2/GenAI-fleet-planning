import rclpy
import json
import collections
import threading
import tkinter as tk
from tkinter import messagebox
#Setup inside a virtual environment
import requests
import os

from forklift import Forklift



COMMON_PROMPT = """You control a forklift robot that has access to following commands:
                - pick_up(object): makes the forklift pick up an object specified as a string. Returns nothing
                - move(x,y): makes the forklift move to the specified coordinates. Takes two integers, returns
                - drop(object): makes the forklift drop an object in front of it, specified as a string. Returns nothing
                nothing\n
                """

TASK_PROMPT = "\nYour tasks is: "

FORMAT_INSTRUCTION = """You should return the proposed instructions in a form following this example:
                        [
                        {"cmd": "cmd_name",
                        "args": [arg1, arg2]
                        },
                        {"cmd": "cmd_name2",
                        "args": []
                        }
                        ...More commands
                    ]. 
                    Return only the JSON and say nothing else, do not wrap json in a comment.
                      If there are no arguments, leave the array empty.
                    You may only use the functions that were given to
                    you before in the returned JSON and nothing else. You may assume that the actions are always
                    successful.\n.
                    """

class GUI:
    def __init__(self, root, node):

        self.object_states = {"environment": [
                                {"objects": ["cube"]},
                                {"assets": ["storage_area"]},
                                {"object_positions": [{"cube": (-2, 2)}]},
                                {"asset_positions": [{"storage_area": (0, 0)}]}
                                ]
                            }

        self.root = root
        self.node = node
        self.API_KEY = os.environ.get('OPEN_AI_KEY')

        self.prompt_label = tk.Label(root, text="Enter what you want the robot to do:")
        self.prompt_label.pack()

        self.prompt_text = tk.Text(root, width=50, height=10)
        self.prompt_text.pack()

        self.start_button = tk.Button(root, text="Create an initiate plan", command=self.get_ai_response)
        self.start_button.pack()

        response_label = tk.Label(root)
        response_label.pack()

        self.json_commands = collections.deque()
    
    def get_ai_response(self, model="gpt-4o-mini"):

        #Convert the object states to a string
        object_states_str = json.dumps(self.object_states)

        instructions = COMMON_PROMPT +  object_states_str + TASK_PROMPT + self.prompt_text.get("1.0", "end-1c") + "\n" + FORMAT_INSTRUCTION
        print(instructions)

        api_key = self.API_KEY
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        url = "https://api.openai.com/v1/chat/completions"

        data = {
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
            code = res['choices'][0]['message']['content']
            self.parse_and_write_ai_response(code)
            return
        else:
            raise Exception(f"Request failed with status code {response.status_code}: {response.text}")

    def parse_and_write_ai_response(self, response):

        try:
            with open('instructions.json', 'w') as json_file:
                #Write the response string to a json file
                json_file.write(response)
        except Exception as e:
            print("Error writing json")

        self.load_json_commands()
        self.start_execution()

    def load_json_commands(self):
        try:
            with open('instructions.json') as json_file:
                data = json.load(json_file)
                for item in data:
                    cmd_pair = (item["cmd"], item["args"])
                    self.json_commands.append(cmd_pair)
        except Exception as e:
            print("Error loading json",e)
    
    def start_execution(self):
        self.node.start_execution(self.json_commands)


def main(args=None):
    rclpy.init(args=args)
    node = Forklift()
    
    root = tk.Tk()
    app = GUI(root, node)
    
    #Separate thread for the ROS2 node, so that the gui can run in the main thread
    spin_thread = threading.Thread(target=rclpy.spin, args=(node,))
    spin_thread.start()

    root.protocol("WM_DELETE_WINDOW", lambda: on_closing(root, node))
    root.mainloop()

def on_closing(root, node):

    node.destroy_node()
    rclpy.shutdown()
    root.destroy()

if __name__ == '__main__':
    main()
