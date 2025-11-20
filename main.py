from machine import Pin, PWM
import time

# Which GPIOs your servos are on:
# SERVO 1 → GP0, SERVO 2 → GP1, SERVO 3 → GP2, etc.
SERVO_PINS = [0, 1]   # change this list for more / different channels

def make_servo(pin_num):
    pwm = PWM(Pin(pin_num))
    pwm.freq(50)          # standard 50 Hz
    return pwm

servos = [make_servo(p) for p in SERVO_PINS]

def angle_to_duty(angle_deg):
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

def set_angles(angles):
    # angles is a list like [30, 90, 150]
    for s, a in zip(servos, angles):
        s.duty_u16(angle_to_duty(a))

while True:
    set_angles([0, 0])
    time.sleep(1)
    set_angles([45, 45])
    time.sleep(1)
    set_angles([90, 90])
    time.sleep(1)
