import time
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from rcl_interfaces.msg import SetParametersResult, ParameterDescriptor
from smartyard_lab.core import validate_value

SENSOR_QOS = QoSProfile(depth=5, reliability=ReliabilityPolicy.BEST_EFFORT,
                        durability=DurabilityPolicy.VOLATILE)
STATE_QOS = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.VOLATILE)

class ConfigNode(Node):
    def __init__(self, name):
        super().__init__(name)
        self.rules = {}
        self.add_on_set_parameters_callback(self.validate_parameters)

    def setting(self, name, default, low=None, high=None, read_only=False):
        self.rules[name] = (type(default), low, high)
        descriptor = ParameterDescriptor(read_only=read_only,
                                         description='Smart yard educational setting')
        self.declare_parameter(name, default, descriptor)
        ok, why = validate_value(name, self.value(name), self.rules)
        if not ok:
            raise ValueError(why)

    def value(self, name):
        return self.get_parameter(name).value

    def validate_parameters(self, params):
        # Validation only: do not change timers or application state here.
        for param in params:
            ok, why = validate_value(param.name, param.value, self.rules)
            if not ok:
                return SetParametersResult(successful=False, reason=why)
        return SetParametersResult(successful=True)

def age(received):
    return time.monotonic() - received if received is not None else float('inf')

def finish(node, executor=None):
    import rclpy
    if executor:
        executor.shutdown(timeout_sec=2.0)
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()
