import cv2
import mediapipe as mp
from utils import get_angle

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

class SideBendDetector:
    def __init__(self):
        self.pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.counter = 0
        self.stage = "center"
        self.feedback = "Stand tall, hands at your sides"

    def reset(self):
        self.counter = 0
        self.stage = "center"
        self.feedback = "Counter reset"

    def process(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        res = self.pose.process(rgb)
        rgb.flags.writeable = True

        h, w, _ = frame.shape

        if res.pose_landmarks:
            lm = res.pose_landmarks.landmark

            l_shoulder = [lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
            l_hip = [lm[mp_pose.PoseLandmark.LEFT_HIP.value].x, lm[mp_pose.PoseLandmark.LEFT_HIP.value].y]
            l_knee = [lm[mp_pose.PoseLandmark.LEFT_KNEE.value].x, lm[mp_pose.PoseLandmark.LEFT_KNEE.value].y]

            r_shoulder = [lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x, lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
            r_hip = [lm[mp_pose.PoseLandmark.RIGHT_HIP.value].x, lm[mp_pose.PoseLandmark.RIGHT_HIP.value].y]
            r_knee = [lm[mp_pose.PoseLandmark.RIGHT_KNEE.value].x, lm[mp_pose.PoseLandmark.RIGHT_KNEE.value].y]

            l_torso_angle = get_angle(l_shoulder, l_hip, l_knee)
            r_torso_angle = get_angle(r_shoulder, r_hip, r_knee)
            min_bend = min(l_torso_angle, r_torso_angle)

            if min_bend <= 145 and self.stage == "center":
                self.stage = "bent"
                self.counter += 1
                self.feedback = "Good stretch! Return to center"
            elif min_bend > 165 and self.stage == "bent":
                self.stage = "center"
                self.feedback = "Bend toward the other side"

            mp_drawing.draw_landmarks(frame, res.pose_landmarks, mp_pose.POSE_CONNECTIONS)

        return frame, self.counter, self.stage, self.feedback