from math import *
import time

class Tripot_gait:
    def __init__(self, beta_ang = pi/4):
        self.legs_ROT_dict = {
            'legi' : self.rotation_matrix(0),
            'legl' : self.rotation_matrix(pi),
            'legj' : self.rotation_matrix(beta_ang),
            'legm' : self.rotation_matrix(pi + beta_ang),
            'legk' : self.rotation_matrix(pi/2 + beta_ang),
            'legn' : self.rotation_matrix(-beta_ang)
        }
        self.anti_beta_dict = {
            'legi' : 0,
            'legl' : -pi,
            'legj' : -beta_ang,
            'legm' : -(pi + beta_ang),
            'legk' : -(pi/2 + beta_ang),
            'legn' : -(-beta_ang)
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