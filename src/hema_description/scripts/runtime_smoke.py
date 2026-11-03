#!/usr/bin/env python3
"""Bounded smoke test against an ALREADY RUNNING Hema simulation in velocity mode.

Publishes only /wheel_controller/commands, never starts/stops external processes.
The test checks exported states; passive effort NaNs mean unavailable interfaces.
Run after sourcing ROS and launching simulation.launch.py command_interface:=velocity.
"""
import argparse
import json
import math
from pathlib import Path
import statistics
import time


WHEELS = ['left_wheel_joint', 'right_wheel_joint']
EXPECTED = WHEELS + [
    f'caster_{corner}_{kind}_joint'
    for corner in ('front_left', 'front_right', 'rear_left', 'rear_right')
    for kind in ('swivel', 'wheel')
]


def run(args):
    import rclpy
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import JointState, LaserScan
    from rosgraph_msgs.msg import Clock
    from std_msgs.msg import Float64MultiArray
    from controller_manager_msgs.srv import ListControllers

    started = time.monotonic()
    deadline = started + args.timeout
    report = {
        'passed': False, 'command_units': 'rad/s',
        'expected_movable_joints': EXPECTED,
        'checks': {}, 'errors': [], 'controllers': {},
        'optional_entity_state': {'status': 'skipped', 'reason': 'service unavailable'},
    }
    latest = {}
    received_names = set()
    bad_states = set()
    samples = []
    clock_values = []
    scans = []
    passive_unavailable_effort = set()
    state_messages = 0
    node = None
    publisher = None

    def on_states(msg):
        nonlocal state_messages
        state_messages += 1
        now = time.monotonic()
        received_names.update(msg.name)
        row = {}
        for index, name in enumerate(msg.name):
            for field in ('position', 'velocity', 'effort'):
                values = getattr(msg, field)
                value = float(values[index]) if index < len(values) else float('nan')
                if field == 'effort' and name not in WHEELS and math.isnan(value):
                    passive_unavailable_effort.add(name)
                    continue
                if not math.isfinite(value):
                    bad_states.add(f'{name}/{field}')
                row[f'{name}/{field}'] = value
        latest.clear()
        latest.update(row)
        samples.append((now, row))

    def on_clock(msg):
        clock_values.append(msg.clock.sec + msg.clock.nanosec * 1e-9)

    def on_scan(msg):
        scans.append({
            'frame_id': msg.header.frame_id,
            'angle_min': float(msg.angle_min),
            'angle_max': float(msg.angle_max),
            'range_min': float(msg.range_min),
            'range_max': float(msg.range_max),
            'ranges': [float(value) for value in msg.ranges],
        })

    def pump(seconds, predicate=None):
        until = min(time.monotonic() + seconds, deadline)
        while rclpy.ok() and time.monotonic() < until:
            if predicate is not None and predicate():
                return True
            rclpy.spin_once(node, timeout_sec=min(0.03, max(0.0, until-time.monotonic())))
        return bool(predicate()) if predicate is not None else None

    def command_phase(speed, duration):
        begin = time.monotonic()
        end = min(begin + duration, deadline)
        next_publish = 0.0
        while rclpy.ok() and time.monotonic() < end:
            if time.monotonic() >= next_publish:
                publisher.publish(Float64MultiArray(data=[speed, speed]))
                next_publish = time.monotonic() + 0.05
            rclpy.spin_once(node, timeout_sec=0.02)
        tail = [row for stamp, row in samples if stamp >= begin + duration * 0.6]
        means = {}
        for wheel in WHEELS:
            values = [row.get(f'{wheel}/velocity', float('nan')) for row in tail]
            finite = [v for v in values if math.isfinite(v)]
            means[wheel] = statistics.mean(finite) if finite else None
        return means

    try:
        rclpy.init(args=[])
        node = rclpy.create_node('hema_runtime_smoke')
        node.create_subscription(JointState, '/joint_states', on_states, qos_profile_sensor_data)
        node.create_subscription(Clock, '/clock', on_clock, qos_profile_sensor_data)
        node.create_subscription(LaserScan, '/scan', on_scan, qos_profile_sensor_data)
        publisher = node.create_publisher(Float64MultiArray, '/wheel_controller/commands', 10)
        manager = node.create_client(ListControllers, '/controller_manager/list_controllers')
        ready = pump(min(15.0, args.timeout - 8.0), manager.service_is_ready)
        if not ready:
            raise RuntimeError('controller_manager/list_controllers unavailable within timeout')
        # Controllers may still be activating after manager discovery.
        controllers_ready = False
        activation_deadline = min(time.monotonic() + 10.0, deadline - 5.0)
        while time.monotonic() < activation_deadline and not controllers_ready:
            future = manager.call_async(ListControllers.Request())
            if not pump(min(2.0, max(0.0, activation_deadline-time.monotonic())), future.done):
                raise RuntimeError('list_controllers service did not respond')
            result = future.result()
            report['controllers'] = {c.name: {'state': c.state, 'type': c.type} for c in result.controller}
            controllers_ready = all(report['controllers'].get(name, {}).get('state') == 'active'
                                    for name in ('joint_state_broadcaster', 'wheel_controller'))
            if not controllers_ready:
                pump(0.2)
        report['checks']['controllers_active'] = controllers_ready
        wheel_type = report['controllers'].get('wheel_controller', {}).get('type', '')
        report['checks']['velocity_controller_type'] = wheel_type == 'velocity_controllers/JointGroupVelocityController'
        if not controllers_ready or not report['checks']['velocity_controller_type']:
            raise RuntimeError('Expected active joint_state_broadcaster and velocity wheel_controller')
        streams_ready = pump(4.0, lambda: set(EXPECTED) <= received_names and
                             len(clock_values) >= 2 and len(scans) >= 2 and
                             publisher.get_subscription_count() > 0)
        report['checks']['streams_and_command_subscriber'] = streams_ready
        if not streams_ready:
            raise RuntimeError('Missing joint states, /scan, simulation clock, or command subscriber')
        scan = scans[-1]
        scan_ranges = scan['ranges']
        report['lidar'] = {
            'frame_id': scan['frame_id'],
            'samples': len(scan_ranges),
            'angle_min': scan['angle_min'],
            'angle_max': scan['angle_max'],
            'field_of_view_degrees': math.degrees(scan['angle_max'] - scan['angle_min']),
            'range_min': scan['range_min'],
            'range_max': scan['range_max'],
            'messages': len(scans),
        }
        report['checks']['lidar_frame'] = scan['frame_id'] == 'lidar_link'
        report['checks']['lidar_samples'] = len(scan_ranges) == 361
        report['checks']['lidar_180_degrees'] = (
            abs(scan['angle_min'] + math.pi / 2) < 1e-5 and
            abs(scan['angle_max'] - math.pi / 2) < 1e-5)
        report['checks']['lidar_ranges_valid'] = bool(scan_ranges) and all(
            not math.isnan(value) and
            (math.isinf(value) or scan['range_min'] <= value <= scan['range_max'])
            for value in scan_ranges)
        report['checks']['lidar_not_blocked_by_body'] = not any(
            math.isfinite(value) and value <= scan['range_min'] + 0.02
            for value in scan_ranges)
        if deadline - time.monotonic() < 4.5:
            raise RuntimeError('Insufficient remaining timeout for movement and stop verification')

        # Let the newly spawned robot settle before commanding motion.
        command_phase(0.0, 0.5)
        moving = command_phase(2.0, 2.0)
        report['moving_mean_wheel_velocity'] = moving
        report['checks']['wheel_velocity_tracks_command'] = all(
            value is not None and abs(value - 2.0) <= 0.5 for value in moving.values())
        report['checks']['wheel_velocities_comparable'] = (
            all(value is not None for value in moving.values()) and
            abs(moving[WHEELS[0]] - moving[WHEELS[1]]) <= 0.5)
        stopped = command_phase(0.0, 1.0)
        report['stopped_mean_wheel_velocity'] = stopped
        report['checks']['wheels_stop'] = all(
            value is not None and abs(value) <= 0.3 for value in stopped.values())

        # Optional read-only pose check. No plugin is installed by this script.
        try:
            from gazebo_msgs.srv import GetEntityState
            for service_name in ('/get_entity_state', '/gazebo/get_entity_state'):
                client = node.create_client(GetEntityState, service_name)
                if not client.service_is_ready():
                    pump(0.15, client.service_is_ready)
                if not client.service_is_ready():
                    continue
                request = GetEntityState.Request()
                request.name = 'hema'
                request.reference_frame = 'world'
                future = client.call_async(request)
                if not pump(1.0, future.done):
                    report['optional_entity_state'] = {'status': 'skipped', 'reason': 'service timed out'}
                    break
                response = future.result()
                if not response.success:
                    report['optional_entity_state'] = {
                        'status': 'skipped',
                        'reason': getattr(response, 'status_message', 'entity state service returned success=false'),
                    }
                    break
                state = response.state
                xyz = [state.pose.position.x, state.pose.position.y, state.pose.position.z]
                quaternion = [state.pose.orientation.x, state.pose.orientation.y,
                              state.pose.orientation.z, state.pose.orientation.w]
                twist = [state.twist.linear.x, state.twist.linear.y, state.twist.linear.z,
                         state.twist.angular.x, state.twist.angular.y, state.twist.angular.z]
                finite = all(math.isfinite(v) for v in xyz + quaternion + twist)
                report['optional_entity_state'] = {
                    'status': 'checked', 'service': service_name,
                    'position': xyz, 'orientation_xyzw': quaternion, 'twist': twist,
                }
                report['checks']['optional_model_state_finite'] = finite
                break
        except ImportError:
            report['optional_entity_state'] = {'status': 'skipped', 'reason': 'gazebo_msgs unavailable'}
        report['checks']['expected_joints_present'] = set(EXPECTED) <= received_names
        report['checks']['exported_states_finite'] = not bad_states
        report['checks']['clock_advances'] = len(clock_values) > 1 and clock_values[-1] > clock_values[0]
        report['passed'] = all(report['checks'].values())
    except Exception as error:
        report['errors'].append(f'{type(error).__name__}: {error}')
    finally:
        if publisher is not None and rclpy.ok():
            # Always send a stop, including failure/interruption paths. This is not
            # an emergency-stop mechanism and cannot guarantee delivery after loss of DDS.
            try:
                for _ in range(3):
                    publisher.publish(Float64MultiArray(data=[0.0, 0.0]))
                    rclpy.spin_once(node, timeout_sec=0.02)
                report['stop_command_sent'] = True
            except Exception as error:
                report['stop_command_sent'] = False
                report['errors'].append(f'stop: {error}')
                report['passed'] = False
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        report.update({
            'elapsed_wall_seconds': time.monotonic() - started,
            'joint_state_messages': state_messages,
            'received_joint_names': sorted(received_names),
            'nonfinite_exported_interfaces': sorted(bad_states),
            'passive_effort_unavailable': sorted(passive_unavailable_effort),
            'clock_start': clock_values[0] if clock_values else None,
            'clock_end': clock_values[-1] if clock_values else None,
            'scan_messages': len(scans),
        })
        if report['errors']:
            report['passed'] = False
    return report


def json_safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=float, default=35.0,
                        help='Overall wall-clock budget, 10 through 38 seconds (default 35).')
    args = parser.parse_args()
    if not 10.0 <= args.timeout <= 38.0:
        parser.error('--timeout must be between 10 and 38 seconds')
    try:
        report = run(args)
    except (Exception, KeyboardInterrupt) as error:
        report = {'passed': False, 'errors': [f'{type(error).__name__}: {error}']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(json_safe(report), indent=2, allow_nan=False)
    args.output.write_text(payload + '\n', encoding='utf-8')
    print(payload)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
