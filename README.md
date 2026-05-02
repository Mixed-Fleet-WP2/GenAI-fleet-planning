# Programming robotic fleets utilising large language models

## Overview

This repository contains research code for the Mixed Fleet project
researched at Tampere University. The work is associated
with **Work Package 2: Programming Multi-Machine Fleets (WP2)** of the project which you can read more about [here](https://blogs.tuni.fi/cs/projects/mixed-fleet-cross-disciplinary-work-towards-seamless-collaboration-between-mobile-work-machines-and-humans/). The aim of this repository is to provide a proof-of-concept application of Large Language Models in the programming of robotic fleets. Blog post concerning the subject can be read [here](https://blogs.tuni.fi/cs/projects/first-steps-towards-programming-mixed-fleet-systems-by-domain-experts/).

**This document will be continously updated during the course of the project**

## Running the Meteor simulation

Instructions are provided for native install. Docker install is work in progress
under branch *meteor_sim_env_dockerized*

### Installing natively

The simulation in this repository uses [ROS2 (Robot Operating System)](https://docs.ros.org/en/jazzy/index.html) and the open-source robotics simulator [Gazebo](https://gazebosim.org/home). The used environment is as follows:

- ROS2 version Jazzy Jalisco
- Gazebo version Harmonic
- Nav2 navigation stack
- **Ubuntu 24.04 Noble Numbat** (has been successfully ran on WSL2)
- Python 3 (tested with 3.12 which is the default Noble install)
- C/C++ compiler supporting C++17
- RTX 5070 TI 16gb

If the system has no GPU available, the real-time-factor of the simulation is most likely
too low for the environment to work properly

1. **Install ROS2 following the instructions from: https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html.** Make sure to use the version given in the link and also install the development tools and the Desktop Install.
    
    You can verify successful install using the instructions from this [link](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html#try-some-examples)

2. **Clone the project repository and enter the project directory**: 
    ```console
    git clone -b meteor_sim_env git@github.com:Mixed-Fleet-WP2/GenAI-fleet-planning.git && cd GenAI-fleet-planning.git
    ```

3. **Source the underlying ROS2 environment** (this has to be done everytime ROS2 commands are used and is not specific to the project):
    ```console
    source /opt/ros/jazzy/setup.bash
    ```
    If you want to do this automatically, add sourcing to your bash profile. For example:
    ```console
    echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
    ```

4. **Create a new Python virtual environment and activate it** (e.g to the project directory). Make sure that step 4 is done first, otherwise the virtual environment does not inherit the ros2   packages!:
    ```console
    python3 -m venv .ros_venv 
    source .ros_venv/bin/activate
    ```
    This virtual environment is for installing dependencies that 
    the ROS2 installation does not install globally

5. Install the Python dependencies used by the project
    ```console
    pip install -r requirements.txt
    ```

6. **Install an MQTT broker on your system**   
    The system has been tested using the Echlipse Mosquitto MQTT broker. 
    Instructions for installing and testing can be found from [link](https://github.com/eclipse-mosquitto/mosquitto)

7. Before building the project, run the below command to ensure that all the ROS dependencies have been installed
    ```console
    sudo rosdep init
    rosdep update
    rosdep install --from-paths src -r -y --skip-keys="nav2_launch"
    ```
8. Build the project by entering the the following command while inside the project directory/workspace
    ```console
    colcon build
    ```
9. **_In a new terminal_, navigate to the project directory and source the built setup files** (remember to activate the virtual environment again)
    ```console
    source .ros_venv/bin/activate
    source install/setup.bash
    ```
10. **Run the simulation with one forklift (forklift_1) and one drone (drone_1**)
    ```console
    ros2 launch mf_simulation multi_robot_launch.py
    ```
11. **Sending an action**
    To test if the system works correctly, you can execute the following command
    ```console
    bash test_command.bash <host> <port>
    ```
    The command assumes that there is a robot named drone_1 in the environment (by default there is). The command uses localhost and port 1883 by default.

## Customization

### Changing the number of robots

The package _mf_simulation_ contains a file __robot_default.yml__ which has an example of the default state of the simulation (1 forklift and 1 drone). By changing the file's contents, the number of robots can be changed. The default scenario is used in the METEOR scenario. The workspace
should be rebuilt after changing the file.

### Changing default MQTT broker

If your broker does not run on port 1883 and/or localhost, you can change
the port and host used by the system by passing additional ros2 parameters to the 
launch command:
```
ros2 launch mf_simulation multi_robot_launch.py mqtt_host:=<host> mqtt_port:=<port>
```

## Notes to WSL2 users

If you are running the simulation using WSL2, you must export the following
environment variable in order to utilise the GPU:
```console
export GALLIUM_DRIVER=d3d12
```
See the related [issue](https://github.com/microsoft/WSL/issues/12584#issuecomment-2658951125)

In addition, if you have a laptop with integrated graphics, export the following environment variable (example uses NVIDIA GPU):
```console
export MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA
```
See related [documentation](https://github.com/microsoft/wslg/wiki/GPU-selection-in-WSLg)

To check if the GPU is utilised, install the mesa-utils and run the command:
```
sudo apt install mesa-utils
glxinfo -B
```

The output should be something like the following:
```console
name of display: :0
display: :0  screen: 0
direct rendering: Yes
Extended renderer info (GLX_MESA_query_renderer):
    Vendor: Microsoft Corporation (0xffffffff)
    Device: D3D12 (NVIDIA GeForce RTX 5070 Ti) (0xffffffff)
    Version: 25.2.8
    Accelerated: yes
    Video memory: 32341MB
    Unified memory: no
    ...
```

If Device: D3D12 show something like __(Intel(R) Iris(R) Xe Graphics)__ or __llvmpipe__,
the GPU is not being utilised.


