import cv2
import mediapipe as mp
from utils import get_angle

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

class LungeDetector:
    def __init__(self):
        self.pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.counter = 0
        self.stage = "up"
        self.feedback = "Stand straight to start"

    def reset(self):
        self.counter = 0
        self.stage = "up"
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
            l_knee = [lm[mp_pose.PoseLandmark.LEFT_KNEE.value].x, lm[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
            l_ankle = [lm[mp_pose.PoseLandmark.LEFT_ANKLE.value].x, lm[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]

            r_hip = [lm[mp_pose.PoseLandmark.RIGHT_HIP.value].x, lm[mp_pose.PoseLandmark.RIGHT_HIP.value].y]
            r_knee = [lm[mp_pose.PoseLandmark.RIGHT_KNEE.value].x, lm[mp_pose.PoseLandmark.RIGHT_KNEE.value].y]
            r_ankle = [lm[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x, lm[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y]

            l_angle = get_angle(l_hip, l_knee, l_ankle)
            r_angle = get_angle(r_hip, r_knee, r_ankle)
            
            # The bent lead knee has the smaller angle
            lead_knee_angle = min(l_angle, r_angle)

            if lead_knee_angle <= 95:
                if self.stage == "up":
                    self.stage = "down"
                    self.feedback = "Push back up to standing"
            elif lead_knee_angle > 160:
                if self.stage == "down":
                    self.counter += 1
                    self.feedback = "Great rep!"
                self.stage = "up"

            mp_drawing.draw_landmarks(frame, res.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            cv2.putText(frame, f"Knee: {int(lead_knee_angle)} deg", 
                        (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 208, 255), 2)

        return frame, self.counter, self.stage, self.feedback