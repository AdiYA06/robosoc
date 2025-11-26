from machine import Pin, PWM
import time
import leg_alg

# Which GPIOs your servos are on:
# SERVO 1 → GP0, SERVO 2 → GP1, SERVO 3 → GP2, etc.
SERVO_PINS = [0, 1]   # change this list for more / different channels

spider = leg_alg.Connection(SERVO_PINS)

while True:
    spider.set_angles([0, 0])
    time.sleep(1)
    spider.set_angles([45, 45])
    time.sleep(1)
    spider.set_angles([90, 90])
    time.sleep(1)