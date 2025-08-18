#include "drone_controller.hh"


DroneController::DroneController() : Navigatable(){
    
    lift_publisher_  = create_publisher<TwistMsg>("cmd_vel", 10);
    pid_controller_ = PIDController(lift_interval_, 0.18, 0.0, 0.4);

    search_subscription_ = this->create_subscription<std_msgs::msg::String>("search", 10, [this](const std_msgs::msg::String::ConstSharedPtr msg){
        this->search_callback(msg);
    });
    
}


void DroneController::search_callback(std_msgs::msg::String::ConstSharedPtr msg){

    // No command arguments to parse but at least check that action id is present
    auto action = parse_json<SearchAction>(msg->data, this);

    if (!action.has_value()){
        return;
    }

    search(action.value());

}

void DroneController::search(SearchAction action){

    const static MoveAction rack_1 = {action.action_id,
                                    -12, 3.25, 2.0, 0.0, 0.0, -1.57};
    const static MoveAction rack_2 = {action.action_id,
                                    1.0, -16.7, 2.0, 0,0,-1.57};
    const static MoveAction rack_3 = {action.action_id, 11, 22, 2.0, 0, 0, 3.14};
     
    // Rack 2 is the "found rack" so it is last
    //rack_3, rack_1, 
    std::vector<MoveAction> nav_goals = {{action.action_id,
                                    1.0, -1.0, 0.5, 0,0,-1.57}};
    

    std::function<void(const FollowWaypointsActionGoalHandle::WrappedResult&, int)> success_callback = [this](const FollowWaypointsActionGoalHandle::WrappedResult &result, int action_id){
            if(result.code == rclcpp_action::ResultCode::SUCCEEDED){
                Position rack_position = {1.0, -16.7, 0.2, 0, 0, -1.57};
                Feedback fb;
                fb.type = SUCCESS;
                fb.action_id = action_id;
                fb.message = "Search success";
                fb.return_value = rack_position;
                send_feedback(fb);
            }else{
                send_feedback({action_id, ERROR, "Search failed", {}});
            }
    };

    // If the drone needs to move in the z-axis, execute the lift operation
    // in a timer callback and after that run the 2D navigation

    // Dimensions are in meters

    // Actions share the z axis, so use the z of first
    if (std::abs(current_pos_.z - rack_1.z) > 0.05) {
        pid_controller_.set_new_goal(rack_1.z, current_pos_.z);
        // Run the lift operation in a callback based timer that is assigned its own callback group
        // After lift, the callback calls 2d navigation
        auto start_time = this->now();
        lift_timer_ = this->create_wall_timer(std::chrono::milliseconds(lift_interval_),
        // Lift needs the action id of some action to send feedback
        // since all MoveActions in search share the same action id (because they are under the search-action)
        // pass the first action
        [this, nav_goals, start_time, success_callback]() {this->lift(start_time, nav_goals.at(0), [this, nav_goals, success_callback](){send_nav_goals(nav_goals, success_callback);});}, nav_callback_group_);
        
        return;
    }

    

    // Pass a custom success callback
    send_nav_goals(nav_goals, success_callback);

}

void DroneController::navigate_to_pose(const MoveAction& action){

    // If the drone needs to move in the z-axis, execute the lift operation
    // in a timer callback and after that run the 2D navigation

    // Dimensions are in meters
    if (std::abs(current_pos_.z - action.z) > 0.05) {
        pid_controller_.set_new_goal(action.z, current_pos_.z);
        // Run the lift operation in a callback based timer that is assigned its own callback group
        // After lift, the callback calls 2d navigation
        auto start_time = this->now();
        lift_timer_ = this->create_wall_timer(std::chrono::milliseconds(lift_interval_),
        [this, action, start_time]() {this->lift(start_time, action, [this, action](){send_nav_goal(action);});}, nav_callback_group_);
        
        return;
    }

    //If no lift is needed, just run 2D nav
    send_nav_goal(action);
    
    return;
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

    rclcpp::shutdown();
    return 0;
}



