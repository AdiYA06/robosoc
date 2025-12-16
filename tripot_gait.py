from math import *
import numpy as np
import time

class Tripot_gait:
    def __init__(self, beta_ang = 60):
        self.legs_ROT_dict = {
            'legi' : self.rotation_matrix(0),
            'legl' : self.rotation_matrix(pi),
            'legj' : self.rotation_matrix(-beta_ang),
            'legm' : self.rotation_matrix(-beta_ang),
            'legk' : self.rotation_matrix(beta_ang),
            'legn' : self.rotation_matrix(beta_ang)
        }
        self.legs_offset = {
            'legi' : [30,0,0],
            'legl' : [-30,0,0],
            'legj' : [30,0,0],
            'legm' : [-30,0,0],
            'legk' : [-30,0,0],
            'legn' : [30,0,0]
        }

    def bezier_curve(self, p1, p2, p3, i, duration = 0.5 ,steps=100):
        t = i / steps
        te = 0.5 * (1 - cos(pi * t))  # easing

        y = (1 - te)**2 * p1[0] + 2 * (1 - te) * te * p2[0] + te**2 * p3[0]
        z = (1 - te)**2 * p1[1] + 2 * (1 - te) * te * p2[1] + te**2 * p3[1]
        time.sleep(duration / steps)
        return y, z
    
    def rotation_matrix(self, beta):
        ROT = [
            [cos(beta), -sin(beta), 0],
            [sin(beta), cos(beta),  0],
            [0,         0,          1]
        ]
        return ROT
    
if __name__ == '__main__':
    ang = Tripot_gait()
    np.set_printoptions(suppress=True, precision=3)
    print(np.dot(ang.legs_ROT_dict['legj'],[160,0,-100]))