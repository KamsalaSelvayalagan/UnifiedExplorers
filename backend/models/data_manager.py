"""
data_manager.py
Handles ALL SQLite database operations for SmartARTrainer
"""

import sqlite3
from backend.models.db_config import get_db_connection, close_connection
import os
import base64
import hashlib
import hmac

# =====================================================
# PASSWORD HASHING (PBKDF2-SHA256)
# Store format: pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>
# =====================================================

_PBKDF2_ITERATIONS = 200_000

def hash_password(plain_password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 with a random 16-byte salt."""
    if plain_password is None:
        raise ValueError("Password cannot be None")
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS
    )
    return "pbkdf2_sha256$%d$%s$%s" % (
        _PBKDF2_ITERATIONS,
        base64.b64encode(salt).decode("utf-8"),
        base64.b64encode(dk).decode("utf-8"),
    )

def verify_password(plain_password: str, stored_value: str) -> bool:
    """
    Verify user-entered password against stored hash.
    Backward compatible: if stored_value is not in pbkdf2 format, treat it as plaintext.
    """
    if stored_value is None:
        return False

    # Legacy plaintext support (so older accounts still work)
    if not stored_value.startswith("pbkdf2_sha256$"):
        # constant-time compare
        return hmac.compare_digest(str(stored_value), str(plain_password))

    try:
        _algo, iter_str, salt_b64, hash_b64 = stored_value.split("$", 3)
        iterations = int(iter_str)
        salt = base64.b64decode(salt_b64.encode("utf-8"))
        expected = base64.b64decode(hash_b64.encode("utf-8"))
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt,
            iterations
        )
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


# =====================================================
# REGISTRATION & LOGIN
# =====================================================

def determine_plan_id(fitness_data):
    if not fitness_data or not fitness_data.get('workout_experience'):
        return 1

    experience = fitness_data.get('workout_experience', '').lower()

    if 'beginner' in experience or 'none' in experience:
        return 1
    elif 'intermediate' in experience or 'moderate' in experience:
        return 2
    elif 'advanced' in experience or 'expert' in experience:
        return 3
    return 1


def register_user(name, email, password, fitness_data=None):
    connection = get_db_connection()
    if not connection:
        return False, "Database connection failed", None

    cursor = None
    try:
        cursor = connection.cursor()
        password_hash = hash_password(password)

        if fitness_data:
            # Use ML model 
            try:
                from backend.ml.workout_plan_predictor import predict_plan
                plan_id, plan_label = predict_plan(fitness_data)  # plan_id 1..15, label "Beginner 3"
            except Exception as e:
                print("Model prediction failed, fallback to rule-based:", e)

                # Fallback to your old logic (1/2/3)
                plan_id = determine_plan_id(fitness_data)
                if plan_id == 1:
                    plan_label = "Beginner 1"
                elif plan_id == 2:
                    plan_label = "Intermediate 1"
                else:
                    plan_label = "Advanced 1"

            query = """
                INSERT INTO trainee (
                    name, email, pwd, dob, gender, height, weight,
                    workout_experience, workout_duration, weekly_frequency,
                    fitness_level, plan_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            params = (
                name, email, password_hash,
                fitness_data.get('dob'),
                fitness_data.get('gender'),
                fitness_data.get('height'),
                fitness_data.get('weight'),
                fitness_data.get('workout_experience'),
                fitness_data.get('workout_duration'),
                fitness_data.get('weekly_frequency'),
                plan_label,   
                plan_id       
            )

        else:
            # If no fitness data, default to Beginner 1
            query = """
                INSERT INTO trainee (name, email, pwd, fitness_level, plan_id)
                VALUES (?, ?, ?, ?, ?)
            """
            params = (name, email, password_hash, "Beginner 1", 1)

        cursor.execute(query, params)
        connection.commit()
        return True, "Registration successful", cursor.lastrowid

    except sqlite3.IntegrityError:
        return False, "Email already exists", None
    except sqlite3.Error as e:
        return False, f"Database error: {e}", None
    finally:
        close_connection(connection, cursor)


def login_user(email, password):
    connection = get_db_connection()
    if not connection:
        return False, "Database connection failed", None

    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT trainee_id, name, email, pwd FROM trainee WHERE email = ?",
            (email,)
        )
        row = cursor.fetchone()
        if not row:
            return False, "Invalid email or password", None

        stored_pwd = row["pwd"]
        if not verify_password(password, stored_pwd):
            return False, "Invalid email or password", None

        # Optional: auto-upgrade legacy plaintext passwords to hashed format on successful login
        if stored_pwd and not str(stored_pwd).startswith("pbkdf2_sha256$"):
            try:
                cursor.execute(
                    "UPDATE trainee SET pwd = ? WHERE trainee_id = ?",
                    (hash_password(password), row["trainee_id"])
                )
                connection.commit()
            except sqlite3.Error:
                pass

        user_data = {"trainee_id": row["trainee_id"], "name": row["name"], "email": row["email"]}
        return True, "Login successful", user_data
    finally:
        close_connection(connection, cursor)

def get_workout_by_id(workout_id):
    connection = get_db_connection()
    if not connection:
        return None

    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT workout_name, description
            FROM workout
            WHERE workout_id = ?
        """, (workout_id,))
        return cursor.fetchone()
    finally:
        close_connection(connection, cursor)


def get_all_workouts():
    connection = get_db_connection()
    if not connection:
        return []

    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT workout_id, workout_name, video_url, description
            FROM workout
            ORDER BY workout_id
        """)
        return cursor.fetchall()
    finally:
        close_connection(connection, cursor)

