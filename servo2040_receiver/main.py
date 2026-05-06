"""Servo 2040 MicroPython receiver + robot init."""

import sys
import time
import ujson
import uselect
from math import atan2, cos, degrees, pi, sqrt
import legs_IK
import tripot_gait
import servo_control

FAILSAFE_S = 0.7
FAILSAFE_HOLD_S = 0.25
FAILSAFE_DECAY_S = 1.10
CONTROL_HZ = 30
CONTROL_DT_MS = int(1000 / CONTROL_HZ)
ANGLE_PRINT_MS = 250
MAX_WALK_SPEED = 0.7
MAX_WALK_STRIDE = 170
INIT_START_STAGGER_S = 0.12
INIT_JOINT_STAGGER_S = 0.08
INIT_ANGLES = [0, 28, 115]
STAND_ANGLES = [0, 28, 115]
STAND_TRANSITION_S = 3.0
STAND_TRANSITION_STEPS = 150
DEMO_ON_BOOT = False
DEMO_REPEAT = False
LEG_CONFIGS = (
    # Use pins=None for legs that are not physically connected.
    ("legi", [0, 1, 2]),
    ("legj", [3,4,5]),
    # Add the remaining legs back one at a time while diagnosing init resets.
    # ("legk", [6,7,8]),
    # ("legl", [9,10,11]),
    # ("legm", [12,13,14]),
    # ("legn", [15,16,17]),
)

TURN_DEADBAND = 0.10
TURN_ACCEL_PER_TICK = 0.02
TURN_DECEL_PER_TICK = 0.07

last_cmd_ms = time.ticks_ms()
last_cmd = {
    "mode": "init",
    "vx": 0.0,
    "vy": 0.0,
    "turn": 0.0,
    "speed": 0.0,
    "height": 0.0,
    "ts": 0.0,
}


