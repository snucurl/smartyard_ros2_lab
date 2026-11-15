"""PC 4: single active goal, feedback, cancellation and local interlocks."""
import threading
import time
import rclpy
from rclpy.action import ActionServer, GoalResponse, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from smartyard_interfaces.action import TransportBlock
from smartyard_interfaces.msg import YardSensor, VehicleState
from smartyard_lab.common import ConfigNode, SENSOR_QOS, STATE_QOS, age, finish
from smartyard_lab.core import check_transport, advance


class Transporter(ConfigNode):
    def __init__(self):
        super().__init__('transporter')
        self.setting('travel_speed_mps', 1.0, 0.2, 2.0)
        self.setting('sensor_timeout_sec', 3.0, 0.5, 30.0)
        self.setting('max_load_t', 50.0, 0.1, 200.0)
        self.setting('max_wind_mps', 10.0, 0.0, 60.0)
        self.lock = threading.RLock()
        self.stopping = threading.Event()
        self.sensor = self.sensor_received = None
        self.busy = False
        self.job_id = ''
        self.state = 'IDLE'
        self.moved = 0.0
        self.seen_jobs = set()
        self.action_group = ReentrantCallbackGroup()
        self.sensor_sub = self.create_subscription(
            YardSensor, 'sensor_state', self.on_sensor, SENSOR_QOS)
        self.publisher = self.create_publisher(VehicleState, 'vehicle_state', STATE_QOS)
        self.timer = self.create_timer(0.2, self.publish_state)
        self.server = ActionServer(
            self, TransportBlock, 'transport_block', self.execute,
            goal_callback=self.on_goal, cancel_callback=self.on_cancel,
            callback_group=self.action_group)
        self.get_logger().info('READY transport_block; one active goal maximum')

    def on_sensor(self, msg):
        with self.lock:
            self.sensor, self.sensor_received = msg, time.monotonic()

    def eligibility(self, request):
        return check_transport(
            request, self.sensor, age(self.sensor_received),
            self.value('sensor_timeout_sec'), self.value('max_load_t'),
            self.value('max_wind_mps'))

    def on_goal(self, request):
        with self.lock:
            allowed, reason, _ = self.eligibility(request)
            if self.busy:
                allowed, reason = False, 'VEHICLE_BUSY'
            elif request.job_id in self.seen_jobs:
                allowed, reason = False, 'DUPLICATE_JOB_ID'
            if not allowed:
                self.get_logger().warning(f'REJECT {request.job_id}: {reason}')
                return GoalResponse.REJECT
            # Reserve before execute is scheduled, so simultaneous goals cannot pass.
            self.busy = True
            self.job_id = request.job_id
            self.state = 'ACCEPTED'
            self.moved = 0.0
            self.seen_jobs.add(request.job_id)
            return GoalResponse.ACCEPT

    def on_cancel(self, _goal_handle):
        self.get_logger().info('CANCEL requested')
        return CancelResponse.ACCEPT

    def publish_state(self):
        msg = VehicleState()
        msg.stamp = self.get_clock().now().to_msg()
        with self.lock:
            msg.job_id, msg.state, msg.busy = self.job_id, self.state, self.busy
            msg.moved_m = self.moved
            msg.speed_mps = self.value('travel_speed_mps') if self.state == 'RUNNING' else 0.0
        self.publisher.publish(msg)

    def execute(self, handle):
        start = previous = time.monotonic()
        last_feedback = 0.0
        result = TransportBlock.Result()
        terminal, reason = 'ABORTED', 'SHUTDOWN'
        with self.lock:
            _, _, total = self.eligibility(handle.request)
            self.state = 'RUNNING'
        try:
            while rclpy.ok() and not self.stopping.is_set():
                now = time.monotonic()
                if handle.is_cancel_requested:
                    terminal, reason = 'CANCELED', 'OPERATOR_CANCEL'
                    break
                with self.lock:
                    allowed, reason, _ = self.eligibility(handle.request)
                    if not allowed:
                        terminal = 'ABORTED'
                        break
                    speed = self.value('travel_speed_mps')
                    self.moved = advance(self.moved, speed, now - previous, total)
                    moved = self.moved
                previous = now
                if now - last_feedback >= 0.5:
                    feedback = TransportBlock.Feedback()
                    feedback.progress_percent = 100.0 * moved / total
                    feedback.moved_m, feedback.speed_mps = moved, speed
                    handle.publish_feedback(feedback)
                    last_feedback = now
                if moved >= total:
                    terminal, reason = 'SUCCEEDED', 'COMPLETED'
                    break
                self.stopping.wait(0.05)
            result.success = terminal == 'SUCCEEDED'
            result.reason = reason
            result.elapsed_sec = time.monotonic() - start
            with self.lock:
                result.moved_m = self.moved
            result.final_zone = handle.request.target_zone if result.success else 'IN_TRANSIT'
            if terminal == 'SUCCEEDED':
                handle.succeed()
            elif terminal == 'CANCELED':
                handle.canceled()
            else:
                handle.abort()
        except Exception as exc:
            terminal = 'ABORTED'
            result.success, result.reason = False, f'EXECUTION_ERROR: {exc}'
            result.elapsed_sec = time.monotonic() - start
            result.final_zone = 'IN_TRANSIT'
            with self.lock:
                result.moved_m = self.moved
            if handle.is_active:
                handle.abort()
            self.get_logger().error(result.reason)
        finally:
            with self.lock:
                self.state, self.busy = terminal, False
            self.get_logger().info(
                f'RESULT {handle.request.job_id}: {terminal} {result.reason} '
                f'distance={result.moved_m:.2f}m time={result.elapsed_sec:.2f}s')
        return result


def main(args=None):
    rclpy.init(args=args)
    node = Transporter()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.stopping.set()
        finish(node, executor)
