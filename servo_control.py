from machine import Pin, PWM
import time
from math import *

class servo_movement:
    def __init__(self, pin_list):
        self.servos = [self.make_servo(p) for p in pin_list]

    def make_servo(self, pin_num):
        pwm = PWM(Pin(pin_num))

        # standard 50 Hz
        pwm.freq(50)
        return pwm
    
    def angle_to_duty(self, angle_deg):
        # Clamp angle to 0–180
        if angle_deg < 0:
            angle_deg = 0
        if angle_deg > 180:
            angle_deg = 180
        min_us = 500      # 0°
        max_us = 2500     # 180°
        us = min_us + (angle_deg / 180) * (max_us - min_us)
        duty = int((us / 20000) * 65535)   # 20 ms period at 50 Hz
        return duty
    
    def turn_angles(self, angles):
        for s, a in zip(self.servos, angles):
            s.duty_u16(self.angle_to_duty(a))

    def ease_in_out_quad(self, t):
        """
            Easing coefficient function, curve.
            Parameters
            ----------
                t(float): a float within [0, 1], basically step.
        """
        return 2*t*t if t < 0.5 else 1 - ((-2*t + 2)**2) / 2

    def turn_angles_eased(self, target_angles, pre_angles, duration=0.5, steps=200):
        """
        Smoothly interpolate servos from pre_angles to target_angles using an ease-in-out sine curve.
        Parameters
        ----------
        target_angles : Sequence[float]
            Iterable of target angles for each servo (in the same units expected by self.turn_angles).
        pre_angles : Sequence[float]
            Iterable of starting angles corresponding to target_angles. Values are copied at call time.
        duration : float, optional
            Total time in seconds over which the interpolation runs (default 0.5). The method is blocking
            for the duration of the motion.
        steps : int, optional
            Number of discrete interpolation steps (default 200). Higher values give smoother motion.
        ------
        ValueError
            If steps is not a positive integer or duration is negative. (time.sleep will also raise for
            invalid sleep values.)
        Examples
        --------
        # Smoothly move from current_angles to goal_angles over 0.8 seconds with 400 steps:
        # self.turn_angles_eased(goal_angles, current_angles, duration=0.8, steps=400)
        """
        start_angles = list(pre_angles)

        for i in range(steps + 1):
            t = i / steps
            # e = self.ease_in_out_quad(t) # basic ease motion curve.
            e = -(cos(pi * t) - 1) / 2 # sine motion curve.

            new_angles = []
            for sa, ta in zip(start_angles, target_angles):
                if sa == ta:
                    # no change needed → keep constant angle
                    new_angles.append(sa)
                else:
                    # easing interpolation
                    new_angles.append(sa + (ta - sa) * e)

            self.turn_angles(new_angles)
            time.sleep(duration / steps)