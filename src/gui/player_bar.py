"""
PlayerBar - transport controls + seekable progress slider + speed slider.

Pure UI widget: it never touches AudioPlayer/TTS directly. It emits
Qt signals and exposes small setter methods so MainWindow stays the
only place that coordinates playback logic.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSlider


def format_time(seconds):
    seconds = max(0, int(seconds))
    minutes, secs = divmod(seconds, 60)
    return f"{minutes:02d}:{secs:02d}"


class PlayerBar(QWidget):
    play_pause_clicked = Signal()
    stop_clicked = Signal()
    seek_requested = Signal(float)   # 0.0 - 1.0 fraction of duration
    speed_changed = Signal(float)    # e.g. 1.25

    def __init__(self, parent=None):
        super().__init__(parent)
        self._duration = 0.0
        self._user_seeking = False
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # Progress row
        progress_row = QHBoxLayout()
        self.time_label = QLabel("00:00")
        progress_row.addWidget(self.time_label)

        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.setEnabled(False)
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)
        progress_row.addWidget(self.progress_slider)

        self.duration_label = QLabel("00:00")
        progress_row.addWidget(self.duration_label)
        root.addLayout(progress_row)

        # Controls row
        controls_row = QHBoxLayout()
        self.play_btn = QPushButton("\u25b6 Play")
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self.play_pause_clicked)
        controls_row.addWidget(self.play_btn)

        self.stop_btn = QPushButton("\u23f9 Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_clicked)
        controls_row.addWidget(self.stop_btn)

        controls_row.addStretch()

        controls_row.addWidget(QLabel("Speed:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(50, 200)
        self.speed_slider.setValue(100)
        self.speed_slider.setFixedWidth(100)
        self.speed_slider.valueChanged.connect(self._on_speed_slider_changed)
        controls_row.addWidget(self.speed_slider)

        self.speed_label = QLabel("1.0x")
        controls_row.addWidget(self.speed_label)

        root.addLayout(controls_row)

    # ---------- slider event plumbing ----------

    def _on_slider_pressed(self):
        self._user_seeking = True

    def _on_slider_released(self):
        self._user_seeking = False
        fraction = self.progress_slider.value() / 1000.0
        self.seek_requested.emit(fraction)

    def _on_speed_slider_changed(self, value):
        speed = value / 100.0
        self.speed_label.setText(f"{speed:.1f}x")
        self.speed_changed.emit(speed)

    @property
    def is_seeking(self):
        return self._user_seeking

    # ---------- state setters (called by MainWindow) ----------

    def set_duration(self, seconds):
        self._duration = seconds
        self.duration_label.setText(format_time(seconds))

    def set_position(self, seconds):
        if self._user_seeking:
            return
        self.time_label.setText(format_time(seconds))
        if self._duration > 0:
            fraction = min(seconds / self._duration, 1.0)
            self.progress_slider.setValue(int(fraction * 1000))

    def reset(self):
        self.progress_slider.setValue(0)
        self.time_label.setText("00:00")
        self.duration_label.setText("00:00")

    def set_ready_to_play(self, ready):
        self.play_btn.setEnabled(ready)

    def set_transport_enabled(self, enabled):
        self.progress_slider.setEnabled(enabled)
        self.stop_btn.setEnabled(enabled)

    def set_play_label(self, text):
        self.play_btn.setText(text)

    def set_generating(self, generating):
        self.play_btn.setEnabled(not generating)
        self.play_btn.setText("Generating..." if generating else "\u25b6 Play")

    def current_speed(self):
        return self.speed_slider.value() / 100.0
