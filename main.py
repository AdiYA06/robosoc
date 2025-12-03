from machine import Pin, PWM
import time
import legs_IK
import servo_control

# Which GPIOs your servos are on:
# SERVO 1 → GP0, SERVO 2 → GP1, SERVO 3 → GP2, etc.
SERVO_PINS = [0, 1, 2]   # change this list for more / different channels

leg1 = legs_IK.SpiderLeg("Leg1", 43.8, 88, 166, SERVO_PINS)
control = servo_control.servo_movement(SERVO_PINS)

leg1.set_angles([89.1814610210269,47.20376603670172, 129])

'''newTarget = [40, 1, -100]
new_angles = leg1.inverseKinematics(target=newTarget)
joint_positions = leg1.forwardKinematics()
print(joint_positions[3])'''
