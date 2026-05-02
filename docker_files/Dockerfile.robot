# First we have the build layer

# Global args
ARG BASE_IMAGE=ros
ARG BASE_TAG=jazzy-ros-base
ARG DISTRO=jazzy
ARG PKG_NAME


FROM ${BASE_IMAGE}:${BASE_TAG} AS builder
ARG DISTRO
ARG BUILD_DIR=/build_dir
# Redeclare the PKG_NAME arg in this stage to be able to use it in this stage
ARG PKG_NAME
WORKDIR ${BUILD_DIR}
COPY  ./src/${PKG_NAME} ./src/${PKG_NAME}
COPY ./docker_files/gz_util_pkg ./src/gz_util_pkg
# mf_utils contains shared types etc. that are used by both the
# forklift and the drone package, so we also need to copy it to the builder stage
# We also need nav2_launch and attach_interfaces for the forklift package, so we copy them as well
COPY  ./src/mf_utils ./src/mf_utils
COPY ./src/attach_interfaces ./src/attach_interfaces
COPY ./src/nav2_launch ./src/nav2_launch

SHELL ["/bin/bash", "-c"]

RUN apt-get update \
    && source /opt/ros/${DISTRO}/setup.bash \
    && (rosdep init || true) \
    && rosdep update \
    && rosdep install \
        --from-paths ./src/${PKG_NAME} ./src/gz_util_pkg ./src/mf_utils ./src/attach_interfaces ./src/nav2_launch \
        --ignore-src -r -y \
        --skip-keys="ros_gz_sim" \
    && source /opt/ros/${DISTRO}/setup.bash \
    && colcon build \
        --merge-install \
        --cmake-args -DBUILD_TESTING=OFF \
    && mkdir -p /pkg_meta/${PKG_NAME} /pkg_meta/gz_util_pkg /pkg_meta/mf_utils /pkg_meta/attach_interfaces /pkg_meta/nav2_launch \
    && cp ./src/${PKG_NAME}/package.xml /pkg_meta/${PKG_NAME}/ \
    && cp ./src/gz_util_pkg/package.xml /pkg_meta/gz_util_pkg/ \
    && cp ./src/mf_utils/package.xml /pkg_meta/mf_utils/ \
    && cp ./src/attach_interfaces/package.xml /pkg_meta/attach_interfaces/ \
    && cp ./src/nav2_launch/package.xml /pkg_meta/nav2_launch/ \
    && rm -rf build log src \
    # Apt-get clean would probably be not necessary because ubuntu
    # images do that automatically (ubuntu is base of the ros images), but we do it just in case
    # https://docs.docker.com/build/building/best-practices/#apt-get
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# This is the runtime layer
# https://www.ros.org/reps/rep-2001.html#id95
FROM ${BASE_IMAGE}:${BASE_TAG} AS runtime

# These have to be redeclared in the second stage to be used in this stage
# https://stackoverflow.com/questions/53681522/share-variable-in-multi-stage-dockerfile-arg-before-from-not-substituted
ARG BASE_IMAGE
ARG BASE_TAG
ARG DISTRO
ARG PKG_NAME

ENV DEBIAN_FRONTEND=noninteractive

ARG USERNAME=ros
ARG USER_UID=1000
ARG USER_GID=${USER_UID}
ARG WORKSPACE=ws

# Use bash as the default shell for subsequent commands
# because sh does not understand commands like "source"
SHELL ["/bin/bash", "-c"]

# Copy the package.xml files to the runtime layer
# (to the root's home directory!)
# For installing the dependencies with rosdep
COPY --from=builder /pkg_meta/${PKG_NAME}/package.xml ./src_meta/${PKG_NAME}/
COPY --from=builder /pkg_meta/gz_util_pkg/package.xml ./src_meta/gz_util_pkg/
COPY --from=builder /pkg_meta/mf_utils/package.xml ./src_meta/mf_utils/
COPY --from=builder /pkg_meta/attach_interfaces/package.xml ./src_meta/attach_interfaces/
COPY --from=builder /pkg_meta/nav2_launch/package.xml ./src_meta/nav2_launch/
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-${DISTRO}-rmw-cyclonedds-cpp \
    sudo \
    # Install the ros dependencies with rosdep
    # Depending on the base image, rosdep might already be initialized, so we ignore the error if it is already initialized
    && (rosdep init || true) \
    && rosdep update \
    && rosdep install --from-paths ./src_meta/gz_util_pkg ./src_meta/${PKG_NAME} ./src_meta/mf_utils ./src_meta/attach_interfaces ./src_meta/nav2_launch --ignore-src -r -y --dependency-types exec run \
    && rm -rf ./src_meta \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# If the user already exists (e.g. by default in the base image), delete it and create new
RUN if id -u ${USER_UID} ; then userdel `id -un ${USER_UID}` ; fi && \
    # Create a group named after the username
    groupadd --gid ${USER_GID} ${USERNAME} && \
    # Create user with USER_ID and add it to the group created above
    # also create home directory that is named after the user
    useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME} \
    && echo ${USERNAME} ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME}

# Create the directory first
RUN mkdir -p /gz_models
# Set ownership to your non-root user
# (same in all images) so the container
# can write to the directory
RUN chown -R 1000:1000 /gz_models

USER ${USERNAME}

ENV HOME=/home/${USERNAME}
ENV USER=${USERNAME}

WORKDIR /home/${USERNAME}/${WORKSPACE}

# Copy the created binaries to the new user's workspace NOT ROOT's!
COPY  --from=builder /build_dir/install ./install

# For the meshes and textures to be available for Gazebo, copy the model directory to a directory
# that can be mounted as a volume to the Gazebo container
# SO THE GZ_SIM_RESOURCE PATH SHOULD BE SET TO /gz_models
COPY --from=builder /build_dir/install/share/${PKG_NAME}/models /models_staging/${PKG_NAME}/models

# Write the source command to the .bashrc to ensure ROS environment is set up for the user
RUN echo "source /opt/ros/${DISTRO}/setup.bash" >> ~/.bashrc

# Source the overlay
RUN source ~/.bashrc && echo "if [ -f ~/${WORKSPACE}/install/setup.bash ]; then source ~/${WORKSPACE}/install/setup.bash; fi" >> ~/.bashrc

