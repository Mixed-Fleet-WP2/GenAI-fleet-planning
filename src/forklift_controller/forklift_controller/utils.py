import subprocess
import math
import numpy as np

"""
Teleports an object to a given position in the world. Utilised
by drop and pick_up functions.
"""
def move_object_to_point(object, x, y, z, orient_x=0, orient_y=0, orient_z=0, orient_w=0):

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

        # Set an offset from the target by moving the real target away to the opposite direction of the vector,
        # this is quite a stupid solution but prevents the forklift from crashing into the object
        # it tries to pick up
        """
        self.target_x = goal_x #- 0.75 * direction_vector_x_component
        self.target_y = goal_y #- 0.75 * direction_vector_y_component
        """

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