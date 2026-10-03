import cv2
import numpy as np
import mediapipe as mp
from utils import get_angle  # uses your get_angle function

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

class PushupDetector:
    def __init__(self):
        self.pose = mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.counter = 0
        self.stage = "up"
        self.feedback = "Get into plank position"

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

            # Left side landmarks
            left_shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                             landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
            left_elbow = [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x,
                          landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
            left_wrist = [landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x,
                          landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y]
            left_hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x,
                        landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]
            left_knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x,
                         landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y]

            # Right side landmarks
            right_shoulder = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x,
                              landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
            right_elbow = [landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x,
                           landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]
            right_wrist = [landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].x,
                           landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].y]
            right_hip = [landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x,
                         landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y]
            right_knee = [landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].x,
                          landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].y]

            # Calculate arm flexion angles
            left_arm_angle = get_angle(left_shoulder, left_elbow, left_wrist)
            right_arm_angle = get_angle(right_shoulder, right_elbow, right_wrist)
            avg_arm_angle = (left_arm_angle + right_arm_angle) / 2.0

            # Calculate body posture (hip angle)
            left_body_angle = get_angle(left_shoulder, left_hip, left_knee)
            right_body_angle = get_angle(right_shoulder, right_hip, right_knee)
            avg_body_angle = (left_body_angle + right_body_angle) / 2.0

            # Form feedback: Check if back is straight
            if avg_body_angle < 140:
                self.feedback = "Keep your hips straight!"
            else:
                # State logic for push-up rep
                if avg_arm_angle > 160:
                    if self.stage == "down":
                        self.counter += 1
                        self.feedback = "Solid rep!"
                    self.stage = "up"
                elif avg_arm_angle <= 90:
                    if self.stage == "up":
                        self.stage = "down"
                        self.feedback = "Push straight up!"
                elif 90 < avg_arm_angle < 160 and self.stage == "down":
                    self.feedback = "Lock out at the top"

            # Draw pose skeleton
            mp_drawing.draw_landmarks(
                frame,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(0, 255, 136), thickness=2, circle_radius=2),
                mp_drawing.DrawingSpec(color=(255, 187, 0), thickness=2, circle_radius=2)
            )

            # Display arm angle overlay
            elbow_px = (int(left_elbow[0] * w), int(left_elbow[1] * h))
            cv2.putText(frame, f"{int(avg_arm_angle)} deg", 
                        elbow_px, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        return frame, self.counter, self.stage, self.feedback