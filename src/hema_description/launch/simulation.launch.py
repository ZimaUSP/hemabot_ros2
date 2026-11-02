#!/usr/bin/env python3
"""Inicia Hema em ROS 2 Jazzy/Harmonic ou Humble/Gazebo Classic."""

import os
from pathlib import Path
import shlex
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    EmitEvent,
    IncludeLaunchDescription,
    LogInfo,
    OpaqueFunction,
    RegisterEventHandler,
    SetEnvironmentVariable,
)
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
import xacro
import yaml


def _continue_on_success(next_actions, label):
    """Interrompe a sequência se o spawn ou a ativação de um controlador falhar."""
    def callback(event, context):
        if event.returncode == 0:
            return next_actions
        reason = f'{label} falhou (código {event.returncode}). Consulte o log acima.'
        return [LogInfo(msg=f'ERROR: {reason}'), EmitEvent(event=Shutdown(reason=reason))]
    return callback


def _launch_setup(context):
    package_share = Path(get_package_share_directory('hema_description'))
    backend = LaunchConfiguration('backend').perform(context)
    interface = LaunchConfiguration('command_interface').perform(context)
    gui = LaunchConfiguration('gui').perform(context)
    spawn_z = LaunchConfiguration('spawn_z').perform(context)
    controller_file = package_share / 'config' / f'controllers_{interface}.yaml'

    # A mesma interface seleciona o hardware Xacro e seu YAML de controladores.
    description = xacro.process_file(
        str(package_share / 'urdf' / 'robot.urdf.xacro'),
        mappings={
            'backend': backend,
            'command_interface': interface,
            'controllers_file': str(controller_file),
            'articulate_slides': LaunchConfiguration('articulate_slides').perform(context),
            'caster_z_adjust': LaunchConfiguration('caster_z_adjust').perform(context),
        },
    ).toxml()
    # Classic/Humble repassa robot_description como override de parametro ROS.
    # Comentarios com texto livre (por exemplo ': ') podem quebrar esse parser.
    # O roundtrip elimina comentarios, preservando os elementos da descricao.
    description = ET.tostring(ET.fromstring(description), encoding='unicode')
    state_publisher = Node(
        package='robot_state_publisher', executable='robot_state_publisher',
        name='robot_state_publisher', output='screen',
        parameters=[{
            'robot_description': ParameterValue(description, value_type=str),
            'use_sim_time': True,
        }],
    )

    # O plugin do simulador cria /controller_manager; não iniciar outro nó igual.
    joint_state_spawner = Node(
        package='controller_manager', executable='spawner', output='screen',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager',
                   '--controller-manager-timeout', '120', '--switch-timeout', '120'],
    )
    wheel_spawner = Node(
        package='controller_manager', executable='spawner', output='screen',
        arguments=['wheel_controller', '--controller-manager', '/controller_manager',
                   '--controller-manager-timeout', '120', '--switch-timeout', '120'],
    )

    extra_actions = []
    if backend == 'harmonic':
        simulator_share = Path(get_package_share_directory('ros_gz_sim'))
        world_path = package_share / 'worlds' / 'empty.sdf'
        # gz_sim.launch.py usa um comando shell: proteger caminhos com espaços.
        gz_args = f'-r -v 3 {shlex.quote(str(world_path))}'
        if gui == 'false':
            gz_args = f'-s {gz_args}'
        simulator = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(simulator_share / 'launch' / 'gz_sim.launch.py')),
            launch_arguments={'gz_args': gz_args, 'on_exit_shutdown': 'true'}.items(),
        )
        spawn = Node(
            package='ros_gz_sim', executable='create', output='screen',
            arguments=['-world', 'hema_world', '-name', 'hema',
                       '-topic', '/robot_description', '-z', spawn_z],
        )
        extra_actions.append(Node(
            package='ros_gz_bridge', executable='parameter_bridge',
            name='hema_clock_bridge', output='screen',
            arguments=['/world/hema_world/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
            remappings=[('/world/hema_world/clock', '/clock')],
        ))
    else:
        simulator_share = Path(get_package_share_directory('gazebo_ros'))
        simulator = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(simulator_share / 'launch' / 'gazebo.launch.py')),
            launch_arguments={
                'world': str(package_share / 'worlds' / 'empty.world'),
                'gui': gui, 'pause': 'false', 'verbose': 'true', 'server_required': 'true',
            }.items(),
        )
        spawn = Node(
            package='gazebo_ros', executable='spawn_entity.py', output='screen',
            arguments=['-entity', 'hema', '-topic', '/robot_description',
                       '-z', spawn_z, '-timeout', '120'],
        )

    # Os handlers são registrados antes dos processos para evitar condições de corrida.
    spawn_to_states = RegisterEventHandler(OnProcessExit(
        target_action=spawn,
        on_exit=_continue_on_success([joint_state_spawner], 'Inserção do robô'),
    ))
    states_to_wheels = RegisterEventHandler(OnProcessExit(
        target_action=joint_state_spawner,
        on_exit=_continue_on_success([wheel_spawner], 'joint_state_broadcaster'),
    ))
    check_wheels = RegisterEventHandler(OnProcessExit(
        target_action=wheel_spawner,
        on_exit=_continue_on_success([], 'wheel_controller'),
    ))
    resource_root = str(package_share.parent)
    resource_env = []
    for variable in ('GZ_SIM_RESOURCE_PATH', 'GAZEBO_MODEL_PATH'):
        inherited = os.environ.get(variable, '')
        value = resource_root + (os.pathsep + inherited if inherited else '')
        resource_env.append(SetEnvironmentVariable(name=variable, value=value))

    return [*resource_env, spawn_to_states, states_to_wheels, check_wheels,
            state_publisher, simulator, *extra_actions, spawn]


def generate_launch_description():
    share = Path(get_package_share_directory('hema_description'))
    cad = yaml.safe_load((share / 'config' / 'cad_parameters.yaml').read_text())
    return LaunchDescription([
        DeclareLaunchArgument('backend', default_value='harmonic', choices=['harmonic', 'classic'],
                              description='Jazzy/Harmonic ou Humble/Classic.'),
        DeclareLaunchArgument('command_interface', default_value='velocity',
                              choices=['velocity', 'position', 'effort'],
                              description='Interface de comando das duas rodas.'),
        DeclareLaunchArgument('articulate_slides', default_value='false', choices=['true', 'false'],
                              description='Libera as corrediças passivas; exige revisão mecânica.'),
        DeclareLaunchArgument('caster_z_adjust', default_value=str(cad['caster_z_adjust']),
                              description='Ajuste vertical da rodinha em metros.'),
        DeclareLaunchArgument('spawn_z', default_value=str(cad['wheel_radius'] + 0.01),
                              description='Altura inicial do eixo das rodas: raio + 0.01 m.'),
        DeclareLaunchArgument('gui', default_value='true', choices=['true', 'false'],
                              description='Abre a interface gráfica do simulador.'),
        OpaqueFunction(function=_launch_setup),
    ])
