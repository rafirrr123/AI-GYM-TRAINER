from gevent import monkey
monkey.patch_all()

import base64
import cv2
import numpy as np
import gc
from datetime import date, timedelta
from flask import Flask, jsonify, request, render_template, url_for, redirect, session
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector

from database_connection import get_db_connection

# --- App Configuration ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'aigym_super_secret_key_2026'

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="gevent")

# ----------------- LAZY DETECTOR REGISTRY -----------------
# Map exercise keys to module paths and class names so nothing loads on boot
DETECTOR_REGISTRY = {
    "bicep_curls": {"module": "workouts.bisup_curl", "class": "BicepCurlDetector", "title": "Bicep Curls", "type": "dual"},
    "squats": {"module": "workouts.squat", "class": "SquatDetector", "title": "Squats", "type": "single"},
    "pushups": {"module": "workouts.pushup", "class": "PushupDetector", "title": "Push-ups", "type": "single"},
    "shoulder_press": {"module": "workouts.shoulder_press", "class": "ShoulderPressDetector", "title": "Shoulder Press", "type": "single"},
    "jumping_jacks": {"module": "workouts.jumping_jacks", "class": "JumpingJackDetector", "title": "Jumping Jacks", "type": "single"},
    "lateral_raises": {"module": "workouts.lateral_raise", "class": "LateralRaiseDetector", "title": "Lateral Raises", "type": "single"},
    "lunges": {"module": "workouts.lunges", "class": "LungeDetector", "title": "Lunges", "type": "single"},
    "high_knees": {"module": "workouts.high_knees", "class": "HighKneesDetector", "title": "High Knees", "type": "single"},
    "side_bends": {"module": "workouts.side_bends", "class": "SideBendDetector", "title": "Side Bends", "type": "single"},
    "plank_hold": {"module": "workouts.plank_hold", "class": "PlankHoldDetector", "title": "Plank Hold", "type": "single"},
}

# Single active instance tracker
active_detector = None
active_exercise_key = None

def get_or_switch_detector(exercise_key):
    """Ensures ONLY ONE detector exists in memory at any time."""
    global active_detector, active_exercise_key

    if active_exercise_key == exercise_key and active_detector is not None:
        return active_detector

    # Clean up and release the previous detector
    if active_detector is not None:
        if hasattr(active_detector, 'close'):
            active_detector.close()
        del active_detector
        active_detector = None
        gc.collect()

    config = DETECTOR_REGISTRY.get(exercise_key)
    if not config:
        return None

    # Dynamically import and instantiate ONLY the requested model
    import importlib
    mod = importlib.import_module(config["module"])
    detector_class = getattr(mod, config["class"])
    
    active_detector = detector_class()
    active_exercise_key = exercise_key
    gc.collect()
    return active_detector

# ----------------- AUTHENTICATION ROUTES -----------------

@app.route("/")
def main():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template("login.html")

@app.route("/login", methods=["GET"])
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template("login.html")

@app.route("/loging", methods=["POST"])
def loging():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        return render_template("login.html", error="Please enter both username and password")

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, username, password_hash FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for("home"))
        else:
            return render_template("login.html", error="Invalid username or password")
    except mysql.connector.Error as err:
        return render_template("login.html", error=f"Database error: {err}")

@app.route("/signup", methods=["GET"])
def signup():
    return render_template("signup.html")

@app.route("/signing", methods=["POST"])
def signing():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        return render_template("signup.html", error="Fields cannot be empty")

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return render_template("signup.html", error="Username already exists. Please pick another.")

        hashed_pw = generate_password_hash(password)
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, hashed_pw))
        conn.commit()

        cursor.close()
        conn.close()
        return redirect(url_for("tutorial"))
    except mysql.connector.Error as err:
        return render_template("signup.html", error=f"Database error: {err}")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

# ----------------- APP PAGES -----------------

@app.route("/tutorial")
def tutorial():
    return render_template("tutorial.html")

