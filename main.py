from machine import Pin, PWM
import time
import legs_IK
import servo_control

# Which GPIOs your servos are on:
# SERVO 1 → GP0, SERVO 2 → GP1, SERVO 3 → GP2, etc.
SERVO_PINS = [0, 1, 2]   # change this list for more / different channels

leg1 = legs_IK.SpiderLeg("Leg1", 43.8, 88, 166, SERVO_PINS)
control = servo_control.servo_movement(SERVO_PINS)
while True:
    leg1.set_angles([0,0,90])
    time.sleep(5)
    current_angle = leg1.get_angles()
    current_target = leg1.get_target()
    newTarget = [80,50, -150]
    new_angles = leg1.inverseKinematics(target=newTarget)
    joint_positions = leg1.forwardKinematics()
    print(new_angles)
    time.sleep(10)
    #leg1.set_angles([0,0,90])
