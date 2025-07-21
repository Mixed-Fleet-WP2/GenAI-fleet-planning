#include "drone_controller.hh"


DroneController::DroneController() : Navigatable(){
    
    lift_publisher_  = create_publisher<TwistMsg>("cmd_vel", 10);
    pid_controller_ = PIDController(lift_interval_, 0.18, 0.0, 0.4);
    
}

void DroneController::lift(const float z, std::function<void()> send_nav_goal, rclcpp::Time start, int action_id){
    auto twist_msg = TwistMsg();

    const auto elapsed_time = (this->now() - start).seconds();
    float error = z - current_pos_.z;

    // Preempt the action if it takes too long
    if (elapsed_time > 30.0){
        Feedback feedback = {action_id, CANCELLED, "Drone lift timeout!"};
        send_feedback(feedback);

    }

    if (std::abs(error) < 0.05) {
        lift_timer_->cancel();
        RCLCPP_INFO_STREAM(get_logger(), "Stopping lift");
        // Send stop command
        twist_msg.linear.z = 0.0;
        lift_publisher_->publish(twist_msg);
        send_nav_goal();
        return;
    }

    float control_value = pid_controller_.calculate_input(error);
    //RCLCPP_INFO_STREAM(get_logger(), "CONTROL VALUE IS: " + std::to_string(control_value));
    twist_msg.linear.z = control_value;
    lift_publisher_->publish(twist_msg);

}

void DroneController::navigate_to_pose(const Position& pos, int action_id){

    auto run_2D_nav = [this, pos, action_id](){
        this->send_nav_goal(pos, action_id);
    };

    // If the drone needs to move in the z-axis, execute the lift operation
    // in a timer callback and after that run the 2D navigation

    // Dimensions are in meters
    if (std::abs(current_pos_.z - pos.z) > 0.05) {
        RCLCPP_INFO_STREAM(get_logger(), "LIFT IN PROGRESS");
        pid_controller_.set_new_goal(pos.z, current_pos_.z);
        // Run the lift operation in a callback based timer that is assigned its own callback group
        // After lift, the callback calls 2d navigation
        auto start_time = this->now();
        lift_timer_ = this->create_wall_timer(std::chrono::milliseconds(lift_interval_),
        [this, z=pos.z, run_2D_nav, start_time, action_id]() {this->lift(z, run_2D_nav, start_time, action_id);}, nav_callback_group_);
        
        return;
    }

    //If no lift is needed, just run 2D nav
    run_2D_nav();
    
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



