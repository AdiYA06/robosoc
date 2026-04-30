from math import acos, asin, atan2, cos, degrees, pi, radians, sin, sqrt
try:
    import servo_control
    is_simulate = False
except ImportError:
    print("servo_control module not found. Running in simulation mode.")
    is_simulate = True


SERVO_OFFSETS = (90, 90, 0)


class SpiderLeg:
    def __init__(self, name, COXA, FEMUR, TIBIA, pin_list = None):
        """
            Initialize a spider leg with given name and segment lengths.
            Args:
                name (str): Name of the leg.
                COXA (float): Length of the Coxa segment.
                FEMUR (float): Length of the Femur segment.
                TIBIA (float): Length of the Tibia segment.
                pin_list (list | None): Servo GPIO pins. Use None for a virtual/disconnected leg.
            """
        # Spider leg: COXA -> FEMUR -> TIBIA.
        self.control = None
        if not is_simulate and pin_list is not None:
            self.control = servo_control.servo_movement(pin_list)
        self.name = name
        self.COXA = COXA
        self.FEMUR = FEMUR
        self.TIBIA = TIBIA
        self.theta1 = 90.
        self.theta2 = 160.
        self.theta3 = 130.
        self.joints = self.forwardKinematics()

    def clamp(self, x, min_val=-1.0, max_val=1.0):
        return max(min(x, max_val), min_val)

    def cos_rule(self, A, B, C):
        # Law of cosines with numerical safety
        value = (A**2 + B**2 - C**2) / (2 * A * B)
        value = self.clamp(value)
        return acos(value)
    
    def set_angles(self, angles, easing = 0, duration = 0.2, steps = 200):
        """
            Set the joint angles of the leg and move the servos accordingly.
            Args:
                angles (list): A list of joint angles in degrees [theta1, theta2, theta3].
            Returns:
                list: A list of the set joint angles in degrees.
        """
        target_angles = [
            angle + SERVO_OFFSETS[idx]
            for idx, angle in enumerate(angles)
        ]
        pre_angles = self.get_angles()
        
        servo_angles = self.normalize_angles(target_angles)
        self.theta1, self.theta2, self.theta3 = servo_angles
        if self.control is not None:
            if easing:
                self.control.turn_angles_eased(servo_angles, pre_angles, duration, steps)
            else:
                self.control.turn_angles(servo_angles)
        return self.get_angles()
    
    def get_angles(self):
        return [self.theta1, self.theta2, self.theta3]

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

    def inverseKinematics(self, target = None, easing = 0):
        """
            Calculate the joint angles required to reach a target position, and set_angle.
            Args:
                target(list of coordinate - xyz): a list of joint position in unit same as the length of legs.
            Return:
                list: a list of joint angles required to reach the position in degrees.
        """
        if target is None:
            target = self.joints[3]
        x, y, z = target[0], target[1], target[2]
        
        theta1 = atan2(y, x)
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
        ang1 = ang.copy()
        self.set_angles(ang, easing)
        self.forwardKinematics()
        return ang1
        
    def forwardKinematics(self, angles = None):
        """
            Calculate the joint positions (x, y, z) based on the given joint angles.
            Args:
                angles (list): A list of joint angles in degrees [theta1, theta2, theta3].
            Returns:
                list: A list of joint positions [[x0, y0, z0], [x1, y1, z1], [x2, y2, z2], [x3, y3, z3]].
        """
        if angles is None:
            angles = [radians(self.theta1), radians(self.theta2), radians(self.theta3)]
        theta1, theta2, theta3 = angles[0]-pi/2, angles[1]-pi/2, angles[2]

        Xa = self.COXA * cos(theta1)
        Ya = self.COXA * sin(theta1)
        G2 = sin(theta2) * self.FEMUR # vertical height of theta3
        P1 = cos(theta2) * self.FEMUR # horizontal distance of theta3
        Xc = cos(theta1) * P1
        Yc = sin(theta1) * P1

        H = sqrt(self.FEMUR**2 + self.TIBIA**2 - 2*self.FEMUR*self.TIBIA*cos(radians(180) - theta3))
        phi1 = self.cos_rule(self.FEMUR, H, self.TIBIA)
        phi2 = self.cos_rule(self.TIBIA, H, self.FEMUR)
        phi3 = phi1 - theta2
        P = cos(phi3) * H
        Yb = sin(theta1) * P
        Xb = cos(theta1) * P
        G1 = sin(phi3) * H * -1

        jointLocation = [
            [0,     0,      0], # initial joint
            [Xa,    Ya,     0], # COXA-FEMUR joint
            [Xa+Xc, Ya+Yc,  G2],# FEMUR-TIBIA joint
            [Xa+Xb, Ya+Yb,  G1] # tip of the leg
        ]

        self.joints = jointLocation
        return jointLocation
