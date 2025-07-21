from launch.actions import OpaqueFunction
from launch import Substitution
from launch.launch_context import LaunchContext
from launch.launch_description import LaunchDescription

def print_helper(items, context: LaunchContext):

    print_str: str = ""
    for arg in items:

        # Get the value the substitution holds
        if isinstance(arg, Substitution):
            
            arg = arg.perform(context=context)
        
        print_str += f"{str(arg)} "
    

def launch_print(*args: str|int|float|bool|Substitution, launch_description: LaunchDescription):

    if not launch_description:
        raise ValueError("No LaunchDescription object supplied to launch_print")
    if not isinstance(launch_description, LaunchDescription):
        raise TypeError(f"""Launch print expects launch_description
                        to be of type {type(LaunchDescription)}. 
                        Got type {type(launch_description)} instead""")
    
    launch_description.add_action(
        OpaqueFunction(function=lambda context: print_helper(args, context)))


