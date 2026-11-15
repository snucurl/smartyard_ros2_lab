cmake_minimum_required(VERSION 3.8)
project(smartyard_interfaces)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(builtin_interfaces REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/YardSensor.msg"
  "msg/VehicleState.msg"
  "srv/CheckTransport.srv"
  "action/TransportBlock.action"
  DEPENDENCIES builtin_interfaces
)
ament_export_dependencies(rosidl_default_runtime)
ament_package()
