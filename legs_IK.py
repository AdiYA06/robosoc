from math import *
import time
# import servo_control

class SpiderLeg:
    def __init__(self, name, COXA, FEMUR, TIBIA, pin_list = None):
        #spider leg => COXA-FEMUR-TIBIA
        # self.control = servo_control.servo_movement(pin_list)
        self.name = name
        self.COXA = COXA
        self.FEMUR = FEMUR
        self.TIBIA = TIBIA
        self.theta1 = 0.
        self.theta2 = 0.
        self.theta3 = 0.
        self.joints = self.forwardKinematics()

    def cos_rule(self, A, B, C):
        return acos((A**2 + B**2 - C**2)/(2*A*B))
    
    def set_angles(self, angles):
        x = angles[1]
        x = -x if x>0 else abs(x)
        angles[1] = 90-x
        
        pre_angles = self.get_angles()
        y = pre_angles[1]
        y = -y if y>0 else abs(y)
        pre_angles[1] = 90-y
        
        _angles = self.normalize_angles(angles)
        self.theta1, self.theta2, self.theta3 = _angles
        # self.control.turn_angles(_angles, self.get_angels())
        # self.control.turn_angles_eased(_angles, pre_angles)
        return self.get_angles()
    
    def get_angles(self):
        return [self.theta1, self.theta2-90, self.theta3]

    def normalize_angles(self, angles):
        """
        Normalize joint angles to be in the range [-180, 180] degrees.
        
        Args:
            angles (list): A list of joint angles in degrees.
            
        Returns:
            list: A list of normalized joint angles in degrees.
        """
        for idx, ang in enumerate(angles):
            sign = 1
            if ang < 0:
                sign = -1
            angles[idx] = sign * (abs(ang) % 360)
            if abs(ang) > 180:
                angles[idx] = ang - (360 * sign)
        return angles
    
    def get_target(self):
        return self.joints[3]

    def inverseKinematics(self, target = None):
        '''
            Calculate the joint angles required to reach a target position, and set_angle.
            Args:
                target(truple 4x3): a truple of joint position in unit same as the length of legs.

            Return:
                list: a list of joint angles required to reach the position in degrees.
        '''
        if target is None:
            target = self.joints[3]
        x, y, z = target[0], abs(target[1]), target[2]
        
        theta1 = acos( y / x )
        theta1 = theta1 if target[1] > 0 else -theta1
        Xa = cos(theta1) * self.COXA
        Ya = sin(theta1) * self.COXA
        
        Xb = x - Xa
        Yb = y - Ya
        
        P = sqrt(Xb**2 + Yb**2)

        G = abs(z)

        H = sqrt(P**2 + G**2)

        phi3 = asin(G/H)

        # C = FEMUR, A = TIBIA, B = H
        phi2 = self.cos_rule(self.TIBIA, H, self.FEMUR)

        # C = TIBIA, A = FEMUR, B = H
        phi1 = self.cos_rule(self.FEMUR, H, self.TIBIA)

        if z > 0:
            theta2 = phi1 + phi3
        else:
            theta2 = phi1 - phi3
        
        theta3 = phi1 + phi2
        ang = [degrees(theta1), degrees(theta2), degrees(theta3)]
        
        self.set_angles(ang)
        self.forwardKinematics()
        return ang
        
    def forwardKinematics(self, angles = None):
        '''
            Calculate the joint positions (x, y, z) based on the given joint angles.
        '''
        if angles is None:
            angles = [pi/2 - radians(self.theta1), radians(self.theta2) - pi/2, radians(self.theta3)]
        theta1, theta2, theta3 = angles

        Xa = self.COXA * cos(theta1)
        Ya = self.COXA * sin(theta1)
        G2 = sin(theta2) * self.FEMUR
        P1 = cos(theta2) * self.FEMUR
        Xc = cos(theta1) * P1
        Yc = sin(theta1) * P1

        H = sqrt(self.FEMUR**2 + self.TIBIA**2 - 2*self.FEMUR*self.TIBIA*cos(radians(180) - theta3))
        phi1 = self.cos_rule(self.FEMUR, H, self.TIBIA)
        phi2 = self.cos_rule(self.TIBIA, H, self.FEMUR)
        phi3 = phi1 - theta2
        Pp = cos(phi3) * H
        P2 = Pp - P1
        Yb = sin(theta1) * Pp
        Xb = cos(theta1) * Pp
        G1 = sin(phi3) * H * -1

        jointLocation = [
            [0,     0,      0], # initial joint
            [Xa,    Ya,     0], # COXA-FEMUR joint
            [Xa+Xc, Ya+Yc,  G2],# FEMUR-TIBIA joint
            [Xa+Xb, Ya+Yb,  G1] # tip of the leg
        ]

        self.joints = jointLocation
        return jointLocation
    
if __name__ == '__main__' :
    # Initialize a spider leg with given name and segment lengths
    leg = SpiderLeg("Leg1", COXA=43.8, FEMUR=166, TIBIA=88) #mm

    # Set the joint angles (in degrees) for the leg
    leg.set_angles([0, 45, 70])

    # Get the current joint angles
    currentAngles = leg.get_angles()

    # Get the current target position (x, y, z) of the leg tip
    currentTarget = leg.get_target()
    #Define the new tar4get
    newTarget = [100, 100, 0]
    # Calculate the joint angles required to reach a new target position using inverse kinematics
    new_angles = leg.inverseKinematics(target=newTarget)

    # Calculate the joint positions based on the joint angles using forward kinematics
    # We do this to confirm that calculated angles are the ones required to reach the new target
    joint_positions = leg.forwardKinematics()

    # Print results
    print("Current Joint Angles:", currentAngles)
    print("Current Target Position:", currentTarget)
    print("New Joint Angles:", new_angles)
    print("New Joint Positions:", joint_positions)
    print("Desired Target",newTarget,"Forward kinematics test", joint_positions[3])
    print("Values in above arrays should be very close to each other")

