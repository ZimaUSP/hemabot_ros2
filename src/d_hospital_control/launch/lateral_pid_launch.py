import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('d_hospital_control')
    default_params_file = os.path.join(pkg_share, 'config', 'pid_params.yaml')

    params_file = LaunchConfiguration('params_file')

    declare_params_file_cmd = DeclareLaunchArgument(
        name='params_file',
        default_value=default_params_file,
        description='Caminho para o arquivo yaml com os ganhos do PID',
    )

    lateral_pid_node = Node(
        package='d_hospital_control',
        executable='lateral_pid_controller',
        name='lateral_pid_controller',
        output='screen',
        parameters=[params_file, {'use_sim_time': True}],
    )

    ld = LaunchDescription()
    ld.add_action(declare_params_file_cmd)
    ld.add_action(lateral_pid_node)
    return ld
