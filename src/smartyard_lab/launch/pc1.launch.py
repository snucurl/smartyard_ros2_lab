from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    default_config = PathJoinSubstitution([FindPackageShare('smartyard_lab'), 'config', 'yard.yaml'])
    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value='yard01'),
        DeclareLaunchArgument('config', default_value=default_config),
        Node(package='smartyard_lab', executable='sensor_station',
             namespace=LaunchConfiguration('namespace'), output='screen',
             parameters=[LaunchConfiguration('config')]),
    ])
