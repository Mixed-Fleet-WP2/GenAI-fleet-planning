import rclpy

from rclpy.node import Node
from rclpy.clock import Clock
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy, QoSDurabilityPolicy

from px4_msgs.msg import OffboardControlMode
from px4_msgs.msg import TrajectorySetpoint
from px4_msgs.msg import VehicleCommand

#FOR THIS TO WORK THE FOLLOWING HAVE TO BE SPECIFIED IN THE AIRFRAME

# param set-default NAV_DLL_ACT 0
# param set COM_RCL_EXCEPT 4
# param set COM_OF_LOSS_T 5

# THIS SHOULD BE SET BY DEFAULT BY PX4 WHEN USING SITL MODELS
# # param set UXRCE_DDS_SYNCT 0

#Modified from: https://github.com/Jaeyoung-Lim/px4-offboard
class DroneController(Node):

    def __init__(self):
        super().__init__('drone')
        qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.RMW_QOS_POLICY_RELIABILITY_BEST_EFFORT,
            durability=QoSDurabilityPolicy.RMW_QOS_POLICY_DURABILITY_TRANSIENT_LOCAL,
            history=QoSHistoryPolicy.RMW_QOS_POLICY_HISTORY_KEEP_LAST,
            depth=1
        )

        

       
        self.publisher_offboard_mode = self.create_publisher(OffboardControlMode, '/fmu/in/offboard_control_mode', qos_profile)
        self.publisher_trajectory = self.create_publisher(TrajectorySetpoint, '/fmu/in/trajectory_setpoint', qos_profile)

        self.vehicle_command_publisher = self.create_publisher(VehicleCommand, '/fmu/in/vehicle_command', qos_profile)

        self.offboard_setpoint_counter = 0


        self.offboard_timer = self.create_timer(1.0, self.timer_callback)


    def timer_callback(self):

        #Switch to offboard mode after sending appropriate
        #the autopilot will only switch to offboard mode if it has received
        #enough offboard control messages (i.e. a stable stream of them)
        if self.offboard_setpoint_counter == 10:
            self.get_logger().info("Switching to offboard mode")

            msg_mode = VehicleCommand()
            msg_mode.param1 = 1.0
            msg_mode.param2 = 6.0
            msg_mode.command = VehicleCommand.VEHICLE_CMD_DO_SET_MODE
            msg_mode.target_system = 1
            msg_mode.target_component = 1
            msg_mode.source_system = 1
            msg_mode.source_component = 1
            msg_mode.from_external = True
            msg_mode.timestamp = int(Clock().now().nanoseconds / 1000)
            self.vehicle_command_publisher.publish(msg_mode)

            self.arm()
            self.get_logger().info("Arming vehicle")
        
        self.publish_offboard_control_mode()
        self.publish_trajectory_setpoint()

        if self.offboard_setpoint_counter < 11:
            self.offboard_setpoint_counter += 1

    #This function is used to publish the trajectory setpoint
    #which actually tells the autopilot where to go
    #However, this functions only after offboard mode is set and the vehicle is armed
    def publish_trajectory_setpoint(self):
        trajectory_msg = TrajectorySetpoint()
        #Because in mavlink coord frame, positive z is down, we need to set z to negative
        #See https://docs.px4.io/main/en/ros2/user_guide.html#ros-2-px4-frame-conventions
        trajectory_msg.position = [0.0, 0.0, -5.0]
        trajectory_msg.yaw = -3.14
        trajectory_msg.timestamp = int(Clock().now().nanoseconds / 1000)
        self.publisher_trajectory.publish(trajectory_msg)

    #This tells the autopilot px4 what kind of control message we are sending/are going to send
    #In this case, we are sending position setpoints only.
    #If these are not sent at regular intervals, the autopilot will switch to fail-safe mode
    #as a safety feature
    def publish_offboard_control_mode(self):

        offboard_msg = OffboardControlMode()
        offboard_msg.position=True
        offboard_msg.velocity=False
        offboard_msg.acceleration=False
        offboard_msg.attitude=False
        offboard_msg.body_rate=False
        offboard_msg.timestamp = int(Clock().now().nanoseconds / 1000)
        self.publisher_offboard_mode.publish(offboard_msg)

    #Modified from:
    #https://github.com/PX4/px4_ros_com/blob/main/src/examples/offboard/offboard_control.cpp

    #Command params can be seen from:
    #https://github.com/PX4/px4_msgs/blob/main/msg/VehicleCommand.msg
    def arm(self):
        vehicle_command_msg = VehicleCommand()
        vehicle_command_msg.timestamp = int(Clock().now().nanoseconds / 1000)
        vehicle_command_msg.command = VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM
        vehicle_command_msg.param1 = 1.0
        vehicle_command_msg.target_system = 1
        vehicle_command_msg.target_component = 1
        self.vehicle_command_publisher.publish(vehicle_command_msg)
        self.get_logger().info('Publishing: "%s"' % vehicle_command_msg)
       

def main(args=None):
    rclpy.init(args=args)

    offboard_control = DroneController()

    rclpy.spin(offboard_control)

    offboard_control.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
