import cv2
import mediapipe as mp

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

class HighKneesDetector:
    def __init__(self):
        self.pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.counter = 0
        self.stage = "down"
        self.feedback = "Drive knees up high!"

    def reset(self):
        self.counter = 0
        self.stage = "down"
        self.feedback = "Counter reset"

    def process(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        res = self.pose.process(rgb)
        rgb.flags.writeable = True

        if res.pose_landmarks:
            lm = res.pose_landmarks.landmark

            l_hip_y = lm[mp_pose.PoseLandmark.LEFT_HIP.value].y
            r_hip_y = lm[mp_pose.PoseLandmark.RIGHT_HIP.value].y
            l_knee_y = lm[mp_pose.PoseLandmark.LEFT_KNEE.value].y
            r_knee_y = lm[mp_pose.PoseLandmark.RIGHT_KNEE.value].y

            # Check if either knee reaches hip height
            knee_raised = (l_knee_y <= l_hip_y) or (r_knee_y <= r_hip_y)

            if knee_raised and self.stage == "down":
                self.counter += 1
                self.stage = "up"
                self.feedback = "Keep the pace up!"
            elif not knee_raised and (l_knee_y > l_hip_y + 0.1) and (r_knee_y > r_hip_y + 0.1):
                self.stage = "down"

            mp_drawing.draw_landmarks(frame, res.pose_landmarks, mp_pose.POSE_CONNECTIONS)

        return frame, self.counter, self.stage, self.feedback