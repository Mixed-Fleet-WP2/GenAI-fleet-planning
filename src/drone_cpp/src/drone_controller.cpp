#include "drone_controller.hh"


DroneController::DroneController() : Navigatable(){
    
    lift_publisher_  = create_publisher<TwistMsg>("cmd_vel", 10);
    pid_controller_ = PIDController(lift_interval_, 0.18, 0.0, 0.4);
    
}

void DroneController::lift(rclcpp::Time start, const MoveAction action){
    auto twist_msg = TwistMsg();

    const int id = action.action_id;
    const auto elapsed_time = (this->now() - start).seconds();
    float error = id - current_pos_.z;

    // Preempt the action if it takes too long
    if (elapsed_time > 30.0){
        Feedback feedback = {id, CANCELLED, "Drone lift timeout!"};
        send_feedback(feedback);

    }

    if (std::abs(error) < 0.05) {
        lift_timer_->cancel();
        RCLCPP_INFO_STREAM(get_logger(), "Stopping lift");
        // Send stop command
        twist_msg.linear.z = 0.0;
        lift_publisher_->publish(twist_msg);
        send_nav_goal(action);
        return;
    }

    float control_value = pid_controller_.calculate_input(error);
    //RCLCPP_INFO_STREAM(get_logger(), "CONTROL VALUE IS: " + std::to_string(control_value));
    twist_msg.linear.z = control_value;
    lift_publisher_->publish(twist_msg);

}

void DroneController::navigate_to_pose(const MoveAction& action){

    // If the drone needs to move in the z-axis, execute the lift operation
    // in a timer callback and after that run the 2D navigation

    // Dimensions are in meters
    if (std::abs(current_pos_.z - action.z) > 0.05) {
        RCLCPP_INFO_STREAM(get_logger(), "LIFT IN PROGRESS");
        pid_controller_.set_new_goal(action.z, current_pos_.z);
        // Run the lift operation in a callback based timer that is assigned its own callback group
        // After lift, the callback calls 2d navigation
        auto start_time = this->now();
        lift_timer_ = this->create_wall_timer(std::chrono::milliseconds(lift_interval_),
        [this, action, start_time]() {this->lift(start_time, action);}, nav_callback_group_);
        
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



