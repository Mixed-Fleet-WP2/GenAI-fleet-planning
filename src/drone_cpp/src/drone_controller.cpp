#include "drone_controller.hh"
#include "conversion_utils.hpp"

DroneController::DroneController() :
    Node("default_name"){
    
    node_name_ = this->get_name();

    callback_group_ = create_callback_group(
        rclcpp::CallbackGroupType::MutuallyExclusive,
        false);
    
    callback_group_executor_.add_callback_group(callback_group_, get_node_base_interface());

    nav_to_pose_client_ = rclcpp_action::create_client<NavToPoseAction>(
        this, // Pass a reference to the node
        "navigate_to_pose", //This is defined by the nav2 launch system already,
        callback_group_
    );

    move_to_pose_subscriber_ = this->create_subscription<std_msgs::msg::String>(
        "move", 10, 
        [this](const std::shared_ptr<std_msgs::msg::String> msg) {
            this->move_to_pose_callback(msg);
        }
    );

    odom_subsciber_ = create_subscription<OdomMsg>(
        "odom", 10,
        [this](const std::shared_ptr<OdomMsg> msg){
            this->odom_received_callback(msg);
        }
    );

    feedback_publisher_ = this->create_publisher<std_msgs::msg::String>(
        "feedback", 10);
    
    status_publisher_ = this->create_publisher<std_msgs::msg::String>("/robot_state_updates", 10);

    current_pos_ = {};

}

DroneController::~DroneController(){

}

void DroneController::move_to_pose_callback(
    const std::shared_ptr<std_msgs::msg::String> msg){
    
    try {
        const std::string &msg_str = msg->data;
        json json_object = json::parse(msg_str);
        json args_object = json_object["args"];
        // How to iterate over json object
        //https://json.nlohmann.me/features/iterators/#access-object-keys-during-iteration
        for (const auto& elem : args_object.items() ){
            if (elem.value().is_number_float()){
                // https://cplusplus.com/reference/string/stof/
                float arg_as_float = elem.value();
                RCLCPP_INFO(get_logger(), "The value is %f", arg_as_float);
            }else{
                RCLCPP_ERROR(get_logger(),"The argument of json was not a float!");
            }
        }
    }catch (int errorCode){
        
    }

    
}
void DroneController::odom_received_callback(const std::shared_ptr<OdomMsg> msg) {

    // https://docs.ros2.org/foxy/api/std_msgs/msg/Header.html
    // Since gazebo clock is used, the timestamp is relative to simulation start
    auto timestamp = msg->header.stamp.sec;
    auto [roll, pitch, yaw] = quaternion_to_euler(msg->pose.pose.orientation.x,msg->pose.pose.orientation.y,
                                        msg->pose.pose.orientation.z, msg->pose.pose.orientation.w);
    
    auto x = static_cast<float>(msg->pose.pose.position.x);
    auto y = static_cast<float>(msg->pose.pose.position.y);
    auto z = static_cast<float>(msg->pose.pose.position.z);
                      
    current_pos_ = {x,y,z,roll,pitch,yaw};
    current_pos_.round();

    // https://json.nlohmann.me/features/arbitrary_types/
    
    // Construct the json payload that is sent to the "database"
    json status = {};
    status[node_name_] = {
        {"robot_status", "online"},
        {"robot_position", {current_pos_.x, current_pos_.y, current_pos_.z}},
        {"timestamp", timestamp}
    };

    auto stringified_status = status.dump();
    auto message = std_msgs::msg::String();
    message.data = stringified_status;
    status_publisher_->publish(message);
    
};

void DroneController::nav_result_callback(
    const NavToPoseGoalHandle::WrappedResult &result){

    switch (result.code) {
        case rclcpp_action::ResultCode::SUCCEEDED:
            RCLCPP_INFO(get_logger(), "Navigation succeeded");
            return;
        case rclcpp_action::ResultCode::ABORTED:
            RCLCPP_ERROR(get_logger(), "Goal failed");
            return;
        case rclcpp_action::ResultCode::CANCELED:
            RCLCPP_ERROR(get_logger(), "Goal was canceled");
            return;
        default:
            RCLCPP_ERROR(get_logger(), "Unknown status code");
            return;
        }
}


void DroneController::nav_feedback_callback(std::shared_ptr<NavToPoseGoalHandle>, const std::shared_ptr<const NavToPoseAction::Feedback> feedback){
    auto curr_pose_x = feedback->current_pose.pose.position.x;
    auto curr_pose_y = feedback->current_pose.pose.position.y;
    RCLCPP_INFO(get_logger(), "Current pose (%f, %f)", curr_pose_x, curr_pose_y);
}

void DroneController::nav_goal_acknowledged_callback(const std::shared_ptr<NavToPoseGoalHandle> &goal){
    if (!goal) {
        RCLCPP_ERROR(get_logger(), "Failed to send goal to server");
    }else{
        RCLCPP_INFO(get_logger(), "Sent goal to server");
    }

}

void DroneController::navigate_to_pose(const Position &pos){

    if (!nav_to_pose_client_->wait_for_action_server(std::chrono::seconds(10))){
        RCLCPP_ERROR(this->get_logger(), "Action server not available after waiting");
        return;
    }

    // Action definition can be seen from:
    // https://github.com/ros-navigation/navigation2/blob/main/nav2_msgs/action/NavigateToPose.action
    PoseStampedMsg goal_msg;
    goal_msg.pose.position.x = pos.x;
    goal_msg.pose.position.y = pos.y;
    //goal_msg.pose.position.z = pos.z
    NavToPoseAction::Goal goal;
    goal.pose = goal_msg;

    auto send_goal_options = rclcpp_action::Client<NavToPoseAction>::SendGoalOptions();

    send_goal_options.goal_response_callback = [this](const 
            NavToPoseGoalHandle::SharedPtr &goal){
            this->nav_goal_acknowledged_callback(goal);
        };

    send_goal_options.feedback_callback = [this](std::shared_ptr<NavToPoseGoalHandle> g,
        const std::shared_ptr<const NavToPoseAction::Feedback> feedback){
            this->nav_feedback_callback(g, feedback);
        };

    send_goal_options.result_callback = 
        [this](const NavToPoseGoalHandle::WrappedResult
            &result){
                this->nav_result_callback(result);
            };
    
    future_goal_handle_ = nav_to_pose_client_->async_send_goal(goal, send_goal_options);
    

};

/**
 * Round the value of the Position to one decimal place
 */
void DroneController::Position::round() {
    // https://www.reddit.com/r/cpp_questions/comments/173uhmq/how_do_i_round_a_double_to_one_decimal/
    x = std::round(x*10) / 10;
    y = std::round(y*10) / 10;
    z = std::round(z*10) / 10;
    angular_x = std::round(angular_x*10) / 10;
    angular_y = std::round(angular_y*10) / 10;
    angular_z = std::round(angular_z*10) / 10;

}

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<DroneController>());
  rclcpp::shutdown();
  return 0;
}



