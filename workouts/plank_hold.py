import time
import cv2
import mediapipe as mp
from utils import get_angle

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

class PlankHoldDetector:
    def __init__(self):
        self.pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.hold_seconds = 0
        self.last_tick = time.time()
        self.stage = "plank"
        self.feedback = "Hold plank with straight back"

    def reset(self):
        self.hold_seconds = 0
        self.last_tick = time.time()
        self.stage = "plank"
        self.feedback = "Timer reset"

    def process(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        res = self.pose.process(rgb)
        rgb.flags.writeable = True

        h, w, _ = frame.shape
        now = time.time()

        if res.pose_landmarks:
            lm = res.pose_landmarks.landmark

            l_shoulder = [lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
            l_hip = [lm[mp_pose.PoseLandmark.LEFT_HIP.value].x, lm[mp_pose.PoseLandmark.LEFT_HIP.value].y]
            l_ankle = [lm[mp_pose.PoseLandmark.LEFT_ANKLE.value].x, lm[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]

            body_angle = get_angle(l_shoulder, l_hip, l_ankle)

            # Valid plank range
            if 155 <= body_angle <= 180:
                self.stage = "holding"
                self.feedback = "Good form! Keep holding"
                if now - self.last_tick >= 1.0:
                    self.hold_seconds += int(now - self.last_tick)
                    self.last_tick = now
            else:
                self.stage = "paused"
                self.last_tick = now
                if body_angle < 155:
                    self.feedback = "Hips sagging! Raise your core"
                else:
                    self.feedback = "Hips too high! Lower to a straight line"

            mp_drawing.draw_landmarks(frame, res.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            cv2.putText(frame, f"Angle: {int(body_angle)} deg", 
                        (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 136), 2)
        else:
            self.last_tick = now

        return frame, self.hold_seconds, self.stage, self.feedback