@app.route("/home")
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    username = session.get('username', 'Athlete')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT COALESCE(SUM(total_reps), 0) AS lifetime_reps
        FROM workout_history
        WHERE user_id = %s
    """, (user_id,))
    lifetime_reps = cursor.fetchone()['lifetime_reps']

    cursor.execute("""
        SELECT DISTINCT DATE(completed_at) AS workout_date
        FROM workout_history
        WHERE user_id = %s
        ORDER BY workout_date DESC
    """, (user_id,))
    date_rows = cursor.fetchall()

    total_active_days = len(date_rows)

    streak = 0
    if date_rows:
        today = date.today()
        yesterday = today - timedelta(days=1)
        latest_date = date_rows[0]['workout_date']

        if latest_date in (today, yesterday):
            expected = latest_date
            for row in date_rows:
                if row['workout_date'] == expected:
                    streak += 1
                    expected -= timedelta(days=1)
                else:
                    break

    cursor.execute("""
        SELECT exercise_name, left_reps, right_reps, total_reps, completed_at
        FROM workout_history
        WHERE user_id = %s
        ORDER BY completed_at DESC
        LIMIT 6
    """, (user_id,))
    recent_workouts = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "home.html",
        username=username,
        streak=streak,
        total_active_days=total_active_days,
        lifetime_reps=lifetime_reps,
        workouts=recent_workouts
    )

@app.route("/home/easy")
def easy():
    return render_template("easy.html")

@app.route("/home/medium")
def medium():
    return render_template("medium.html")

@app.route("/home/hard")
def hard():
    return render_template("hard.html")

@app.route("/home/exercises")
def exercises():
    return render_template("exercises.html")

# ----------------- LEGACY EXERCISE PAGES -----------------

@app.route('/bicepcurl')
def bicepcurl():
    return redirect(url_for('workout_session', exercise_key='bicep_curls'))

@app.route('/squat')
def squat():
    return redirect(url_for('workout_session', exercise_key='squats'))

@app.route('/pushup')
def pushup():
    return redirect(url_for('workout_session', exercise_key='pushups'))

# ----------------- WORKOUT SAVE ENDPOINT -----------------

@app.route("/save_workout", methods=["POST"])
def save_workout():
    if 'user_id' not in session:
        return jsonify({"status": "unauthorized"}), 401

    data = request.get_json() or {}
    exercise = data.get('exercise', 'Bicep Curls')
    l_cnt = int(data.get('l_cnt', 0))
    r_cnt = int(data.get('r_cnt', 0))

    if exercise in ['Bicep Curls', 'bicep_curls']:
        final_reps = min(l_cnt, r_cnt)
    else:
        final_reps = int(data.get('total_reps', max(l_cnt, r_cnt)))

    if final_reps > 0:
        user_id = session['user_id']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, left_reps, right_reps, total_reps 
            FROM workout_history 
            WHERE user_id = %s 
              AND exercise_name = %s 
              AND DATE(completed_at) = CURDATE()
            LIMIT 1
        """, (user_id, exercise))
        existing_row = cursor.fetchone()

        if existing_row:
            cursor.execute("""
                UPDATE workout_history 
                SET left_reps = left_reps + %s,
                    right_reps = right_reps + %s,
                    total_reps = total_reps + %s,
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (l_cnt, r_cnt, final_reps, existing_row['id']))
        else:
            cursor.execute("""
                INSERT INTO workout_history (user_id, exercise_name, left_reps, right_reps, total_reps)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, exercise, l_cnt, r_cnt, final_reps))

        conn.commit()
        cursor.close()
        conn.close()

    return jsonify({"status": "saved", "paired_reps": final_reps})

# ----------------- UNIFIED WORKOUT PLAYER -----------------

@app.route("/workout/<exercise_key>")
def workout_session(exercise_key):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    config = DETECTOR_REGISTRY.get(exercise_key)
    if not config:
        return redirect(url_for('exercises'))

    return render_template(
        "workout_player.html",
        exercise_key=exercise_key,
        title=config["title"],
        mode=config["type"]
    )