# =====================================================
# Workout & WORKOUT PLAN
# =====================================================

WORKOUT_COLUMNS = [
    "jumpingjack_crt",
    "pushup_crt",
    "plank_time",
    "crunches_crt",
    "squat_crt",
    "cobrastretch_time"
]


def get_trainee_info(trainee_id):
    connection = get_db_connection()
    if not connection:
        return None

    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT trainee_id, name, plan_id, fitness_level
            FROM trainee
            WHERE trainee_id = ?
        """, (trainee_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        close_connection(connection, cursor)




def get_workout_plan(plan_id):
    connection = get_db_connection()
    if not connection:
        return []

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM workout_plan WHERE plan_id = ?", (plan_id,))
        row = cursor.fetchone()
        if not row:
            return []

        return [
            {"workout_id": 1, "name": "Jumping Jacks", "target": row["jumpingjack_count"]},
            {"workout_id": 2, "name": "Push Ups", "target": row["pushup_count"]},
            {"workout_id": 3, "name": "Plank", "target": row["plank_time"]},
            {"workout_id": 4, "name": "Crunches", "target": row["crunches_count"]},
            {"workout_id": 5, "name": "Squats", "target": row["squat_count"]},
            {"workout_id": 6, "name": "Cobra Stretch", "target": row["cobra_stretch_time"]}
        ]

    finally:
        close_connection(connection, cursor)


# =====================================================
# WORKOUT SESSION
# =====================================================

def save_workout_session(trainee_id, session_data):
    connection = get_db_connection()
    if not connection:
        return False, "Database connection failed"

    try:
        cursor = connection.cursor()
        cols = ["trainee_id"] + WORKOUT_COLUMNS
        placeholders = ["?"] * len(cols)

        query = f"INSERT INTO workout_session ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
        params = [trainee_id] + [session_data.get(c, 0) for c in WORKOUT_COLUMNS]

        cursor.execute(query, params)
        connection.commit()
        return True, "Session saved"
    except sqlite3.Error as e:
        return False, str(e)
    finally:
        close_connection(connection, cursor)


def get_latest_session_status(trainee_id):
    connection = get_db_connection()
    if not connection:
        return None

    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT * FROM workout_session
            WHERE trainee_id = ?
            ORDER BY session_id DESC LIMIT 1
        """, (trainee_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        close_connection(connection, cursor)

# =====================================================
# PROFILE
# =====================================================

def get_trainee(trainee_id):
    connection = get_db_connection()
    if not connection:
        return None

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM trainee WHERE trainee_id = ?", (trainee_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        close_connection(connection, cursor)


def update_trainee(trainee_id, **kwargs):
    if not kwargs:
        return False, "No fields to update"

    connection = get_db_connection()
    if not connection:
        return False, "Database connection failed"

    try:
        cursor = connection.cursor()
        fields = [f"{k}=?" for k in kwargs]
        values = list(kwargs.values()) + [trainee_id]

        query = f"UPDATE trainee SET {', '.join(fields)} WHERE trainee_id = ?"
        cursor.execute(query, values)
        connection.commit()
        return True, "Profile updated"
    finally:
        close_connection(connection, cursor)
        
# =====================================================
# ANALYTICS (GLOBAL SHARED INSTANCE)
# =====================================================

class WorkoutSessionStats:
    def __init__(self, exercise_name, reps_completed, correct_reps, wrong_reps, duration):
        self.exercise_name = exercise_name
        self.reps_completed = reps_completed
        self.correct_reps = correct_reps
        self.wrong_reps = wrong_reps
        self.duration = duration


class SessionAnalytics:
    def __init__(self):
        self.sessions = []
        self.total_sessions = 0

    def load_sessions(self, trainee_id):
        connection = get_db_connection()
        if not connection:
            return

        try:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT * FROM workout_session
                WHERE trainee_id = ?
                ORDER BY session_id DESC
            """, (trainee_id,))
            rows = cursor.fetchall()

            self.sessions.clear()
            self.total_sessions = len(rows)

            for row in rows:
                exercises = [
                    ("Push-up", "pushup_crt", "pushup_wrg"),
                    ("Jumping Jack", "jumpingjack_crt", "jumpingjack_wrg"),
                    ("Squat", "squat_crt", "squat_wrg"),
                    ("Crunches", "crunches_crt", "crunches_wrg")
                ]

                for name, crt_col, wrg_col in exercises:
                    crt = row[crt_col] or 0
                    wrg = row[wrg_col] or 0
                    if crt or wrg:
                        self.sessions.append(
                            WorkoutSessionStats(
                                name, crt + wrg, crt, wrg, 0
                            )
                        )

                time_exercises = [
                    ("Plank", "plank_time"),
                    ("Cobra Stretch", "cobrastretch_time")
                ]

                for name, col in time_exercises:
                    t = row[col] or 0
                    if t:
                        self.sessions.append(
                            WorkoutSessionStats(name, 0, 0, 0, t)
                        )

        finally:
            close_connection(connection, cursor)


# ✅ THIS LINE FIXES YOUR ERROR
session_analytics = SessionAnalytics()
# =====================================================
# FORGOT PASSWORD (USED BY LoginScreen UI)
# =====================================================

def check_email_exists(email: str) -> bool:
    """Return True if the email exists in trainee table."""
    connection = get_db_connection()
    if not connection:
        return False

    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT 1 FROM trainee WHERE email = ? LIMIT 1", (email,))
        return cursor.fetchone() is not None
    except sqlite3.Error:
        return False
    finally:
        close_connection(connection, cursor)


def verify_password_match(email: str, password: str) -> bool:
    """
    Return True if the given password matches the current password in DB.
    Used to prevent setting the same old password again.
    """
    connection = get_db_connection()
    if not connection:
        return False

    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT pwd FROM trainee WHERE email = ? LIMIT 1", (email,))
        row = cursor.fetchone()
        if not row:
            return False
        return verify_password(password, row["pwd"])
    except sqlite3.Error:
        return False
    finally:
        close_connection(connection, cursor)

def update_password(email: str, new_password: str):
    """
    Update the password for the given email.
    Returns: (success: bool, message: str)
    """
    connection = get_db_connection()
    if not connection:
        return False, "Database connection failed"

    cursor = None
    try:
        cursor = connection.cursor()
        new_hash = hash_password(new_password)
        cursor.execute(
            "UPDATE trainee SET pwd = ? WHERE email = ?",
            (new_hash, email)
        )
        connection.commit()

        if cursor.rowcount == 0:
            return False, "Email not found"

        return True, "Password updated"
    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    finally:
        close_connection(connection, cursor)

def promote_trainee_plan(trainee_id, new_plan_id):
    MIN_PLAN_ID = 1
    MAX_PLAN_ID = 15

    if new_plan_id > MAX_PLAN_ID:
        return False, "Already at maximum level"

    connection = get_db_connection()
    if not connection:
        return False, "DB connection failed"

    try:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE trainee
            SET plan_id = ?
            WHERE trainee_id = ?
        """, (new_plan_id, trainee_id))

        connection.commit()
        return True, "Plan updated"

    finally:
        close_connection(connection, cursor)
        

