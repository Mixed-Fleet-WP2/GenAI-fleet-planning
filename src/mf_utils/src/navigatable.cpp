#include "mf_utils/navigatable.hpp"

Navigatable::Navigatable() : Node("default_name"){

    node_name_ = this->get_name();

    // https://docs.ros.org/en/foxy/How-To-Guides/Using-callback-groups.html#basics-of-callback-groups
    odom_callback_group_ = create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
    auto odom_subsciber_options = rclcpp::SubscriptionOptions();
    odom_subsciber_options.callback_group = odom_callback_group_;

    nav_callback_group_ = create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);

    // Run the navigation client in a separate cb group/in a separate thread
    nav_to_pose_client_ = rclcpp_action::create_client<NavToPoseAction>(
        this, // Pass a reference to the node
        "navigate_to_pose", //This is defined by the nav2 launch system already,
        nav_callback_group_
    );

    move_to_pose_subscriber_ = this->create_subscription<std_msgs::msg::String>(
        "move", 10, 
        [this](const std::shared_ptr<std_msgs::msg::String> msg) {
            this->move_to_pose_callback(msg);
        }
    );

    // Run in its own thread
    odom_subsciber_ = create_subscription<OdomMsg>(
        "odom", 10,
        [this](const std::shared_ptr<OdomMsg> msg){
            this->odom_received_callback(msg);
        },
        odom_subsciber_options
    );

    // THINGS RUNNING IN DIFFERENT THREADS:
    // odom
    // nav2 callbacks
    // lift (in normal std::thread)

    feedback_publisher_ = this->create_publisher<std_msgs::msg::String>(
        "/feedback", 10);
    

    status_publisher_ = this->create_publisher<std_msgs::msg::String>("/robot_state_updates", 10);

    current_pos_ = {};

}

void Navigatable::nav_feedback_callback(std::shared_ptr<NavToPoseGoalHandle>, const std::shared_ptr<const NavToPoseAction::Feedback> feedback, int action_id){
    auto curr_pose_x = feedback->current_pose.pose.position.x;
    auto curr_pose_y = feedback->current_pose.pose.position.y;

    //RCLCPP_INFO(get_logger(), "Current pose (%f, %f)", curr_pose_x, curr_pose_y);
}

void Navigatable::nav_goal_acknowledged_callback(std::shared_ptr<NavToPoseGoalHandle> goal, int action_id){
    if (!goal) {
        Feedback feedback = {action_id, ERROR, "Failed to send nav goal to action server"};
        send_feedback(feedback);
    }else{
        RCLCPP_INFO(get_logger(), "Sent goal to server");
    }

}

void Navigatable::move_to_pose_callback(
    const std::shared_ptr<std_msgs::msg::String> msg){
    
    RCLCPP_INFO_STREAM(get_logger(), "RECEIVED NAV REQUEST");
    const std::string &msg_str = msg->data;
    
    auto action = parse_json<MoveAction>(msg_str, this);
    
    if (!action.has_value()){
        return;
    }

    navigate_to_pose(action.value());

}

void Navigatable::odom_received_callback(const std::shared_ptr<OdomMsg> msg) {


    //RCLCPP_INFO_STREAM(get_logger(), "ODOM RECEIVED");
    // https://docs.ros2.org/foxy/api/std_msgs/msg/Header.html
    // Since gazebo clock is used, the timestamp is relative to simulation start

    int32_t timestamp = msg->header.stamp.sec;
    auto [roll, pitch, yaw] = quaternion_to_euler(msg->pose.pose.orientation.x,msg->pose.pose.orientation.y,
                                        msg->pose.pose.orientation.z, msg->pose.pose.orientation.w);
    
    current_pos_.x = static_cast<float>(msg->pose.pose.position.x);
    current_pos_.y = static_cast<float>(msg->pose.pose.position.y);
    current_pos_.z = static_cast<float>(msg->pose.pose.position.z);
    current_pos_.roll = roll;
    current_pos_.pitch = pitch;
    // Rotate the object so the long side is 
    current_pos_.yaw = yaw;
    current_pos_.round();

    // https://json.nlohmann.me/features/arbitrary_types/
    
    // Construct the json payload that is sent to the "database"
    
    RobotState state = {};
    state.robot_position = current_pos_;
    state.robot_status = RobotStatus(ONLINE);
    state.timestamp = timestamp;
    
    json status = {};
    status[node_name_] = state;
    
    auto message = std_msgs::msg::String();
    message.data = status.dump();
    status_publisher_->publish(message);
    
};

