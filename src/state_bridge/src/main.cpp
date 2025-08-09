#include "rclcpp/rclcpp.hpp"
#include "state_bridge.hpp"


// https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Writing-a-Composable-Node.html
int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
    // Assign 3 threads: the main thread and two other for the two callback groups
    auto executor = rclcpp::executors::MultiThreadedExecutor(rclcpp::ExecutorOptions(), 2);
    auto node = std::make_shared<state_bridge::StateBridge>();
    executor.add_node(node);
    executor.spin();
    rclcpp::shutdown();
    return 0;
}