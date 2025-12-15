import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import legs_IK
import time

class Simulator:
    def __init__(self, leg):
        self.leg = leg
        plt.ion()
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_xlabel('X-axis')
        self.ax.set_ylabel('Y-axis')
        self.ax.set_zlabel('Z-axis')
        self.ax.set_title('Spider Leg Visualization')

        # Initial joint positions
        joint_positions = self.leg.forwardKinematics()
        self.plot_leg(joint_positions)

    def plot_leg(self, joint_positions):
        self.ax.cla()  # Clear previous plot
        x = [joint[0] for joint in joint_positions]
        y = [joint[1] for joint in joint_positions]
        z = [joint[2] for joint in joint_positions]

        # Plot leg segments
        self.ax.plot(x, y, z, "-o", linewidth=2, markersize=8)

        # Calculate midpoints for labels
        coxa_mid = [(joint_positions[0][i] + joint_positions[1][i])/2 for i in range(3)]
        femur_mid = [(joint_positions[1][i] + joint_positions[2][i])/2 for i in range(3)]
        tibia_mid = [(joint_positions[2][i] + joint_positions[3][i])/2 for i in range(3)]

        self.ax.text(coxa_mid[0], coxa_mid[1], coxa_mid[2], 'Coxa', fontsize=12, color='blue')
        self.ax.text(femur_mid[0], femur_mid[1], femur_mid[2], 'Femur', fontsize=12, color='blue')
        self.ax.text(tibia_mid[0], tibia_mid[1], tibia_mid[2], 'Tibia', fontsize=12, color='blue')

        # Keep the axes fixed but do NOT reset view
        range_limit = 200
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

    def moving(self, step):
        delta = step
        while True:  # Loop forever
            # Move leg from z = -100 to z = 0
            for z in range(delta, -delta, -5):  # include 0
                newTarget = [100, z, -100]
                leg.inverseKinematics(target=newTarget)
                joint_positions = leg.forwardKinematics()
                print([round(v) for v in joint_positions[3]])
                sim.plot_leg(joint_positions)
                time.sleep(0.05)  # smaller delay for smoother motion

            # Move leg back from z = 0 to z = -100
            for z in range(-delta, delta, 5):
                newTarget = [100, z, -100]
                leg.inverseKinematics(target=newTarget)
                joint_positions = leg.forwardKinematics()
                print([round(v) for v in joint_positions[3]])
                sim.plot_leg(joint_positions)
                time.sleep(0.05)

if __name__ == '__main__':
    leg = legs_IK.SpiderLeg("Leg1", COXA=43.8, FEMUR=88, TIBIA=166)
    leg.set_angles([90, 30, 120])

    sim = Simulator(leg)
    sim.moving(150)