import subprocess

from rclpy.node import Node
from tf2_ros import TransformListener, Buffer
from rclpy.time import Duration, Time


def get_pos_as_other_coord_frame(node: Node, target_frame: str, source_frame: str):
    buffer = Buffer()
    listener = TransformListener(buffer, node)
    try:
        transform = buffer.lookup_transform(target_frame, source_frame, Time(), Duration(seconds=10))
        translation = transform.transform.translation
        rotation = transform.transform.rotation
        translation = [translation.x, translation.y, translation.z]
        rotation = [rotation.x, rotation.y, rotation.z, rotation.w]
    except Exception as e:
        node.get_logger().error(f"Error getting transform: {e}")
        return None
    
    return [translation[0], translation[1], translation[2], rotation[0], rotation[1], rotation[2], rotation[3]]
            

"""
Teleports an object to a given position in the world. Utilised
by drop and pick_up functions.
"""
def move_object_to_point(object, x, y, z, orient_x=0, orient_y=0, orient_z=0, orient_w=0):

    cmd = [
        "gz", "service",
        "-s", "/world/depot/set_pose",
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