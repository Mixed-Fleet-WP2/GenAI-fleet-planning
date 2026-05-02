#!/bin/bash
set -e

# Source ROS2 base installation
source /opt/ros/jazzy/setup.bash

# Source workspace overlay if it exists
if [ -f "/home/ros/ws/install/setup.bash" ]; then
    source /home/ros/ws/install/setup.bash
fi

# Execute the command passed to docker run / docker exec
exec "$@"