////https://robotics.stackexchange.com/questions/107697/turtlebot4-nav2-how-to-call-action-navigatetopose-from-node-in-cpp
void Navigatable::nav_result_callback(
    const NavToPoseGoalHandle::WrappedResult &result, int action_id){
     RCLCPP_INFO_STREAM(get_logger(), "CALLBACKS");
    Feedback feedback = {};
    feedback.action_id = action_id;
    
    switch (result.code) {
        case rclcpp_action::ResultCode::SUCCEEDED:
            feedback.type = SUCCESS;
            feedback.message = "Navigation succeeded";
            break;
        case rclcpp_action::ResultCode::ABORTED:
            feedback.type = ERROR;
            feedback.message = result.result->error_msg;
            break;
        case rclcpp_action::ResultCode::CANCELED:
            feedback.type = CANCELLED;
            feedback.message = "Goal was canceled";
            break;
        default:
            feedback.type = ERROR;
            feedback.message = "Unknow status code received from navigation";
            break;
        }
    RCLCPP_INFO_STREAM(get_logger(), "SENDIN NAV FEED");
    send_feedback(feedback);
}

void Navigatable::send_nav_goal(const MoveAction& action){

    int id = action.action_id;

    if (std::abs(action.x - current_pos_.x) < 0.1 &&
        (std::abs(action.y - current_pos_.y) < 0.1) &&
        (std::abs(action.yaw - current_pos_.yaw)) < 5) {
            RCLCPP_INFO_STREAM(get_logger(), "GOAL DONE");
            send_feedback({id, SUCCESS, "Navigation to goal complete"});
            return;
        }

    if (!nav_to_pose_client_->wait_for_action_server(std::chrono::seconds(10))){
        RCLCPP_ERROR(this->get_logger(), "Action server not available after waiting");
        return;
    }

    RCLCPP_ERROR_STREAM(get_logger(), "NAV GOAL SENDING");
    // Action definition can be seen from:
    // https://github.com/ros-navigation/navigation2/blob/main/nav2_msgs/action/NavigateToPose.action
    auto [qx,qy,qz,qw] = euler_to_quaternion(action.roll, action.pitch, action.yaw);
    auto goal_msg = PoseStampedMsg();
    goal_msg.header.frame_id = "map";
    goal_msg.header.stamp = this->get_clock()->now();
    goal_msg.pose.position.x = action.x;
    goal_msg.pose.position.y = action.y;
    goal_msg.pose.position.z = action.z;
    goal_msg.pose.orientation.x = qx;
    goal_msg.pose.orientation.y = qy;
    goal_msg.pose.orientation.z = qz;
    goal_msg.pose.orientation.w = qw;
    

    NavToPoseAction::Goal goal;
    
    goal.pose = goal_msg;

    auto send_goal_options = rclcpp_action::Client<NavToPoseAction>::SendGoalOptions();

    send_goal_options.goal_response_callback = [this, id](const 
            NavToPoseGoalHandle::SharedPtr &goal){
            this->nav_goal_acknowledged_callback(goal, id);
        };

    send_goal_options.feedback_callback = [this, id](std::shared_ptr<NavToPoseGoalHandle> g,
        const std::shared_ptr<const NavToPoseAction::Feedback> feedback){
            this->nav_feedback_callback(g, feedback, id);
        };

    send_goal_options.result_callback = 
        [this, id](const NavToPoseGoalHandle::WrappedResult
            &result){
                this->nav_result_callback(result, id);
            };
    
    future_goal_handle_ = nav_to_pose_client_->async_send_goal(goal, send_goal_options);

}

void Navigatable::send_feedback(Feedback feedback){

    RCLCPP_INFO_STREAM(get_logger(), feedback.message);
    // Implicit conversion
    json feedback_json = feedback;

    std_msgs::msg::String msg = std_msgs::msg::String();
    msg.data = feedback_json.dump();

    feedback_publisher_->publish(msg);

}