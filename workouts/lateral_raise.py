import cv2
import mediapipe as mp
from utils import get_angle

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

class LateralRaiseDetector:
    def __init__(self):
        self.pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.counter = 0
        self.stage = "down"
        self.feedback = "Stand straight, arms at your sides"

    def reset(self):
        self.counter = 0
        self.stage = "down"
        self.feedback = "Counter reset"

    def process(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        res = self.pose.process(rgb)
        rgb.flags.writeable = True

        h, w, _ = frame.shape

        if res.pose_landmarks:
            lm = res.pose_landmarks.landmark

            l_hip = [lm[mp_pose.PoseLandmark.LEFT_HIP.value].x, lm[mp_pose.PoseLandmark.LEFT_HIP.value].y]
            l_shoulder = [lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
            l_elbow = [lm[mp_pose.PoseLandmark.LEFT_ELBOW.value].x, lm[mp_pose.PoseLandmark.LEFT_ELBOW.value].y]

            r_hip = [lm[mp_pose.PoseLandmark.RIGHT_HIP.value].x, lm[mp_pose.PoseLandmark.RIGHT_HIP.value].y]
            r_shoulder = [lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x, lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
            r_elbow = [lm[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x, lm[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]

            l_angle = get_angle(l_hip, l_shoulder, l_elbow)
            r_angle = get_angle(r_hip, r_shoulder, r_elbow)
            avg_angle = (l_angle + r_angle) / 2.0

            if avg_angle >= 85:
                if self.stage == "down":
                    self.counter += 1
                    self.feedback = "Good lift! Lower slowly"
                self.stage = "up"
            elif avg_angle < 30:
                self.stage = "down"
                self.feedback = "Raise arms up to shoulder level"

            mp_drawing.draw_landmarks(frame, res.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            cv2.putText(frame, f"{int(avg_angle)} deg", 
                        (int(l_shoulder[0] * w), int(l_shoulder[1] * h)), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 136), 2)

        return frame, self.counter, self.stage, self.feedback