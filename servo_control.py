from machine import Pin, PWM
import time
import math

class servo_movement:
    def __init__(self, pin_list):
        self.servos = [self.make_servo(p) for p in pin_list]

    def make_servo(self, pin_num):
        pwm = PWM(Pin(pin_num))
        pwm.freq(50)          # standard 50 Hz
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
        return 2*t*t if t < 0.5 else 1 - ((-2*t + 2)**2) / 2

    def turn_angles_eased(self, target_angles, pre_angles, duration=0.5, steps=200):
        start_angles = list(pre_angles)  # ensure mutable list

        for i in range(steps + 1):
            t = i / steps
            # e = self.ease_in_out_quad(t) # basic ease motion curve.
            e = -(math.cos(math.pi * t) - 1) / 2 # sine motion curve.

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
