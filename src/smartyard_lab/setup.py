from glob import glob
from setuptools import find_packages, setup

setup(
    name='smartyard_lab', version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/smartyard_lab']),
        ('share/smartyard_lab', ['package.xml']),
        ('share/smartyard_lab/launch', glob('launch/*.launch.py')),
        ('share/smartyard_lab/config', glob('config/*.yaml')),
    ],
    install_requires=['setuptools'], zip_safe=True,
    maintainer='Smart Yard Course', maintainer_email='maintainer@example.com',
    description='ROS 2 Humble smart yard lab', license='MIT',
    tests_require=['pytest'],
    entry_points={'console_scripts': [
        'sensor_station = smartyard_lab.sensor_station:main',
        'control_center = smartyard_lab.control_center:main',
        'dispatch_checker = smartyard_lab.dispatch_checker:main',
        'transporter = smartyard_lab.transporter:main',
        'parameter_tool = smartyard_lab.parameter_tool:main',
    ]},
)
