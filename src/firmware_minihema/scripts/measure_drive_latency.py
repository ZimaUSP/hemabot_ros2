#!/usr/bin/env python3
"""Measure how long the robot takes to start moving after a velocity command.

Publishes forward velocity steps on a twist_mux input and timestamps, for each step:

  1. publish   - the command is published on the input topic
  2. mux       - twist_mux forwards it to the diff_drive_controller
  3. wheel     - an encoder reports motion (a wheel position in /joint_states moves by one pulse)

publish -> mux covers DDS and twist_mux; mux -> wheel covers the ros2_control loop, the hardware
interface, the motor and one encoder pulse (up to ~0.1 s at the default speed: 12 pulses per turn).
Discovery is excluded: the script waits until twist_mux and joint_states are connected first.

SAFETY: run it with the robot suspended, wheels off the ground. The robot drives forward.

    ros2 run firmware_minihema measure_drive_latency.py
    ros2 run firmware_minihema measure_drive_latency.py --topic /cmd_vel --speed 0.1 --trials 10
"""

import argparse
import math
import statistics
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.utilities import remove_ros_args
from sensor_msgs.msg import JointState

# Below this, publish -> mux is explained by message passing
MUX_LATENCY_WARN_S = 0.1
# Healthy mux -> wheel time, besides the wait for the first encoder pulse: one 20 Hz control cycle,
# motor spin-up and one /joint_states period, with margin
CONTROL_LATENCY_BASE_S = 0.25
ENCODER_TICKS_PER_REV = 12


@dataclass
class Trial:
    published_at: float
    mux_at: Optional[float] = None
    wheel_at: Optional[float] = None
    baseline: Dict[str, float] = field(default_factory=dict)

    @property
    def mux_latency(self) -> Optional[float]:
        return None if self.mux_at is None else self.mux_at - self.published_at

    @property
    def wheel_latency(self) -> Optional[float]:
        return None if self.wheel_at is None else self.wheel_at - self.published_at


class DriveLatencyProbe(Node):
    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__("drive_latency_probe")
        self._args = args
        self._publisher = self.create_publisher(Twist, args.topic, 10)
        self.create_subscription(Twist, args.mux_topic, self._on_mux_output, 10)
        self.create_subscription(JointState, "/joint_states", self._on_joint_states, 10)

        self._positions: Dict[str, float] = {}
        self._driving = False
        self.trials: List[Trial] = []

    # -- Subscriptions ---------------------------------------------------------------------

    def _on_mux_output(self, msg: Twist) -> None:
        trial = self._current_trial()
        if trial is not None and trial.mux_at is None and msg.linear.x > 0.0:
            trial.mux_at = time.monotonic()

    def _on_joint_states(self, msg: JointState) -> None:
        now = time.monotonic()
        self._positions = {
            name: position
            for name, position in zip(msg.name, msg.position)
            if name in self._args.joints
        }
        trial = self._current_trial()
        if trial is None or trial.wheel_at is not None:
            return
        for name, position in self._positions.items():
            if name in trial.baseline and abs(position - trial.baseline[name]) >= self._args.motion_threshold:
                trial.wheel_at = now
                return

    def _current_trial(self) -> Optional[Trial]:
        return self.trials[-1] if self._driving and self.trials else None

    # -- Driving -----------------------------------------------------------------------------

    def wait_for_connections(self, timeout_s: float) -> bool:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if self._publisher.get_subscription_count() > 0 and self._positions:
                return True
            rclpy.spin_once(self, timeout_sec=0.1)
        return False

    def run_trial(self) -> Trial:
        self._publish_for(0.0, self._args.rest_time)

        trial = Trial(published_at=0.0, baseline=dict(self._positions))
        self.trials.append(trial)
        self._driving = True
        trial.published_at = time.monotonic()
        self._publish_for(self._args.speed, self._args.drive_time)
        self._driving = False
        return trial

    def stop(self) -> None:
        self._publish_for(0.0, 0.5)

    def _publish_for(self, linear_x: float, duration_s: float) -> None:
        message = Twist()
        message.linear.x = float(linear_x)
        period = 1.0 / self._args.rate
        end = time.monotonic() + duration_s
        next_publish = time.monotonic()
        while time.monotonic() < end:
            if time.monotonic() >= next_publish:
                self._publisher.publish(message)
                next_publish += period
            rclpy.spin_once(self, timeout_sec=0.005)


def format_seconds(value: Optional[float]) -> str:
    return "   --- " if value is None else f"{value * 1e3:6.0f} ms"


