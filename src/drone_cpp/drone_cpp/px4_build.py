#!/usr/bin/env python3
import os
import subprocess
import sys
import time
import atexit
import re
from ament_index_python.packages import get_package_share_directory, get_package_prefix

HOME_DIR:str = os.path.expanduser("~")

#PX4_PATH is always defined as it becomes from the launch file
#where there exists a default value which is ~/PX4-Autopilot
PX4_DIR:str = os.environ.get("PX4_PATH")

PX4_BINARY:str = os.path.join(PX4_DIR, "build/px4_sitl_default/bin/px4")

# https://stackoverflow.com/questions/320232/ensuring-subprocesses-are-dead-on-exiting-python-program
def cleanup(processes, **kwargs):
    timeout_sec = 5
    for p in processes: # list of your processes
        p_sec = 0
        for second in range(timeout_sec):
            if p.poll() == None:
                time.sleep(1)
                p_sec += 1
        if p_sec >= timeout_sec:
            p.kill() # supported from python 2.6
    print('cleaned up!', flush=True)


def build_px4():

    try:
        #Environment variables are set by the calling launch file and are fetched with os.environ
        build_process = subprocess.run(["make", "px4_sitl_default"], cwd=PX4_DIR, check=True, env=os.environ, capture_output=False, text=True)
    except FileNotFoundError:
        print(f"ERROR: The directory {PX4_DIR} does not exist", file=sys.stderr, flush=True)
        sys.exit(1)
    except subprocess.CalledProcessError:
        print("ERROR: PX4 build failed.", file=sys.stderr, flush=True)
        sys.exit(1)


def main():
    
    pkg_install = get_package_share_directory('drone_cpp')
    drone_node_path = os.path.join(pkg_install, 'lib', 'drone_cpp', 'drone_node')
    
    processes:list[subprocess.Popen] = []
    if not os.path.exists(PX4_BINARY):
        print("PX4 not built. Building now.", flush=True)
        build_px4()
    else:
        print("PX4 already built, proceeding", flush=True)
    try:
        
        path = subprocess.check_output(["which", "micro-xrce-dds-agent"], text=True).strip()
        
        # Popen is non-blocking
        # See: # https://stackoverflow.com/questions/39187886/what-is-the-difference-between-subprocess-popen-and-subprocess-run
        run_micro_agent = subprocess.Popen([path, 'udp4', '-p', '8888'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=True,  
                                bufsize=1,           
                                universal_newlines=True)
        processes.append(run_micro_agent)

        # Wait for a while to the agent to start (should be fast)
        time.sleep(2)

        # Env variables are passed implicitly:
        # From: https://docs.python.org/3/library/subprocess.html#subprocess.Popen
        # If env is not None, it must be a mapping that defines the environment variables for the new process;
        # these are used instead of the default behavior of inheriting the current process’ environment.
        px4_process = subprocess.Popen(
                                [PX4_BINARY],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=True,  
                                bufsize=1,           
                                universal_newlines=True
                            )
        processes.append(px4_process)
        
        atexit.register(cleanup, processes)
        
        try:
            for line in px4_process.stdout:
                info_line = line.strip()
                is_success_msg = re.search(r'Ready for takeoff!', info_line)
                if is_success_msg:
                    ros_node_process = subprocess.Popen(
                        ['ros2', 'run', 'drone_cpp', 'drone_node',
                        '--ros-args', '-p', 'use_sim_time:=True']
                    )
                    print("Flight node started", flush=True)
                    processes.append(ros_node_process)
                    break
            for line in px4_process.stdout:
                info_line = line.strip()
                print(info_line, flush=True)

            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            print("Exiting", flush=True)
        except Exception as e:
            print(e, flush=True)
        
    except Exception as e:
        print("Starting px4 failed", flush=True)
        print(e)
#Ready for takeoff!
if __name__ == "__main__":
    main()