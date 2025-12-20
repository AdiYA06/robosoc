from machine import Pin, PWM
import time
import legs_IK
import servo_control
import tripot_gait

# Which GPIOs your servos are on:
# SERVO 1 → GP0, SERVO 2 → GP1, SERVO 3 → GP2, etc.
# SERVO_PINS = [0, 1, 2]
# control = servo_control.servo_movement(SERVO_PINS)
tripot = tripot_gait.Tripot_gait()

legs = [
    legs_IK.SpiderLeg("legi", 43.8, 88, 166, [0,1,2]),
    # legs_IK.SpiderLeg("legj", 43.8, 88, 166),
    # legs_IK.SpiderLeg("legk", 43.8, 88, 166),
    # legs_IK.SpiderLeg("legl", 43.8, 88, 166),
    # legs_IK.SpiderLeg("legm", 43.8, 88, 166),
    # legs_IK.SpiderLeg("legn", 43.8, 88, 166)
]
tripot.movement(legs, 0)