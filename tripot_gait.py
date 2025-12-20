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
    
    def calculate_gait_targets(self, legs, swing_legs, p1, p3, S, A, num_of_steps, t, angle, x_pos):
        """Calculate IK targets for all legs at time step t."""
        targets = {}

        # swing & stance curves
        p2_up = [0, S + 2*A]
        p2_down = [0, S]

        y_up, z_up = self.bezier_curve(p1, p2_up, p3, t, steps=num_of_steps)
        y_down, z_down = self.bezier_curve(p1, p2_down, p3, t, steps=num_of_steps)

        for leg in legs:
            R_leg = self.rotation_matrix(self.anti_beta_dict[leg.name])

            if leg.name in swing_legs:
                y, z = y_up, z_up
                sign = +1
            else:
                y, z = y_down, z_down
                sign = -1

            target = [
                sign * R_leg[0][1] * y,
                sign * R_leg[1][1] * y,
                sign * R_leg[2][1] * y,
            ]

            # body rotation
            R_body = self.rotation_matrix(radians(angle))
            target_rot = [
                x_pos   + R_body[0][0]*target[0] + R_body[0][1]*target[1] + R_body[0][2]*target[2],
                0       + R_body[1][0]*target[0] + R_body[1][1]*target[1] + R_body[1][2]*target[2],
                z       + R_body[2][0]*target[0] + R_body[2][1]*target[1] + R_body[2][2]*target[2],
            ]

            targets[leg.name] = target_rot
        return targets
    
    def movement(self, legs, angle = 0, T = 140, S = -100, A = 20, step = 100, xpos = 150):
        p1 = [T/2, S]
        p3 = [-T/2, S]

        tripod_A = {'legi', 'legk', 'legm'}
        tripod_B = {'legj', 'legl', 'legn'}

        tripods = [tripod_A, tripod_B]

        while True:
            for swing_tripod in tripods:
                for t in range(0, step + 1, 1):
                    targets = self.calculate_gait_targets(
                        legs, swing_tripod,
                        p1, p3, S, A,
                        step, t,
                        angle,
                        xpos
                    )

                    for leg in legs:
                        leg.inverseKinematics(targets[leg.name])

if __name__ == '__main__':
    pass