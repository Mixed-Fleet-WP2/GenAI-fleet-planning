#include "drone_controller.hh"

explicit DroneController::DroneController(const std::string &node_name) :
    Node(node_name){

    callback_group_ = create_callback_group(
        rclcpp::CallbackGroupType::MutuallyExclusive,
        false);
    
    callback_group_executor_.add_callback_group(callback_group_, 
        get_node_base_interface());

    nav_to_pose_client_ = rclcpp_action::create_client<NavToPoseAction>(
        this, // Get the node info by passing this
        "navigate_to_pose", //This is defined by the nav2 launch system already,
        callback_group_
    );

    move_to_pose_subscriber_ = this->create_subscription<std_msgs::msg::String>(
        "move", 10, 
        [this](const std::shared_ptr<std_msgs::msg::String> msg) {
            this->move_to_pose_callback(msg);
        }
    );

    feedback_publisher_ = this->create_publisher<std_msgs::msg::String>(
        "feedback", 10);

}


void DroneController::move_to_pose_callback(
    const std::shared_ptr<std_msgs::msg::String> msg){

    const std::string &msg_str = msg->data;
    json json_object = json::parse(msg_str);

    for (const auto& key : json_object){

        if (json_object[key].is_number_float()){
            // https://cplusplus.com/reference/string/stof/
            float arg_as_float = json_object[key];
        }else{
            RCLCPP_ERROR(get_logger(),"The argument of json was not a float!");
        }
    }
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

