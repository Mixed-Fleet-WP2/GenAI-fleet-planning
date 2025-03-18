from launch.substitutions import LaunchConfiguration
from launch import LaunchContext
from launch.actions import OpaqueFunction

def launch_print(context:LaunchContext, item:LaunchConfiguration):

    item_val = item.perform(context)

    print("THE VALUE OF THE ITEM IS: ", item_val)

