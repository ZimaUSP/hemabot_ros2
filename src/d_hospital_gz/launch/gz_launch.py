"""Launch the complete HemaBot simulation with ROS 2 and Gazebo Sim."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    AppendEnvironmentVariable,
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    RegisterEventHandler,
)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_gz = get_package_share_directory("d_hospital_gz")
    pkg_ros_gz_sim = get_package_share_directory("ros_gz_sim")

    default_world = os.path.join(pkg_gz, "worlds", "obstacles.world")
    default_urdf = os.path.join(pkg_gz, "urdf", "d_hospital_gz.urdf.xacro")
    bridge_config = os.path.join(pkg_gz, "config", "lidarbot_bridge.yaml")
    controllers_config = os.path.join(pkg_gz, "config", "controllers.yaml")

    world = LaunchConfiguration("world")
    urdf_path = LaunchConfiguration("urdf_path")
    gz_args = LaunchConfiguration("gz_args")
    spawn_z = LaunchConfiguration("spawn_z")
    use_sim_time = LaunchConfiguration("use_sim_time")

    robot_description = {
        "robot_description": Command(["xacro ", urdf_path]),
        "use_sim_time": use_sim_time,
    }

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[robot_description],
    )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, "launch", "gz_sim.launch.py")
        ),
        launch_arguments={
            "gz_args": [gz_args, " ", world],
            "on_exit_shutdown": "true",
        }.items(),
    )

    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        name="spawn_d_hospital",
        output="screen",
        arguments=[
            "-topic",
            "robot_description",
            "-name",
            "d_hospital",
            "-allow_renaming",
            "true",
            "-z",
            spawn_z,
        ],
    )

    spawn_controllers = Node(
        package="controller_manager",
        executable="spawner",
        output="screen",
        arguments=[
            "joint_state_broadcaster",
            "diff_controller",
            "--controller-manager",
            "/controller_manager",
            "--param-file",
            controllers_config,
            "--controller-manager-timeout",
            "60",
            "--switch-timeout",
            "60",
            "--service-call-timeout",
            "60",
        ],
    )

    start_controllers_after_spawn = RegisterEventHandler(
        OnProcessExit(
            target_action=spawn_robot,
            on_exit=[spawn_controllers],
        )
    )

    gazebo_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="gazebo_bridge",
        output="screen",
        parameters=[
            {
                "config_file": bridge_config,
                "use_sim_time": use_sim_time,
            }
        ],
    )

    image_bridge = Node(
        package="ros_gz_image",
        executable="image_bridge",
        name="camera_image_bridge",
        output="screen",
        arguments=["/camera/image_raw"],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "world",
                default_value=default_world,
                description="Absolute path to the Gazebo world file",
            ),
            DeclareLaunchArgument(
                "urdf_path",
                default_value=default_urdf,
                description="Absolute path to the robot Xacro file",
            ),
            DeclareLaunchArgument(
                "gz_args",
                default_value="-r -v 4",
                description=(
                    "Arguments passed to Gazebo. Use '-r -s -v 4' for headless mode"
                ),
            ),
            DeclareLaunchArgument(
                "spawn_z",
                default_value="0.08",
                description="Initial robot height above the ground in metres",
            ),
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="true",
                description="Use the Gazebo simulation clock",
            ),
            AppendEnvironmentVariable(
                "GZ_SIM_RESOURCE_PATH", os.path.join(pkg_gz, "models")
            ),
            robot_state_publisher,
            gazebo,
            spawn_robot,
            gazebo_bridge,
            image_bridge,
            start_controllers_after_spawn,
        ]
    )