# =====================================================
# RESET AFTER PROMOTION
# =====================================================

def reset_sessions_after_promotion(trainee_id):
    trainee = get_trainee_info(trainee_id)

    # ✅ 15-plan rule:
    # Advanced plans are 11..15, so do NOT reset in Advanced
    if trainee:
        plan_id = trainee.get("plan_id", 1)
        if plan_id >= 11:
            return False, "Advanced level reached. No reset."

    connection = get_db_connection()
    if not connection:
        return False, "DB connection failed"

    cursor = None
    try:
        cursor = connection.cursor()

        # DELETE old sessions → fresh start
        cursor.execute("""
            DELETE FROM workout_session
            WHERE trainee_id = ?
        """, (trainee_id,))

        connection.commit()
        return True, "Sessions reset"

    except sqlite3.Error as e:
        return False, str(e)

    finally:
        close_connection(connection, cursor)


def update_fitness_level(trainee_id, plan_id):
    level, _ = plan_level_and_index(plan_id)  # Beginner/Intermediate/Advanced

    connection = get_db_connection()
    if not connection:
        return False

    try:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE trainee
            SET fitness_level = ?, plan_id = ?
            WHERE trainee_id = ?
        """, (level, plan_id, trainee_id))

        connection.commit()
        return True
    finally:
        close_connection(connection, cursor)
        
        



# =======================
# PLAN ID HELPERS (15 plans)
# =======================
BEGINNER_START = 1        # 1..5
INTERMEDIATE_START = 6    # 6..10
ADVANCED_START = 11       # 11..15
PLANS_PER_LEVEL = 5

def plan_level_and_index(plan_id: int) -> tuple[str, int]:
    """
    Returns:
      ("Beginner"/"Intermediate"/"Advanced", index 1..5)
    """
    if plan_id is None:
        return "Beginner", 3  # safe default

    if 1 <= plan_id <= 5:
        return "Beginner", plan_id
    if 6 <= plan_id <= 10:
        return "Intermediate", plan_id - 5
    if 11 <= plan_id <= 15:
        return "Advanced", plan_id - 10

    # fallback
    return "Beginner", 3


def make_plan_id(level: str, index_1_to_5: int) -> int:
    """Convert (level + index) -> plan_id in 1..15."""
    idx = max(1, min(PLANS_PER_LEVEL, int(index_1_to_5)))

    level = (level or "").lower()
    if "inter" in level:
        return INTERMEDIATE_START + (idx - 1)
    if "adv" in level:
        return ADVANCED_START + (idx - 1)
    return BEGINNER_START + (idx - 1)


def get_next_plan_same_index(plan_id: int) -> int:
    """
    Beginner k -> Intermediate k -> Advanced k -> Advanced k
    """
    level, idx = plan_level_and_index(plan_id)

    if level == "Beginner":
        return make_plan_id("Intermediate", idx)
    if level == "Intermediate":
        return make_plan_id("Advanced", idx)
    return plan_id  # already Advanced


def reset_sessions_after_inactivity(trainee_id):
    """
    Reset sessions for inactivity (30+ days).
    ✅ This MUST reset even Advanced (plan_id 11–15).
    """
    connection = get_db_connection()
    if not connection:
        return False, "DB connection failed"

    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute("""
            DELETE FROM workout_session
            WHERE trainee_id = ?
        """, (trainee_id,))
        connection.commit()
        return True, "Sessions reset due to inactivity"
    except sqlite3.Error as e:
        return False, str(e)
    finally:
        close_connection(connection, cursor)

