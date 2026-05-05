"""Servo2040 servo output using one shared Pimoroni ServoCluster."""

import time
from math import cos, pi
from servo import ServoCluster


ANGLE_DEADBAND = 0.6
SERVO_MIN_US = 500
SERVO_MAX_US = 2500

_SHARED_CLUSTER = None
_SHARED_PIN_TO_INDEX = {}
_BATCH_DEPTH = 0
_BATCH_PULSES = []


def clamp_angle(angle_deg):
    if angle_deg < 0:
        return 0
    if angle_deg > 180:
        return 180
    return angle_deg


def angle_to_pulse_us(angle_deg):
    return SERVO_MIN_US + (clamp_angle(angle_deg) / 180) * (SERVO_MAX_US - SERVO_MIN_US)


def configure_shared_cluster(pin_groups):
    """Create one ServoCluster for every physical pin used by the robot."""
    global _SHARED_CLUSTER, _SHARED_PIN_TO_INDEX

    pins = []
    for group in pin_groups:
        if group is None:
            continue
        for pin in group:
            if pin not in pins:
                pins.append(pin)

    _SHARED_PIN_TO_INDEX = {pin: idx for idx, pin in enumerate(pins)}
    _SHARED_CLUSTER = ServoCluster(pio=0, sm=0, pins=pins) if pins else None
    print("ServoCluster connected pins", pins)


def begin_batch():
    global _BATCH_DEPTH
    _BATCH_DEPTH += 1


def end_batch():
    global _BATCH_DEPTH, _BATCH_PULSES

    if _BATCH_DEPTH > 0:
        _BATCH_DEPTH -= 1
    if _BATCH_DEPTH != 0:
        return

    pending = _BATCH_PULSES
    _BATCH_PULSES = []
    if _SHARED_CLUSTER is None:
        return
    # Flush by joint index instead of by leg. This avoids visibly completing
    # one whole leg before the next leg starts when pulse writes are slow.
    for joint_idx in range(3):
        for pending_joint_idx, servo_index, pulse_us in pending:
            if pending_joint_idx == joint_idx:
                _SHARED_CLUSTER.pulse(servo_index, pulse_us)
    for pending_joint_idx, servo_index, pulse_us in pending:
        if pending_joint_idx >= 3:
            _SHARED_CLUSTER.pulse(servo_index, pulse_us)


def write_pulse(servo_index, pulse_us, joint_idx=0):
    if _BATCH_DEPTH > 0:
        _BATCH_PULSES.append((joint_idx, servo_index, pulse_us))
        return
    _SHARED_CLUSTER.pulse(servo_index, pulse_us)


class servo_movement:
    def __init__(self, pin_list):
        self.pin_list = list(pin_list)
        self.servo_indexes = [self._index_for_pin(pin) for pin in self.pin_list]
        self.last_angles = [None for _ in self.pin_list]
        self.angle_deadband = ANGLE_DEADBAND

    def _index_for_pin(self, pin):
        if _SHARED_CLUSTER is None:
            configure_shared_cluster([self.pin_list])
        if pin not in _SHARED_PIN_TO_INDEX:
            raise RuntimeError("Pin {} was not included in ServoCluster setup".format(pin))
        return _SHARED_PIN_TO_INDEX[pin]

    def turn_angles(self, angles):
        for idx, angle in enumerate(angles):
            if idx >= len(self.servo_indexes):
                break
            last = self.last_angles[idx]
            if last is not None and abs(angle - last) < self.angle_deadband:
                continue
            self.last_angles[idx] = angle
            write_pulse(self.servo_indexes[idx], angle_to_pulse_us(angle), idx)

    def turn_angles_eased(self, target_angles, pre_angles, duration=0.2, steps=200):
        start_angles = list(pre_angles)

        for i in range(steps + 1):
            t = i / steps
            e = -(cos(pi * t) - 1) / 2
            new_angles = [
                sa if sa == ta else sa + (ta - sa) * e
                for sa, ta in zip(start_angles, target_angles)
            ]
            self.turn_angles(new_angles)
            time.sleep(duration / steps)
