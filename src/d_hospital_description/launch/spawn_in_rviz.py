from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
import os
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # Diretório do pacote d_hospital_gazebo
    d_hospital_gazebo_dir = get_package_share_directory('d_hospital_description')

    # Declarando o argumento gui com valor padrão "true"
    gui_arg = DeclareLaunchArgument(
        'gui',
        default_value='true',
        description='Se deve ou não iniciar o Gazebo com GUI'
    )

    # Incluindo o arquivo de lançamento hospital.launch.py
    include_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(d_hospital_gazebo_dir, 'launch', 'display.py')
        ),
        launch_arguments={'gui': LaunchConfiguration('gui')}.items()
    )

    return LaunchDescription([
        gui_arg,
        include_launch
    ])
