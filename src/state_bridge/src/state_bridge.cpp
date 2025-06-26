#include "state_bridge.hpp"

// In theory, this ros node could be replaced with pure Gazebo node
// but the bridge must run anyway for the clock
// https://gazebosim.org/api/transport/12/messages.html

using namespace state_bridge;

StateBridge::StateBridge(const rclcpp::NodeOptions & option) : rclcpp::Node("state_bridge", option) 
{   
    // Create messages that are publisher through mqtt_bridge
    pose_publisher_ = this->create_publisher<std_msgs::msg::String>("/object_state_updates", 10);
    pose_subscriber_ = this->create_subscription<tf2_msgs::msg::TFMessage>(
        "/object_state_updates_gz", 10, [this](const tf2_msgs::msg::TFMessage::SharedPtr msg) {
            this->pose_callback(msg);
        }
    );
}

void StateBridge::pose_callback(const tf2_msgs::msg::TFMessage::SharedPtr msg)
{   
    // The object poses are published by gazebos PosePublisher
    // In this case, the Pose_V type of gazebo is bridged to tf message type
    // in order to get the object name, which is the child_frame_id of the first (and only) transform
    std::string object_name;
    auto content = msg->transforms[0];
    object_name = content.child_frame_id;

    auto [roll, pitch, yaw] = quaternion_to_euler(
        content.transform.rotation.x,
        content.transform.rotation.y,
        content.transform.rotation.z,
        content.transform.rotation.w
    );

    Position position = {
        static_cast<float>(content.transform.translation.x),
        static_cast<float>(content.transform.translation.y),
        static_cast<float>(content.transform.translation.z),
        roll,
        pitch,
        yaw
        
    };

    position.round();

    // Construct the json payload that is sent to the "database"
    json payload = {};
    // See types.hpp for the to_json and from_json functions
    payload[object_name] = position;
    auto stringified_payload = payload.dump();
    auto message = std_msgs::msg::String();
    message.data = stringified_payload;
    pose_publisher_->publish(message);

}


// https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Writing-a-Composable-Node.html
#ifndef IS_COMPOSED

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<StateBridge>());
  rclcpp::shutdown();
  return 0;
}

#else
    #include <rclcpp_components/register_node_macro.hpp>
    //Namespace is needed here despite using namespace because macros are expanded before namespaces are checked
    RCLCPP_COMPONENTS_REGISTER_NODE(state_bridge::StateBridge)
#endif