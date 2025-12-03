from machine import Pin, PWM
import time
import legs_IK
import servo_control

# Which GPIOs your servos are on:
# SERVO 1 → GP0, SERVO 2 → GP1, SERVO 3 → GP2, etc.
SERVO_PINS = [0, 1, 2]   # change this list for more / different channels

leg1 = legs_IK.SpiderLeg("Leg1", 43.8, 88, 166, SERVO_PINS)
control = servo_control.servo_movement(SERVO_PINS)

#leg1.set_angles([89.1814610210269,47.20376603670172, 129])
'''while True:
    leg1.set_angles([120,0,90])
    leg1.set_angles([120,30,90])
    leg1.set_angles([40,-20,120])
    leg1.set_angles([40,30,90])'''

'''new_target = ([70,1,-100])
leg1.inverseKinematics(new_target)
joint_positions = leg1.forwardKinematics()
print(joint_positions[3])'''

'''leg1.set_angles([0,45,120])
leg1.set_angles([0,60,90])
while True:
    leg1.set_angles([-45,60,90])
    leg1.set_angles([-45,45,120])
    leg1.set_angles([45,45,120])
    leg1.set_angles([45,60,90])'''
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

'''leg1.set_angles([0,45,120])
time.sleep(1)
new_target = ([80,0,-100])
leg1.inverseKinematics(new_target)
for i in range(60,-60, -5):
    new_target = ([70,i,-100])
    leg1.inverseKinematics(new_target)
    time.sleep(0.05)'''
