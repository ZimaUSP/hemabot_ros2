    
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    keyboard_node = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop_twist_keyboard',
        parameters=[{'use_sim_time': "False"}],
        remappings=[('/cmd_vel', '/cmd_vel_keyboard')]
    )

    return LaunchDescription([
        keyboard_node
    ])