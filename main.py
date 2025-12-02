from machine import Pin, PWM
import time
import legs_IK
import servo_control

# Which GPIOs your servos are on:
# SERVO 1 → GP0, SERVO 2 → GP1, SERVO 3 → GP2, etc.
SERVO_PINS = [0, 1, 2]   # change this list for more / different channels

leg1 = legs_IK.SpiderLeg("Leg1", 43.8, 88, 166, SERVO_PINS)
control = servo_control.servo_movement(SERVO_PINS)

newTarget = [70, 60, -100]
new_angles = leg1.inverseKinematics(target=newTarget)

#leg1.set_angles([31.002719133873992,48.35442581009674,141.43745904027168])
#print(leg1.get_angles())
#new_angles = leg1.inverseKinematics([80,79,-150])
#print(new_angles)
