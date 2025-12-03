import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import legs_IK

class Simulator:
    def __init__(self,joint_positions):
        # Create a new figure for the plot
        fig = plt.figure()
        
        # Add a 3D subplot to the figure, where 111 stands for 1x1 grid and the first subplot
        ax = fig.add_subplot(111, projection='3d')

        # Extract x, y, and z coordinates of each joint from joint_positions
        x = [joint[0] for joint in joint_positions]
        y = [joint[1] for joint in joint_positions]
        z = [joint[2] for joint in joint_positions]

        # Plot the leg segments connecting the joints with markers at each joint
        ax.plot(x, y, z, "-o", linewidth=2, markersize=8)

        # Calculate the midpoints of each segment (Coxa, Femur, and Tibia)
        coxa_mid = [(joint_positions[0][i] + joint_positions[1][i])/2 for i in range(3)]
        femur_mid = [(joint_positions[1][i] + joint_positions[2][i])/2 for i in range(3)]
        tibia_mid = [(joint_positions[2][i] + joint_positions[3][i])/2 for i in range(3)]

        # Add labels for each segment at their respective midpoints
        ax.text(coxa_mid[0], coxa_mid[1], coxa_mid[2], 'Coxa', fontsize=12, color='blue')
        ax.text(femur_mid[0], femur_mid[1], femur_mid[2], 'Femur', fontsize=12, color='blue')
        ax.text(tibia_mid[0], tibia_mid[1], tibia_mid[2], 'Tibia', fontsize=12, color='blue')

        # Set labels for the x, y, and z axes
        ax.set_xlabel('X-axis')
        ax.set_ylabel('Y-axis')
        ax.set_zlabel('Z-axis')

        # Set the title for the plot
        ax.set_title('Spider Leg Visualization')

        self.set_equal_axis(ax, x, y, z)

        # Display the plot
        plt.show()

    def set_equal_axis(self, ax, x, y, z):
        max_range = max(
            max(x) - min(x),
            max(y) - min(y),
            max(z) - min(z)
        ) / 2

        mid_x = (max(x) + min(x)) / 2
        mid_y = (max(y) + min(y)) / 2
        mid_z = (max(z) + min(z)) / 2

        ax.set_xlim(mid_x - max_range, mid_x + max_range)
        ax.set_ylim(mid_y - max_range, mid_y + max_range)
        ax.set_zlim(mid_z - max_range, mid_z + max_range)

if __name__ == '__main__':
    # Call the plot_leg function with the joint_positions
    leg = legs_IK.SpiderLeg("Leg1", COXA=43.8, FEMUR=88, TIBIA=166) #mm
    # Set the joint angles (in degrees) for the leg
    leg.set_angles([90, 30, 120])

    # Get the current joint angles
    currentAngles = leg.get_angles()

    # Get the current target position (x, y, z) of the leg tip
    currentTarget = leg.get_target()
    #Define the new tar4get
    newTarget = [90, 80, -100]
    # Calculate the joint angles required to reach a new target position using inverse kinematics
    new_angles = leg.inverseKinematics(target=newTarget)
    print(new_angles)
    joint_positions = leg.forwardKinematics()
    print(joint_positions[3])
    Simulator(joint_positions)