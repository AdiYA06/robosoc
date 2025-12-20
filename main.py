from machine import Pin, PWM
import time
import legs_IK
import servo_control
import tripot_gait

tripot = tripot_gait.Tripot_gait()
'''leg = legs_IK.SpiderLeg("legi", 43.8, 88, 166, [0,1,2])
while True:
    leg.set_angles([0,70,130])'''
# For the legs here, i dont know there error that legn and legj, legk and legexchanged their characteristics,
legs = [
    # legs_IK.SpiderLeg("legi", 43.8, 88, 166, [0,1,2]),
    # legs_IK.SpiderLeg("legj", 43.8, 88, 166, [0,1,2]),
    # legs_IK.SpiderLeg("legk", 43.8, 88, 166, [0,1,2]),
    # legs_IK.SpiderLeg("legl", 43.8, 88, 166),
    # legs_IK.SpiderLeg("legm", 43.8, 88, 166, [0,1,2]),
    legs_IK.SpiderLeg("legn", 43.8, 88, 166, [0,1,2])
]
tripot.movement(legs)