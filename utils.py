import numpy as np

def get_angle(a, b, c):

    p_a = [a.x, a.y] if hasattr(a, 'x') else a
    p_b = [b.x, b.y] if hasattr(b, 'x') else b
    p_c = [c.x, c.y] if hasattr(c, 'x') else c

    radians = np.arctan2(p_c[1] - p_b[1], p_c[0] - p_b[0]) - np.arctan2(p_a[1] - p_b[1], p_a[0] - p_b[0])
    angle = np.abs(np.degrees(radians))

    if angle > 180.0:
        angle = 360.0 - angle

    return float(angle)