class HexapodRobot:
    """Robot setup copied from your current main.py config."""

    def __init__(self):
        self.tripot = tripot_gait.Tripot_gait()
        servo_control.configure_shared_cluster([pins for _, pins in LEG_CONFIGS])
        self.last_mode = "stop"
        self.last_stop_height = None
        self.smoothed_vx = 0.0
        self.smoothed_vy = 0.0
        self.walk_vector_alpha = 0.18
        self.smoothed_turn = 0.0
        self.last_angle_print_ms = time.ticks_ms()
        self.step_min = 20
        self.step_max = 48
        self.legs = [
            legs_IK.SpiderLeg(name, 43.8, 88, 166, pins)
            for name, pins in LEG_CONFIGS
        ]

    def hexapod_init(self):
        print("Init pose:", INIT_ANGLES)
        for leg in self.legs:
            print("Init leg:", leg.name)
            self._set_leg_angles_joint_by_joint(leg, INIT_ANGLES)
            if INIT_START_STAGGER_S > 0:
                time.sleep(INIT_START_STAGGER_S)
        for leg in self.legs:
            print(leg.name, "init angles:", leg.get_angles())
        self._reset_control_state()
        time.sleep(1)

    def _set_leg_angles_joint_by_joint(self, leg, angles):
        target_angles = leg.normalize_angles([
            angles[0] + legs_IK.SERVO_OFFSETS[0],
            angles[1] + legs_IK.SERVO_OFFSETS[1],
            angles[2] + legs_IK.SERVO_OFFSETS[2],
        ])

        current = leg.get_angles()
        for joint_idx in range(3):
            pin = leg.control.pin_list[joint_idx] if leg.control is not None else None
            print("Init joint:", joint_idx, "pin:", pin)
            current[joint_idx] = target_angles[joint_idx]
            leg.theta1, leg.theta2, leg.theta3 = current
            if leg.control is not None:
                leg.control.turn_angle(joint_idx, current[joint_idx])
            if INIT_JOINT_STAGGER_S > 0:
                time.sleep(INIT_JOINT_STAGGER_S)

    def _transition_all_legs(self, target_angles, duration_s, steps):
        if not self.legs:
            return

        start_by_leg = [leg.get_angles() for leg in self.legs]
        target_by_leg = [
            leg.normalize_angles([
                target_angles[0] + legs_IK.SERVO_OFFSETS[0],
                target_angles[1] + legs_IK.SERVO_OFFSETS[1],
                target_angles[2] + legs_IK.SERVO_OFFSETS[2],
            ])
            for leg in self.legs
        ]

        for i in range(steps + 1):
            t = i / steps
            eased = -(cos(pi * t) - 1) / 2
            servo_control.begin_batch()
            try:
                for leg_idx, leg in enumerate(self.legs):
                    current = [
                        start_by_leg[leg_idx][joint] + (target_by_leg[leg_idx][joint] - start_by_leg[leg_idx][joint]) * eased
                        for joint in range(3)
                    ]
                    leg.theta1, leg.theta2, leg.theta3 = current
                    if leg.control is not None:
                        leg.control.turn_angles(current)
            finally:
                servo_control.end_batch()
            time.sleep(duration_s / steps)

        for leg in self.legs:
            leg.forwardKinematics()

    def _reset_control_state(self):
        self.tripot.reset_walk_phase()
        self.tripot.reset_turn_phase()
        self.last_mode = "init"
        self.last_stop_height = -125
        self.smoothed_vx = 0.0
        self.smoothed_vy = 0.0
        self.smoothed_turn = 0.0

    def _set_pose(self, mode, target_angles, duration_s):
        if self.last_mode != mode:
            print("Pose:", mode, target_angles)
            self._transition_all_legs(target_angles, duration_s, STAND_TRANSITION_STEPS)
            self.tripot.reset_walk_phase()
            self.tripot.reset_turn_phase()
            self._reset_walk_input()
            self.smoothed_turn = 0.0
            self.last_stop_height = None
            self.last_mode = mode

    def _apply_same_ik_target(self, target):
        angles_by_leg = []
        for leg in self.legs:
            angles_by_leg.append((leg, leg.calculate_inverse_angles(target)))
        servo_control.begin_batch()
        try:
            for leg, angles in angles_by_leg:
                leg.set_angles(angles)
        finally:
            servo_control.end_batch()
        for leg, _ in angles_by_leg:
            leg.forwardKinematics()

    def _slew_turn(self, target_turn):
        """Smooth turn input to avoid reversal current spikes.

        - If requested direction flips, first decelerate to zero quickly.
        - Then accelerate toward the new direction more slowly.
        """
        current = self.smoothed_turn
        target = target_turn

        opposite = (current > 0 and target < 0) or (current < 0 and target > 0)
        if opposite:
            if current > 0:
                current = max(0.0, current - TURN_DECEL_PER_TICK)
            else:
                current = min(0.0, current + TURN_DECEL_PER_TICK)
        else:
            delta = target - current
            if delta > TURN_ACCEL_PER_TICK:
                delta = TURN_ACCEL_PER_TICK
            elif delta < -TURN_ACCEL_PER_TICK:
                delta = -TURN_ACCEL_PER_TICK
            current += delta

        if abs(current) < TURN_DEADBAND:
            current = 0.0
        self.smoothed_turn = max(-1.0, min(1.0, current))
        return self.smoothed_turn

    def _print_leg_angles(self):
        now_ms = time.ticks_ms()
        if time.ticks_diff(now_ms, self.last_angle_print_ms) < ANGLE_PRINT_MS:
            return
        self.last_angle_print_ms = now_ms
        for leg in self.legs:
            print(leg.name, "current angles:", leg.get_angles())

    def _stance_from_height(self, height):
        stance_z = -125 + (height * 45)
        xpos = 130 + (stance_z + 125) * (20 / 45)
        return stance_z, max(110, min(150, xpos))

    def _gait_step_for_speed(self, speed):
        step = round(self.step_max - (self.step_max - self.step_min) * speed)
        return max(self.step_min, min(self.step_max, int(step)))

    def _reset_walk_input(self):
        self.smoothed_vx = 0.0
        self.smoothed_vy = 0.0

    def _demo_hold_command(self, label, cmd, duration_ms):
        print("Demo:", label)
        end_ms = time.ticks_add(time.ticks_ms(), duration_ms)
        while time.ticks_diff(end_ms, time.ticks_ms()) > 0:
            self.apply_command(cmd)
            time.sleep_ms(CONTROL_DT_MS)

    def demo_movement(self):
        """Run a local straight-walk demo without web or serial commands."""
        print("Demo movement starting")
        self.apply_command({
            "mode": "stand",
            "vx": 0.0,
            "vy": 0.0,
            "turn": 0.0,
            "speed": 0.0,
            "height": 0.0,
            "ts": 0.0,
        })
        time.sleep_ms(500)

        self._demo_hold_command("walk forward", {
            "mode": "walk",
            "vx": 1.0,
            "vy": 0.0,
            "turn": 0.0,
            "speed": 0.7,
            "height": 0.0,
            "ts": 0.0,
        }, 8000)

        self.apply_command({
            "mode": "stand",
            "vx": 0.0,
            "vy": 0.0,
            "turn": 0.0,
            "speed": 0.0,
            "height": 0.0,
            "ts": 0.0,
        })
        print("Demo movement complete")

    def apply_command(self, cmd):
        """Live non-blocking gait control from web command packets."""
        mode = cmd.get("mode", "stop")
        vx = cmd.get("vx", 0.0)
        vy = cmd.get("vy", 0.0)
        turn = cmd.get("turn", 0.0)
        speed = cmd.get("speed", 0.0)
        height = cmd.get("height", 0.0)
        speed = max(0.0, min(1.0, speed))
        stance_z, xpos = self._stance_from_height(height)

        if mode == "init":
            self._set_pose("init", INIT_ANGLES, 1.0)
            return

        if mode == "stand":
            self._set_pose("stand", STAND_ANGLES, STAND_TRANSITION_S)
            return

        if mode == "stop":
            self.smoothed_turn = 0.0
            if self.last_mode != "stop":
                self._apply_same_ik_target([xpos, 0, stance_z])
                self.tripot.reset_walk_phase()
                self.tripot.reset_turn_phase()
                self.last_stop_height = stance_z
                self._reset_walk_input()
            elif self.last_stop_height is None or abs(stance_z - self.last_stop_height) > 0.5:
                self._apply_same_ik_target([xpos, 0, stance_z])
                self.last_stop_height = stance_z
            self.last_mode = "stop"
            return

        if mode == "turn":
            self.last_stop_height = None
            self._reset_walk_input()
            if self.last_mode != "turn":
                self.tripot.reset_turn_phase()

            turn_speed = speed
            gait_step = self._gait_step_for_speed(turn_speed)
            turn = max(-1.0, min(1.0, turn))
            turn_cmd = self._slew_turn(turn)
            turn_mag = abs(turn_cmd)

            turn_max_angle = 10 + 30 * turn_mag
            turn_A = 20 + int(20 * turn_speed)
            self.tripot.turn_step(
                self.legs,
                turn_ratio=turn_cmd,
                max_angle=turn_max_angle,
                T=80 + int(70 * turn_speed),
                body_height=stance_z,
                A=turn_A,
                step=gait_step,
                xpos=xpos,
            )
            self.last_mode = "turn"
            return

        if mode == "walk":
            self.smoothed_turn = 0.0
            self.last_stop_height = None
            walk_speed = min(speed, MAX_WALK_SPEED)
            gait_step = self._gait_step_for_speed(walk_speed)
            if self.last_mode != "walk":
                self.tripot.reset_walk_phase()
                self.smoothed_vx = vx
                self.smoothed_vy = vy

            self.smoothed_vx += (vx - self.smoothed_vx) * self.walk_vector_alpha
            self.smoothed_vy += (vy - self.smoothed_vy) * self.walk_vector_alpha
            mag = sqrt(self.smoothed_vx * self.smoothed_vx + self.smoothed_vy * self.smoothed_vy)
            if mag < 0.03:
                self.last_mode = "walk"
                return

            walk_angle = degrees(atan2(self.smoothed_vy, self.smoothed_vx))
            stride = max(40, int((80 + 130 * walk_speed) * min(1.0, mag)))
            stride = min(MAX_WALK_STRIDE, stride)
            walk_A = 15 + int(20 * walk_speed)
            self.tripot.walk_step(
                self.legs,
                angle=walk_angle,
                T=stride,
                body_height=stance_z,
                A=walk_A,
                step=gait_step,
                xpos=xpos,
            )
            # Printing during gait can overload Thonny/USB and make disconnects harder to diagnose.
            # self._print_leg_angles()
            self.last_mode = "walk"


