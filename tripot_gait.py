from math import *
import time

class Tripot_gait:
    def __init__(self):
        pass

    def bezier_curve(self, p1, p2, p3, i, duration = 0.5 ,steps=100):
        t = i / steps
        te = 0.5 * (1 - cos(pi * t))  # easing

        y = (1 - te)**2 * p1[0] + 2 * (1 - te) * te * p2[0] + te**2 * p3[0]
        z = (1 - te)**2 * p1[1] + 2 * (1 - te) * te * p2[1] + te**2 * p3[1]
        time.sleep(duration / steps)
        return y, z