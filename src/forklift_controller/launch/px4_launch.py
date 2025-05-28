#!/usr/bin/env python3
import os
import subprocess
import sys

HOME_DIR = os.path.expanduser("~")

#DEFAULT_PATH = os.path.join(HOME_DIR, 'PX4-Autopilot')
#PX4_PATH is always defined as it becomes from the launch file
#where there exists a default value which is ~/PX4-Autopilot
PX4_DIR = os.environ.get("PX4_PATH")

PX4_BINARY = os.path.join(PX4_DIR, "build/px4_sitl_default/bin/px4")

ENV_VARS = {'PX4_SYS_AUTOSTART': '4001',
            
            }

def build_px4():

    try:
        build_process = subprocess.run(["make", "px4_sitl_default"], cwd=PX4_DIR, check=True, env=os.environ, capture_output=False, text=True)
    except FileNotFoundError:
        print(f"ERROR: The directory {PX4_DIR} does not exist", file=sys.stderr, flush=True)
        sys.exit(1)
    except subprocess.CalledProcessError:
        print("ERROR: PX4 build failed.", file=sys.stderr, flush=True)
        sys.exit(1)


def main():
    print(os.environ['PX4_GZ_MODEL'])
    
    if not os.path.exists(PX4_BINARY):
        print("PX4 not built. Building now.", flush=True)
        build_px4()
    else:
        print("PX4 already built, proceeding", flush=True)

if __name__ == "__main__":
    main()
