"""PC 3: short, read-only eligibility service using cached telemetry."""
import time
import rclpy
from smartyard_interfaces.msg import YardSensor, VehicleState
from smartyard_interfaces.srv import CheckTransport
from smartyard_lab.common import ConfigNode, SENSOR_QOS, STATE_QOS, age, finish
from smartyard_lab.core import check_transport

class DispatchChecker(ConfigNode):
    def __init__(self):
        super().__init__('dispatch_checker')
        self.setting('max_load_t', 50.0, 0.1, 200.0)
        self.setting('max_wind_mps', 10.0, 0.0, 60.0)
        self.setting('sensor_timeout_sec', 3.0, 0.5, 30.0)
        self.sensor = self.vehicle = None
        self.sensor_received = self.vehicle_received = None
        self.sensor_sub = self.create_subscription(YardSensor, 'sensor_state', self.on_sensor, SENSOR_QOS)
        self.vehicle_sub = self.create_subscription(VehicleState, 'vehicle_state', self.on_vehicle, STATE_QOS)
        self.service = self.create_service(CheckTransport, 'check_transport', self.check)
        self.get_logger().info('READY check_transport')

    def on_sensor(self, msg):
        self.sensor, self.sensor_received = msg, time.monotonic()

    def on_vehicle(self, msg):
        self.vehicle, self.vehicle_received = msg, time.monotonic()

    def check(self, request, response):
        allowed, reason, distance = check_transport(
            request, self.sensor, age(self.sensor_received),
            self.value('sensor_timeout_sec'), self.value('max_load_t'),
            self.value('max_wind_mps'),
            self.vehicle.busy if self.vehicle else False, age(self.vehicle_received))
        response.allowed, response.reason, response.distance_m = allowed, reason, distance
        self.get_logger().info(f'CHECK {request.job_id}: allowed={allowed} reason={reason}')
        return response

def main(args=None):
    rclpy.init(args=args)
    node = DispatchChecker()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        finish(node)
