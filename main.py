from machine import Pin, PWM
import time
import legs_IK
import servo_control

# Which GPIOs your servos are on:
# SERVO 1 → GP0, SERVO 2 → GP1, SERVO 3 → GP2, etc.
SERVO_PINS = [0, 1, 2]   # change this list for more / different channels

leg1 = legs_IK.SpiderLeg("Leg1", 43.8, 88, 166, SERVO_PINS)
control = servo_control.servo_movement(SERVO_PINS)

new_target = ([80,0,-100])
time.sleep(1)
while True:
    new_target = ([80,60,-100])
    leg1.inverseKinematics(new_target)
    new_target = ([80,60,-80])
    leg1.inverseKinematics(new_target)

    new_target = ([80,-60,-80])
    leg1.inverseKinematics(new_target)
    new_target = ([80,-60,-100])
    leg1.inverseKinematics(new_target)