@socketio.on('process_frame')
def handle_generic_frame(data):
    if not data or 'image' not in data or 'exercise_key' not in data:
        print("⚠️ Malformed frame packet")
        return

    exercise_key = data['exercise_key']
    config = DETECTOR_REGISTRY.get(exercise_key)
    if not config:
        print(f"⚠️ Unknown exercise key: {exercise_key}")
        return

    detector = get_or_switch_detector(exercise_key)
    if detector is None:
        print(f"❌ Could not load detector: {exercise_key}")
        return

    try:
        _, encoded = data['image'].split(',', 1)
        img_bytes = base64.b64decode(encoded)
        frame = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)

        if frame is None:
            print("⚠️ Failed cv2.imdecode")
            return

        if config["type"] == "dual":
            frame, l_cnt, l_stg, r_cnt, r_stg = detector.process(frame)
            count = min(l_cnt, r_cnt)
            stage = f"L: {l_stg} | R: {r_stg}"
            feedback = f"Left: {l_cnt} | Right: {r_cnt}"
        else:
            frame, count, stage, feedback = detector.process(frame)

        _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 40])
        img_base64 = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"

        emit('frame_result', {
            'image': img_base64,
            'count': count,
            'stage': str(stage).upper(),
            'feedback': feedback
        })
        print(f"✅ Success: Frame emitted for {exercise_key}")

    except Exception as e:
        print(f"❌ Exception in process_frame for {exercise_key}: {e}")
        import traceback
        traceback.print_exc()

@socketio.on('reset_active_workout')
def handle_generic_reset(data):
    exercise_key = data.get('exercise_key')
    global active_detector, active_exercise_key
    if active_exercise_key == exercise_key and active_detector is not None:
        active_detector.reset()
        emit('workout_reset', {'count': 0, 'stage': 'RESET', 'feedback': 'Ready'})

# ----------------- BACKWARD-COMPATIBLE WEBSOCKETS -----------------

@socketio.on('video_frame')
def handle_frame(data):
    if not data or ',' not in data:
        return
    detector = get_or_switch_detector('bicep_curls')
    try:
        _, encoded = data.split(',', 1)
        img_bytes = base64.b64decode(encoded)
        frame = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            return
        frame, l_cnt, l_stg, r_cnt, r_stg = detector.process(frame)
        _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
        emit('response_frame', {
            'image': f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}",
            'l_cnt': l_cnt,
            'l_stg': l_stg,
            'r_cnt': r_cnt,
            'r_stg': r_stg
        })
    except Exception as e:
        print("Bicep frame error:", e)

@socketio.on('reset_counter')
def handle_reset():
    detector = get_or_switch_detector('bicep_curls')
    if detector:
        detector.reset()
    emit('counter_reset', {'l_cnt': 0, 'l_stg': 'down', 'r_cnt': 0, 'r_stg': 'down'})

@socketio.on('squat_frame')
def handle_squat_frame(data):
    if not data or ',' not in data:
        return
    detector = get_or_switch_detector('squats')
    try:
        _, encoded = data.split(',', 1)
        img_bytes = base64.b64decode(encoded)
        frame = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            return
        frame, count, stage, feedback = detector.process(frame)
        _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
        emit('squat_response', {
            'image': f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}",
            'count': count,
            'stage': stage,
            'feedback': feedback
        })
    except Exception as e:
        print("Squat frame error:", e)

@socketio.on('reset_squat')
def handle_squat_reset():
    detector = get_or_switch_detector('squats')
    if detector:
        detector.reset()
    emit('squat_reset', {'count': 0, 'stage': 'up', 'feedback': 'Counter reset'})

@socketio.on('pushup_frame')
def handle_pushup_frame(data):
    if not data or ',' not in data:
        return
    detector = get_or_switch_detector('pushups')
    try:
        _, encoded = data.split(',', 1)
        img_bytes = base64.b64decode(encoded)
        frame = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            return
        frame, count, stage, feedback = detector.process(frame)
        _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
        emit('pushup_response', {
            'image': f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}",
            'count': count,
            'stage': stage,
            'feedback': feedback
        })
    except Exception as e:
        print("Pushup frame error:", e)

@socketio.on('reset_pushup')
def handle_pushup_reset():
    detector = get_or_switch_detector('pushups')
    if detector:
        detector.reset()
    emit('pushup_reset', {'count': 0, 'stage': 'up', 'feedback': 'Counter reset'})

# ----------------- RUN SERVER -----------------

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)