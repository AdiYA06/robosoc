"""Servo 2040 MicroPython receiver + robot init."""

import sys
import time
import ujson
import uselect
from math import atan2, degrees, sqrt
import legs_IK
import tripot_gait

FAILSAFE_S = 0.7
FAILSAFE_HOLD_S = 0.25
FAILSAFE_DECAY_S = 1.10
CONTROL_HZ = 50
CONTROL_DT_MS = int(1000 / CONTROL_HZ)
SAFE_POWER_MODE = True

# Safe-power profile: reduce peak current spikes from aggressive gait changes.
SAFE_WALK_SPEED_SCALE = 0.88
SAFE_WALK_STRIDE_SCALE = 0.88
SAFE_WALK_AMPLITUDE_SCALE = 0.84

SAFE_TURN_SPEED_CAP = 0.45
SAFE_TURN_INPUT_SCALE = 0.45
SAFE_TURN_AMPLITUDE_SCALE = 0.65
SAFE_TURN_ANGLE_SCALE = 0.45
TURN_DEADBAND = 0.10
TURN_ACCEL_PER_TICK = 0.02
TURN_DECEL_PER_TICK = 0.07

last_cmd_ms = time.ticks_ms()
last_cmd = {
    "mode": "stop",
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
        self.last_mode = "stop"
        self.last_stop_height = None
        self.smoothed_walk_angle = None
        self.smoothed_vx = 0.0
        self.smoothed_vy = 0.0
        self.walk_vector_alpha = 0.18
        self.smoothed_turn = 0.0
        self.step_min = 20
        self.step_max = 40
        self.legs = [
            legs_IK.SpiderLeg("legi", 43.8, 88, 166, [0, 1, 2]),
            # legs_IK.SpiderLeg("legj", 43.8, 88, 166, [0,1,2]),
            # legs_IK.SpiderLeg("legk", 43.8, 88, 166, [0,1,2]),
            # legs_IK.SpiderLeg("legl", 43.8, 88, 166, [0,1,2]),
            # legs_IK.SpiderLeg("legm", 43.8, 88, 166, [0,1,2]),
            # legs_IK.SpiderLeg("legn", 43.8, 88, 166, [0,1,2]),
        ]

    def hexapod_init(self):
        for leg in self.legs:
            leg.set_angles([0, 0, 0])
        time.sleep(1)

    def _wrap_angle_deg(self, angle):
        while angle <= -180:
            angle += 360
        while angle > 180:
            angle -= 360
        return angle

    def _angle_diff_deg(self, target, current):
        return self._wrap_angle_deg(target - current)

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

    def apply_command(self, cmd):
        """Live non-blocking gait control from web command packets."""
        mode = cmd.get("mode", "stop")
        vx = cmd.get("vx", 0.0)
        vy = cmd.get("vy", 0.0)
        turn = cmd.get("turn", 0.0)
        speed = cmd.get("speed", 0.0)
        height = cmd.get("height", 0.0)
        speed = max(0.0, min(1.0, speed))
        stance_z = -125 + (height * 45)   # exact: -170 .. -80
        xpos = 130 + (stance_z + 125) * (20 / 45)  # ~0.4444
        xpos = max(110, min(150, xpos))
        gait_step = int(round(self.step_max - (self.step_max - self.step_min) * speed))
        gait_step = max(self.step_min, min(self.step_max, gait_step))

        if mode == "stop":
            self.smoothed_turn = 0.0
            if self.last_mode != "stop":
                for leg in self.legs:
                    leg.inverseKinematics([xpos, 0, stance_z], easing=1)
                self.tripot.reset_walk_phase()
                self.tripot.reset_turn_phase()
                self.last_stop_height = stance_z
                self.smoothed_walk_angle = None
                self.smoothed_vx = 0.0
                self.smoothed_vy = 0.0
            elif self.last_stop_height is None or abs(stance_z - self.last_stop_height) > 0.5:
                for leg in self.legs:
                    leg.inverseKinematics([xpos, 0, stance_z], easing=0)
                self.last_stop_height = stance_z
            self.last_mode = "stop"
            return

        if mode == "turn":
            self.last_stop_height = None
            self.smoothed_walk_angle = None
            self.smoothed_vx = 0.0
            self.smoothed_vy = 0.0
            if self.last_mode != "turn":
                self.tripot.reset_turn_phase()

            # Prevent hard left<->right reversals from creating current spikes.
            turn_speed = speed
            if SAFE_POWER_MODE:
                turn_speed = min(turn_speed, SAFE_TURN_SPEED_CAP)
                turn = max(-1.0, min(1.0, turn * SAFE_TURN_INPUT_SCALE))
            else:
                turn = max(-1.0, min(1.0, turn))
            turn_cmd = self._slew_turn(turn)
            turn_mag = abs(turn_cmd)

            turn_max_angle = 10 + 30 * turn_mag
            if SAFE_POWER_MODE:
                turn_max_angle *= SAFE_TURN_ANGLE_SCALE
            turn_A = 20 + int(20 * turn_speed)
            if SAFE_POWER_MODE:
                turn_A = int(turn_A * SAFE_TURN_AMPLITUDE_SCALE)
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
            walk_speed = speed
            if SAFE_POWER_MODE:
                walk_speed = max(0.0, min(1.0, walk_speed * SAFE_WALK_SPEED_SCALE))
            gait_step = int(round(self.step_max - (self.step_max - self.step_min) * walk_speed))
            gait_step = max(self.step_min, min(self.step_max, gait_step))
            if self.last_mode != "walk":
                self.tripot.reset_walk_phase()
                self.smoothed_walk_angle = None
                self.smoothed_vx = vx
                self.smoothed_vy = vy

            self.smoothed_vx += (vx - self.smoothed_vx) * self.walk_vector_alpha
            self.smoothed_vy += (vy - self.smoothed_vy) * self.walk_vector_alpha
            mag = sqrt(self.smoothed_vx * self.smoothed_vx + self.smoothed_vy * self.smoothed_vy)
            if mag < 0.03:
                self.last_mode = "walk"
                return

            walk_angle = degrees(atan2(self.smoothed_vy, self.smoothed_vx))
            self.smoothed_walk_angle = walk_angle
            stride = max(30, int((60 + 100 * walk_speed) * min(1.0, mag)))
            if SAFE_POWER_MODE:
                stride = max(28, int(stride * SAFE_WALK_STRIDE_SCALE))
            walk_A = 15 + int(20 * walk_speed)
            if SAFE_POWER_MODE:
                walk_A = int(walk_A * SAFE_WALK_AMPLITUDE_SCALE)
            self.tripot.walk_step(
                self.legs,
                angle=walk_angle,
                T=stride,
                body_height=stance_z,
                A=walk_A,
                step=gait_step,
                xpos=xpos,
            )
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


def apply_failsafe():
    stop_cmd = {
        "mode": "stop",
        "vx": 0.0,
        "vy": 0.0,
        "turn": 0.0,
        "speed": 0.0,
        "height": last_cmd.get("height", 0.0),
        "ts": 0.0,
    }
    apply_command(stop_cmd)


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
        "mode": "turn" if abs(last_cmd.get("turn", 0.0)) > 0.02 else ("walk" if (abs(last_cmd.get("vx", 0.0)) > 0.02 or abs(last_cmd.get("vy", 0.0)) > 0.02) else "stop"),
        "vx": last_cmd.get("vx", 0.0) * ratio,
        "vy": last_cmd.get("vy", 0.0) * ratio,
        "turn": last_cmd.get("turn", 0.0) * ratio,
        "speed": last_cmd.get("speed", 0.0) * ratio,
        "height": last_cmd.get("height", 0.0),
        "ts": 0.0,
    }
    if ratio < 0.02:
        soft_cmd["mode"] = "stop"
    apply_command(soft_cmd)


def main():
    global last_cmd_ms, last_cmd, robot

    print("Building robot config...")
    robot = HexapodRobot()
    print("Running hexapod init...")
    robot.hexapod_init()
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
