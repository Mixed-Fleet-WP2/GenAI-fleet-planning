import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist,PoseArray
from std_msgs.msg import Bool
import math
import numpy as np
from movement_interface.srv import MovementSuccess, Pickup, Drop
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup

from utils import calculate_position_targets, move_object_to_point, reset_contact_sensor, euler_to_quaternion, euler_from_quaternion, get_frame_pos_as_global

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

        self.__target_angle = 0
        self.__kp = 0.7  # Proportional gain
        self.__kp_movement = 0.2
        self.__target_x = 0.0
        self.__target_y = 0.0

        self.__service_cb_group = ReentrantCallbackGroup()
        self.__create_subscription(Odometry, "/model/forklift/odometry", self.__get_odom, 10)
        self.__create_subscription(Bool, "/forklift/touched", self.__detect_contact, 10)

        self.__srv = self.__create_service(MovementSuccess, "move", self.__move_forklift_to_point, callback_group=self.__service_cb_group)
        self.__pickup_srv = self.__create_service(Pickup, "pick_up", self.__pick_up, callback_group=self.__service_cb_group) 
        self.__drop_srv = self.__create_service(Drop, "drop", self.__drop, callback_group=self.__service_cb_group)
        self.__subscription = self.__create_subscription(
            PoseArray,
            'object_poses',  
            self.__pose_array_callback,
            10
        )
        self.__movement_controller = self.__create_publisher(Twist, "/cmd_vel", 10)

        self.__current_yaw = None
        self.__current_x = None
        self.__current_y = None
        self.__current_z = None
        self.__in_cube_contact = False

        self.__current_quaternion_w = 0.0
        self.__current_quaternion_x = 0.0
        self.__current_quaternion_y = 0.0
        self.__current_quaternion_z = 0.0
        self.__odom_received = False

    def move_forklift_to_point(self, request, response):
        self.__target_x = request.x
        self.__target_y = request.y
        self.__target_angle = calculate_position_targets(request.x, request.y, self.__current_x, self.__current_y, self.__current_yaw)
        self.__rotate()
        self.__move()
        response.success = True
        return response

    def pick_up(self, request, response):
        object = request.object
        self.__pick_up_object(object)
        response.success = True
        return response
    
    def drop(self, request, response):
        object = request.object
        self.__drop_object(object)
        response.success = True
        return response    

    def pose_array_callback(self, msg):
        self.__cube_pose_x = msg.poses[CUBE_POSE_INDEX].position.x
        self.__cube_pose_y = msg.poses[CUBE_POSE_INDEX].position.y
        
    def __pick_up_object(self, object):
        # 0.05 offset is to put the cube's origin between the 2 forks, otherwise it would be at the center of the left fork
        fork_center_x, fork_center_y = self.__get_frame_pos_as_global(self.__current_x, self.__current_y, self.__current_yaw, FORK_PLATE_JOINT_ORIGIN_X, FORK_PLATE_JOINT_ORIGIN_Y,
                                                                    LEFT_FORK_VISUAL_ORIGIN_X, LEFT_FORK_VISUAL_ORIGIN_Y - 0.05)
        # Movement to target is complete, pick up the target
        move_object_to_point('cube', fork_center_x, fork_center_y, TELEPORT_HEIGHT, self.__current_quaternion_x,
                                  self.__current_quaternion_y, self.__current_quaternion_z, self.__current_quaternion_w)

        return True

    def __drop_object(self, object):
        # Get the coordinates of a point right in front of the forklift, relative to the global frame
        x, y = self.__get_frame_pos_as_global(self.__current_x, self.__current_y, self.__current_yaw, FORK_PLATE_JOINT_ORIGIN_X, FORK_PLATE_JOINT_ORIGIN_Y,
                                            FORK_LENGTH + CUBE_WIDTH / 2, LEFT_FORK_VISUAL_ORIGIN_Y - 0.05)
        
        move_object_to_point('cube', x, y, TELEPORT_HEIGHT, self.__current_quaternion_x, self.__current_quaternion_y,
                                  self.__current_quaternion_z, self.__current_quaternion_w)
        self.__in_cube_contact = False
        reset_contact_sensor()

    def __get_odom(self, msg):
        orientation_q = msg.pose.pose.orientation
        self.__current_x = msg.pose.pose.position.x
        self.__current_y = msg.pose.pose.position.y
        self.__current_z = msg.pose.pose.position.z
        self.__current_quaternion_x = orientation_q.x
        self.__current_quaternion_y = orientation_q.y
        self.__current_quaternion_z = orientation_q.z
        self.__current_quaternion_w = orientation_q.w
        yaw = euler_from_quaternion(orientation_q.x, orientation_q.y, orientation_q.z, orientation_q.w)
        self.__current_yaw = round(yaw, 2)
        self.__odom_received = True
    
    def __detect_contact(self, msg):
        self.__in_cube_contact = msg.data
    
    def __move(self):
        while True:
            error_x = self.__target_x - self.__current_x
            error_y = self.__target_y - self.__current_y
            distance_error = math.hypot(error_x, error_y)
            msg = Twist()
            if distance_error < 0.2 or self.__in_cube_contact:
                msg.linear.x = 0.0
                self.__movement_controller.publish(msg)
                self.__get_logger().info(f"Move complete, current location: ({self.__current_x}, {self.__current_y})")
                self.__in_cube_contact = False
                return True
            else:
                # Multiplying by a small value results in slower linear movement
                msg.linear.x = self.__kp_movement * distance_error
                self.__movement_controller.publish(msg)

    def __rotate(self):
        if self.__odom_received:
            while True:
                error = self.__target_angle - self.__current_yaw
                if error > math.pi:
                    error -= 2 * math.pi
                elif error < -math.pi:
                    error += 2 * math.pi

                msg = Twist()
                if abs(error) < 0.01:  # Smaller threshold for rotation completion
                    
                    #Make a small teleport command to make the forklift face exactly the target
                    x,y,z,w = euler_to_quaternion(self.__target_angle)
                    move_object_to_point('forklift', self.__current_x, self.__current_y, self.__current_z, x, y, z, w)
                
                    msg.angular.z = 0.0
                    self.__movement_controller.publish(msg)
                    self.get_logger().info(f"Rotation complete: {self.__current_yaw:.2f} radians")
                    return True
                else:
                    msg.angular.z = self.__kp * error
                    self.__movement_controller.publish(msg)

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
