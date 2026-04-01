ARG BASE_IMAGE=osrf/ros
ARG BASE_TAG=jazzy-desktop-full

FROM ${BASE_IMAGE}:${BASE_TAG}

ENV DEBIAN_FRONTEND=noninteractive
ENV GZ_VERSION=harmonic

ARG DISTRO=jazzy
ARG USERNAME=ros
ARG USER_UID=1000
ARG USER_GID=${USER_UID}
ARG WORKSPACE=docker_simulation_ws

# Only what desktop-full doesn't already have
RUN apt-get update && apt-get install -y \
    ros-${DISTRO}-rmw-cyclonedds-cpp \
    #ros-${DISTRO}-rosbag2-storage-mcap \
    chrony \
    tmux \
    nano \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ARG BASE_IMAGE=osrf/ros
ARG BASE_TAG=jazzy-desktop-full

FROM ${BASE_IMAGE}:${BASE_TAG}

ENV DEBIAN_FRONTEND=noninteractive
ENV GZ_VERSION=harmonic

ARG DISTRO=jazzy
ARG USERNAME=ubuntu
ARG WORKSPACE=docker_simulation_ws

# System packages
RUN apt-get update && apt-get install -y \
    ros-${DISTRO}-rmw-cyclonedds-cpp \
    mesa-utils \
    chrony \
    tmux \
    nano \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Add ubuntu user to useful groups (no sudo needed here, already root)
#RUN usermod -a -G render,video ${USERNAME} || true

#RUN usermod -aG video,render ubuntu
RUN groupadd -f render && \
    usermod -aG video,render ubuntu

# Allow sudo without password (optional but common in dev containers)
RUN echo "${USERNAME} ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME} && \
    chmod 0440 /etc/sudoers.d/${USERNAME}

USER ${USERNAME}

ENV HOME=/home/${USERNAME}
ENV USER=${USERNAME}

WORKDIR /home/${USERNAME}/${WORKSPACE}

# Shell setup
RUN echo "source /opt/ros/${DISTRO}/setup.bash" >> ~/.bashrc && \
    echo "if [ -f ~/${WORKSPACE}/install/setup.bash ]; then source ~/${WORKSPACE}/install/setup.bash; fi" >> ~/.bashrc && \
    echo "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp" >> ~/.bashrc && \
    echo "export GZ_VERSION=harmonic" >> ~/.bashrc && \
    echo "export GZ_SIM_SYSTEM_PLUGIN_PATH=/opt/ros/${DISTRO}/lib/" >> ~/.bashrc

ENTRYPOINT ["/ros_entrypoint.sh"]

CMD ["bash", "-c", "source /opt/ros/jazzy/setup.bash && gz sim empty.sdf -v 4"]