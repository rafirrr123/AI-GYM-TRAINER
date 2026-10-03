import cv2
import mediapipe as mp

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

class JumpingJackDetector:
    def __init__(self):
        self.pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.counter = 0
        self.stage = "closed"
        self.feedback = "Step back so full body is visible"

    def reset(self):
        self.counter = 0
        self.stage = "closed"
        self.feedback = "Counter reset"

    def process(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        res = self.pose.process(rgb)
        rgb.flags.writeable = True

        if res.pose_landmarks:
            lm = res.pose_landmarks.landmark

            l_wrist = lm[mp_pose.PoseLandmark.LEFT_WRIST.value]
            r_wrist = lm[mp_pose.PoseLandmark.RIGHT_WRIST.value]
            l_shoulder = lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
            r_shoulder = lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
            l_ankle = lm[mp_pose.PoseLandmark.LEFT_ANKLE.value]
            r_ankle = lm[mp_pose.PoseLandmark.RIGHT_ANKLE.value]

            # In screen coordinates, y=0 is TOP of frame (so y < shoulder_y means hands are ABOVE shoulders)
            hands_overhead = (l_wrist.y < l_shoulder.y) and (r_wrist.y < r_shoulder.y)
            feet_spread = abs(l_ankle.x - r_ankle.x) > (abs(l_shoulder.x - r_shoulder.x) * 1.3)

            if hands_overhead and feet_spread:
                if self.stage == "closed":
                    self.counter += 1
                    self.stage = "open"
                    self.feedback = "Keep the rhythm!"
            elif (not hands_overhead) and (not feet_spread):
                self.stage = "closed"
                self.feedback = "Jump and spread arms wide"

            mp_drawing.draw_landmarks(
                frame,
                res.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(0, 255, 136), thickness=2, circle_radius=2),
                mp_drawing.DrawingSpec(color=(255, 112, 67), thickness=2, circle_radius=2)
            )

        return frame, self.counter, self.stage, self.feedback