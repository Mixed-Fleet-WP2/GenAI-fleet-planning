#include "drone_controller.hh"


DroneController::DroneController() :
    Node("default_name"){
    
    node_name_ = this->get_name();
    
    // https://docs.ros.org/en/foxy/How-To-Guides/Using-callback-groups.html#basics-of-callback-groups
    odom_callback_group_ = create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
    auto odom_subsciber_options = rclcpp::SubscriptionOptions();
    odom_subsciber_options.callback_group = odom_callback_group_;

    nav_callback_group_ = create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
    auto nav_subscriber_options = rclcpp::SubscriptionOptions();
    nav_subscriber_options.callback_group = nav_callback_group_;
    
    // Run the navigation client in a separate cb group/in a separate thread
    nav_to_pose_client_ = rclcpp_action::create_client<NavToPoseAction>(
        this, // Pass a reference to the node
        "navigate_to_pose", //This is defined by the nav2 launch system already,
        nav_callback_group_
    );

    // Assign the move_to_pose subsciber to the same callback group
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

    //THINGS RUNNING IN DIFFERENT THREADS:
    // odom
    // navigation
    // lift

    // Everything else in main thread

    feedback_publisher_ = this->create_publisher<std_msgs::msg::String>(
        "/feedback", 10);
    
    lift_publisher_  = create_publisher<TwistMsg>("cmd_vel", 10);
    
    status_publisher_ = this->create_publisher<std_msgs::msg::String>("/robot_state_updates", 10);

    current_pos_ = {};

}

DroneController::~DroneController() noexcept
{
}

void DroneController::move_to_pose_callback(
    const std::shared_ptr<std_msgs::msg::String> msg){
    
    try {
        const std::string &msg_str = msg->data;
        
        if (json::accept(msg_str)){
            RCLCPP_ERROR_STREAM(get_logger(), "Received invalid json of the format: " + msg_str);
        }
        
        json json_object = json::parse(msg_str);
        // https://json.nlohmann.me/home/exceptions/#jsonexceptiontype_error302
        ExecutableAction action = json_object.template get<ExecutableAction>();
        auto args = action.command_arguments;

        std::thread t([this, args](){
            
            lift(stof(args.at("z")));
            
            navigate_to_pose(stof(args.at("x")),
                        stof(args.at("y")),
                        stof(args.at("z")),                
                        stof(args.at("roll")),
                        stof(args.at("pitch")),
                        stof(args.at("yaw")));
        });


    }catch (json::type_error &e){
        RCLCPP_ERROR_STREAM(get_logger(), e.what());
    }catch (std::out_of_range &e){
        RCLCPP_ERROR_STREAM(get_logger(), &e);
    }catch(std::invalid_argument &e){
        RCLCPP_ERROR_STREAM(get_logger(), &e);
    }

}

void DroneController::lift(float z){
    // https://docs.ros2.org/foxy/api/rclcpp/classrclcpp_1_1QoS.html#a98fb6b31d7c5cbd4788412663fd38cfb


    


}

void DroneController::odom_received_callback(const std::shared_ptr<OdomMsg> msg) {

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
    status_publisher_->publish(message);
    
};

////https://robotics.stackexchange.com/questions/107697/turtlebot4-nav2-how-to-call-action-navigatetopose-from-node-in-cpp
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

void DroneController::navigate_to_pose(const float x, const float y, const float z, const float roll, const float pitch, const float yaw){

    if (!nav_to_pose_client_->wait_for_action_server(std::chrono::seconds(10))){
        RCLCPP_ERROR(this->get_logger(), "Action server not available after waiting");
        return;
    }

    // Action definition can be seen from:
    // https://github.com/ros-navigation/navigation2/blob/main/nav2_msgs/action/NavigateToPose.action
    auto [qx,qy,qz,qw] = euler_to_quaternion(roll, pitch,yaw);
    auto goal_msg = PoseStampedMsg();
    goal_msg.pose.position.x = x;
    goal_msg.pose.position.y = y;
    goal_msg.pose.position.z = z;
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

int main(int argc, char * argv[])
{
    rclcpp::init(argc, argv);

    // Assign 3 threads: the main thread and two other for the two callback groups
    auto executor = rclcpp::executors::MultiThreadedExecutor(rclcpp::ExecutorOptions(), 3);
    executor.add_node(std::make_shared<DroneController>());
    executor.spin();
    rclcpp::shutdown();
    return 0;
}



