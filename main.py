from machine import Pin, PWM
import time
import leg_alg

# Which GPIOs your servos are on:
# SERVO 1 → GP0, SERVO 2 → GP1, SERVO 3 → GP2, etc.
SERVO_PINS = [0, 1, 2]   # change this list for more / different channels

leg1 = leg_alg.SpiderLeg("Leg1", 43.8, 166, 88, SERVO_PINS)

while True:
    leg1.set_angles([20,45,100])
    current_angle = leg1.get_angles()
    current_target = leg1.get_target()
    newTarget = [100,100, 0]
    new_angles = leg1.inverseKinematics(target=newTarget)
    joint_positions = leg1.forwardKinematics()
    print(joint_positions)
    print(current_angle)
    print(new_angles)
    time.sleep(10)