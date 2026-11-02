import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'd_hospital_control'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='D Hospital',
    maintainer_email='user@example.com',
    description='Controlador PID em malha fechada para corrigir o erro lateral (e_y) usando odometria.',
    license='BSD 3-Clause',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'lateral_pid_controller = d_hospital_control.lateral_pid_controller:main',
        ],
    },
)
