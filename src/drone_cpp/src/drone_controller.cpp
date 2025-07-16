#include "drone_controller.hh"


DroneController::DroneController() :
    Node("default_name"){
    
    node_name_ = this->get_name();

    //auto pid_controller_ = PIDController(lift_interval_, 0.1, 0.5, 0.3);

    // https://docs.ros.org/en/foxy/How-To-Guides/Using-callback-groups.html#basics-of-callback-groups
    odom_callback_group_ = create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
    auto odom_subsciber_options = rclcpp::SubscriptionOptions();
    odom_subsciber_options.callback_group = odom_callback_group_;

    nav_callback_group_ = create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
    // auto nav_subscriber_options = rclcpp::SubscriptionOptions();
    // nav_subscriber_options.callback_group = nav_callback_group_;
    
    // Run the navigation client in a separate cb group/in a separate thread
    nav_to_pose_client_ = rclcpp_action::create_client<NavToPoseAction>(
        this, // Pass a reference to the node
        "navigate_to_pose" //This is defined by the nav2 launch system already,
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
    // navigation
    // lift (in normal std::thread)

    // Everything else in main thread

    feedback_publisher_ = this->create_publisher<std_msgs::msg::String>(
        "/feedback", 10);
    
    lift_publisher_  = create_publisher<TwistMsg>("cmd_vel", 10);
    
    status_publisher_ = this->create_publisher<std_msgs::msg::String>("/robot_state_updates", 10);

    current_pos_ = {};


}


void DroneController::move_to_pose_callback(
    const std::shared_ptr<std_msgs::msg::String> msg){
    
    RCLCPP_INFO(get_logger(), "Moving requested");
    

    try {
        const std::string &msg_str = msg->data;
        
        if (!json::accept(msg_str)){
            RCLCPP_ERROR_STREAM(get_logger(), "Received invalid json of the format: " + msg_str);
            return;
        }
        
        json json_object = json::parse(msg_str);
        // https://json.nlohmann.me/home/exceptions/#jsonexceptiontype_error302
        ExecutableAction action = json_object.template get<ExecutableAction>();
        auto args = action.command_arguments;

        Position new_pos = {};
        new_pos.x =  args.at("x").get<float>();
        new_pos.y = args.at("y").get<float>();
        new_pos.z = args.at("z").get<float>();
        new_pos.roll = args.at("roll").get<float>();
        new_pos.pitch = args.at("pitch").get<float>();
        new_pos.yaw = args.at("yaw").get<float>();

        navigate_to_pose(new_pos, action.action_id);

        

    }catch (json::type_error &e){
        RCLCPP_ERROR_STREAM(get_logger(), e.what());
    }catch (std::out_of_range &e){
        RCLCPP_ERROR_STREAM(get_logger(), e.what());
    }catch(std::invalid_argument &e){
        RCLCPP_ERROR_STREAM(get_logger(), e.what());
    }

}

void DroneController::lift_callback(const float z, std::function<void()> cb, rclcpp::Time start){
    auto twist_msg = TwistMsg();

    const auto elapsed_time = (this->now() - start).seconds();
    //RCLCPP_INFO_STREAM(get_logger(), "ELAPSED TIME: " + std::to_string(elapsed_time));

    float error = z - current_pos_.z;

    if (std::abs(error) < 0.1 || elapsed_time > 30.0) {
        lift_timer_->cancel();
        RCLCPP_INFO_STREAM(get_logger(), "Stopping lift");
        // Send stop command
        twist_msg.linear.z = 0.0;
        lift_publisher_->publish(twist_msg);
        return;
    }

    float control_value = pid_controller_.calculate_input(error);
    RCLCPP_INFO_STREAM(get_logger(), "CONTROL VALUE IS: " + std::to_string(control_value));
    twist_msg.linear.z = control_value;
    lift_publisher_->publish(twist_msg);

}


void DroneController::odom_received_callback(const std::shared_ptr<OdomMsg> msg) {


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
    //RCLCPP_INFO_STREAM(get_logger(), "Publishing" + message.data);
    status_publisher_->publish(message);
    
};

////https://robotics.stackexchange.com/questions/107697/turtlebot4-nav2-how-to-call-action-navigatetopose-from-node-in-cpp
void DroneController::nav_result_callback(
    const NavToPoseGoalHandle::WrappedResult &result, int action_id){

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


void DroneController::nav_feedback_callback(std::shared_ptr<NavToPoseGoalHandle>, const std::shared_ptr<const NavToPoseAction::Feedback> feedback, int action_id){
    auto curr_pose_x = feedback->current_pose.pose.position.x;
    auto curr_pose_y = feedback->current_pose.pose.position.y;
    RCLCPP_INFO(get_logger(), "Current pose (%f, %f)", curr_pose_x, curr_pose_y);
}

void DroneController::nav_goal_acknowledged_callback(std::shared_ptr<NavToPoseGoalHandle> goal){
    if (!goal) {
        RCLCPP_ERROR(get_logger(), "Failed to send goal to server");
    }else{
        RCLCPP_INFO(get_logger(), "Sent goal to server");
    }

}

void DroneController::navigate_to_pose(const Position& pos, int action_id){

    if (std::abs(current_pos_.x - pos.x) < 0.1 &&
        std::abs(current_pos_.y - pos.y) < 0.1 &&
        std::abs(current_pos_.z - pos.z) < 0.1 &&
        std::abs(current_pos_.yaw - pos.yaw) < 5){
        
        return;
    }

    auto continuation_func = [this, pos, action_id](){
        this->send_nav_goal(pos, action_id);
    };

    // If the drone needs to move in the z-axis, execute the operation
    // in a timer callback and after that run the 2D navigation
    if (std::abs(current_pos_.z - pos.z) > 0.1) {
        RCLCPP_INFO_STREAM(get_logger(), "LIFT IN PROGRESS");
        pid_controller_.set_new_goal(pos.z, current_pos_.z);
        // Run the lift operation in a callback based timer that is assigned its own callback group
        auto start_time = this->now();
        lift_timer_ = this->create_wall_timer(std::chrono::milliseconds(lift_interval_),
        [this, z=pos.z, continuation_func, start_time]() {this->lift_callback(z, continuation_func, start_time);}, nav_callback_group_);
        
        return;
    }

    //If no lift is needed, just run 2D nav
    continuation_func();
    
    return;
}

void DroneController::send_nav_goal(const Position& pos, int action_id){

    if (!nav_to_pose_client_->wait_for_action_server(std::chrono::seconds(10))){
        RCLCPP_ERROR(this->get_logger(), "Action server not available after waiting");
        return;
    }

    // Action definition can be seen from:
    // https://github.com/ros-navigation/navigation2/blob/main/nav2_msgs/action/NavigateToPose.action
    auto [qx,qy,qz,qw] = euler_to_quaternion(pos.roll, pos.pitch, pos.yaw);
    auto goal_msg = PoseStampedMsg();
    goal_msg.pose.position.x = pos.x;
    goal_msg.pose.position.y = pos.y;
    goal_msg.pose.position.z = pos.z;
    goal_msg.pose.orientation.x = qx;
    goal_msg.pose.orientation.y = qy;
    goal_msg.pose.orientation.z = qz;
    goal_msg.pose.orientation.w = qw;
    
    NavToPoseAction::Goal goal;
    
    goal.pose = goal_msg;

    auto send_goal_options = rclcpp_action::Client<NavToPoseAction>::SendGoalOptions();

    send_goal_options.goal_response_callback = [this](const 
            NavToPoseGoalHandle::SharedPtr &goal){
            this->nav_goal_acknowledged_callback(goal);
        };

    send_goal_options.feedback_callback = [this, action_id](std::shared_ptr<NavToPoseGoalHandle> g,
        const std::shared_ptr<const NavToPoseAction::Feedback> feedback){
            this->nav_feedback_callback(g, feedback, action_id);
        };

    send_goal_options.result_callback = 
        [this, action_id](const NavToPoseGoalHandle::WrappedResult
            &result){
                this->nav_result_callback(result, action_id);
            };
    
    future_goal_handle_ = nav_to_pose_client_->async_send_goal(goal, send_goal_options);

}

int main(int argc, char * argv[])
{
    rclcpp::init(argc, argv);
    
    // Assign 3 threads: the main thread and two other for the two callback groups
    auto executor = rclcpp::executors::MultiThreadedExecutor(rclcpp::ExecutorOptions(), 3);
    auto node = std::make_shared<DroneController>();
    executor.add_node(node);
    executor.spin();

    rclcpp::shutdown();

    // rclcpp::spin(std::make_shared<DroneController>());

    rclcpp::shutdown();
    return 0;
}



