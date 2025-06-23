#include "state_bridge.hpp"

StateBridge::StateBridge() : rclcpp::Node("default_name") 
{
    pose_publisher_ = this->create_publisher<std_msgs::msg::String>("object_positions", 10);
    pose_subscriber_ = this->create_subscription<tf2_msgs::msg::TFMessage>(
        "object_positions", 10, [this](const tf2_msgs::msg::TFMessage::SharedPtr msg) {
            this->pose_callback(msg);
        }
    );
}

void StateBridge::pose_callback(const tf2_msgs::msg::TFMessage::SharedPtr msg)
{   
    // The object poses are publisher by gazebos PosePublisher
    // In this case, the Pose_V type of gazebo is bridged to tf message type
    // in order to get the object name, which is the child_frame_id of the first (and only) transform
    std::string object_name;
    if (!msg->transforms.empty()) {
        object_name = msg->transforms[0].child_frame_id;
    }
}