def summarize(name: str, values: List[float]) -> str:
    if not values:
        return f"{name}: no data"
    return (
        f"{name}: min {min(values) * 1e3:.0f} ms | median {statistics.median(values) * 1e3:.0f} ms"
        f" | max {max(values) * 1e3:.0f} ms"
    )


def expected_control_latency(speed: float, wheel_radius: float) -> float:
    """Healthy upper bound for mux -> wheel: base latency plus the time of one encoder pulse."""
    wheel_speed = speed / wheel_radius
    return CONTROL_LATENCY_BASE_S + (2.0 * math.pi / ENCODER_TICKS_PER_REV) / wheel_speed


def report(trials: List[Trial], control_latency_warn_s: float) -> None:
    print("\n trial |   publish->mux |  publish->wheel")
    for index, trial in enumerate(trials, start=1):
        print(f" {index:5d} | {format_seconds(trial.mux_latency):>14} | {format_seconds(trial.wheel_latency):>15}")

    mux = [t.mux_latency for t in trials if t.mux_latency is not None]
    wheel = [t.wheel_latency for t in trials if t.wheel_latency is not None]
    control = [t.wheel_at - t.mux_at for t in trials if t.wheel_at is not None and t.mux_at is not None]

    print()
    print(summarize("publish -> mux  ", mux))
    print(summarize("mux -> wheel    ", control))
    print(summarize("publish -> wheel", wheel))
    print()

    findings = []
    if len(mux) < len(trials):
        findings.append("twist_mux did not forward some commands: is another higher-priority input active "
                        "(joystick, web UI), or is the --topic wrong?")
    if len(wheel) < len(trials):
        findings.append("Some steps produced no encoder motion: check the motor power supply, the encoder "
                        "wiring and the 'Control loop stalled' warnings of ros2_control_node.")
    if mux and max(mux) > MUX_LATENCY_WARN_S:
        findings.append("Slow publish -> mux: the delay is upstream of ros2_control (DDS, twist_mux, CPU load).")
    if control and max(control) > control_latency_warn_s:
        findings.append(f"Slow mux -> wheel (expected under {control_latency_warn_s * 1e3:.0f} ms at this "
                        "speed): the delay is in the ros2_control loop or the motors. Look for 'Control loop "
                        "stalled' warnings in the ros2_control_node output and check CPU load (htop).")

    for finding in findings:
        print(f"* {finding}")
    if not findings:
        print("All stages within the expected latency.")


def positive_float(text: str) -> float:
    value = float(text)
    if not value > 0.0:
        raise argparse.ArgumentTypeError(f"must be positive, got {text}")
    return value


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", default="/cmd_vel_joy", help="twist_mux input to publish on")
    parser.add_argument("--mux-topic", default="/diff_controller/cmd_vel_unstamped", help="twist_mux output")
    parser.add_argument("--speed", type=positive_float, default=0.2, help="forward speed of each step, m/s")
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--drive-time", type=float, default=1.5, help="duration of each step, s")
    parser.add_argument("--rest-time", type=float, default=1.5, help="pause before each step, s")
    parser.add_argument("--rate", type=positive_float, default=20.0, help="publish rate, Hz")
    parser.add_argument("--joints", nargs="+", default=["left_wheel_joint", "right_wheel_joint"])
    parser.add_argument("--wheel-radius", type=positive_float, default=0.040, help="m, as in controllers.yaml")
    parser.add_argument("--motion-threshold", type=float, default=math.pi / 12,
                        help="wheel rotation that counts as motion, rad (default: half an encoder pulse)")
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args(remove_ros_args(sys.argv)[1:])
    rclpy.init()
    probe = DriveLatencyProbe(args)
    try:
        print(f"Waiting for twist_mux on {args.topic} and for /joint_states ...")
        if not probe.wait_for_connections(timeout_s=15.0):
            print("Timed out: is minihema_launch running?", file=sys.stderr)
            return 1

        print(f"Driving {args.trials} forward steps at {args.speed} m/s. Keep the wheels off the ground!")
        for index in range(args.trials):
            trial = probe.run_trial()
            print(f"  step {index + 1}: mux {format_seconds(trial.mux_latency)}, "
                  f"wheel {format_seconds(trial.wheel_latency)}")
        probe.stop()
        report(probe.trials, expected_control_latency(args.speed, args.wheel_radius))
        return 0
    except KeyboardInterrupt:
        return 130
    finally:
        try:
            probe.stop()
        except Exception:  # the context may already be shutting down
            pass
        probe.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
