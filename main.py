from machine import Pin, PWM
import time
import legs_IK
import servo_control
import tripot_gait

# Which GPIOs your servos are on:
# SERVO 1 → GP0, SERVO 2 → GP1, SERVO 3 → GP2, etc.
SERVO_PINS = [0, 1, 2]   # change this list for more / different channels

legs = [legs_IK.SpiderLeg("leg1", 43.8, 88, 166, SERVO_PINS)]
control = servo_control.servo_movement(SERVO_PINS)
tripot = tripot_gait.Tripot_gait()

delta = 1
num_of_steps = 500
T = 160
S = -70
A = 20
while True:
    p1,p2,p3 = [-T/2,S], [0,S+2*A], [T/2,S] # p1 = [-T/2, S], p2 = [0, S+2A], p3 = [T/2, S] T = 160
    for t in range(0,num_of_steps+1,delta):
        y, z = tripot.bezier_curve(p1,p2,p3, t, steps = num_of_steps)
        for leg in legs:
            leg.inverseKinematics(target=[160, y, z])
            joint_positions = leg.forwardKinematics()
    p2 = [0,S]
    for t in range(0,num_of_steps+1,delta):
        y, z = tripot.bezier_curve(p1,p2,p3, t, steps = num_of_steps)
        for leg in legs:
            leg.inverseKinematics(target=[160, -y, z])
            joint_positions = leg.forwardKinematics()