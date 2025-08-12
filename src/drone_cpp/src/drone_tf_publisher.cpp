#include "drone_tf_publisher.hpp"
#include <iostream>

DroneTfPublisher::DroneTfPublisher() : 
    rclcpp::Node("default"){
    
    odometry_subscription_ = this->create_subscription<nav_msgs::msg::Odometry>(
        "odom", 10,
        std::bind(&DroneTfPublisher::publish_transform, this, std::placeholders::_1));
    tf_broadcaster_ = std::make_unique<tf2_ros::TransformBroadcaster>(*this);

}

void DroneTfPublisher::publish_transform(const nav_msgs::msg::Odometry &msg){

    geometry_msgs::msg::TransformStamped t;

    // Read message content and assign it to
    // corresponding tf variables
    t.header.stamp = this->get_clock()->now();

    // Publish transform base_link -> base_footprint
    t.header.frame_id = "base_link";
    t.child_frame_id = "base_footprint";

    // https://docs.ros2.org/foxy/api/nav_msgs/msg/Odometry.html
    //double drone_pos_x = msg.pose.pose.position.x;
    //double drone_pos_y = msg.pose.pose.position.y;
    double drone_pos_z = msg.pose.pose.position.z;

    t.transform.translation.x = 0.0;
    t.transform.translation.y = 0.0;
    // Set translation negative because the footprint is projection to the ground
    t.transform.translation.z = -drone_pos_z;

    double drone_quaternion_x = msg.pose.pose.orientation.x;
    double drone_quaternion_y = msg.pose.pose.orientation.y;
    double drone_quaternion_z = msg.pose.pose.orientation.z;
    double drone_quaternion_w = msg.pose.pose.orientation.w;
    tf2::Quaternion drone_q(drone_quaternion_x, drone_quaternion_y,
                            drone_quaternion_z, drone_quaternion_w);
    
    // https://answers.ros.org/question/371925/
    // drone_q = drone_q.normalize();

    //https://robotics.stackexchange.com/questions/46421/transform-quaternion
    // Convert quaternion into matrix
    tf2::Matrix3x3 m(drone_q);

    double roll, pitch, yaw;
    // Get euler from the matrix
    m.getRPY(roll, pitch, yaw);
    
    // Set the quaternion values based on euler
    // See: http://wiki.ros.org/tf2/Tutorials/Quaternions
    drone_q.setEuler(0,0, yaw);
    // https://answers.ros.org/question/371925/
    drone_q = drone_q.normalize();

    tf2::Quaternion q;
    q.setRPY(0, 0, msg.pose.pose.orientation.x);
    t.transform.rotation.x = q.x();
    t.transform.rotation.y = q.y();
    t.transform.rotation.z = q.z();
    t.transform.rotation.w =  q.w();
    //RCLCPP_INFO(this->get_logger(), "Got here");
    tf_broadcaster_->sendTransform(t);

}

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<DroneTfPublisher>());
  rclcpp::shutdown();
  return 0;
}