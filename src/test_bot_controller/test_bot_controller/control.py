import rclpy
from rclpy.node import Node
import json

import collections
from movement_interface.srv import MovementSuccess, Pickup
import threading
import tkinter as tk
from tkinter import messagebox
#Setup inside a virtual environment
import requests
import os

class Forklift(Node):

    def __init__(self):
        super().__init__('forklift_robot')
        self.move_cli = self.create_client(MovementSuccess, 'move')
        self.pick_up_cli = self.create_client(Pickup, 'pick_up')  
        self.json_commands = collections.deque()
        self.move_req = MovementSuccess.Request()
        self.pick_up_req = Pickup.Request()

        while not self.move_cli.wait_for_service(timeout_sec=1.0) and not self.pick_up_cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Services not available yet')

    def move(self, x, y):
        self.move_req.x = x
        self.move_req.y = y
        return self.move_cli.call(self.move_req)

    def pick_up(self):
        return self.pick_up_cli.call(self.pick_up_req)

    def execute_commands(self, commands):
        self.index_of_current_command = 0

        while commands:
            func_call, args = commands.popleft()
            
            if func_call == "move":
                self.get_logger().info("Move")
                self.get_logger().info(str(args[0]))
                x = int(args[0])
                y = int(args[1])

                response = self.move(x, y)
                was_success = bool(response.success)

                if not was_success:
                    raise Exception("Movement was not successful")

            elif func_call == "pick_up":
                self.get_logger().info("Pick up")
                response = self.pick_up()
                was_success = bool(response.success)

                if not was_success:
                    raise Exception("Picking up the object was not successful")
            
            self.index_of_current_command += 1

        self.get_logger().info("All commands executed")
    
    def start_execution(self, commands):

        exec_thread = threading.Thread(target=self.execute_commands, args=(commands,))
        exec_thread.start()

COMMON_PROMPT = """You control a forklift robot that has access to following commands:
                - pick_up(object): makes the forklift pick up an object specified as a string. Returns nothing
                - move(x,y): makes the forklift move to the specified coordinates. Takes two integers, returns
                nothing\n
                """

TASK_PROMPT = "\nYour tasks is: "

FORMAT_INSTRUCTION = """You should return the proposed instructions in a form following this example:
                        [
                        {"cmd": "cmd_name",
                        "args": [arg1, arg2]
                        },
                        [
                        {"cmd": "cmd_name2",
                        "args": []
                        }
                        ...More commands
                    ]. 
                    Return only the JSON and say nothing else. If there are no arguments, leave the array empty.
                    You may only use the functions that were given to
                    you before in the returned JSON nothing else. You may assume that the actions are always
                    successful\n.
                    """


class ForkliftApp:
    def __init__(self, root, node):

        self.object_states = {"environment": [
                                {"objects": ["container"]},
                                {"assets": ["storage_area"]},
                                {"object_positions": [{"container": (-2, 2)}]},
                                {"asset_positions": [{"storage_area": (0, 0)}]}
                                ]
                            }

        self.root = root
        self.node = node
        self.API_KEY = os.environ.get('OPEN_AI_KEY')

        self.prompt_label = tk.Label(root, text="Enter your prompt for the AI:")
        self.prompt_label.pack()

        self.prompt_text = tk.Text(root, width=50, height=10)
        self.prompt_text.pack()

        self.start_button = tk.Button(root, text="Send and initiate", command=self.get_ai_response)
        self.start_button.pack()

        response_label = tk.Label(root)
        response_label.pack()

        self.json_commands = collections.deque()
    
    def get_ai_response(self, messages=None, model="gpt-3.5-turbo"):

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
            "model": "gpt-3.5-turbo",
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
            print("Error loading json")
    
    def start_execution(self):
        try:
            print("Starting execution")
            self.node.start_execution(self.json_commands)
        except Exception as e:
            messagebox.showerror("Error", str(e))

def main(args=None):
    rclpy.init(args=args)
    node = Forklift()
    
    root = tk.Tk()
    app = ForkliftApp(root, node)
    

    spin_thread = threading.Thread(target=rclpy.spin, args=(node,))
    spin_thread.start()


    root.protocol("WM_DELETE_WINDOW", lambda: on_closing(root, node))
    root.mainloop()

def on_closing(root, node):
    if messagebox.askokcancel("Quit", "Do you want to quit?"):
        node.destroy_node()
        rclpy.shutdown()
        root.destroy()

if __name__ == '__main__':
    main()
