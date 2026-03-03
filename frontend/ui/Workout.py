"""
Workout Workout displaying workout plan
Connected to SQLite database using workout_session for unlocks
Professional UI with glassmorphism effects and high-quality layout
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from backend.models.data_manager import (
    get_trainee_info,
    get_workout_plan,
    save_workout_session,
    WORKOUT_COLUMNS
)
from backend.utils.activity_tracker import update_last_activity
from backend.models.data_manager import plan_level_and_index


class Workout(QWidget):
    logoutSignal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.trainee_id = None
        self.trainee = None
        self.workouts = []
        self.completed_indices = set()
        self.session_completed = False
        self.init_ui()

    # ------------------- UI SETUP -------------------
    def init_ui(self):
        self.setStyleSheet("background: #0F0C29;")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ---------------- NAV BAR ----------------
        nav_bar = QFrame()
        nav_bar.setFixedHeight(80)
        nav_bar.setStyleSheet("""
            QFrame {
                background: rgba(15, 12, 41, 0.45);
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(50, 0, 50, 0)

        app_title = QLabel("SmartARTrainer")
        app_title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        app_title.setStyleSheet("color: #667eea; background: transparent; border: none;")
        nav_layout.addWidget(app_title)
        nav_layout.addStretch()

        btn_style = """
            QPushButton {
                background: %s;
                color: white;
                border: %s;
                border-radius: 8px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: rgba(102, 126, 234, 0.3);
            }
        """

        dash_btn = QPushButton("Workout")
        dash_btn.setStyleSheet(btn_style % ("rgba(102,126,234,0.8)", "none"))

        analytics_btn = QPushButton("Dashboard")
        analytics_btn.setStyleSheet(btn_style % ("transparent", "1px solid rgba(255,255,255,0.4)"))
        analytics_btn.clicked.connect(self.on_analytics_clicked)

        profile_btn = QPushButton("Profile")
        profile_btn.setStyleSheet(btn_style % ("transparent", "1px solid rgba(255,255,255,0.4)"))
        profile_btn.clicked.connect(self.on_profile_clicked)

        
        nav_layout.addWidget(analytics_btn)
        nav_layout.addSpacing(10)
        nav_layout.addWidget(dash_btn)
        nav_layout.addSpacing(10)
        nav_layout.addWidget(profile_btn)

        main_layout.addWidget(nav_bar)

        # ---------------- TOP ROW: TRAINEE INFO + LOGOUT ----------------
        top_row_container = QWidget()
        top_row_container.setStyleSheet("background: transparent; border: none;")
        top_row = QHBoxLayout(top_row_container)
        top_row.setContentsMargins(50, 20, 50, 0)
        top_row.setSpacing(18)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)

        # Give object names so we can override any global QLabel QSS
        self.welcome_label = QLabel("Trainee: Loading...")
        self.welcome_label.setObjectName("welcomeLabel")
        self.welcome_label.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self.welcome_label.setAutoFillBackground(False)
        self.welcome_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.plan_label = QLabel("Plan: Personalized")
        self.plan_label.setObjectName("planLabel")
        self.plan_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Medium))
        self.plan_label.setAutoFillBackground(False)
        self.plan_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # HARD override (beats global QLabel styles)
        top_row_container.setStyleSheet("""
            QWidget { background: transparent; border: none; }

            QLabel#welcomeLabel {
                color: #ffffff;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }

            QLabel#planLabel {
                color: #a3bffa;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)

        info_col.addWidget(self.welcome_label)
        info_col.addWidget(self.plan_label)

        top_row.addLayout(info_col)
        top_row.addStretch()

        self.logout_btn = QPushButton("Logout")
        self.logout_btn.setFixedSize(130, 46)
        self.logout_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.08);
                color: white;
                border-radius: 12px;
                font-weight: bold;
                border: 1px solid rgba(255,255,255,0.12);
            }
            QPushButton:hover {
                background: rgba(255,107,107,0.16);
                border-color: #ff6b6b;
                color: #ff6b6b;
            }
        """)
        self.logout_btn.clicked.connect(self.logoutSignal.emit)
        top_row.addWidget(self.logout_btn)

        main_layout.addWidget(top_row_container)

        # ---------------- MAIN CONTAINER ----------------
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(50, 20, 50, 40)
        self.grid_layout.setSpacing(40)
        main_layout.addWidget(self.grid_container)

    # ------------------- DATA HANDLING -------------------
    def set_user(self, user_data: dict):
        self.trainee_id = user_data.get("trainee_id")
        self.load_Workout_data()

    def load_Workout_data(self):
        if not self.trainee_id:
            return

        self.trainee = get_trainee_info(self.trainee_id)

        if not self.trainee:
            self.welcome_label.setText("Trainee: Not found")
            self.plan_label.setText("Plan: -")
            self.workouts = []
            self.refresh_cards()
            return

        self.welcome_label.setText(f"Trainee: {self.trainee.get('name', 'User')}")
        plan_id = self.trainee.get("plan_id", 1)
        main_level, _ = plan_level_and_index(plan_id)
        self.plan_label.setText(f"Plan: {main_level}")

        plan_id = self.trainee.get("plan_id")
        self.workouts = get_workout_plan(plan_id) if plan_id else []
        self.refresh_cards()

    # ------------------- Workout CARDS -------------------
    def refresh_cards(self):
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            w = item.widget() if item else None
            if w:
                w.setParent(None)

        card_layout = QHBoxLayout()
        card_layout.setSpacing(28)

        # ---------------- LEFT HALF (secondary) ----------------
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(14, 0, 14, 0)
        left_layout.setSpacing(12)

        left.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left.setMinimumWidth(380)

        left_layout.addStretch(2)

        quote_top = QLabel("Are you ready to beat your challenge today?")
        quote_top.setAlignment(Qt.AlignmentFlag.AlignCenter)
        quote_top.setWordWrap(True)
        quote_top.setStyleSheet("""
            QLabel {
                color: rgba(255,255,255,0.90);
                font-size: 40px;
                font-weight: 200;
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)

        quote_bottom = QLabel("Let’s start 💪")
        quote_bottom.setAlignment(Qt.AlignmentFlag.AlignCenter)
        quote_bottom.setStyleSheet("""
            QLabel {
                color: #a3bffa;
                font-size: 34px;
                font-weight: 200;
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)

        left_layout.addWidget(quote_top)
        left_layout.addWidget(quote_bottom)
        left_layout.addStretch(3)

        # ---------------- RIGHT HALF (PRIMARY) ----------------
        right = QFrame()
        right_layout = QVBoxLayout(right)
        right_layout.setSpacing(18)

        right.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.10);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 24px;
            }
        """)
        right_layout.setContentsMargins(44, 40, 44, 40)

        header = QHBoxLayout()
        h1 = QLabel("Workout")
        h2 = QLabel("Repetition / Time")

        for h in (h1, h2):
            h.setFont(QFont("Segoe UI", 24, QFont.Weight.ExtraBold))
            h.setStyleSheet("""
                color: #ffffff;
                letter-spacing: 0.9px;
                background: transparent;
                border: none;
                padding: 0px;
            """)

        header.addWidget(h1)
        header.addStretch(2)
        header.addWidget(h2)
        right_layout.addLayout(header)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background: rgba(255,255,255,0.32); border: none;")
        right_layout.addWidget(divider)

        if not self.workouts:
            empty = QLabel("No workouts found for this plan.")
            empty.setFont(QFont("Segoe UI", 18, QFont.Weight.Medium))
            empty.setStyleSheet("""
                color: rgba(255,255,255,0.90);
                background: transparent;
                border: none;
                padding: 0px;
            """)
            right_layout.addWidget(empty)
        else:
            for workout in self.workouts:
                wname = workout.get("name", "Workout")
                unit = "seconds" if wname in ["Plank", "Cobra Stretch"] else "reps"
                target_val = workout.get("target", 0)

                row = QHBoxLayout()
                row.setSpacing(22)

                name = QLabel(wname)
                name.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
                name.setStyleSheet("""
                    color: #ffffff;
                    background: transparent;
                    border: none;
                    padding: 0px;
                """)

                val = QLabel(f"{target_val} {unit}")
                val.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
                val.setStyleSheet("""
                    color: #dbeafe;
                    background: transparent;
                    border: none;
                    padding: 0px;
                """)

                row.addWidget(name)
                row.addStretch(3)
                row.addWidget(val)
                right_layout.addLayout(row)

        right_layout.addStretch(1)

        start_btn = QPushButton("Start Workout")
        start_btn.setFixedHeight(66)
        start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                           stop:0 #667eea, stop:1 #764ba2);
                color: white;
                font-size: 19px;
                font-weight: bold;
                border-radius: 18px;
                padding: 12px 18px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                           stop:0 #764ba2, stop:1 #667eea);
            }
        """)
        start_btn.clicked.connect(self.start_workout_safely)
        right_layout.addWidget(start_btn)

        card_layout.addWidget(left, 1)
        card_layout.addWidget(right, 4)

        container = QWidget()
        container.setLayout(card_layout)
        self.grid_layout.addWidget(container, 0, 0)

    def start_workout_safely(self):
        """Start the first workout in the plan (unlocked) - go to demo screen."""
        if not self.workouts:
            QMessageBox.information(self, "No Workouts", "No workout plan found for this user.")
            return

        first = self.workouts[0]
        workout_id = first.get("workout_id")

        if workout_id is None:
            QMessageBox.warning(self, "Not Available", "Workout demo screen is not connected.")
            return

        main_win = self.window()
        if hasattr(main_win, "show_workout_demo"):
            main_win.show_workout_demo(workout_id)
        else:
            QMessageBox.warning(self, "Not Available", "Workout demo screen is not connected.")

    # ---------------- SESSION TRACKING ----------------

    def mark_exercise_completed(self, index):
        """Call this when an exercise is completed"""
        self.completed_indices.add(index)

        if len(self.completed_indices) == len(self.workouts):
            self.finalize_session()


    def finalize_session(self):
        """Save workout session to database when all exercises are done"""
        if self.session_completed:
            return  # prevent double saving

        session_data = {col: 0 for col in WORKOUT_COLUMNS}

        # mark completed workouts as 1
        for i, workout in enumerate(self.workouts):
            if i < len(WORKOUT_COLUMNS) and i in self.completed_indices:
                session_data[WORKOUT_COLUMNS[i]] = 1

        success, msg = save_workout_session(self.trainee_id, session_data)

        if success:
            
            update_last_activity(self.trainee_id)
            
            self.session_completed = True
            QMessageBox.information(self, "Session Saved",
                                    "Workout session completed and saved successfully!")
            
            self.session_completed = False
            self.completed_indices.clear()
        else:
            QMessageBox.critical(self, "Database Error", msg)


    def on_profile_clicked(self):
        main_win = self.window()
        if hasattr(main_win, "show_profile"):
            main_win.show_profile()
        else:
            QMessageBox.information(self, "Not Available", "Profile screen is not connected.")

    def on_analytics_clicked(self):
        main_win = self.window()
        if hasattr(main_win, "show_analytics"):
            main_win.show_analytics()
        else:
            QMessageBox.information(self, "Not Available", "Analytics screen is not connected.")
