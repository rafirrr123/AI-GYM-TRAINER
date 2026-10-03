import cv2
import mediapipe as mp
import numpy as np

class BicepCurlDetector:
    def __init__(self):
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

        # Left arm states
        self.left_counter = 0
        self.left_stage = "down"

        # Right arm states
        self.right_counter = 0
        self.right_stage = "down"

    def reset(self):
        self.left_counter = 0
        self.left_stage = "down"
        self.right_counter = 0
        self.right_stage = "down"

    def calculate_angle(self, a, b, c):
        a = np.array(a)  # Shoulder
        b = np.array(b)  # Elbow
        c = np.array(c)  # Wrist

        radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
        angle = np.abs(radians * 180.0 / np.pi)

        if angle > 180.0:
            angle = 360.0 - angle

        return angle

    def process(self, frame):
        h, w, _ = frame.shape

        # Convert to RGB for MediaPipe
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image_rgb.flags.writeable = False
        results = self.pose.process(image_rgb)
        image_rgb.flags.writeable = True

        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark

            try:
                # ----------------- LEFT ARM -----------------
                l_shoulder = [landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                              landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
                l_elbow = [landmarks[self.mp_pose.PoseLandmark.LEFT_ELBOW.value].x,
                           landmarks[self.mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
                l_wrist = [landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST.value].x,
                           landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST.value].y]

                left_angle = self.calculate_angle(l_shoulder, l_elbow, l_wrist)

                # Rep transition logic
                if left_angle > 160:
                    self.left_stage = "down"
                if left_angle < 35 and self.left_stage == "down":
                    self.left_stage = "up"
                    self.left_counter += 1

                # Draw angle at left elbow
                cv2.putText(frame, f"{int(left_angle)} deg", 
                            (int(l_elbow[0] * w), int(l_elbow[1] * h)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 136), 2, cv2.LINE_AA)

                # ----------------- RIGHT ARM -----------------
                r_shoulder = [landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x,
                              landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
                r_elbow = [landmarks[self.mp_pose.PoseLandmark.RIGHT_ELBOW.value].x,
                           landmarks[self.mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]
                r_wrist = [landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST.value].x,
                           landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST.value].y]

                right_angle = self.calculate_angle(r_shoulder, r_elbow, r_wrist)

                # Rep transition logic
                if right_angle > 160:
                    self.right_stage = "down"
                if right_angle < 35 and self.right_stage == "down":
                    self.right_stage = "up"
                    self.right_counter += 1

                # Draw angle at right elbow
                cv2.putText(frame, f"{int(right_angle)} deg", 
                            (int(r_elbow[0] * w), int(r_elbow[1] * h)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2, cv2.LINE_AA)

            except Exception:
                pass

            # Draw pose landmarks and skeleton
            self.mp_drawing.draw_landmarks(
                frame,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                self.mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=2),
                self.mp_drawing.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2)
            )

        # Returns all 5 variables so app.py receives both arm counters
        return frame, self.left_counter, self.left_stage, self.right_counter, self.right_stage