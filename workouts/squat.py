import sys
import os
import cv2
import mediapipe as mp

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import get_angle

import cv2
import numpy as np
import mediapipe as mp
from utils import get_angle

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

class SquatDetector:
    def __init__(self):
        self.pose = mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.counter = 0
        self.stage = "up"
        self.feedback = "Stand straight to begin"

    def reset(self):
        self.counter = 0
        self.stage = "up"
        self.feedback = "Counter reset"

    def process(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_frame.flags.writeable = False
        results = self.pose.process(rgb_frame)
        rgb_frame.flags.writeable = True

        h, w, _ = frame.shape

        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark

            # Left leg: Hip (23), Knee (25), Ankle (27)
            left_hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x,
                        landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]
            left_knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x,
                         landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
            left_ankle = [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x,
                          landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]

            # Right leg: Hip (24), Knee (26), Ankle (28)
            right_hip = [landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x,
                         landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y]
            right_knee = [landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].x,
                          landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].y]
            right_ankle = [landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x,
                           landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y]

            # Calculate knee angles using get_angle
            left_knee_angle = get_angle(left_hip, left_knee, left_ankle)
            right_knee_angle = get_angle(right_hip, right_knee, right_ankle)

            avg_knee_angle = (left_knee_angle + right_knee_angle) / 2.0

            # State Logic
            if avg_knee_angle > 165:
                if self.stage == "down":
                    self.counter += 1
                    self.feedback = "Good rep!"
                self.stage = "up"

            elif avg_knee_angle <= 90:
                if self.stage == "up":
                    self.stage = "down"
                    self.feedback = "Drive up through heels!"
            elif 90 < avg_knee_angle < 165 and self.stage == "down":
                self.feedback = "Rise up completely"

            # Draw pose skeleton
            mp_drawing.draw_landmarks(
                frame,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(0, 255, 136), thickness=2, circle_radius=2),
                mp_drawing.DrawingSpec(color=(0, 208, 255), thickness=2, circle_radius=2)
            )

            knee_px = (int(left_knee[0] * w), int(left_knee[1] * h))
            cv2.putText(frame, f"{int(avg_knee_angle)} deg", 
                        knee_px, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        return frame, self.counter, self.stage, self.feedback