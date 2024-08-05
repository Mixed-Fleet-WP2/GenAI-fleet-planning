import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist,PoseArray
from std_msgs.msg import Bool
import math
import numpy as np
from collections import deque
from movement_interface.srv import MovementSuccess, Pickup, Drop, CubePos
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup
from tf2_msgs.msg import TFMessage

from utils import calculate_position_targets, move_object_to_point, reset_contact_sensor, euler_to_quaternion, euler_from_quaternion

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


class PrimitiveNode(Node):
    def __init__(self):
        super().__init__("rotation_node")

        self.target_angle = 0
        self.kp = 0.7  # Proportional gain
        self.kp_movement = 0.2
        self.target_x = 0.0
        self.target_y = 0.0

        self.cube_pos_x = None
        self.cube_pos_y = None

        self.subscription_cb_group = ReentrantCallbackGroup()
        self.service_cb_group = ReentrantCallbackGroup()
        self.create_subscription(Odometry, "/model/forklift/odometry", self.__get_odom, 10)
        self.create_subscription(Bool, "/forklift/touched", self.__detect_contact, 10)

        self.cube_pos_service = self.create_service(CubePos, 'cube_pos', self.send_cube_pos, callback_group=self.service_cb_group)
        self.srv = self.create_service(MovementSuccess, "move", self.move_forklift_to_point, callback_group=self.service_cb_group)
        self.pickup_srv = self.create_service(Pickup, "pick_up", self.pick_up, callback_group=self.service_cb_group) 
        self.drop_srv = self.create_service(Drop, "drop", self.drop, callback_group=self.service_cb_group)
        self.subscription = self.create_subscription(
            TFMessage,
            'cube_pose',  
            self.cube_pose_callback,
            10
        )
        self.movement_controller = self.create_publisher(Twist, "/cmd_vel", 10)

        self.current_yaw = None
        self.current_x = None
        self.current_y = None
        self.current_z = None
        self.action_in_progress = False
        self.in_cube_contact = False

        self.current_quaternion_w = 0.0
        self.current_quaternion_x = 0.0
        self.current_quaternion_y = 0.0
        self.current_quaternion_z = 0.0
        self.odom_received = False
        self.command_queue = deque()

    def send_cube_pos(self, request, response):
        response.pos_vector[0] = self.cube_pos_x
        response.pos_vector[1] = self.cube_pos_y
        return response

    def move_forklift_to_point(self, request, response):
        self.action_in_progress = True
        self.target_x = request.x
        self.target_y = request.y
        self.target_angle = calculate_position_targets(request.x, request.y, self.current_x, self.current_y, self.current_yaw)
        self.rotation_complete = False
        self.rotate()
        self.move()
        response.success = True
        return response

    def pick_up(self, request, response):
        object = request.object
        self.pick_up_object(object)
        response.success = True
        return response
    
    def drop(self, request, response):
        object = request.object
        self.drop_object(object)
        response.success = True
        return response    

    def cube_pose_callback(self, msg):
        self.cube_pos_x = msg.transforms[1].transform.translation.x
        self.cube_pos_y = msg.transforms[1].transform.translation.y
        
    def move(self):

        while True:

            error_x = self.target_x - self.current_x
            error_y = self.target_y - self.current_y
            distance_error = math.hypot(error_x, error_y)
            msg = Twist()
            if distance_error < 0.2 or self.in_cube_contact:
                msg.linear.x = 0.0
                self.movement_controller.publish(msg)
                self.get_logger().info(f"Move complete, current location: ({self.current_x}, {self.current_y})")
                self.action_in_progress = False
                self.in_cube_contact = False
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
        move_object_to_point('cube', fork_center_x, fork_center_y, TELEPORT_HEIGHT, self.current_quaternion_x,
                                  self.current_quaternion_y, self.current_quaternion_z, self.current_quaternion_w)

        cube_x, cube_y = self.cube_pos_x, self.cube_pos_y

        if abs(fork_center_x - cube_x) < 0.5 and abs(fork_center_y - cube_y) < 0.5:
            return True
        return False

    def drop_object(self, object):
        # Get the coordinates of a point right in front of the forklift, relative to the global frame
        x, y = self.get_frame_pos_as_global(FORK_PLATE_JOINT_ORIGIN_X, FORK_PLATE_JOINT_ORIGIN_Y,
                                            FORK_LENGTH + CUBE_WIDTH / 2, LEFT_FORK_VISUAL_ORIGIN_Y - 0.05)
        move_object_to_point('cube', x, y, TELEPORT_HEIGHT, self.current_quaternion_x, self.current_quaternion_y,
                                  self.current_quaternion_z, self.current_quaternion_w)
        self.in_cube_contact = False
        reset_contact_sensor()

    def __get_odom(self, msg):
        orientation_q = msg.pose.pose.orientation
        self.current_x = msg.pose.pose.position.x
        self.current_y = msg.pose.pose.position.y
        self.current_z = msg.pose.pose.position.z
        self.current_quaternion_x = orientation_q.x
        self.current_quaternion_y = orientation_q.y
        self.current_quaternion_z = orientation_q.z
        self.current_quaternion_w = orientation_q.w
        yaw = euler_from_quaternion(orientation_q.x, orientation_q.y, orientation_q.z, orientation_q.w)
        self.current_yaw = round(yaw, 2)
        self.odom_received = True
    
    def __detect_contact(self, msg):
        self.in_cube_contact = msg.data
  
    def rotate(self):
        while True:
            error = self.target_angle - self.current_yaw
            if error > math.pi:
                error -= 2 * math.pi
            elif error < -math.pi:
                error += 2 * math.pi

            msg = Twist()
            if abs(error) < 0.01:  # Smaller threshold for rotation completion
                
                #Make a small teleport command to make the forklift face exactly the target
                x,y,z,w = euler_to_quaternion(self.target_angle)
                move_object_to_point('forklift', self.current_x, self.current_y, self.current_z, x, y, z, w)
            
                msg.angular.z = 0.0
                self.movement_controller.publish(msg)
                self.get_logger().info(f"Rotation complete: {self.current_yaw:.2f} radians")
                return True
            else:
                msg.angular.z = self.kp * error
                self.movement_controller.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = PrimitiveNode()
    # https://answers.ros.org/question/358343/rate-and-sleep-function-in-rclpy-library-for-ros2/
    #One is the default thread, another reserved for service callbacks
    executor = MultiThreadedExecutor(num_threads=2)
    rclpy.spin(node, executor=executor)

    rclpy.shutdown()

if __name__ == '__main__':
    main()
