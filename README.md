# Programming robotic fleets utilising large language models

## Overview

This repository contains research code for the Mixed Fleet project
researched at Tampere University. The work is associated
with **Work Package 2: Programming Multi-Machine Fleets (WP2)** of the project which you can read more about [here](https://blogs.tuni.fi/cs/projects/mixed-fleet-cross-disciplinary-work-towards-seamless-collaboration-between-mobile-work-machines-and-humans/). The aim of this repository is to provide a proof-of-concept application of Large Language Models in the programming of robotic fleets. Blog post concerning the subject can be read [here](https://blogs.tuni.fi/cs/projects/first-steps-towards-programming-mixed-fleet-systems-by-domain-experts/).

**This document will be continously updated during the course of the project**

## Running the Meteor simulation

Instructions are provided for native install as well as through Docker

### Installing natively

The simulation in this repository uses [ROS2 (Robot Operating System)](https://docs.ros.org/en/jazzy/index.html) and the open-source robotics simulator [Gazebo](https://gazebosim.org/home). The used environment is as follows:

- ROS2 version Jazzy Jalisco
- Gazebo version Harmonic
- Nav2 navigation stack
- **Ubuntu 24.04 Noble Numbat** (has been successfully ran on WSL2)
- Python 3 (tested with 3.12 which is the default Noble install)
- C/C++ compiler supporting C++17


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
    source install/setup.bash
    ```
10. If the machine does not have GPU available, use software rendering by setting the following variable:
    ```
    export LIBGL_ALWAYS_SOFTWARE=1
    ```

11. **Run the simulation with one forklift (forklift_1) and one drone (drone_1**)
    ```console
    ros2 launch mf_simulation multi_robot_launch.py
    ```

MQTT COMMAND INSTRUCTIONS HERE