robot = None


def clamp(value, lo, hi, default):
    try:
        x = float(value)
    except Exception:
        return default
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


def sanitize(payload):
    return {
        "mode": str(payload.get("mode", "stop")),
        "vx": clamp(payload.get("vx"), -1.0, 1.0, 0.0),
        "vy": clamp(payload.get("vy"), -1.0, 1.0, 0.0),
        "turn": clamp(payload.get("turn"), -1.0, 1.0, 0.0),
        "speed": clamp(payload.get("speed"), 0.0, 1.0, 0.0),
        "height": clamp(payload.get("height"), -1.0, 1.0, 0.0),
        "ts": clamp(payload.get("ts"), 0.0, 1e20, 0.0),
    }


def apply_command(cmd):
    if robot is None:
        return
    robot.apply_command(cmd)


def demo_movement():
    if robot is None:
        return
    robot.demo_movement()


def apply_failsafe():
    safe_mode = "init" if last_cmd.get("mode") == "init" else "stand"
    stop_cmd = {
        "mode": safe_mode,
        "vx": 0.0,
        "vy": 0.0,
        "turn": 0.0,
        "speed": 0.0,
        "height": last_cmd.get("height", 0.0),
        "ts": 0.0,
    }
    apply_command(stop_cmd)


def movement_mode_from_command(cmd):
    mode = cmd.get("mode", "stop")
    if mode in ("init", "stand"):
        return mode
    if abs(cmd.get("turn", 0.0)) > 0.02:
        return "turn"
    if abs(cmd.get("vx", 0.0)) > 0.02 or abs(cmd.get("vy", 0.0)) > 0.02:
        return "walk"
    return "stand"


