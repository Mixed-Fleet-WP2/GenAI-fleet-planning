import subprocess
import math
import numpy as np

"""
Teleports an object to a given position in the world. Utilised
by drop and pick_up functions.
"""
def move_object_to_point(object, x, y, z, orient_x, orient_y, orient_z, orient_w):

    cmd = [
        "gz", "service",
        "-s", "/world/default/set_pose",
        "--reqtype", "gz.msgs.Pose",
        "--reptype", "gz.msgs.Boolean",
        "--timeout", "300",
        "--req", (
            f'name: "{object}", position: {{x: {x}, y: {y}, z: {z}}}, '
            f'orientation: {{x: {orient_x}, y: {orient_y}, '
            f'z: {orient_z}, w: {orient_w}}}'
        )
    ]

    try:
        subprocess.run(cmd, capture_output=False, text=True, check=True)
    except Exception as e:
        print(e)

def calculate_position_targets(goal_x:float, goal_y:float, entity_x:float, entity_y:float, entity_yaw:float):
        # Calculate the x and y components of the vector that starts from the forklift and ends at the target
        direction_vector_x_component = goal_x - entity_x
        direction_vector_y_component = goal_y - entity_y
        # Calculate the length of the sum vector (direct vector leading to target)
        distance = math.hypot(direction_vector_x_component, direction_vector_y_component)

        # convert to the sum vector to unit vector, courtesy of ChatGPT
        if distance > 0:
            direction_vector_x_component /= distance
            direction_vector_y_component /= distance

        # Calculate how big the x, y and yaw differences are between the current
        # position of the forklift and the target
        x_diff_to_target = goal_x - entity_x
        y_diff_to_target =  goal_y - entity_y
        angle_diff_to_target = math.atan2(y_diff_to_target, x_diff_to_target)

        # Calculate the target angle (relative to the world) that we must achieve
        target_angle = entity_yaw + (angle_diff_to_target - entity_yaw)

        return target_angle

def reset_contact_sensor():
     
    cmd = [
    "gz", "service",
    "-s", "/forklift/enable",
    "--reqtype", "gz.msgs.Boolean",
    "--reptype", "gz.msgs.Empty",
    "--timeout", "3000",
    "--req", "data: true"
    ]

    try:
        subprocess.run(cmd, capture_output=False, text=True, check=True)
    except Exception as e:
        print(e)

def euler_to_quaternion(yaw):
    quaternion = np.zeros(4)
    quaternion[3] = math.cos(yaw / 2)
    quaternion[2] = math.sin(yaw / 2)
    x = quaternion[0]
    y = quaternion[1]
    z = quaternion[2]
    w = quaternion[3]

    return x, y, z, w

def euler_from_quaternion(x, y, z, w):
    t3 = +2.0 * (w * z + x * y)
    t4 = +1.0 - 2.0 * (y * y + z * z)
    return math.atan2(t3, t4)

"""
Function to get the global position of a link's frame in the global coordinate system
Primarily used to get the global position of the forklift's fork frame
to teleport the cube to the correct position.

frame_local_pos_x: the x-coordinate of the origin of a frame specified in terms of the base link's 
coordinate system. In Gazebo one can see the this coordinate by inspecting the link (if the link
is not fixed)
frame_local_y: the y-coordinate of the origin of a frame specified in terms of the base link's 
coordinate system. In Gazebo one can see the this coordinate by inspecting the link (if the link
is not fixed)
offset_x: How much the returned x-coordinate should be offset to the
x-direction (in the forklift's coordinate frame, not global) i.e. forward when looking towards the front
offset_y: How much the returned y-coordinate should be offset to the
y-direction (in the forklift's coordinate frame, not global) i.e. left when looking towards the front
"""

def get_frame_pos_as_global(parent_x, parent_y, parent_yaw, frame_local_pos_x, frame_local_pos_y, offset_x=0, offset_y=0):

    frame_local_position = np.array([frame_local_pos_x + offset_x, frame_local_pos_y + offset_y])

    # Transformation matrix to rotate the forlift's coordinate axis to the same
    # position as global axis
    rotation_matrix = np.array([
        [np.cos(parent_yaw), -np.sin(parent_yaw)],
        [np.sin(parent_yaw), np.cos(parent_yaw)]
    ])

    rotated_local_position = rotation_matrix.dot(frame_local_position)

    frame_global_pos_x = rotated_local_position[0] + parent_x
    frame_global_pos_y = rotated_local_position[1] + parent_y

    return frame_global_pos_x, frame_global_pos_y