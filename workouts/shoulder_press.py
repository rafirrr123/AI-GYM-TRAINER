import cv2
import mediapipe as mp
from utils import get_angle

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

class ShoulderPressDetector:
    def __init__(self):
        self.pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.counter = 0
        self.stage = "down"
        self.feedback = "Bring weights to shoulder level"

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

            # Left Arm: Shoulder (11), Elbow (13), Wrist (15)
            l_shoulder = [lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
            l_elbow = [lm[mp_pose.PoseLandmark.LEFT_ELBOW.value].x, lm[mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
            l_wrist = [lm[mp_pose.PoseLandmark.LEFT_WRIST.value].x, lm[mp_pose.PoseLandmark.LEFT_WRIST.value].y]

            # Right Arm: Shoulder (12), Elbow (14), Wrist (16)
            r_shoulder = [lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x, lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
            r_elbow = [lm[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x, lm[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]
            r_wrist = [lm[mp_pose.PoseLandmark.RIGHT_WRIST.value].x, lm[mp_pose.PoseLandmark.RIGHT_WRIST.value].y]

            # Middle parameter must be the joint bending (elbow)
            l_angle = get_angle(l_shoulder, l_elbow, l_wrist)
            r_angle = get_angle(r_shoulder, r_elbow, r_wrist)
            avg_angle = (l_angle + r_angle) / 2.0

            if avg_angle > 155:
                if self.stage == "down":
                    self.counter += 1
                    self.feedback = "Solid press! Lower with control"
                self.stage = "up"
            elif avg_angle < 95:
                if self.stage == "up":
                    self.stage = "down"
                    self.feedback = "Press directly overhead!"

            mp_drawing.draw_landmarks(
                frame,
                res.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(0, 255, 136), thickness=2, circle_radius=2),
                mp_drawing.DrawingSpec(color=(186, 104, 200), thickness=2, circle_radius=2)
            )

            cv2.putText(frame, f"{int(avg_angle)} deg", 
                        (int(l_elbow[0] * w), int(l_elbow[1] * h)), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        return frame, self.counter, self.stage, self.feedback