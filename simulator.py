import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import legs_IK
import time
import tripot_gait
import numpy as np

class Simulator:
    def __init__(self, leg):
        self.leg = leg
        self.tripot = tripot_gait.Tripot_gait()
        self.leg_config = {
            'Legi': {'angle': 0,            'x': 90},
            'Legj': {'angle': -np.pi/4,     'x': 120},
            'Legk': {'angle': np.pi/4,      'x': 120},
            'Legl': {'angle': np.pi,        'x': 90},
            'Legm': {'angle': -np.pi/4,     'x': 110},
            'Legn': {'angle': np.pi/4,      'x': 110},
        }
        plt.ion()
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.rot = lambda x :self.tripot.rotation_matrix(x)
        
        self.ax.set_xlabel('X-axis')
        self.ax.set_ylabel('Y-axis')
        self.ax.set_zlabel('Z-axis')
        self.ax.set_title('Spider Leg Visualization')

        # Initial joint positions
        joint_positions = self.leg.forwardKinematics()
        self.plot_leg(leg, joint_positions)

    def plot_leg(self, leg, joint_positions):
        self.ax.cla()  # Clear previous plot
        cfg = self.leg_config[leg.name]
        R = self.rot(cfg['angle'])
        t = np.array([cfg['x'], 0, 0])
        x, y, z = [], [], []
        for p in joint_positions:
            p_body = R @ np.array(p) + t
            x.append(p_body[0])
            y.append(p_body[1])
            z.append(p_body[2])

        # Plot leg segments
        self.ax.plot(x, y, z, "-o", linewidth=2, markersize=8)

        # Calculate midpoints for labels
        coxa_mid = [(x[0] + x[1])/2, (y[0] + y[1])/2, (z[0] + z[1])/2]
        femur_mid = [(x[1] + x[2])/2, (y[1] + y[2])/2, (z[1] + z[2])/2]
        tibia_mid = [(x[2] + x[3])/2, (y[2] + y[3])/2, (z[2] + z[3])/2]

        self.ax.text(coxa_mid[0], coxa_mid[1], coxa_mid[2], 'Coxa', fontsize=12, color='blue')
        self.ax.text(femur_mid[0], femur_mid[1], femur_mid[2], 'Femur', fontsize=12, color='blue')
        self.ax.text(tibia_mid[0], tibia_mid[1], tibia_mid[2], 'Tibia', fontsize=12, color='blue')

        # Keep the axes fixed but do NOT reset view
        range_limit = 300
        self.ax.set_xlim(-range_limit, range_limit)
        self.ax.set_ylim(-range_limit, range_limit)
        self.ax.set_zlim(-range_limit, range_limit)

        plt.draw()
        plt.pause(0.001)

    def set_equal_axis(self, x, y, z):
        max_range = max(max(x) - min(x), max(y) - min(y), max(z) - min(z)) / 2
        mid_x = (max(x) + min(x)) / 2
        mid_y = (max(y) + min(y)) / 2
        mid_z = (max(z) + min(z)) / 2
        self.ax.set_xlim(mid_x - max_range, mid_x + max_range)
        self.ax.set_ylim(mid_y - max_range, mid_y + max_range)
        self.ax.set_zlim(mid_z - max_range, mid_z + max_range)

    def moving(self, leg, step = 1):
        delta = step
        num_of_steps = 100
        while True:  # Loop forever
            p1,p2,p3 = [-130,-100], [0,20], [130,-100] # p1 = [-T/2, S], p2 = [0, S+2A], p3 = [T/2, S]
            for t in range(0,num_of_steps+1,delta):
                self.ax.cla()
                y, z = self.tripot.bezier_curve(p1,p2,p3, t, steps = num_of_steps)
                newTarget = [160, y, z]
                leg.inverseKinematics(target=newTarget)
                joint_positions = leg.forwardKinematics()
                sim.plot_leg(leg, joint_positions)
                print([round(v) for v in joint_positions[3]])
            p1,p2,p3 = [-130,-100], [0,-100], [130,-100]
            for t in range(0,num_of_steps+1,delta):
                self.ax.cla()
                y, z = self.tripot.bezier_curve(p1,p2,p3, t, steps = num_of_steps)
                newTarget = [160, -y, z]
                leg.inverseKinematics(target=newTarget)
                joint_positions = leg.forwardKinematics()
                sim.plot_leg(leg, joint_positions)
                print([round(v) for v in joint_positions[3]])

if __name__ == '__main__':
    legs = [
        legs_IK.SpiderLeg("Legi", 43.8, 88, 166),
        legs_IK.SpiderLeg("Legj", 43.8, 88, 166),
        legs_IK.SpiderLeg("Legk", 43.8, 88, 166),
        legs_IK.SpiderLeg("Legl", 43.8, 88, 166),
        legs_IK.SpiderLeg("Legm", 43.8, 88, 166),
        legs_IK.SpiderLeg("Legn", 43.8, 88, 166),
    ]
    legi = legs[0]
    legj = legs[1]
    legk = legs[2]
    legl = legs[3]
    legm = legs[4]
    legn = legs[5]
    legi.set_angles([90, 30, 120])

    sim = Simulator(legi)
    sim.moving(legi)