def apply_soft_failsafe(elapsed_ms):
    """Mask brief command dropouts and ramp down smoothly on longer losses."""
    hold_ms = int(FAILSAFE_HOLD_S * 1000)
    decay_ms = max(1, int(FAILSAFE_DECAY_S * 1000))

    if elapsed_ms <= hold_ms:
        # Keep the last command for short link blips.
        apply_command(last_cmd)
        return

    t = elapsed_ms - hold_ms
    if t >= decay_ms:
        apply_failsafe()
        return

    # Linear decay from 1 -> 0 during decay window.
    ratio = max(0.0, 1.0 - (t / decay_ms))
    soft_cmd = {
        "mode": movement_mode_from_command(last_cmd),
        "vx": last_cmd.get("vx", 0.0) * ratio,
        "vy": last_cmd.get("vy", 0.0) * ratio,
        "turn": last_cmd.get("turn", 0.0) * ratio,
        "speed": last_cmd.get("speed", 0.0) * ratio,
        "height": last_cmd.get("height", 0.0),
        "ts": 0.0,
    }
    if ratio < 0.02:
        soft_cmd["mode"] = "init" if last_cmd.get("mode") == "init" else "stand"
    apply_command(soft_cmd)


def main():
    global last_cmd_ms, last_cmd, robot

    print("Building robot config...")
    robot = HexapodRobot()
    print("Running hexapod init...")
    robot.hexapod_init()

    if DEMO_ON_BOOT:
        while True:
            demo_movement()
            if not DEMO_REPEAT:
                break

    print("Init complete. Starting serial receiver...")

    poll = uselect.poll()
    poll.register(sys.stdin, uselect.POLLIN)
    print("Servo 2040 receiver started")
    next_tick_ms = time.ticks_ms()

    while True:
        events = poll.poll(0)
        if events:
            line = sys.stdin.readline()
            if line:
                try:
                    payload = ujson.loads(line)
                    cmd = sanitize(payload)
                    last_cmd = cmd
                    last_cmd_ms = time.ticks_ms()
                except Exception:
                    pass

        now_ms = time.ticks_ms()
        if time.ticks_diff(now_ms, next_tick_ms) >= 0:
            elapsed = time.ticks_diff(now_ms, last_cmd_ms)
            if elapsed > int(FAILSAFE_S * 1000):
                apply_soft_failsafe(elapsed)
            else:
                apply_command(last_cmd)
            next_tick_ms = time.ticks_add(next_tick_ms, CONTROL_DT_MS)

        time.sleep_ms(1)


main()
