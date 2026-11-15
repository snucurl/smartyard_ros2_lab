from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    config = PathJoinSubstitution([FindPackageShare('smartyard_lab'), 'config', 'yard.yaml'])
    nodes = [Node(package='smartyard_lab', executable=name,
                  namespace=LaunchConfiguration('namespace'), output='screen',
                  parameters=[LaunchConfiguration('config')])
             for name in ['sensor_station', 'transporter', 'dispatch_checker', 'control_center']]
    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value='yard01'),
        DeclareLaunchArgument('config', default_value=config), *nodes])
