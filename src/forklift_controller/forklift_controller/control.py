import rclpy
import json
import collections
import threading
import tkinter as tk
import requests
import os
import re
import sys

from rclpy.executors import MultiThreadedExecutor

from forklift import Forklift

CLAUDE_MODELS = ["claude-3-sonnet-20240229", "claude-3-5-sonnet-20240620", "claude-3-opus-20240229", "claude-3-haiku-20240307"]
OPEN_AI_MODELS = ["gpt-4o-mini", "gpt-3.5-turbo", "gpt-4o"]
LLAMA_MODELS = ["llama3.1-405b","llama3.1-70b","llama3.1-8b","llama3-70b","llama3-8b", "llama2-13b"]


COMMON_PROMPT = """You control a fleet of robots and have access to following commands:
                - pick_up(robot, object): makes the robot specified by the argument pick up an object specified as a string. Returns nothing
                - move(robot, x,y): makes the robot specified by the argument move to the specified coordinates. Takes two integers, returns
                - drop(robot, object): makes the robot specified by the argument drop an object in front of it, specified as a string. Returns nothing\n\n
                """

TASK_PROMPT = "\n\nYour tasks is: {task}"

FORMAT_INSTRUCTION = """\n\nYou should return the proposed instructions in a form following this example:
                        [
                        {"cmd": "cmd_name",
                        "args": [arg1, arg2, arg3],
                        "reason": "Explain the reasoning behind command here"
                        },
                        {"cmd": "cmd_name2",
                        "args": [arg1, arg2],
                        "reason": "Explain the reasoning behind command 2 here"
                        }
                        ...More commands
                    ]. 
                    Return only the JSON and say nothing else, do not wrap json in a comment.
                      If there are no arguments, leave the array empty.
                    You may only use the functions that were given to
                    you before in the returned JSON and nothing else. You may assume that the actions are always
                    successful. Use only the functions
                    you deem necessary. In addition to the commands, explain the reasoning behind the commands an include
                    it in the JSON as string following the format specified before, do not insert comments
                    outside the JSON. 
                    """

class GUI:
    def __init__(self, root, nodes):

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

        
        self.json_commands = collections.deque()
        self.command_lock = threading.Lock()
        self.nodes = nodes

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

        self.start_button = tk.Button(self.btn_frame, text="Create an initiate plan", command=self.get_ai_response)
        self.start_button.pack(anchor='center')
    
    def callback(self,selection):
        self.model = selection

    def get_ai_response(self):
        
        is_claude = False
        model_name = self.model

        temp_node = self.nodes["forklift_1"]
        x,y = temp_node.get_cube_pos()
        self.object_states["environment"]["object_positions"]["cube"] = (x,y)
       
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
            api_key = self.OPEN_AI_API_KEY
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", 'content-type': 'application/json'}
        elif model_name in CLAUDE_MODELS:
            is_claude = True
            api_key = self.CLAUDE_API_KEY
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
            
            if is_claude:
                code = res['content'][0]['text']
            else:
                code = res['choices'][0]['message']['content']

            self.parse_and_write_ai_response(code, model_name)
        else:
            raise Exception(f"Request failed with status code {response.status_code}: {response.text}")

    def parse_and_write_ai_response(self, response, model_name):

        try:
            with open('instructions.json', 'w') as json_file:
                #Write the response string to a json file
                json_file.write(response)
                #Write the output to gui
                header = f"Response written by {model_name}\n\n"
                self.response_area.configure(state="normal")
                self.response_area.insert("1.0", header + response)
                self.response_area.configure(state="disable")
        except Exception as e:
            print("Error writing json",e)

        self.load_json_commands()

        #Start execution on separate thread, because otherwise GUI doesn't have time to update the view
        execution_thread = threading.Thread(target=self.start_execution, daemon=True)
        execution_thread.start()
        execution_thread.join

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
        with self.command_lock:
            commands = self.json_commands

            while commands:
                func_name, args = commands.popleft()
                
                node_name = args[0]
                node = self.nodes[node_name]
                node.get_logger().info(node_name)

                if func_name == "move":
                    node.get_logger().info("Move")
                    
                    x = float(args[1])
                    y = float(args[2])

                    response = node.move(x, y)
                    was_success = bool(response.success)

                    if not was_success:
                        raise Exception("Movement to point was not successful")

                elif func_name == "pick_up":
                    node.get_logger().info("Pick up")
                    object = args[1]
                    response = node.pick_up(object)
                    was_success = bool(response.success)

                    if not was_success:
                        raise Exception("Picking up the object was not successful")
                    
                elif func_name == "drop":
                    node.get_logger().info("Drop")
                    object = args[1]
                    response = node.drop(object)
                    was_success = bool(response.success)

                    if not was_success:
                        raise Exception("Dropping the object was not successful")
                    
                node.get_logger().info("All commands executed")



def main(args=None):

    amount_of_robots = int(sys.argv[1])

    
    rclpy.init(args=args)

    executor = MultiThreadedExecutor()
    nodes = {}

    for i in range(0,amount_of_robots):
        robot = Forklift(node_name=f'forklift_{i+1}')
        nodes[f'forklift_{i+1}'] = robot
        executor.add_node(robot)


    root = tk.Tk()
    app = GUI(root, nodes)

    #Separate thread for the ROS2 node, so that the gui can run in the main thread
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    root.protocol("WM_DELETE_WINDOW", lambda: on_closing(root, spin_thread, executor, nodes))
    root.mainloop()


def on_closing(root, spin_thread, executor, nodes):
    # Stop executor's spinning thread
    executor.shutdown()
    spin_thread.join() 

    # Destroy all forklifts
    for node in nodes.values():
        node.destroy_node()

    rclpy.shutdown()

    root.destroy()

if __name__ == '__main__':
    main()
