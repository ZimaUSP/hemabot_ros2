"""Adaptador em memória usado no diagnóstico; executar após carregar o ROS/workspace.

Uso: python3 docs/simular_fortress_sem_editar.py use_sim_time:=true
Não edita o launch original. A inicialização visual foi validada no robô;
controle, sensores, TF e navegação ainda precisam de validação independente.
"""

import os
import sys
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchService


def main():
    share = Path(get_package_share_directory('d_hospital_gz'))
    for name in ('IGN_GAZEBO_RESOURCE_PATH', 'GZ_SIM_RESOURCE_PATH'):
        previous = os.environ.get(name, '')
        os.environ[name] = str(share / 'models') + (os.pathsep + previous if previous else '')

    path = share / 'launch' / 'gz_launch.py'
    code = path.read_text()
    code = code.replace('ros_ign_gazebo', 'ros_gz_sim')
    code = code.replace('ign_gazebo.launch.py', 'gz_sim.launch.py')
    scope = {'__file__': str(path), '__name__': 'temporary_simulation_launch'}
    exec(compile(code, str(path), 'exec'), scope)
    service = LaunchService(argv=sys.argv[1:] or ['use_sim_time:=true'])
    service.include_launch_description(scope['generate_launch_description']())
    return service.run()


if __name__ == '__main__':
    raise SystemExit(main())
