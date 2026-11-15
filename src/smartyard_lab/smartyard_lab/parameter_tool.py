"""Run on any PC. Uses standard parameter services, with read-back."""
import argparse
import json
import os
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rcl_interfaces.srv import GetParameters, SetParametersAtomically


def wait(node, client, request, timeout=5.0):
    if not client.wait_for_service(timeout_sec=timeout):
        raise RuntimeError('parameter service not found; check domain, node name and network')
    future = client.call_async(request)
    rclpy.spin_until_future_complete(node, future, timeout_sec=timeout)
    if not future.done():
        raise RuntimeError('parameter response timeout; use get to verify actual target value')
    return future.result()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['get', 'set'])
    parser.add_argument('node', help='absolute ROS node name')
    parser.add_argument('name')
    parser.add_argument('value', nargs='?', help='JSON scalar, e.g. 0.5 or true or "text"')
    args = parser.parse_args()
    if not args.node.startswith('/'):
        parser.error('node must be absolute, for example /yard01/transporter')
    if args.operation == 'set' and args.value is None:
        parser.error('set requires a JSON value')
    rclpy.init(args=[])
    node = Node(f'parameter_tool_{os.getpid()}')
    code = 0
    try:
        target = args.node.rstrip('/')
        if args.operation == 'set':
            value = json.loads(args.value)
            if type(value) not in (bool, int, float, str):
                raise ValueError('this teaching tool accepts scalar values only')
            request = SetParametersAtomically.Request()
            request.parameters = [Parameter(args.name, value=value).to_parameter_msg()]
            client = node.create_client(SetParametersAtomically, target + '/set_parameters_atomically')
            response = wait(node, client, request)
            print(f'successful={response.result.successful} reason={response.result.reason}')
            if not response.result.successful:
                code = 2
        request = GetParameters.Request()
        request.names = [args.name]
        client = node.create_client(GetParameters, target + '/get_parameters')
        response = wait(node, client, request)
        value = response.values[0]
        fields = {1: 'bool_value', 2: 'integer_value', 3: 'double_value', 4: 'string_value'}
        actual = getattr(value, fields[value.type]) if value.type in fields else None
        print(f'{target}/{args.name} = {actual!r} (type={value.type})')
    except Exception as exc:
        print(f'ERROR: {exc}')
        code = 1
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    raise SystemExit(code)
