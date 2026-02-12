from machine import Pin, PWM
import time
import legs_IK
import servo_control
import tripot_gait

class main:
    def __init__(self):
        # For the legs here, i dont know there error that legn and legj, legk and legexchanged their characteristics,
        self.tripot = tripot_gait.Tripot_gait()
        self.legs = [
            legs_IK.SpiderLeg("legi", 43.8, 88, 166, [0,1,2]),
            # legs_IK.SpiderLeg("legj", 43.8, 88, 166, [0,1,2]),
            # legs_IK.SpiderLeg("legk", 43.8, 88, 166, [0,1,2]),
            # legs_IK.SpiderLeg("legl", 43.8, 88, 166),
            # legs_IK.SpiderLeg("legm", 43.8, 88, 166, [0,1,2]),
            # legs_IK.SpiderLeg("legn", 43.8, 88, 166, [0,1,2])
        ]
        
    def hexapod_init(self):
        for leg in self.legs:
            leg.set_angles([0,0,0])
        time.sleep(1)
        for leg in self.legs:
            leg.set_angles([0,45,120])
        time.sleep(1)
        
    def temp(self):
        self.tripot.movement(self.legs)

if __name__ == "__main__":
    main = main()
    main.hexapod_init()
    main.temp()
