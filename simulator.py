import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import legs_IK
import time
import tripot_gait
from math import *

class Simulator:
    def __init__(self, legs):
        self.legs = legs
        self.tripot = tripot_gait.Tripot_gait(pi / 4)
        self.leg_config = {
            'legi': {'y': 0, 'x': 50},
            'legj': {'y': 40, 'x': 50},
            'legk': {'y': 40, 'x': -50},
            'legl': {'y': 0, 'x': -50},
            'legm': {'y': -40, 'x': -50},
            'legn': {'y': -40, 'x': 50},
        }
        plt.ion()
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111, projection='3d')
        
        self.ax.set_xlabel('X-axis')
        self.ax.set_ylabel('Y-axis')
        self.ax.set_zlabel('Z-axis')
        self.ax.set_title('Spider Leg Visualization')

        # Initial joint positions for all legs
        for leg in self.legs:
            joint_positions = leg.forwardKinematics()
            self.plot_leg(leg, joint_positions)

    def plot_leg(self, leg, joint_positions):
        cfg = self.leg_config[leg.name]
        # R = self.rot(cfg['angle'])
        R = self.tripot.legs_ROT_dict[leg.name]
        t = [cfg['x'], cfg['y'], 0]
        # Display leg name near hip joint
        jp = joint_positions[2]
        hip_pos = [
            R[0][0]*jp[0] + R[0][1]*jp[1] + R[0][2]*jp[2] + t[0],
            R[1][0]*jp[0] + R[1][1]*jp[1] + R[1][2]*jp[2] + t[1],
            R[2][0]*jp[0] + R[2][1]*jp[1] + R[2][2]*jp[2] + t[2],
        ]
        self.ax.text(hip_pos[0], hip_pos[1], hip_pos[2]+10, leg.name, fontsize=10, color='red')
        x, y, z = [], [], []
        for p in joint_positions:
            p_body = [
                R[0][0]*p[0] + R[0][1]*p[1] + R[0][2]*p[2] + t[0],
                R[1][0]*p[0] + R[1][1]*p[1] + R[1][2]*p[2] + t[1],
                R[2][0]*p[0] + R[2][1]*p[1] + R[2][2]*p[2] + t[2],
            ]
            x.append(p_body[0])
            y.append(p_body[1])
            z.append(p_body[2])

        # Plot leg segments
        self.ax.plot(x, y, z, "-o", linewidth=2, markersize=8)

        # Keep the axes fixed but do NOT reset view
        range_limit = 300
        self.ax.set_xlim(-range_limit, range_limit)
        self.ax.set_ylim(-range_limit, range_limit)
        self.ax.set_zlim(-range_limit, range_limit)

    def set_equal_axis(self, x, y, z):
        max_range = max(max(x) - min(x), max(y) - min(y), max(z) - min(z)) / 2
        mid_x = (max(x) + min(x)) / 2
        mid_y = (max(y) + min(y)) / 2
        mid_z = (max(z) + min(z)) / 2
        self.ax.set_xlim(mid_x - max_range, mid_x + max_range)
        self.ax.set_ylim(mid_y - max_range, mid_y + max_range)
        self.ax.set_zlim(mid_z - max_range, mid_z + max_range)

    def moving(self, legs, step = 1):
        delta = step
        num_of_steps = 50
        T = 160
        S = -70
        A = 20
        while True:  # Loop forever
            p1,p2,p3 = [-T/2,S], [0,S+2*A], [T/2,S] # p1 = [-T/2, S], p2 = [0, S+2A], p3 = [T/2, S] T = 160
            for t in range(0,num_of_steps+1,delta):
                self.ax.cla()
                y, z = self.tripot.bezier_curve(p1,p2,p3, t, steps = num_of_steps)
                for leg in legs:
                    R = self.tripot.rotation_matrix(self.tripot.anti_beta_dict[leg.name])
                    target = [
                        150 + R[0][1]*y,
                        0   + R[1][1]*y,
                        z   + R[2][1]*y,
                    ]
                    leg.inverseKinematics(target)
                    joint_positions = leg.forwardKinematics()
                    self.plot_leg(leg, joint_positions)
                plt.draw()
                plt.pause(0.001)
            p2 = [0,S]
            for t in range(0,num_of_steps+1,delta):
                self.ax.cla()
                y, z = self.tripot.bezier_curve(p1,p2,p3, t, steps = num_of_steps)
                for leg in legs:
                    R = self.tripot.rotation_matrix(self.tripot.anti_beta_dict[leg.name])
                    target = [
                        150 - R[0][1]*y,
                        0   - R[1][1]*y,
                        z   - R[2][1]*y,
                    ]
                    leg.inverseKinematics(target)
                    joint_positions = leg.forwardKinematics()
                    self.plot_leg(leg, joint_positions)
                plt.draw()
                plt.pause(0.001)

if __name__ == '__main__':
    legs = [
        legs_IK.SpiderLeg("legi", 43.8, 88, 166),
        legs_IK.SpiderLeg("legj", 43.8, 88, 166),
        legs_IK.SpiderLeg("legk", 43.8, 88, 166),
        legs_IK.SpiderLeg("legl", 43.8, 88, 166),
        legs_IK.SpiderLeg("legm", 43.8, 88, 166),
        legs_IK.SpiderLeg("legn", 43.8, 88, 166)
    ]
    for leg in legs:
        leg.set_angles([90, 30, 120])

    sim = Simulator(legs)
    sim.moving(legs)