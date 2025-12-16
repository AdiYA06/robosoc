class Tripot_gait:
    def __init__(self):
        pass

    def bezier_curve(self, p1, p2, p3, t):
        y = (1 - t)**2 * (p1[0]) + 2 * (1-t)*t*(p2[0]) + t**2 * (p3[0])
        z = (1 - t)**2 * (p1[1]) + 2 * (1-t)*t*(p2[1]) + t**2 * (p3[1])
        return y,z