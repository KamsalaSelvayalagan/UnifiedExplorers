"""
Workout Demo Screen - shows exercise demo video/GIF + instructions
"""

import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTextEdit, QDialog, QMessageBox,
    QSizePolicy, QSlider, QStyle
)
from PyQt6.QtCore import Qt, QUrl, QSize, QTimer
from PyQt6.QtGui import QFont, QMovie, QPixmap

from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

from backend.models import data_manager
from backend.utils.unity_embedder import UnityEmbedder


class WorkoutDemo(QWidget):
    """Exercise preview screen with local asset preview + instructions"""

    ASSET_MAP = {
        "squats": "Squats.mp4",
        "push ups": "Push ups.mp4",
        "crunches": "Crunches.mp4",
        "jumping jacks": "Jumping jacks.mp4",
        "plank": "Plank.mp4",
        "cobra stretch": "Cobra stretch.mp4"
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        self.current_workout_id = None
        self.current_workout_name = None
        self.camera_permission_granted = False
        self.movie = None
        
        # Unity embedder for Plank workout
        self.unity_embedder = None
        self.demo_container = None

        # Video
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)

        # Sound ON by default
        self.audio.setVolume(1.0)          # 0.0 to 1.0
        self.is_muted = False


        # connect error handler (NOW exists as a class method)
        self.player.errorOccurred.connect(self.on_media_error)

        # Seek state
        self.is_seeking = False

        # UI refs
        self.video_widget = None
        self.preview_label = None
        self.controls_container = None
        self.play_btn = None
        self.mute_btn = None
        self.icon_volume = None
        self.icon_muted = None
        self.seek_slider = None
        self.current_time_lbl = None
        self.total_time_lbl = None
        self.title_label = None
        self.muscles_label = None
        self.instructions_text = None
        self.start_btn = None

        self.icon_play = None
        self.icon_pause = None
        
        # Background music player for Unity workouts
        self.music_player = QMediaPlayer(self)
        self.music_audio = QAudioOutput(self)
        self._music_normal_volume = 0.35
        self.music_audio.setVolume(self._music_normal_volume)
        self.music_player.setAudioOutput(self.music_audio)
        self.music_player.setLoops(QMediaPlayer.Loops.Infinite)
        self.music_path = self._asset_path("audio.mp3")
        
        # Beep player for alerts
        self.beep_player = QMediaPlayer(self)
        self.beep_audio = QAudioOutput(self)
        self.beep_audio.setVolume(1.0)
        self.beep_player.setAudioOutput(self.beep_audio)
        self.beep_path = self._asset_path("beep.mp3")
        if os.path.exists(self.beep_path):
            self.beep_player.setSource(QUrl.fromLocalFile(self.beep_path))

        self.init_ui()
        self.hook_player_signals()

    # ==================================================
    # Dark styles (white border buttons)
    # ==================================================
    def _apply_dark_msgbox_style(self, msg: QMessageBox):
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #0f0f10;
                border: 1px solid #2a2a2a;
                border-radius: 10px;
                font-family: Segoe UI;
            }

            QLabel {
                color: #ffffff;
                font-size: 16px;
                background: transparent;
            }

            QPushButton {
                background: transparent;
                color: #ffffff;
                font-size: 16px;
                font-weight: 600;
                padding: 4px 16px;
                min-width: 64px;
                border: 1px solid rgba(255,255,255,0.75);
                border-radius: 8px;
            }

            QPushButton:hover {
                background: rgba(255,255,255,0.12);
                color: #ffffff;
            }

            QPushButton:pressed {
                background: rgba(255,255,255,0.20);
                color: #ffffff;
            }
        """)

    def _apply_dark_dialog_style(self, dialog: QDialog):
        dialog.setStyleSheet("""
            QDialog {
                background-color: #0f0f10;
                border: 1px solid #2a2a2a;
                border-radius: 10px;
                font-family: Segoe UI;
            }

            QLabel {
                color: #ffffff;
                font-size: 14px;
                background: transparent;
            }

            QPushButton {
                background: transparent;
                color: #ffffff;
                font-size: 14px;
                font-weight: 600;
                min-width: 70px;
                min-height: 30px;
                padding: 4px 14px;
                border: 1px solid rgba(255,255,255,0.75);
                border-radius: 6px;
            }

            QPushButton:hover {
                background: rgba(255,255,255,0.12);
                color: #ffffff;
            }

            QPushButton:pressed {
                background: rgba(255,255,255,0.20);
                color: #ffffff;
            }
        """)

    def show_dialog(self, title: str, message: str, icon=QMessageBox.Icon.Information):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(icon)
        self._apply_dark_msgbox_style(msg)
        msg.exec()

    # ==================================================
    # Player error handler 
    # ==================================================
    def on_media_error(self, error, error_string=""):
        # friendly fallback when codecs/plugins are missing
        self.stop_preview()
        if self.preview_label:
            self.preview_label.setText(
                "Video preview unavailable on this PC.\n"
                "Tip: Install a media codec pack (Windows) or use GIF previews."
            )
            self.preview_label.setVisible(True)
        if self.video_widget:
            self.video_widget.setVisible(False)

    # ==================================================
    # Unity Embedding (for Plank workout)
    # ==================================================
    def _get_pose_avatar_exe(self) -> str:
        """Get path to PoseToAvatar.exe"""
        app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        return os.path.join(app_root, "UnityBuild", "PoseToAvatar.exe")

    def _init_unity_embedder(self) -> bool:
        """Initialize the Unity embedder"""
        if self.unity_embedder is not None:
            return True  # Already initialized
        
        exe_path = self._get_pose_avatar_exe()
        if not os.path.exists(exe_path):
            self.show_dialog("Error", f"Unity EXE not found: {exe_path}")
            return False
        
        # Use demo_container as the embedding container
        self.unity_embedder = UnityEmbedder(self.demo_container, exe_path)
        
        # Connect signals
        self.unity_embedder.started.connect(self._on_unity_started)
        self.unity_embedder.stopped.connect(self._on_unity_stopped)
        self.unity_embedder.error.connect(self._on_unity_error)
        
        return True
    
    def _launch_unity(self) -> bool:
        """Launch Unity application"""
        if not self._init_unity_embedder():
            return False
        
        # Hide demo UI and launch Unity
        self.demo_container.setVisible(False)
        self._pause_preview()
        
        if self.unity_embedder.start():
            print("WorkoutDemo: Unity launcher initiated")
            # Start background music when Unity starts
            self._start_music()
            return True
        return False
    
    def _stop_unity(self):
        """Stop Unity application"""
        if self.unity_embedder is not None:
            self.unity_embedder.stop()
        self.demo_container.setVisible(True)
    
    def _on_unity_started(self):
        """Called when Unity successfully embeds"""
        print("WorkoutDemo: Unity app started and embedded")
    
    def _on_unity_stopped(self):
        """Called when Unity stops - stop music and beeps"""
        print("WorkoutDemo: Unity app stopped")
        self._stop_music()
        self.demo_container.setVisible(True)
    
    def _on_unity_error(self, error_msg: str):
        """Called when Unity embedding fails"""
        print(f"WorkoutDemo: Unity error: {error_msg}")
        self.demo_container.setVisible(True)
        self.show_dialog("Error", f"Failed to launch Unity: {error_msg}")

    # ==================================================
    # Background Music & Sound Effects
    # ==================================================
    def _start_music(self):
        """Start looping background music while Unity is running"""
        if not self.music_path or not os.path.exists(self.music_path):
            return

        # If already playing, do nothing
        if self.music_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            return

        self.music_player.setSource(QUrl.fromLocalFile(self.music_path))
        self.music_player.play()

    def _stop_music(self):
        """Stop background music safely"""
        try:
            if self.music_player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
                self.music_player.stop()
        except Exception:
            pass

    def _play_beep(self):
        """Play beep sound alert"""
        try:
            if os.path.exists(self.beep_path):
                self.beep_player.stop()
                self.beep_audio.setVolume(1.0)
                self.beep_player.play()
            else:
                from PyQt6.QtWidgets import QApplication
                QApplication.beep()
        except Exception:
            from PyQt6.QtWidgets import QApplication
            QApplication.beep()

    # ==================================================
    # Auto pause/stop on screen change / close
    # ==================================================
    def hideEvent(self, event):
        self._pause_preview()
        super().hideEvent(event)

    def closeEvent(self, event):
        self._pause_preview()
        super().closeEvent(event)

    def resizeEvent(self, event):
        # keep GIF and image scaled nicely when resizing
        self._refresh_scaled_preview()
        super().resizeEvent(event)

    # ==================================================
    def init_ui(self):
        # NOTE: your back/title are white, so background should be dark
        self.setStyleSheet("background:#0f0f10;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 30, 40, 30)
        main_layout.setSpacing(20)

        # ================= Back Button =================
        back_btn = QPushButton("← Back")
        back_btn.setMaximumWidth(220)
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #ffffff;
                font-size: 14px;
                border: none;
            }
            QPushButton:hover { color: #667eea; }
        """)
        back_btn.clicked.connect(self.go_back)
        main_layout.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # ================= Title =================
        self.title_label = QLabel("Workout Demo")
        self.title_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                color: #ffffff;
                font-size: 32px;
                font-weight: bold;
            }
        """)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.title_label)

        # ================= Content Layout =================
        content_layout = QHBoxLayout()
        content_layout.setSpacing(30)

        # ================= Preview Section =================
        self.demo_container = QFrame()
        self.demo_container.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #dddddd;
                border-radius: 16px;
            }
        """)
        preview_layout = QVBoxLayout(self.demo_container)
        preview_layout.setContentsMargins(20, 20, 20, 20)
        preview_layout.setSpacing(12)

        # --- Image/GIF label ---
        self.preview_label = QLabel("No Preview")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(420, 360)
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.preview_label.setStyleSheet("""
            QLabel {
                background: black;
                color: white;
                border-radius: 10px;
            }
        """)

        # --- Video widget ---
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(420, 360)
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video_widget.setStyleSheet("background: black; border-radius: 10px;")
        self.video_widget.hide()

        self.player.setVideoOutput(self.video_widget)

        # --- Controls container ---
        self.controls_container = QFrame()
        self.controls_container.setFixedHeight(60)
        self.controls_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.controls_container.setStyleSheet("""
            QFrame {
                background: #f3f4f6;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
            }
        """)
        controls_outer = QVBoxLayout(self.controls_container)
        controls_outer.setContentsMargins(12, 10, 12, 10)

        controls_row = QHBoxLayout()
        controls_row.setSpacing(10)

        # Play/Pause button
        self.play_btn = QPushButton()
        self.play_btn.setFixedSize(44, 34)
        self.play_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self.icon_play = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        self.icon_pause = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause)

        self.play_btn.setIcon(self.icon_play)
        self.play_btn.setIconSize(QSize(18, 18))
        self.play_btn.setStyleSheet("""
            QPushButton {
                background: #eef2ff;
                border: 2px solid #667eea;
                border-radius: 10px;
            }
            QPushButton:hover {
                background: #e0e7ff;
            }
            QPushButton:pressed {
                background: #c7d2fe;
            }
            QPushButton:checked {
                background: #ddd6fe;              /* slightly different when playing */
                border: 2px solid #764ba2;
            }
        """)
        self.play_btn.clicked.connect(self.toggle_play_pause)

        # Speaker/Mute button
        self.mute_btn = QPushButton()
        self.mute_btn.setFixedSize(44, 34)
        self.mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # Icons (Qt standard)
        self.icon_volume = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume)
        self.icon_muted = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolumeMuted)

        self.mute_btn.setIcon(self.icon_volume)   # sound ON initially
        self.mute_btn.setIconSize(QSize(18, 18))
        self.mute_btn.setStyleSheet("""
            QPushButton {
                background: #eef2ff;                  /* light blue */
                border: 2px solid #667eea;
                border-radius: 10px;
            }
            QPushButton:hover {
                background: #e0e7ff;
            }
            QPushButton:pressed {
                background: #c7d2fe;
            }
            QPushButton:checked {
                background: #fee2e2;                  /* light red when muted */
                border: 2px solid #ef4444;
            }
        """)
        self.mute_btn.clicked.connect(self.toggle_mute)

        self.current_time_lbl = QLabel("00:00")
        self.current_time_lbl.setStyleSheet("color:#111827; font-size:12px;")

        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.seek_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #e5e7eb;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #667eea;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
                background: #764ba2;
            }
        """)
        self.seek_slider.sliderPressed.connect(self.on_seek_pressed)
        self.seek_slider.sliderReleased.connect(self.on_seek_released)
        self.seek_slider.sliderMoved.connect(self.on_seek_moved)

        self.total_time_lbl = QLabel("00:00")
        self.total_time_lbl.setStyleSheet("color:#111827; font-size:12px;")

        controls_row.addWidget(self.play_btn)
        controls_row.addWidget(self.mute_btn)      # ✅ NEW speaker icon near play
        controls_row.addWidget(self.current_time_lbl)
        controls_row.addWidget(self.seek_slider, 1)
        controls_row.addWidget(self.total_time_lbl)

        controls_outer.addLayout(controls_row)
        self.controls_container.hide()

        preview_layout.addWidget(self.preview_label, 1)
        preview_layout.addWidget(self.video_widget, 1)
        preview_layout.addWidget(self.controls_container, 0)

        content_layout.addWidget(self.demo_container, 2)

        # ================= Info Section =================
        info_container = QFrame()
        info_container.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #dddddd;
                border-radius: 16px;
            }
        """)
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(25, 25, 25, 25)
        info_layout.setSpacing(20)

        details_label = QLabel("Workout Name")
        details_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        details_label.setStyleSheet("color:#667eea;")
        info_layout.addWidget(details_label)

        self.muscles_label = QLabel()
        self.muscles_label.setFont(QFont("Segoe UI", 14))
        self.muscles_label.setStyleSheet("color:#333333;")
        self.muscles_label.setWordWrap(True)
        info_layout.addWidget(self.muscles_label)

        instructions_header = QLabel("Instructions")
        instructions_header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        instructions_header.setStyleSheet("color:#667eea;")
        info_layout.addWidget(instructions_header)

        self.instructions_text = QTextEdit()
        self.instructions_text.setReadOnly(True)
        self.instructions_text.setMinimumHeight(200)
        self.instructions_text.setStyleSheet("""
            QTextEdit {
                background: #f9f9f9;
                border: 1px solid #cccccc;
                border-radius: 8px;
                padding: 10px;
                color: #333333;
                font-size: 13px;
            }
        """)
        info_layout.addWidget(self.instructions_text)

        info_layout.addStretch()
        content_layout.addWidget(info_container, 1)

        main_layout.addLayout(content_layout)

        # ================= Start Button =================
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)

        self.start_btn = QPushButton("Start Workout")
        self.start_btn.setMinimumSize(300, 50)
        self.start_btn.setMaximumSize(400, 70)
        self.start_btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.start_btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                       stop:0 #667eea, stop:1 #764ba2);
                color: white;
                border-radius: 12px;
                font-weight: bold;
                font-size: 14px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                       stop:0 #764ba2, stop:1 #667eea);
            }
        """)
        self.start_btn.clicked.connect(self.start_workout)

        button_layout.addStretch()
        button_layout.addWidget(self.start_btn)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

    # ==================================================
    def hook_player_signals(self):
        self.player.positionChanged.connect(self.on_position_changed)
        self.player.durationChanged.connect(self.on_duration_changed)
        self.player.playbackStateChanged.connect(self.on_playback_state_changed)

    # ==================================================
    def assets_path(self, filename: str) -> str:
        # this file is: frontend/ui/workout_demo.py
        # assets are:   frontend/assets/
        frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        return os.path.join(frontend_dir, "assets", filename)
    
    def _asset_path(self, filename: str) -> str:
        """Alias for assets_path for consistency"""
        return self.assets_path(filename)

    @staticmethod
    def normalize_name(name: str) -> str:
        return " ".join(name.strip().lower().split())

    # ==================================================
    def load_workout(self, workout_id):
        self.current_workout_id = workout_id

        try:
            row = data_manager.get_workout_by_id(workout_id)
        except Exception as e:
            self.show_dialog("Database Error", str(e), QMessageBox.Icon.Critical)
            return

        if not row:
            self.show_dialog("Not Found", "Workout not found", QMessageBox.Icon.Warning)
            return

        # expected: (name, description)
        workout_name, description = row
        self.current_workout_name = workout_name

        self.title_label.setText(workout_name)
        self.muscles_label.setText(workout_name)
        self.instructions_text.setText(description or "No instructions available.")

        self.preview_asset(workout_name)

    # ==================================================
    # Cleanup preview state
    # ==================================================
    def stop_preview(self):
        if self.movie:
            self.movie.stop()
            self.movie = None

        # Stop video
        if self.player:
            self.player.pause()
            self.player.setSource(QUrl())

        # Reset controls
        if self.controls_container:
            self.controls_container.hide()
        if self.play_btn and self.icon_play:
            self.play_btn.setIcon(self.icon_play)
        if self.seek_slider:
            self.seek_slider.setRange(0, 0)
            self.seek_slider.setValue(0)
        if self.current_time_lbl:
            self.current_time_lbl.setText("00:00")
        if self.total_time_lbl:
            self.total_time_lbl.setText("00:00")

        # Reset UI
        if self.video_widget:
            self.video_widget.hide()
        if self.preview_label:
            self.preview_label.show()
            self.preview_label.setText("No Preview")
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setMovie(None)
        
        # Reset mute state for next time (optional)
        self.is_muted = False
        self.audio.setMuted(False)
        if self.mute_btn and self.icon_volume:
            self.mute_btn.setIcon(self.icon_volume)


    # ==================================================
    def preview_asset(self, workout_name: str):
        key = self.normalize_name(workout_name)
        filename = self.ASSET_MAP.get(key)

        if not filename:
            self.stop_preview()
            self.preview_label.setText("No Preview Available")
            return

        path = self.assets_path(filename)

        if not os.path.exists(path):
            self.stop_preview()
            self.preview_label.setText(f"File Not Found: {filename}")
            return

        ext = os.path.splitext(filename)[1].lower()

        if ext == ".mp4":
            self.play_video(path)
        elif ext == ".gif":
            self.play_gif(path)
        elif ext in (".png", ".jpg", ".jpeg"):
            self.show_image(path)
        else:
            self.stop_preview()
            self.preview_label.setText("Unsupported Preview Type")

    # ==================================================
    def play_video(self, video_path: str):
        self.stop_preview()

        self.preview_label.hide()
        self.video_widget.show()

        # always show controls for mp4
        self.controls_container.show()
        self.controls_container.raise_()

        self.player.setSource(QUrl.fromLocalFile(video_path))
        self.player.play()

    def play_gif(self, gif_path: str):
        self.stop_preview()
        self.controls_container.hide()

        self.movie = QMovie(gif_path)
        self.movie.setCacheMode(QMovie.CacheMode.CacheAll)
        self.preview_label.setMovie(self.movie)

        self._refresh_scaled_preview()
        self.movie.start()

    def show_image(self, img_path: str):
        self.stop_preview()
        self.controls_container.hide()

        self._last_image_path = img_path
        self._refresh_scaled_preview()

    def _refresh_scaled_preview(self):
        # scale GIF
        if self.movie and self.preview_label:
            self.movie.setScaledSize(self.preview_label.size())

        # scale image
        img_path = getattr(self, "_last_image_path", None)
        if img_path and self.preview_label:
            pix = QPixmap(img_path)
            if pix.isNull():
                self.preview_label.setText("Image Load Failed")
                return
            self.preview_label.setPixmap(
                pix.scaled(
                    self.preview_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )

    # ==================================================
    # Controls
    # ==================================================
    def toggle_play_pause(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setIcon(self.icon_pause)
        else:
            self.play_btn.setIcon(self.icon_play)

    def on_duration_changed(self, duration_ms: int):
        self.seek_slider.setRange(0, max(0, duration_ms))
        self.total_time_lbl.setText(self.format_ms(duration_ms))

    def on_position_changed(self, pos_ms: int):
        if not self.is_seeking:
            self.seek_slider.setValue(pos_ms)
        self.current_time_lbl.setText(self.format_ms(pos_ms))

    def on_seek_pressed(self):
        self.is_seeking = True

    def on_seek_moved(self, value: int):
        self.current_time_lbl.setText(self.format_ms(value))

    def on_seek_released(self):
        self.player.setPosition(self.seek_slider.value())
        self.is_seeking = False
    
    def toggle_mute(self):
        self.is_muted = not self.is_muted
        self.audio.setMuted(self.is_muted)

        if self.is_muted:
            self.mute_btn.setIcon(self.icon_muted)
        else:
            self.mute_btn.setIcon(self.icon_volume)


    @staticmethod
    def format_ms(ms: int) -> str:
        total_seconds = max(0, ms // 1000)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    # ==================================================
    # Navigation / screen switching
    # ==================================================
    def _pause_preview(self):
        if self.player:
            self.player.pause()

    def start_workout(self):
        # pause preview BEFORE permission dialog
        self._pause_preview()

        # Check if this is a plank workout
        is_plank = (self.current_workout_name.strip().lower() == "plank" 
                   if self.current_workout_name else False)
        
        if is_plank:
            # For plank: launch Unity app directly
            if self._launch_unity():
                print("Plank workout started with Unity")
            else:
                self.show_dialog("Error", "Failed to launch Unity for Plank workout")
        else:
            # For other workouts: show coming soon message
            self.show_dialog("Coming Soon", "Camera-based workouts coming soon!\nFor now, only Plank with Unity is available.")

    def go_back(self):
        self._pause_preview()
        self.stop_preview()

        main_win = self.window()
        if hasattr(main_win, "back_from_workout_demo"):
            main_win.back_from_workout_demo()
