import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from std_msgs.msg import Float64, Empty
from geometry_msgs.msg import Point, PoseArray
from functools import partial
import math
import numpy as np
from collections import deque
import subprocess
from movement_interface.srv import MovementSuccess, Pickup
import threading
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup

# Specifies at which index in the pose
# array received from gazebo the cube is located

CUBE_WIDTH = 0.2
FORK_LENGTH = 0.3
FORK_PLATE_JOINT_ORIGIN_X = 0.38
FORK_PLATE_JOINT_ORIGIN_Y = 0
LEFT_FORK_VISUAL_ORIGIN_X = 0.15
LEFT_FORK_VISUAL_ORIGIN_Y = 0.05
# The height at which drop the "picked up cube onto the fork, could be in the future be replaced with an odometry value"
TELEPORT_HEIGHT = 0.2
CUBE_POSE_INDEX = 1


class RotationNode(Node):
    def __init__(self):
        super().__init__("rotation_node")

        self.target_angle = 0
        self.kp = 0.5  # Proportional gain
        self.kp_movement = 0.2
        self.target_x = 0.0
        self.target_y = 0.0

        self.subscription_cb_group = ReentrantCallbackGroup()
        self.service_cb_group = ReentrantCallbackGroup()
        self.create_subscription(Odometry, "/model/forklift/odometry", self.__get_odom, 10, callback_group=self.subscription_cb_group)

        self.srv = self.create_service(MovementSuccess, "move", self.move_forklift_to_point, callback_group=self.service_cb_group)  # CHANGE
        self.pickup_srv = self.create_service(Pickup, "pick_up", self.pick_up, callback_group=self.service_cb_group)  # CHANGE
        self.subscription = self.create_subscription(
            PoseArray,
            'object_poses',  # Replace with your actual topic name
            self.pose_array_callback,
            10
        )
        self.movement_controller = self.create_publisher(Twist, "/cmd_vel", 10)

        self.current_yaw = None
        self.current_x = None
        self.current_y = None
        self.current_z = None
        self.action_in_progress = False

        self.angle_diff_to_target = 0.0
        self.x_diff_to_target = 0.0
        self.y_diff_to_target = 0.0

        self.current_quaternion_w = 0.0
        self.current_quaternion_x = 0.0
        self.current_quaternion_y = 0.0
        self.current_quaternion_z = 0.0
        self.odom_received = False
        self.command_queue = deque()

    def move_forklift_to_point(self, request, response):
        self.action_in_progress = True
        self.calculate_position_targets(request.x, request.y)
        self.rotation_complete = False
        self.rotate()
        self.move()
        response.success = True
        return response

    def pick_up(self, request, response):
        self.pick_up_object('cube')
        response.success = True
        return response

    def __euler_from_quaternion(self, x, y, z, w):
        t3 = +2.0 * (w * z + x * y)
        t4 = +1.0 - 2.0 * (y * y + z * z)
        return math.atan2(t3, t4)

    def pose_array_callback(self, msg):
        # Example: Extract the first pose from the PoseArray
        self.cube_pose_x = msg.poses[CUBE_POSE_INDEX].position.x
        self.cube_pose_y = msg.poses[CUBE_POSE_INDEX].position.y

    def calculate_position_targets(self, goal_x, goal_y):
        # Calculate the x and y components of the vector that starts from the forklift and ends at the target
        direction_vector_x_component = goal_x - self.current_x
        direction_vector_y_component = goal_y - self.current_y
        # Calculate the length of the sum vector (direct vector leading to target)
        distance = math.hypot(direction_vector_x_component, direction_vector_y_component)

        # convert to the sum vector to unit vector
        if distance > 0:
            direction_vector_x_component /= distance
            direction_vector_y_component /= distance

        # Set an offset from the target by moving the real target away to the opposite direction of the vector,
        # this is quite a stupid solution but prevents the forklift from crashing into the object
        # it tries to pick up
        self.target_x = goal_x #- 0.75 * direction_vector_x_component
        self.target_y = goal_y #- 0.75 * direction_vector_y_component

        # Calculate how big the x, y and yaw differences are between the current
        # position of the forklift and the target
        self.x_diff_to_target = self.target_x - self.current_x
        self.y_diff_to_target = self.target_y - self.current_y
        self.angle_diff_to_target = math.atan2(self.y_diff_to_target, self.x_diff_to_target)

        # Calculate the target angle (relative to the world) that we must achieve
        self.target_angle = self.current_yaw + (self.angle_diff_to_target - self.current_yaw)

    """
    Teleports an object to a given position in the world. Utilised
    by drop and pick_up functions.
    """
    def move_object_to_point(self, object, x, y, z, orient_x, orient_y, orient_z, orient_w):

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
            self.get_logger().info(e)

    def move(self):

        while True:

            error_x = self.target_x - self.current_x
            error_y = self.target_y - self.current_y
            distance_error = math.hypot(error_x, error_y)
            msg = Twist()
            if distance_error < 0.2:
                msg.linear.x = 0.0
                self.movement_controller.publish(msg)
                self.get_logger().info(f"Move complete, current location: ({self.current_x}, {self.current_y})")
                self.action_in_progress = False
                return True
            else:
                # Multiplying by a small value results in slower linear movement
                msg.linear.x = self.kp_movement * distance_error
                self.movement_controller.publish(msg)

    """
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

    def get_frame_pos_as_global(self, frame_local_pos_x, frame_local_pos_y, offset_x=0, offset_y=0):

        forklift_origin_global_x = self.current_x
        forklift_origin_global_y = self.current_y
        forklift_rotation_angle = self.current_yaw
        frame_local_position = np.array([frame_local_pos_x + offset_x, frame_local_pos_y + offset_y])

        # Transformation matrix to rotate the forlift's coordinate axis to the same
        # position as global axis
        rotation_matrix = np.array([
            [np.cos(forklift_rotation_angle), -np.sin(forklift_rotation_angle)],
            [np.sin(forklift_rotation_angle), np.cos(forklift_rotation_angle)]
        ])

        rotated_local_position = rotation_matrix.dot(frame_local_position)

        frame_global_pos_x = rotated_local_position[0] + forklift_origin_global_x
        frame_global_pos_y = rotated_local_position[1] + forklift_origin_global_y

        return frame_global_pos_x, frame_global_pos_y

    def pick_up_object(self, object):
        # 0.05 offset is to put the cube's origin between the 2 forks, otherwise it would be at the center of the left fork
        fork_center_x, fork_center_y = self.get_frame_pos_as_global(FORK_PLATE_JOINT_ORIGIN_X, FORK_PLATE_JOINT_ORIGIN_Y,
                                                                    LEFT_FORK_VISUAL_ORIGIN_X, LEFT_FORK_VISUAL_ORIGIN_Y - 0.05)
        # Movement to target is complete, pick up the target
        self.move_object_to_point('cube', fork_center_x, fork_center_y, TELEPORT_HEIGHT, self.current_quaternion_x,
                                  self.current_quaternion_y, self.current_quaternion_z, self.current_quaternion_w)

        cube_x, cube_y = self.cube_pose_x, self.cube_pose_y

        if abs(fork_center_x - cube_x) < 0.5 and abs(fork_center_y - cube_y) < 0.5:
            return True
        return False

    def drop_object(self, object='cube'):
        # Get the coordinates of a point right in front of the forklift, relative to the global frame
        x, y = self.get_frame_pos_as_global(FORK_PLATE_JOINT_ORIGIN_X, FORK_PLATE_JOINT_ORIGIN_Y,
                                            FORK_LENGTH + CUBE_WIDTH / 2, LEFT_FORK_VISUAL_ORIGIN_Y - 0.05)
        self.move_object_to_point('cube', x, y, TELEPORT_HEIGHT, self.current_quaternion_x, self.current_quaternion_y,
                                  self.current_quaternion_z, self.current_quaternion_w)

    def __get_odom(self, msg):
        orientation_q = msg.pose.pose.orientation
        self.current_x = msg.pose.pose.position.x
        self.current_y = msg.pose.pose.position.y
        self.current_z = msg.pose.pose.position.z
        self.current_quaternion_x = orientation_q.x
        self.current_quaternion_y = orientation_q.y
        self.current_quaternion_z = orientation_q.z
        self.current_quaternion_w = orientation_q.w
        yaw = self.__euler_from_quaternion(orientation_q.x, orientation_q.y, orientation_q.z, orientation_q.w)
        self.current_yaw = round(yaw, 2)
        self.odom_received = True

    def rotate(self):
        while True:
            error = self.target_angle - self.current_yaw
            if error > math.pi:
                error -= 2 * math.pi
            elif error < -math.pi:
                error += 2 * math.pi

            msg = Twist()
            if abs(error) < 0.01:  # Smaller threshold for rotation completion
                msg.angular.z = 0.0
                self.movement_controller.publish(msg)
                self.get_logger().info(f"Rotation complete: {self.current_yaw:.2f} radians")
                return True
            else:
                msg.angular.z = self.kp * error
                self.movement_controller.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = RotationNode()
    # https://answers.ros.org/question/358343/rate-and-sleep-function-in-rclpy-library-for-ros2/
    executor = MultiThreadedExecutor(num_threads=4)
    rclpy.spin(node, executor=executor)

    rclpy.shutdown()

if __name__ == '__main__':
    main()
