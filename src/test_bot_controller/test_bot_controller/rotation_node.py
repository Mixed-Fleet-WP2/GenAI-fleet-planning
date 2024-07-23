import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from std_msgs.msg import Float64
from geometry_msgs.msg import Point, PoseArray
from functools import partial
import math
import numpy as np
from collections import deque
import threading
import subprocess
import tf2_ros as tf

#Specifies at which index in the pose
#array received from gazebo the cube is located

CUBE_POS_ARR_INDEX = 1
CUBE_WIDTH = 0.2
FORK_LENGTH = 0.5


class RotationNode(Node):
    def __init__(self):
        super().__init__("rotation_node")

        self.target_angle = 0
        self.kp = 0.9  # Proportional gain
        self.kp_movement = 0.2
        self.target_x  = 0.0
        self.target_y = 0.0

        self.create_subscription(Odometry, "/model/forklift/odometry", self.__get_odom, 10)
        self.create_subscription(Float64, "/rotate", partial(self.handle_command, topic_name="/rotate"), 10)
        self.create_subscription(Point, "/move", partial(self.handle_command, topic_name='/move'), 10)
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
        self.rotation_complete = True
        self.timer = None
        self.move_timer = None
        self.command_queue = deque()

    def handle_command(self, msg, topic_name):
        #Append the received command
        self.command_queue.append((topic_name, msg))
         
    def __euler_from_quaternion(self, x, y, z, w):
        t3 = +2.0 * (w * z + x * y)
        t4 = +1.0 - 2.0 * (y * y + z * z)
        return math.atan2(t3, t4)

    def pose_array_callback(self, msg):
        # Example: Extract the first pose from the PoseArray
        #self.cube_pose_x = msg.poses[10].position.x
        #self.cube_pose_y = msg.poses[10].position.y
        #self.get_logger().info(str(self.cube_pose_x))
        #self.get_logger().info(str(self.cube_pose_y))
        pass
    def handle_cmds(self):
        if self.command_queue and self.odom_received and not self.action_in_progress:
            cmd = self.command_queue.popleft()
            msg_type, msg = cmd
            match msg_type:
                case "/rotate":
                    #Might be needed in the future
                    pass
                case "/move":
                    self.action_in_progress = True
                    self.calculate_position_targets(msg.x, msg.y)
                    self.rotation_complete = False
                    # Enter the rotation loop and rotate until facing the point
                    self.timer = self.create_timer(0.1, self.rotate)
                    # Start a new loop for the actual movement
                    self.move_timer = self.create_timer(0.1, self.move)


    def calculate_position_targets(self, goal_x, goal_y):
         # Calculate the x and y compontents of the vector that starts from the forklift and ends at the target
        direction_vector_x_component = goal_x - self.current_x
        direction_vector_y_component = goal_y - self.current_y
        #Calculate the length of the sum vector (direct vector leading to target)
        distance = math.hypot(direction_vector_x_component, direction_vector_y_component )
        
        # convert to the sum vector to unit vector
        if distance > 0:
            direction_vector_x_component  /= distance
            direction_vector_y_component /= distance
        
        # Set an offset from the target by moving the real target away to the opposite direction of the vector,
        # this is again quite a stupid solution but prevents the forklift from crashing into the object
        # it tries to pick up
        self.target_x = goal_x #- 0.5 * direction_vector_x_component
        self.target_y = goal_y #- 0.5 * direction_vector_y_component 
        
        #Calculate how big the x, y and yaw differences are between the current
        #position of the forklift and the target
        self.x_diff_to_target = self.target_x - self.current_x
        self.y_diff_to_target = self.target_y - self.current_y
        self.angle_diff_to_target = math.atan2(self.y_diff_to_target, self.x_diff_to_target)

        # Calculate the target angle (relative to the world) that we must achieve
        self.target_angle = self.current_yaw + (self.angle_diff_to_target - self.current_yaw)

    """
    Teleports an object to a given position in the world. Utilised
    by drop and pick_up functions.
    """
    def move_object_to_point(self, object, x,y,z, orient_x, orient_y, orient_z, orient_w):

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
        if not self.rotation_complete:
            return

        error_x = self.target_x - self.current_x
        error_y = self.target_y - self.current_y
        distance_error = math.hypot(error_x, error_y) 
        msg = Twist()
        if distance_error < 0.1:
            msg.linear.x = 0.0
            self.movement_controller.publish(msg)
            self.get_logger().info(f"Move complete, current location: ({self.current_x}, {self.current_y})")
            self.action_in_progress = False
            self.move_timer.cancel()
            self.move_timer = None
            
            x,y = self.get_frame_pos_as_global(0.38, 0, 0.15, 0)
            #Movement to target is complete, pick up the target
            FORK_LENGTH / 2 + CUBE_WIDTH/2
            self.move_object_to_point('cube',x,y,0.2, self.current_quaternion_x, self.current_quaternion_y, self.current_quaternion_z, self.current_quaternion_w)
      
        else:
            #Multiplying by a small value results in slower linear movement
            msg.linear.x = self.kp_movement * distance_error
            self.movement_controller.publish(msg)

    """
    offset_x: How much the returned x-coordinate should be offset to the
    x-direction (in the forklift's coordinate frame, not global) i.e. forward when looking towards the front
    offset_y: How much the returned y-coordinate should be offset to the
    y-direction (in the forklift's coordinate frame, not global) i.e. left when looking towards the front
    """

    def get_frame_pos_as_global(self, frame_local_pos_x, frame_local_pos_y, offset_x = 0, offset_y = 0):

        forklift_origin_global_x = self.current_x
        forklift_origin_global_y = self.current_y
        forklift_rotation_angle =  self.current_yaw
        frame_local_position = np.array([frame_local_pos_x + offset_x, frame_local_pos_y + offset_y])

        #Transformation matrix to rotate the forlift's coordinate axis to the same
        #position as global axis
        rotation_matrix = np.array([
            [np.cos(forklift_rotation_angle), -np.sin(forklift_rotation_angle)],
            [np.sin(forklift_rotation_angle), np.cos(forklift_rotation_angle)]
        ])

        rotated_local_position = rotation_matrix.dot(frame_local_position)

        frame_global_pos_x = rotated_local_position[0] + forklift_origin_global_x
        frame_global_pos_y = rotated_local_position[1] + forklift_origin_global_y

        return frame_global_pos_x, frame_global_pos_y

    def pick_up_object(self, object):

        pass
        x,y = self.get_frame_pos_as_global()


    """
    def drop_object(self, object='cube'):
        

        offset_x = self.FORK_LENGTH / 2 + self.CUBE_WIDTH/2

        object_global_x,object_global_y = self.get_frame_pos_as_global(0.36, 0, offset_x )
    """





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
        #if not self.odom_received:
            #self.move_object_relative_to_forklift_origon(0.1)
        self.odom_received = True

        

    def rotate(self):
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
            self.rotation_complete = True
            if self.timer:
                self.get_logger().info(f"Cancelling timer")
                self.timer.cancel()
                self.timer = None
        else:
            msg.angular.z = self.kp * error
            self.movement_controller.publish(msg)
            #self.get_logger().info(f"Target angle: {self.target_angle:.2f}, Current yaw: {self.current_yaw:.2f}, Error: {error:.2f}")

    
def main(args=None):
    rclpy.init(args=args)
    node = RotationNode()
    rate = node.create_rate(2)
    # https://answers.ros.org/question/358343/rate-and-sleep-function-in-rclpy-library-for-ros2/
    thread = threading.Thread(target=rclpy.spin, args=(node, ), daemon=True)
    thread.start()
    try:
        while rclpy.ok():
            node.handle_cmds()
            rate.sleep()
    except KeyboardInterrupt:
        pass

    rclpy.shutdown()

if __name__ == '__main__':
    main()
