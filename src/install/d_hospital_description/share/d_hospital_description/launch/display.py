# Launch lidarbot URDF file using Rviz

# File adapted from https://automaticaddison.com

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource

from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    
    # Set the path to different files and folders
    pkg_path= FindPackageShare(package='d_hospital_description').find('d_hospital_description') #Define caminho para pacote 
    rviz_config_path = os.path.join(pkg_path, 'rviz/description.rviz') #Define configuração do Rviz2
    urdf_model_path = os.path.join(pkg_path, 'urdf/d_hospital.xacro') #Define caminho para o Xacro

    # Launch configuration variables specific to simulation
    gui = LaunchConfiguration('use_gui')  #Parâmetro de uso do GUI
    urdf_model = LaunchConfiguration('urdf_model') #Parâmetro do modelo URDF
    rviz_config_file = LaunchConfiguration('rviz_config_file') #Parâmetro da configuração de RVIZ
    use_sim_time = LaunchConfiguration('use_sim_time') #Parâmetro de tempo de simulação
    
    # Declare the launch arguments  
    declare_urdf_model_path_cmd = DeclareLaunchArgument( #Declara caminho do URDF com base no parâmetro
        name='urdf_model',
        default_value=urdf_model_path, 
        description='Absolute path to robot urdf file')
    
    declare_rviz_config_file_cmd = DeclareLaunchArgument( #Declaro configuração do RVIZ com base no parâmetro
        name='rviz_config_file',
        default_value=rviz_config_path,
        description='Full path to the RVIZ config file to use')
    
    declare_use_sim_time_cmd = DeclareLaunchArgument( #Declara configuração do tempo de uso de simulação com base no parâmetro
        name='use_sim_time',
        default_value='True',
        description='Use simulation (Gazebo) clock if true')

    declare_use_joint_state_publisher_gui_cmd = DeclareLaunchArgument( #Declara uso da interface do GUI com base no parâmetro
        name='use_gui',
        default_value='True',
        description='Flag to enable joint_state_publisher_gui')
    # A GUI to manipulate the joint state values
    start_joint_state_publisher_gui_node = Node( #Declara o nó da GUI de publicação de estados do joint do robô
        condition=IfCondition(gui),
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        name='joint_state_publisher_gui')
    
    # Start robot state publisher
    start_robot_state_publisher_cmd = IncludeLaunchDescription( #Declara o nó da publicação de estados do robô
        PythonLaunchDescriptionSource([os.path.join(pkg_path, 'launch', 'robot_hospital.py')]), 
        launch_arguments={'use_sim_time': use_sim_time, 'urdf_model': urdf_model}.items())

    # Launch RViz
    start_rviz_cmd = Node( #Inicia o RVIZ
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config_file])
    
    # Create the launch description and populate
    ld = LaunchDescription()
    
    # Declare the launch options
    ld.add_action(declare_urdf_model_path_cmd)
    ld.add_action(declare_rviz_config_file_cmd)
    ld.add_action(declare_use_joint_state_publisher_gui_cmd)
    ld.add_action(declare_use_sim_time_cmd)
    
    # Add any actions
    ld.add_action(start_joint_state_publisher_gui_node)
    ld.add_action(start_robot_state_publisher_cmd)
    ld.add_action(start_rviz_cmd)
    
    return ld