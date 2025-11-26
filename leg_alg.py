from math import *
from machine import Pin, PWM
import time
class SpiderLeg:
    def __init__(self, name, COXA, FEMUR, TIBIA):
        #spider leg => COXA-FEMUR-TIBIA
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
        angles = self.normalize_angles(angles)
        self.theta1, self.theta2, self.theta3 = angles
        return self.get_angles()
    
    def get_angles(self):
        return [self.theta1, self.theta2, self.theta3]

    def normalize_angles(self, angles):
        '''
            Normalize joint angles to be in the range [-180, 180] degrees.
            Args:
                angles(list): a list of joint angles in degrees.
            
            Returns:
                list: a list of normalized joint angles in degrees.
        '''
        for idx, ang in enumerate(angles):
            angles[idx] = ((ang + 180) % 360) -180
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
        x, y, z = target[0], target[1], target[2]
        
        theta1 = atan( y / x )
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
            angles = [radians(self.theta1), radians(self.theta2), radians(self.theta3)]
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
    
class Connection:
    def __init__(self, pin_list):
        self.servos = [self.make_servo(p) for p in pin_list]

    def make_servo(self, pin_num):
        pwm = PWM(Pin(pin_num))
        pwm.freq(50)          # standard 50 Hz
        return pwm
        
    
    
if __name__ == '__main__' :
    leg = SpiderLeg("Leg1", 43.8, 166, 88) # mm
    leg.set_angles([0,45,70])

    current_angle = leg.get_angles()

    current_target = leg.get_target()

    newTarget = [100,100, 0]

    new_angles = leg.inverseKinematics(target=newTarget)

    joint_positions = leg.forwardKinematics()
    print(joint_positions)

