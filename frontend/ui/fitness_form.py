"""
Fitness Details Form for user onboarding
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame,
    QRadioButton, QButtonGroup,
    QDoubleSpinBox, QMessageBox, QComboBox, QSpinBox,
    QAbstractSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class _NoWheelMixin:
    """Mixin to disable mouse-wheel changing values (lets parent scroll instead)."""
    def wheelEvent(self, event):  # noqa: N802 (Qt naming)
        event.ignore()


class NoWheelSpinBox(_NoWheelMixin, QSpinBox):
    pass


class NoWheelDoubleSpinBox(_NoWheelMixin, QDoubleSpinBox):
    pass


class NoWheelComboBox(_NoWheelMixin, QComboBox):
    pass


class FitnessForm(QWidget):
    """Comprehensive fitness details form"""

    formCompleted = pyqtSignal(dict)  # Emits all fitness data
    backRequested = pyqtSignal()      # Emits when back button clicked

    def __init__(self, parent=None):
        super().__init__(parent)

        # Track whether user actually touched key inputs
        self._dob_touched = False
        self._height_touched = False
        self._weight_touched = False
        self._duration_touched = False
        self._frequency_touched = False

        self.init_ui()

    # ======================================================
    #  Helper: show validation messages
    # ======================================================
    def show_error(self, title: str, message: str):
        QMessageBox.warning(self, title, message)

    # ======================================================
    #  ✅ NEW: Ask consent before storing fitness details
    # ======================================================
    def ask_storage_consent(self) -> bool:
        """
        Ask user consent to store fitness details before saving to DB.
        Returns True only if user agrees.
        """
        msg = QMessageBox(self)
        msg.setWindowTitle("Consent Required")
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setText("Do you agree to store your fitness details in the database?")
        msg.setInformativeText(
            "We store these details to personalize your workout plan and track your progress.\n"
            "If you do not agree, we cannot save your fitness details."
        )
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        return msg.exec() == QMessageBox.StandardButton.Yes

    def init_ui(self):
        # ================= Scroll Area =================
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                   stop:0 #0f0c29, stop:0.5 #302b63, stop:1 #24243e);
                border: none;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.05);
                width: 10px;
            }
            QScrollBar::handle:vertical {
                background: #667eea;
                border-radius: 5px;
            }
        """)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 80, 0, 40)

        # ================= Card =================
        card = QWidget()
        card.setFixedWidth(650)
        card.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 25px;
                border: 1px solid #e2e8f0;
            }
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(25)
        card_layout.setContentsMargins(40, 50, 40, 50)

        # ================= Title =================
        title = QLabel("Complete Your Fitness Profile")
        title.setFont(QFont("Segoe UI", 36, QFont.Weight.ExtraBold))
        title.setStyleSheet("""
            QLabel {
                color: #667eea;
                background: transparent;
                padding: 10px;
                font-size: 32px;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Elevate your lifestyle with personalized AI coaching")
        subtitle.setFont(QFont("Segoe UI", 16))
        subtitle.setStyleSheet("color: #5c646e; background: transparent; font-size: 14px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)

        # ================= Styles =================
        label_style = "color:#2d3748; font-size:15px; font-weight:800; background:transparent;"

        radio_style = """
            QRadioButton {
                color:#333333;
                font-size:14px;
            }
            QRadioButton::indicator {
                width:18px;
                height:18px;
                border-radius:9px;
                border:2px solid #555;
            }
            QRadioButton::indicator:checked {
                background:#667eea;
                border:2px solid #667eea;
            }
        """

        input_style = """
            QComboBox, QDoubleSpinBox, QSpinBox {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                color: #2d3748;
                padding: 6px 12px;
                font-size: 14px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #4a5568;
                width: 0;
                height: 0;
                margin-right: 10px;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
            QSpinBox::up-button, QSpinBox::down-button {
                width: 20px;
                border-left: 1px solid #e2e8f0;
                background: transparent;
            }
            QDoubleSpinBox::up-arrow, QSpinBox::up-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 4px solid #4a5568;
                width: 0;
                height: 0;
            }
            QDoubleSpinBox::down-arrow, QSpinBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #4a5568;
                width: 0;
                height: 0;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: #2d3748;
                selection-background-color: #667eea;
                selection-color: white;
                border-radius: 8px;
                outline: 0;
            }
        """

        # ================= Helper =================
        def create_row(text, widget):
            container = QWidget()
            container.setFixedWidth(550)
            container.setStyleSheet("""
                background:#ffffff;
                border: 1px solid #edf2f7;
                border-radius:12px;
            """)
            row = QHBoxLayout(container)
            row.setContentsMargins(16, 12, 16, 12)

            lbl = QLabel(text)
            lbl.setStyleSheet(label_style)
            lbl.setWordWrap(True)

            widget.setFixedHeight(40)
            widget.setStyleSheet(input_style)

            row.addWidget(lbl, 1)
            row.addStretch()
            row.addWidget(widget)
            return container

        def create_spinner_row(text, widget):
            container = QWidget()
            container.setFixedWidth(550)
            container.setStyleSheet("""
                background:#ffffff;
                border: 1px solid #edf2f7;
                border-radius:12px;
            """)
            row = QHBoxLayout(container)
            row.setContentsMargins(16, 12, 16, 12)

            lbl = QLabel(text)
            lbl.setStyleSheet(label_style)
            lbl.setWordWrap(True)

            # Hide default buttons
            widget.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            widget.setFixedHeight(40)
            widget.setFixedWidth(100)
            widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            widget.setStyleSheet(input_style)

            # Custom buttons
            btn_style = """
                QPushButton {
                    background-color: #f7fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    color: #4a5568;
                    font-size: 18px;
                    width: 35px;
                    height: 35px;
                }
                QPushButton:hover {
                    background-color: #edf2f7;
                    border-color: #667eea;
                    color: #667eea;
                }
                QPushButton:pressed {
                    background-color: #cbd5e0;
                }
            """

            btn_down = QPushButton("🡃")
            btn_up = QPushButton("🡁")
            btn_down.setStyleSheet(btn_style)
            btn_up.setStyleSheet(btn_style)

            def dec():
                widget.setValue(widget.value() - widget.singleStep())

            def inc():
                widget.setValue(widget.value() + widget.singleStep())

            btn_down.clicked.connect(dec)
            btn_up.clicked.connect(inc)

            # Button container for side-by-side layout
            btn_layout = QHBoxLayout()
            btn_layout.setSpacing(5)
            btn_layout.addWidget(btn_down)
            btn_layout.addWidget(btn_up)

            row.addWidget(lbl, 1)
            row.addStretch()
            row.addWidget(widget)
            row.addLayout(btn_layout)
            return container

        # ================= DOB (force user selection) =================
        self.day_input = NoWheelComboBox()
        self.month_input = NoWheelComboBox()
        self.year_input = NoWheelComboBox()

        self.day_input.addItem("DD")
        for d in range(1, 32):
            self.day_input.addItem(f"{d:02d}")

        self.month_input.addItem("MMM")
        self.month_input.addItems([
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
        ])

        self.year_input.addItem("YYYY")
        for y in range(1976, 2006):
            self.year_input.addItem(str(y))

        for cb in (self.day_input, self.month_input, self.year_input):
            cb.setFixedHeight(40)
            cb.setStyleSheet(input_style)

        def update_dob_touched():
            self._dob_touched = (
                self.day_input.currentIndex() != 0 and
                self.month_input.currentIndex() != 0 and
                self.year_input.currentIndex() != 0
            )

        self.day_input.currentIndexChanged.connect(lambda _: update_dob_touched())
        self.month_input.currentIndexChanged.connect(lambda _: update_dob_touched())
        self.year_input.currentIndexChanged.connect(lambda _: update_dob_touched())

        dob_container = QWidget()
        dob_container.setFixedWidth(550)
        dob_container.setStyleSheet("background:#ffffff; border: 1px solid #edf2f7; border-radius:12px;")
        dob_layout = QHBoxLayout(dob_container)
        dob_layout.setContentsMargins(12, 6, 12, 6)

        dob_label = QLabel("Date of Birth")
        dob_label.setStyleSheet(label_style)
        dob_label.setMinimumWidth(200)

        dob_layout.addWidget(dob_label)
        dob_layout.addWidget(self.day_input)
        dob_layout.addWidget(self.month_input)
        dob_layout.addWidget(self.year_input)
        card_layout.addWidget(dob_container)

        # ================= Gender (no default selection) =================
        gender_label = QLabel("Gender")
        gender_label.setStyleSheet(label_style)
        gender_label.setMinimumWidth(200)

        self.gender_group = QButtonGroup()
        self.gender_group.setExclusive(True)

        self.male_radio = QRadioButton("Male")
        self.female_radio = QRadioButton("Female")

        for rb in (self.male_radio, self.female_radio):
            rb.setStyleSheet(radio_style)
            self.gender_group.addButton(rb)

        gender_box = QWidget()
        gender_box.setFixedWidth(550)
        gender_box.setStyleSheet("background:#ffffff; border: 1px solid #edf2f7; border-radius:12px;")
        gender_layout = QHBoxLayout(gender_box)
        gender_layout.addWidget(gender_label)
        gender_layout.addWidget(self.male_radio)
        gender_layout.addWidget(self.female_radio)
        card_layout.addWidget(gender_box)

        # ================= Height & Weight (require user interaction) =================
        self.height_input = NoWheelDoubleSpinBox()
        self.height_input.setRange(100, 200)
        self.height_input.setSuffix(" cm")
        self.height_input.setValue(100)  # placeholder-like default
        self.height_input.valueChanged.connect(lambda _: setattr(self, "_height_touched", True))
        card_layout.addWidget(create_spinner_row("Height", self.height_input))

        self.weight_input = NoWheelDoubleSpinBox()
        self.weight_input.setRange(30, 150)
        self.weight_input.setSuffix(" kg")
        self.weight_input.setValue(30)  # placeholder-like default
        self.weight_input.valueChanged.connect(lambda _: setattr(self, "_weight_touched", True))
        card_layout.addWidget(create_spinner_row("Weight", self.weight_input))

        # ================= Workout Experience (no default selection) =================
        exp_label = QLabel("Do you have previous workout experience?")
        exp_label.setStyleSheet(label_style)
        exp_label.setMinimumWidth(200)

        self.workout_exp_group = QButtonGroup()
        self.workout_exp_group.setExclusive(True)

        self.workout_yes_radio = QRadioButton("Yes")
        self.workout_no_radio = QRadioButton("No")

        for rb in (self.workout_yes_radio, self.workout_no_radio):
            rb.setStyleSheet(radio_style)
            self.workout_exp_group.addButton(rb)

        exp_box = QWidget()
        exp_box.setFixedWidth(550)
        exp_box.setStyleSheet("background:#ffffff; border: 1px solid #edf2f7; border-radius:12px;")
        exp_layout = QHBoxLayout(exp_box)
        exp_layout.addWidget(exp_label)
        exp_layout.addWidget(self.workout_yes_radio)
        exp_layout.addWidget(self.workout_no_radio)
        card_layout.addWidget(exp_box)

        # ================= Experience Details =================
        self.exp_details_widget = QWidget()
        exp_details_layout = QVBoxLayout(self.exp_details_widget)

        self.duration_input = NoWheelDoubleSpinBox()
        self.duration_input.setRange(0, 600)
        self.duration_input.setSuffix(" mins")
        self.duration_input.setValue(0)
        self.duration_input.valueChanged.connect(lambda _: setattr(self, "_duration_touched", True))

        self.freq_input = NoWheelSpinBox()
        self.freq_input.setRange(0, 7)     # allow 0 as default (means "not selected")
        self.freq_input.setSuffix(" days")
        self.freq_input.setValue(0)        # default 0
        self.freq_input.valueChanged.connect(lambda _: setattr(self, "_frequency_touched", True))

        exp_details_layout.addWidget(create_spinner_row("Workout duration per day?", self.duration_input))
        exp_details_layout.addWidget(create_spinner_row("Workout days per week?", self.freq_input))

        self.exp_details_widget.setVisible(False)

        def on_experience_yes_toggled(checked: bool):
            self.exp_details_widget.setVisible(checked)
            # Reset "touched" flags + values when they hide the section (choose No)
            if not checked:
                self._duration_touched = False
                self._frequency_touched = False
                self.duration_input.setValue(0)
                self.freq_input.setValue(0)

        self.workout_yes_radio.toggled.connect(on_experience_yes_toggled)
        card_layout.addWidget(self.exp_details_widget)

        # ================= Actions =================
        actions_layout = QHBoxLayout()

        back_btn = QPushButton("Back")
        back_btn.setMinimumHeight(55)
        back_btn.setStyleSheet("""
            QPushButton {
                background: #f7fafc;
                color: #4a5568;
                border: 2px solid #e2e8f0;
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #edf2f7;
                border-color: #cbd5e0;
            }
        """)
        back_btn.clicked.connect(self.backRequested.emit)

        submit_btn = QPushButton("Sign Up")
        submit_btn.setMinimumHeight(55)
        submit_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                   stop:0 #667eea, stop:1 #764ba2);
                color: white;
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                   stop:0 #764ba2, stop:1 #667eea);
            }
        """)
        submit_btn.clicked.connect(self.handle_submit)

        actions_layout.addWidget(back_btn, 1)
        actions_layout.addWidget(submit_btn, 2)
        card_layout.addLayout(actions_layout)

        # ================= Final Layout =================
        center = QHBoxLayout()
        center.addStretch()
        center.addWidget(card)
        center.addStretch()

        layout.addLayout(center)
        scroll.setWidget(content)

        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.addWidget(scroll)

    # ======================================================
    # Validations enforced here
    # ======================================================
    def handle_submit(self):
        # ---- DOB must be selected (not placeholders)
        if self.day_input.currentIndex() == 0 or self.month_input.currentIndex() == 0 or self.year_input.currentIndex() == 0:
            self.show_error("Validation Error", "Please select your full Date of Birth (Day, Month, and Year).")
            return

        # ---- Gender must be selected
        if self.gender_group.checkedButton() is None:
            self.show_error("Validation Error", "Please select your Gender.")
            return

        # ---- Height & Weight must be actively set by user
        if not self._height_touched:
            self.show_error("Validation Error", "Please enter your Height.")
            return
        if not self._weight_touched:
            self.show_error("Validation Error", "Please enter your Weight.")
            return

        height = float(self.height_input.value())
        weight = float(self.weight_input.value())

        if not (100 <= height <= 200):
            self.show_error("Validation Error", "Height must be between 100 cm and 200 cm.")
            return
        if not (30 <= weight <= 150):
            self.show_error("Validation Error", "Weight must be between 30 kg and 150 kg.")
            return

        # ---- Workout experience must be selected
        exp_btn = self.workout_exp_group.checkedButton()
        if exp_btn is None:
            self.show_error("Validation Error", "Please select your workout experience (Yes/No).")
            return

        has_exp = (exp_btn.text() == "Yes")

        duration = float(self.duration_input.value()) if has_exp else 0.0
        frequency = int(self.freq_input.value()) if has_exp else 0

        # ---- If Experience = Yes, require user interaction + valid values
        if has_exp:
            if not self._duration_touched:
                self.show_error("Validation Error", "Please enter your workout duration per day.")
                return
            if not self._frequency_touched:
                self.show_error("Validation Error", "Please enter your workout days per week.")
                return

            if duration <= 0:
                self.show_error("Validation Error", "Workout duration must be greater than 0 minutes.")
                return

            # frequency must be 1..7; 0 means "not chosen"
            if frequency == 0:
                self.show_error("Validation Error", "Please select workout days per week (1 to 7).")
                return
            if not (1 <= frequency <= 7):
                self.show_error("Validation Error", "Workout days per week must be between 1 and 7.")
                return

        # ---- Build DOB
        day = self.day_input.currentText()
        month = self.month_input.currentText()
        year = self.year_input.currentText()

        month_map = {
            "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
            "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
            "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
        }
        dob = f"{year}-{month_map[month]}-{day}"

        gender = self.gender_group.checkedButton().text()

        fitness_data = {
            "dob": dob,
            "gender": gender,
            "height": height,
            "weight": weight,
            "workout_experience": "Yes" if has_exp else "No",
            "workout_duration": duration,
            "weekly_frequency": frequency
        }

        # ======================================================
        # ✅ CONSENT CHECK (ONLY CHANGE IN SUBMIT FLOW)
        # ======================================================
        if not self.ask_storage_consent():
            QMessageBox.warning(
                self,
                "Consent required",
                "You must agree to store your fitness details before we can save them.\n"
                "Please click 'Sign Up' again and choose 'Yes' to continue."
            )
            return

        self.formCompleted.emit(fitness_data)

    def get_data(self):
        """Helper to get current state for data preservation"""
        exp_btn = self.workout_exp_group.checkedButton()
        has_exp = (exp_btn is not None and exp_btn.text() == "Yes")

        return {
            "dob_day": self.day_input.currentIndex(),
            "dob_month": self.month_input.currentIndex(),
            "dob_year": self.year_input.currentIndex(),
            "gender_male": self.male_radio.isChecked(),
            "gender_female": self.female_radio.isChecked(),
            "height": self.height_input.value(),
            "weight": self.weight_input.value(),
            "workout_exp_yes": self.workout_yes_radio.isChecked(),
            "workout_exp_no": self.workout_no_radio.isChecked(),
            "duration": self.duration_input.value(),
            "frequency": self.freq_input.value(),
            "touched_dob": self._dob_touched,
            "touched_height": self._height_touched,
            "touched_weight": self._weight_touched,
            "touched_duration": self._duration_touched,
            "touched_frequency": self._frequency_touched
        }

    def set_data(self, data):
        """Restore state for data preservation"""
        if not data:
            return

        self.day_input.setCurrentIndex(data.get("dob_day", 0))
        self.month_input.setCurrentIndex(data.get("dob_month", 0))
        self.year_input.setCurrentIndex(data.get("dob_year", 0))

        # Restore gender (or clear)
        if data.get("gender_male"):
            self.male_radio.setChecked(True)
        elif data.get("gender_female"):
            self.female_radio.setChecked(True)
        else:
            self.gender_group.setExclusive(False)
            self.male_radio.setChecked(False)
            self.female_radio.setChecked(False)
            self.gender_group.setExclusive(True)

        self.height_input.setValue(float(data.get("height", 100)))
        self.weight_input.setValue(float(data.get("weight", 30)))

        # Restore experience (or clear)
        if data.get("workout_exp_yes"):
            self.workout_yes_radio.setChecked(True)
        elif data.get("workout_exp_no"):
            self.workout_no_radio.setChecked(True)
        else:
            self.workout_exp_group.setExclusive(False)
            self.workout_yes_radio.setChecked(False)
            self.workout_no_radio.setChecked(False)
            self.workout_exp_group.setExclusive(True)

        self.duration_input.setValue(float(data.get("duration", 0)))
        self.freq_input.setValue(int(data.get("frequency", 0)))  #keep default 0

        # Restore touched flags
        self._dob_touched = bool(data.get("touched_dob", False))
        self._height_touched = bool(data.get("touched_height", False))
        self._weight_touched = bool(data.get("touched_weight", False))
        self._duration_touched = bool(data.get("touched_duration", False))
        self._frequency_touched = bool(data.get("touched_frequency", False))