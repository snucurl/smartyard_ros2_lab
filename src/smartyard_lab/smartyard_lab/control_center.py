"""PC 2: topic observer, async service/action clients and operator commands."""
import time
import rclpy
from rclpy.action import ActionClient
from std_srvs.srv import Trigger
from smartyard_interfaces.msg import YardSensor, VehicleState
from smartyard_interfaces.srv import CheckTransport
from smartyard_interfaces.action import TransportBlock
from smartyard_lab.common import ConfigNode, SENSOR_QOS, STATE_QOS, age, finish


class ControlCenter(ConfigNode):
    def __init__(self):
        super().__init__('control_center')
        for key, default in [('job_id', 'JOB_001'), ('block_id', 'BLOCK_001'),
                             ('source_zone', 'A'), ('target_zone', 'B')]:
            self.setting(key, default)
        self.setting('sensor_timeout_sec', 3.0, 0.5, 30.0)
        self.setting('request_timeout_sec', 5.0, 1.0, 30.0)
        self.setting('task_timeout_sec', 180.0, 10.0, 600.0)
        self.sensor = self.vehicle = None
        self.sensor_received = self.vehicle_received = None
        self.phase = 'IDLE'
        self.generation = 0
        self.handle = None
        self.cancel_on_accept = False
        self.cancel_sent = False
        self.deadline = 0.0
        self.last_monitor = 0.0
        self.sensor_sub = self.create_subscription(YardSensor, 'sensor_state', self.on_sensor, SENSOR_QOS)
        self.vehicle_sub = self.create_subscription(VehicleState, 'vehicle_state', self.on_vehicle, STATE_QOS)
        self.check_client = self.create_client(CheckTransport, 'check_transport')
        self.action_client = ActionClient(self, TransportBlock, 'transport_block')
        self.start_service = self.create_service(Trigger, 'start_job', self.start)
        self.cancel_service = self.create_service(Trigger, 'cancel_job', self.cancel)
        self.timer = self.create_timer(0.2, self.tick)
        self.get_logger().info('READY; call start_job to start one job; cancel_job to cancel')

    def on_sensor(self, msg):
        self.sensor, self.sensor_received = msg, time.monotonic()

    def on_vehicle(self, msg):
        self.vehicle, self.vehicle_received = msg, time.monotonic()

    def start(self, _request, response):
        timeout = self.value('sensor_timeout_sec')
        if self.phase != 'IDLE':
            response.success, response.message = False, f'CONTROLLER_BUSY: {self.phase}'
        elif age(self.sensor_received) > timeout or age(self.vehicle_received) > timeout:
            response.success, response.message = False, 'TELEMETRY_STALE'
        elif not self.check_client.service_is_ready() or not self.action_client.server_is_ready():
            response.success, response.message = False, 'SERVER_NOT_READY'
        else:
            self.generation += 1
            token = self.generation
            request = CheckTransport.Request()
            for key in ('job_id', 'block_id', 'source_zone', 'target_zone'):
                setattr(request, key, self.value(key))
            self.current_request = request  # Snapshot parameters for this job.
            self.phase = 'CHECKING'
            self.deadline = time.monotonic() + self.value('request_timeout_sec')
            future = self.check_client.call_async(request)
            future.add_done_callback(lambda f: self.checked(f, token))
            response.success, response.message = True, f'REQUEST_QUEUED {request.job_id}'
        return response

    def checked(self, future, token):
        if token != self.generation or self.phase != 'CHECKING':
            return
        try:
            response = future.result()
            if not response.allowed:
                self.get_logger().warning(f'DENIED: {response.reason}')
                self.phase = 'IDLE'
                return
            if age(self.sensor_received) > self.value('sensor_timeout_sec'):
                self.get_logger().warning('SENSOR_STALE before goal send')
                self.phase = 'IDLE'
                return
            goal = TransportBlock.Goal()
            for key in ('job_id', 'block_id', 'source_zone', 'target_zone'):
                setattr(goal, key, getattr(self.current_request, key))
            self.phase, self.cancel_on_accept, self.cancel_sent = 'SENDING', False, False
            self.deadline = time.monotonic() + self.value('request_timeout_sec')
            future = self.action_client.send_goal_async(goal, feedback_callback=self.feedback)
            future.add_done_callback(self.goal_response)
        except Exception as exc:
            self.phase = 'IDLE'
            self.get_logger().error(f'CHECK_ERROR: {exc}')

    def goal_response(self, future):
        try:
            self.handle = future.result()
            if not self.handle.accepted:
                self.phase, self.handle = 'IDLE', None
                self.get_logger().warning('GOAL_REJECTED; inspect PC 4 log for reason')
                return
            self.phase = 'RUNNING'
            self.deadline = time.monotonic() + self.value('task_timeout_sec')
            self.handle.get_result_async().add_done_callback(self.result)
            self.get_logger().info('GOAL_ACCEPTED')
            if self.cancel_on_accept:
                self.request_cancel()
        except Exception as exc:
            # A missing response does not prove that the server did not start.
            self.phase = 'UNKNOWN'
            self.get_logger().error(f'GOAL_OUTCOME_UNKNOWN: {exc}; inspect PC 4')

    def feedback(self, msg):
        data = msg.feedback
        self.get_logger().info(
            f'FEEDBACK {data.progress_percent:.1f}% moved={data.moved_m:.2f}m '
            f'speed={data.speed_mps:.2f}m/s')

    def result(self, future):
        try:
            wrapped = future.result()
            names = {4: 'SUCCEEDED', 5: 'CANCELED', 6: 'ABORTED'}
            data = wrapped.result
            self.get_logger().info(
                f'RESULT {names.get(wrapped.status, str(wrapped.status))}: '
                f'{data.reason} moved={data.moved_m:.2f}m elapsed={data.elapsed_sec:.2f}s')
            self.phase, self.handle = 'IDLE', None
        except Exception as exc:
            self.phase = 'UNKNOWN'
            self.get_logger().error(f'RESULT_UNKNOWN: {exc}; inspect PC 4')

    def request_cancel(self):
        if self.handle is None or self.cancel_sent:
            return
        self.cancel_sent = True
        self.phase = 'CANCELING'
        self.deadline = time.monotonic() + self.value('request_timeout_sec')
        self.handle.cancel_goal_async().add_done_callback(self.cancel_response)

    def cancel_response(self, future):
        try:
            count = len(future.result().goals_canceling)
            self.get_logger().info(f'CANCEL_RESPONSE goals_canceling={count}; wait for RESULT')
        except Exception as exc:
            self.get_logger().error(f'CANCEL_RESPONSE_ERROR {exc}')

    def cancel(self, _request, response):
        if self.phase == 'CHECKING':
            self.generation += 1
            self.phase = 'IDLE'
            response.success, response.message = True, 'CANCELED_BEFORE_GOAL'
        elif self.phase in ('SENDING', 'UNKNOWN') and self.handle is None:
            self.cancel_on_accept = True
            response.success, response.message = True, 'CANCEL_ON_ACCEPT_PENDING'
        elif self.handle is not None and self.phase in ('RUNNING', 'CANCELING', 'UNKNOWN'):
            self.request_cancel()
            response.success, response.message = True, 'CANCEL_REQUESTED; wait for RESULT'
        else:
            response.success, response.message = False, 'NO_ACTIVE_JOB'
        return response

    def tick(self):
        now = time.monotonic()
        if self.phase != 'IDLE' and now > self.deadline:
            if self.phase == 'CHECKING':
                self.generation += 1
                self.phase = 'IDLE'
                self.get_logger().warning('CHECK_TIMEOUT; no goal sent')
            elif self.phase == 'SENDING':
                self.phase, self.cancel_on_accept = 'UNKNOWN', True
                self.get_logger().error('GOAL_RESPONSE_TIMEOUT; late acceptance will be canceled')
            elif self.phase == 'RUNNING':
                self.get_logger().warning('TASK_TIMEOUT; requesting cancel')
                self.request_cancel()
            elif self.phase == 'CANCELING':
                self.phase = 'UNKNOWN'
                self.get_logger().error('CANCEL_RESULT_TIMEOUT; inspect PC 4; no new job allowed')
        if now - self.last_monitor >= 2.0:
            self.last_monitor = now
            self.get_logger().info(
                f'MONITOR phase={self.phase} sensor_age={age(self.sensor_received):.1f}s '
                f'vehicle_age={age(self.vehicle_received):.1f}s')


def main(args=None):
    rclpy.init(args=args)
    node = ControlCenter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        finish(node)
