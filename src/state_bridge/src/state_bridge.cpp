#include "state_bridge.hpp"

// In theory, this ros node could be replaced with pure Gazebo node
// but the bridge must run anyway for the clock
// https://gazebosim.org/api/transport/12/messages.html

using namespace state_bridge;
using namespace attach_interfaces::srv;

StateBridge::StateBridge(const rclcpp::NodeOptions & option) : rclcpp::Node("state_bridge", option) 
{   

    cb_group_ = create_callback_group(rclcpp::CallbackGroupType::Reentrant);
    sub_options_ = rclcpp::SubscriptionOptions();
    sub_options_.callback_group = cb_group_;
    
    // Create messages that are publisher through mqtt_bridge
    pose_publisher_ = this->create_publisher<std_msgs::msg::String>("/object_state_updates", 10);
    
    pose_subscriber_ = this->create_subscription<tf2_msgs::msg::TFMessage>(
        "/object_state_updates_gz", 10, [this](const tf2_msgs::msg::TFMessage::SharedPtr msg) {
            this->pose_callback(msg);
        }
    );

    attach_srv_ = this->create_service<ChangeAttach>(
        "/change_attach", 
        [this](const ChangeAttach::Request::SharedPtr req, ChangeAttach::Response::SharedPtr res){
            attach_srv_callback(req, res);
        }, 
        rclcpp::ServicesQoS(),
        cb_group_
    );

}

void StateBridge::pose_callback(const tf2_msgs::msg::TFMessage::SharedPtr msg){   
    // The object poses are published by gazebos PosePublisher
    // In this case, the Pose_V type of gazebo is bridged to tf message type
    // in order to get the object name, which is the child_frame_id of the first (and only) transform
    auto content = msg->transforms[0];
    std::string object_name = content.child_frame_id;

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

     // Add the object name to the set of object names
     // If it was a new movable object, make initial detachement
    auto [iter, was_inserted] = object_names_.insert(object_name);
    if (was_inserted){
        //Try detach 5 times
        bool success = false;
        
        for (int i=0;i<5;i++){
            success = detach_object(object_name);
            if(success){
                break;
            }
        }

        if (!success){
                RCLCPP_WARN_STREAM(get_logger(), "The object could not be deattached. Simulation might be unusable");
            }
    }

}

bool StateBridge::attach_object(const std::string &object_name, const std::string &attach_to_target){

    std::promise<bool> promise;
    std::future<bool> future = promise.get_future();

    const std::string attach_topic = "/" + attach_to_target + "/" + object_name + "/attach";
    RCLCPP_INFO_STREAM(get_logger(), attach_topic);

    // Detach the object from the fork_1 link
    auto temp_attach_publisher = this->create_publisher<std_msgs::msg::Empty>(
        attach_topic, 10
    );

    const static auto msg = std_msgs::msg::Empty();

    auto temp_attach_state_subscriber = this->create_subscription<std_msgs::msg::String>(
        "/" + object_name + "/state", 10,
        [&promise, this](const std_msgs::msg::String::ConstSharedPtr msg) {
            RCLCPP_INFO_STREAM(get_logger(), "THE DATA IS: " + msg->data);
            if (msg->data == "attached") {
                promise.set_value(true);
            }    
        }, sub_options_
    );

    // Send the detach request every 1/10s
    timer_ = this->create_wall_timer(std::chrono::milliseconds(100), [this, temp_attach_publisher, object_name](){
        RCLCPP_INFO_STREAM(get_logger(), "Attaching");
        temp_attach_publisher->publish(msg);
    }, cb_group_);


    // Wait fot attach to be completed (or fail)
    auto status = future.wait_for(std::chrono::seconds(5));
    // Stop sending deattach messages
    timer_->cancel();

    if (status == std::future_status::timeout){
        return false;
    }

    return true;
    
}

bool StateBridge::detach_object(const std::string & object_name)
{   

    // Expensive operation, but it is not used often
    // (only at the start because the objects are attached initially)
    // I have opened an issue on the Gazebo issue tracker:
    // https://github.com/gazebosim/gz-sim/issues/3021

    // https://en.cppreference.com/w/cpp/thread/future.html
    std::promise<bool> promise;
    std::future<bool> future = promise.get_future();
    // Detach the object from the fork_1 link
    auto temp_detach_publisher = this->create_publisher<std_msgs::msg::Empty>(
        "/" + object_name + "/detach", 10
    );

    const static auto msg = std_msgs::msg::Empty();

    auto temp_detach_state_subscriber = this->create_subscription<std_msgs::msg::String>(
        "/" + object_name + "/state", 10,
        [&promise, this](const std_msgs::msg::String::ConstSharedPtr msg) {
            RCLCPP_INFO_STREAM(get_logger(), "THE DATA IS: " + msg->data);
            if (msg->data == "detached") {
                promise.set_value(true);
            }    
        }, sub_options_
    );

    // timer and temp_detach_state_subscriber run in the same callback group
    // in other of two the available threads

    // Send the detach request every 1/10s
    timer_ = this->create_wall_timer(std::chrono::milliseconds(100), [this, temp_detach_publisher, object_name](){
        temp_detach_publisher->publish(msg);
    }, cb_group_);


    // Wait fot detach to be completed (or fail)
    auto status = future.wait_for(std::chrono::seconds(5));
    // Stop sending deattach messages
    timer_->cancel();

    if (status == std::future_status::timeout){
        return false;
    }

    return true;

   
}

void state_bridge::StateBridge::attach_srv_callback(const attach_interfaces::srv::ChangeAttach::Request::SharedPtr req, attach_interfaces::srv::ChangeAttach::Response::SharedPtr res)
{
    const std::string object = req->object_name;
    const bool is_attach = req->attach;
    const std::string robot_to_attach_to = req->robot_name;

    RCLCPP_INFO_STREAM(get_logger(), "Received request");

    bool success = false;
    if (!is_attach){
        success = detach_object(object);
    }else{
        RCLCPP_INFO_STREAM(get_logger(), "Attaching!");
        success = attach_object(object, robot_to_attach_to);
    }

    res->success = success;

}


#include <rclcpp_components/register_node_macro.hpp>
//Namespace is needed here despite using namespace because macros are expanded before namespaces are checked
RCLCPP_COMPONENTS_REGISTER_NODE(state_bridge::StateBridge)
