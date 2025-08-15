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



}

void DroneController::search(){

    

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



