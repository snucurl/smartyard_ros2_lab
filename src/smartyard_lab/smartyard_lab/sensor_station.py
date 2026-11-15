"""PC 1: periodic sensor publisher and independent vehicle observer."""
import time
import rclpy
from rclpy.qos import ReliabilityPolicy, QoSProfile
from smartyard_interfaces.msg import YardSensor, VehicleState
from smartyard_lab.common import ConfigNode, SENSOR_QOS, STATE_QOS, finish

class SensorStation(ConfigNode):
    def __init__(self):
        super().__init__('sensor_station')
        self.setting('publish_rate_hz', 5.0, 0.5, 20.0)
        self.setting('load_t', 40.0, 0.1, 200.0)
        self.setting('wind_speed_mps', 6.0, 0.0, 60.0)
        self.setting('route_blocked', False)
        self.setting('block_id', 'BLOCK_001')
        self.setting('zone_id', 'A')
        self.setting('reliable_sensor', False, read_only=True)
        qos = (QoSProfile(depth=5, reliability=ReliabilityPolicy.RELIABLE)
               if self.value('reliable_sensor') else SENSOR_QOS)
        self.publisher = self.create_publisher(YardSensor, 'sensor_state', qos)
        self.subscription = self.create_subscription(
            VehicleState, 'vehicle_state', self.on_vehicle, STATE_QOS)
        self.sequence = 0
        self.last_publish = 0.0
        self.last_vehicle = None
        # Fixed 100 Hz scheduler; committed rate is read on every tick.
        self.timer = self.create_timer(0.01, self.tick)
        self.get_logger().info('READY sensor_station; topic=sensor_state')

    def tick(self):
        now = time.monotonic()
        if now - self.last_publish < 1.0 / self.value('publish_rate_hz'):
            return
        self.last_publish = now
        self.sequence += 1
        msg = YardSensor()
        msg.stamp = self.get_clock().now().to_msg()
        msg.sequence = self.sequence
        for name in ('zone_id', 'block_id', 'load_t', 'wind_speed_mps', 'route_blocked'):
            setattr(msg, name, self.value(name))
        self.publisher.publish(msg)

    def on_vehicle(self, msg):
        key = (msg.job_id, msg.state, msg.busy)
        if key != self.last_vehicle:
            self.get_logger().info(f'VEHICLE job={msg.job_id} state={msg.state} busy={msg.busy}')
            self.last_vehicle = key

def main(args=None):
    rclpy.init(args=args)
    node = SensorStation()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        finish(node)
