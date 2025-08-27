#include "mf_utils/navigatable.hpp"

Navigatable::Navigatable() : Node("default_name"){

    node_name_ = this->get_name();

    // https://docs.ros.org/en/foxy/How-To-Guides/Using-callback-groups.html#basics-of-callback-groups
    odom_callback_group_ = create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
    auto odom_subsciber_options = rclcpp::SubscriptionOptions();
    odom_subsciber_options.callback_group = odom_callback_group_;

    nav_callback_group_ = create_callback_group(rclcpp::CallbackGroupType::Reentrant);

    // Run the navigation client in a separate cb group/in a separate thread
    nav_to_pose_client_ = rclcpp_action::create_client<NavToPoseAction>(
        this, // Pass a reference to the node
        "navigate_to_pose", //This is defined by the nav2 launch system already,
        nav_callback_group_
    );

    nav_through_poses_client_ = rclcpp_action::create_client<FollowWaypointsAction>(
        this,
        "follow_waypoints",
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


void Navigatable::move_to_pose_callback(
    const std::shared_ptr<std_msgs::msg::String> msg){
    
    const std::string &msg_str = msg->data;
    
    auto action = parse_json<MoveAction>(msg_str, this);
    
    if (!action.has_value()){
        return;
    }

    // Calls send_nav_goal eventually
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
            this->nav_feedback_callback<NavToPoseGoalHandle, NavToPoseAction>(g, feedback, id);
        };

    send_goal_options.result_callback = 
        [this, id](const NavToPoseGoalHandle::WrappedResult
            &result){
                this->nav_result_callback<NavToPoseGoalHandle>(result, id);
            };
    
    future_goal_handle_ = nav_to_pose_client_->async_send_goal(goal, send_goal_options);

}

void Navigatable::send_nav_goals(std::vector<MoveAction> waypoints, std::function<void(const FollowWaypointsActionGoalHandle::WrappedResult&, int)> result_callback){

    // The actions are a bundle that shares the id
    int id = waypoints.at(0).action_id;
    //RCLCPP_INFO_STREAM(get_logger(), std::to_string(result_callback));

    if (!nav_through_poses_client_->wait_for_action_server(std::chrono::seconds(10))){
        RCLCPP_ERROR(this->get_logger(), "Action server not available after waiting");
        return;
    }

    std::vector<PoseStampedMsg> points;
    points.reserve(waypoints.size());

    std::transform(waypoints.begin(), waypoints.end(),
               std::back_inserter(points),
        [this](const MoveAction &action) {
            auto [qx,qy,qz,qw] = euler_to_quaternion(action.roll, action.pitch, action.yaw);
            PoseStampedMsg goal_msg;
            goal_msg.header.frame_id = "map";
            goal_msg.header.stamp = this->get_clock()->now();
            goal_msg.pose.position.x = action.x;
            goal_msg.pose.position.y = action.y;
            goal_msg.pose.position.z = action.z;
            goal_msg.pose.orientation.x = qx;
            goal_msg.pose.orientation.y = qy;
            goal_msg.pose.orientation.z = qz;
            goal_msg.pose.orientation.w = qw;
            return goal_msg;
    });

    

    FollowWaypointsAction::Goal goals;
    
    goals.poses = points;

    auto send_goal_options = rclcpp_action::Client<FollowWaypointsAction>::SendGoalOptions();

    send_goal_options.goal_response_callback = [this, id](const 
            FollowWaypointsActionGoalHandle::SharedPtr &goal){
            this->nav_goal_acknowledged_callback(goal, id);
        };

    send_goal_options.feedback_callback = [this, id](std::shared_ptr<FollowWaypointsActionGoalHandle> g,
        const std::shared_ptr<const FollowWaypointsAction::Feedback> feedback){
            this->nav_feedback_callback<FollowWaypointsActionGoalHandle, FollowWaypointsAction>(g, feedback, id);
        };
    
    
    auto callback = [this, id, result_callback](const FollowWaypointsActionGoalHandle::WrappedResult &result) {
        if (result_callback) {
            RCLCPP_INFO_STREAM(get_logger(), "Using custom callback");
            result_callback(result, id);
        } else {
            RCLCPP_INFO_STREAM(get_logger(), "Using default callback");
            this->nav_result_callback<FollowWaypointsActionGoalHandle>(result, id);
        }
    };

    send_goal_options.result_callback = callback;

    waypoint_future_goal_handle_ = nav_through_poses_client_->async_send_goal(goals, send_goal_options);

}

void Navigatable::send_feedback(Feedback feedback){

    RCLCPP_INFO_STREAM(get_logger(), "Sending feedback msg: " + feedback.message);
    // Implicit conversion
    json feedback_json = feedback;

    std_msgs::msg::String msg = std_msgs::msg::String();
    msg.data = feedback_json.dump();

    feedback_publisher_->publish(msg);

}

void Navigatable::send_sysml_feedback(std::string topic_without_namespace, json json_object){

        // https://docs.ros.org/en/rolling/Concepts/Intermediate/About-Quality-of-Service-Settings.html
        rclcpp::QoS qos(1);
        // This keeps messages in buffer for late subscribers (i.e mqtt client)
        qos.transient_local();
        // Quarantee sending
        qos.reliable();  

        const auto temp_publisher = this->create_publisher<std_msgs::msg::String>(topic_without_namespace, qos);
        
        std_msgs::msg::String msg = std_msgs::msg::String();

        msg.data = json_object.dump();
        temp_publisher->publish(msg);
        // Sleep a bit so message is sent before publisher is destroyed
        rclcpp::sleep_for(std::chrono::seconds(2));

}