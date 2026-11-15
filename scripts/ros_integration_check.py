"""Ubuntu/Humble only. Starts four local ROS processes in isolated domain 91.

Requires a built/sourced workspace. This is separate from four-PC acceptance.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import time

os.environ['ROS_DOMAIN_ID'] = '91'
os.environ['ROS_LOCALHOST_ONLY'] = '1'
os.environ['RMW_IMPLEMENTATION'] = 'rmw_fastrtps_cpp'
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.parameter import Parameter
from rcl_interfaces.srv import SetParametersAtomically
from std_srvs.srv import Trigger
from smartyard_interfaces.msg import YardSensor, VehicleState
from smartyard_interfaces.srv import CheckTransport
from smartyard_interfaces.action import TransportBlock
from smartyard_lab.common import SENSOR_QOS, STATE_QOS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'validation/ros_run'
OUT.mkdir(parents=True, exist_ok=True)
processes, files, passed = {}, [], []
node = None


def spin_until(predicate, timeout=10.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return
        rclpy.spin_once(node, timeout_sec=0.05)
    raise TimeoutError('condition not reached')


def result(future, timeout=10.0):
    spin_until(future.done, timeout)
    return future.result()


def settle(seconds=1.0):
    """Allow independent telemetry subscriptions to observe restored defaults."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.05)


def call(kind, name, request):
    client = node.create_client(kind, name)
    try:
        if not client.wait_for_service(timeout_sec=10.0):
            raise TimeoutError(name)
        return result(client.call_async(request))
    finally:
        node.destroy_client(client)


def setp(target, name, value, success=True):
    request = SetParametersAtomically.Request()
    request.parameters = [Parameter(name, value=value).to_parameter_msg()]
    reply = call(SetParametersAtomically, '/yard01/' + target + '/set_parameters_atomically', request)
    assert reply.result.successful == success, reply.result.reason


def goal(job):
    request = TransportBlock.Goal()
    request.job_id, request.block_id = job, 'BLOCK_001'
    request.source_zone, request.target_zone = 'A', 'B'
    return result(action.send_goal_async(request))


def stop_process(name):
    proc = processes[name]
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGINT)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()


def mark(name):
    passed.append(name)
    print('PASS ' + name, flush=True)


try:
    for name in ['sensor_station', 'transporter', 'dispatch_checker', 'control_center']:
        stream = (OUT / (name + '.log')).open('w', encoding='utf-8')
        files.append(stream)
        processes[name] = subprocess.Popen(
            ['ros2', 'run', 'smartyard_lab', name, '--ros-args', '-r', '__ns:=/yard01'],
            stdout=stream, stderr=subprocess.STDOUT, env=os.environ.copy(), start_new_session=True)
    rclpy.init(args=[])
    node = Node('integration_probe')
    observations = {'sensor': None, 'vehicle': None}
    sensor_sub = node.create_subscription(YardSensor, '/yard01/sensor_state',
        lambda x: observations.update(sensor=x), SENSOR_QOS)
    vehicle_sub = node.create_subscription(VehicleState, '/yard01/vehicle_state',
        lambda x: observations.update(vehicle=x), STATE_QOS)
    spin_until(lambda: observations['sensor'] is not None and observations['vehicle'] is not None, 20)
    mark('topic telemetry received')
    check = CheckTransport.Request()
    check.job_id, check.block_id = 'TEST_CHECK', 'BLOCK_001'
    check.source_zone, check.target_zone = 'A', 'B'
    spin_until(lambda: call(CheckTransport, '/yard01/check_transport', check).allowed, 15)
    mark('service allowed')
    setp('sensor_station', 'wind_speed_mps', 12.0)
    spin_until(lambda: observations['sensor'].wind_speed_mps == 12.0)
    spin_until(lambda: call(CheckTransport, '/yard01/check_transport', check).reason == 'HIGH_WIND')
    mark('remote parameter causes service denial')
    setp('sensor_station', 'wind_speed_mps', 6.0)
    spin_until(lambda: observations['sensor'].wind_speed_mps == 6.0)
    # Let all independent subscriptions observe the restored state.
    spin_until(lambda: call(CheckTransport, '/yard01/check_transport', check).allowed)
    settle()
    setp('transporter', 'travel_speed_mps', -1.0, success=False)
    mark('invalid parameter rejected')
    action = ActionClient(node, TransportBlock, '/yard01/transport_block')
    assert action.wait_for_server(timeout_sec=10.0)
    # End-to-end controller path (service -> action), maximum valid speed.
    setp('transporter', 'travel_speed_mps', 2.0)
    setp('control_center', 'job_id', 'TEST_CONTROLLER')
    assert call(Trigger, '/yard01/start_job', Trigger.Request()).success
    spin_until(lambda: observations['vehicle'].job_id == 'TEST_CONTROLLER' and observations['vehicle'].busy)
    spin_until(lambda: observations['vehicle'].state == 'SUCCEEDED' and not observations['vehicle'].busy, 25)
    mark('controller service-action chain succeeds')
    # Check controller has consumed the result before the next case.
    spin_until(lambda: call(CheckTransport, '/yard01/check_transport', check).allowed)
    settle()
    handle = goal('TEST_CANCEL')
    assert handle.accepted
    duplicate = goal('TEST_BUSY')
    assert not duplicate.accepted
    assert result(handle.cancel_goal_async()).goals_canceling
    wrapped = result(handle.get_result_async())
    assert wrapped.status == 5 and wrapped.result.reason == 'OPERATOR_CANCEL'
    mark('busy goal rejected and cancellation works')
    assert not goal('TEST_CANCEL').accepted
    mark('duplicate job ID rejected')
    handle = goal('TEST_OBSTACLE')
    assert handle.accepted
    setp('sensor_station', 'route_blocked', True)
    wrapped = result(handle.get_result_async())
    assert wrapped.status == 6 and wrapped.result.reason == 'ROUTE_BLOCKED'
    mark('obstacle aborts action')
    setp('sensor_station', 'route_blocked', False)
    spin_until(lambda: not observations['sensor'].route_blocked)
    spin_until(lambda: call(CheckTransport, '/yard01/check_transport', check).allowed)
    settle()
    handle = goal('TEST_STALE')
    assert handle.accepted
    stop_process('sensor_station')
    wrapped = result(handle.get_result_async(), 8)
    assert wrapped.status == 6 and wrapped.result.reason == 'SENSOR_STALE'
    mark('sensor loss aborts action')
    status = 'PASS'
except Exception as exc:
    status = 'FAIL'
    print(f'FAIL {type(exc).__name__}: {exc}', flush=True)
    raise
finally:
    for name in processes:
        stop_process(name)
    for stream in files:
        stream.close()
    if node:
        node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()
    (OUT / 'result.json').write_text(json.dumps(
        {'status': locals().get('status', 'FAIL'), 'passed': passed,
         'scope': 'four local processes, localhost, domain 91; not WSL multi-PC networking'},
        ensure_ascii=False, indent=2), encoding='utf-8')
