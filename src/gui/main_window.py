"""
MainWindow - assembles the toolbar, document view, player bar, and
notes panel, and coordinates TTSManager / AudioPlayer / TTSWorker.

Threading model:
- TTS generation runs on a QThread (see tts_worker.py) and reports
  back to this class via signals, which Qt marshals onto the GUI
  thread automatically -- so it's always safe to touch widgets in
  the on_generation_finished/on_generation_error slots.
- Playback progress is polled by a QTimer running on the GUI thread
  itself (no background thread touches widgets at all). AudioPlayer's
  internal audio callback thread only ever updates its own
  lock-protected state; the GUI just reads it periodically.
"""

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTextEdit, QSplitter, QFileDialog, QMessageBox,
)

from engine.tts import TTSManager
from engine.document import load_document, DocumentLoadError
from audio.player import AudioPlayer
from gui.player_bar import PlayerBar
from gui.notes_editor import NotesPanel
from gui.tts_worker import TTSWorker
from gui.theme import DARK_THEME, LIGHT_THEME
import config


PROGRESS_POLL_MS = 100


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StudyPal")
        self.setMinimumSize(1000, 700)

        self.tts = TTSManager()
        self.player = AudioPlayer()

        self.dark_mode = True
        self.current_file = ""
        self.recent_files = config.load_recent_files()
        self.has_generated_audio = False
        self._active_worker = None  # keep a reference so QThread isn't GC'd mid-run

        self.progress_timer = QTimer(self)
        self.progress_timer.setInterval(PROGRESS_POLL_MS)
        self.progress_timer.timeout.connect(self._poll_progress)

        self._build_ui()
        self._apply_theme()
        self._refresh_recent_menu()

    # ---------- UI construction ----------

    def _build_ui(self):
        main_panel = QWidget()
        main_layout = QVBoxLayout(main_panel)

        main_layout.addWidget(self._build_toolbar())

        self.text_display = QTextEdit()
        self.text_display.setFont(QFont("Segoe UI", 12))
        self.text_display.setPlaceholderText("Load a document...")
        self.text_display.setReadOnly(True)
        main_layout.addWidget(self.text_display)

        self.player_bar = PlayerBar()
        self.player_bar.play_pause_clicked.connect(self.toggle_playback)
        self.player_bar.stop_clicked.connect(self.stop_playback)
        self.player_bar.seek_requested.connect(self.on_seek_requested)
        self.player_bar.speed_changed.connect(self.on_speed_changed)
        main_layout.addWidget(self.player_bar)

        self.notes_panel = NotesPanel()
        self.notes_panel.setMaximumWidth(400)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(main_panel)
        splitter.addWidget(self.notes_panel)
        splitter.setSizes([750, 350])
        self.setCentralWidget(splitter)

        self.statusBar().showMessage("Ready")

    def _build_toolbar(self):
        toolbar = QWidget()
        toolbar.setFixedHeight(50)
        row = QHBoxLayout(toolbar)
        row.setContentsMargins(5, 5, 5, 5)
        row.setSpacing(10)

        open_btn = QPushButton("\U0001f4c2 Open")
        open_btn.setStyleSheet("font-weight: bold; padding: 6px 16px;")
        open_btn.clicked.connect(self.open_file)
        row.addWidget(open_btn)

        self.recent_combo = QComboBox()
        self.recent_combo.setMinimumWidth(150)
        self.recent_combo.currentIndexChanged.connect(self.on_recent_selected)
        row.addWidget(self.recent_combo)

        row.addWidget(QLabel("Voice:"))
        self.voice_combo = QComboBox()
        self.voice_combo.addItems(self.tts.get_voice_list())
        self.voice_combo.setMinimumWidth(200)
        self.voice_combo.currentTextChanged.connect(self.on_voice_changed)
        row.addWidget(self.voice_combo)

        row.addStretch()

        self.theme_btn = QPushButton("\U0001f319 Dark")
        self.theme_btn.setCheckable(True)
        self.theme_btn.setChecked(True)
        self.theme_btn.clicked.connect(self.toggle_theme)
        row.addWidget(self.theme_btn)

        return toolbar

    # ---------- document loading ----------

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Document", str(Path.home()),
            "All Files (*.*);;Text Files (*.txt);;PDF Files (*.pdf);;Word Files (*.docx)",
        )
        if file_path:
            self.load_document(file_path)

    def load_document(self, file_path):
        try:
            content = load_document(file_path)
        except DocumentLoadError as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.current_file = file_path
        self.text_display.setText(content)

        self.stop_playback()
        self.has_generated_audio = False
        self.player_bar.set_ready_to_play(True)
        self.player_bar.set_play_label("\u25b6 Play")
        self.player_bar.reset()
        self.player_bar.set_transport_enabled(False)

        self.setWindowTitle(f"StudyPal - {Path(file_path).name}")
        self.statusBar().showMessage(f"Loaded: {Path(file_path).name}")
        self._add_recent_file(file_path)

    # ---------- recent files ----------

    def _add_recent_file(self, file_path):
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[: config.MAX_RECENT]
        config.save_recent_files(self.recent_files)
        self._refresh_recent_menu()

    def _refresh_recent_menu(self):
        self.recent_combo.blockSignals(True)
        self.recent_combo.clear()
        self.recent_combo.addItem("\U0001f4c2 Recent Files")
        for file_path in self.recent_files:
            self.recent_combo.addItem(f"\U0001f4c4 {Path(file_path).name}")
        self.recent_combo.blockSignals(False)

    def on_recent_selected(self, index):
        if index <= 0:
            return
        file_path = self.recent_files[index - 1]
        if Path(file_path).exists():
            self.load_document(file_path)
        else:
            QMessageBox.warning(self, "File Not Found", f"File no longer exists:\n{file_path}")
            self.recent_files.pop(index - 1)
            config.save_recent_files(self.recent_files)
            self._refresh_recent_menu()

    # ---------- voice ----------

    def on_voice_changed(self, voice):
        if not voice:
            return
        self.tts.set_voice(voice)
        self.has_generated_audio = False  # cached audio was for the old voice
        self.statusBar().showMessage(f"Voice changed to: {voice}", 2000)

    # ---------- playback ----------

    def toggle_playback(self):
        if not self.has_generated_audio:
            self._generate_and_play()
            return

        if self.player.is_playing:
            self.pause_playback()
        elif self.player.is_paused:
            self.resume_playback()
        else:
            self.player.play()
            self.progress_timer.start()
            self.player_bar.set_play_label("\u23f8 Pause")

    def _generate_and_play(self):
        text = self.text_display.toPlainText().strip()
        if not text:
            return

        self.player_bar.set_generating(True)
        self.statusBar().showMessage("Generating speech...")

        # Generate at a neutral rate; the speed slider is applied purely as
        # a real-time playback multiplier in AudioPlayer (see its docstring).
        # Baking speed into generation *and* applying it again on playback
        # would compound (e.g. 1.5x slider -> 2.25x actual speed), so speed
        # has exactly one place it takes effect: the player.
        self._active_worker = TTSWorker(self.tts, text, 1.0, parent=self)
        self._active_worker.finished.connect(self._on_generation_finished)
        self._active_worker.error.connect(self._on_generation_error)
        self._active_worker.done.connect(self._on_worker_done)
        self._active_worker.start()

    def _on_generation_finished(self, audio, sr):
        self.player.load(audio, sr)
        self.player.set_speed(self.player_bar.current_speed())
        self.has_generated_audio = True

        self.player_bar.set_generating(False)
        self.player_bar.set_duration(self.player.duration)
        self.player_bar.set_transport_enabled(True)
        self.player_bar.set_play_label("\u23f8 Pause")

        self.player.play()
        self.progress_timer.start()
        self.statusBar().showMessage("Playing...")

    def _on_generation_error(self, message):
        self.player_bar.set_generating(False)
        QMessageBox.critical(self, "Error", message)
        self.statusBar().showMessage("Error")

    def _on_worker_done(self):
        # The worker's QThread has fully stopped by this point (see
        # tts_worker.py) -- only now is it safe to drop our reference.
        # Dropping it earlier (right after finished/error) risks the
        # Python object being garbage-collected while the OS thread is
        # still winding down, which crashes with "QThread: Destroyed
        # while thread is still running".
        self._active_worker = None

    def pause_playback(self):
        self.player.pause()
        self.progress_timer.stop()
        self.player_bar.set_play_label("\u25b6 Resume")
        self.statusBar().showMessage("Paused")

    def resume_playback(self):
        # Re-apply current speed in case the user changed it while paused.
        self.player.set_speed(self.player_bar.current_speed())
        self.player.play()
        self.progress_timer.start()
        self.player_bar.set_play_label("\u23f8 Pause")
        self.statusBar().showMessage("Resumed")

    def stop_playback(self):
        self.player.stop()
        self.progress_timer.stop()
        self.player_bar.reset()
        self.player_bar.set_transport_enabled(bool(self.has_generated_audio))
        self.player_bar.set_play_label("\u25b6 Play")
        self.statusBar().showMessage("Stopped")

    def on_seek_requested(self, fraction):
        if not self.player.loaded:
            return
        position = fraction * self.player.duration
        self.player.seek(position)
        self.player_bar.set_position(position)

    def on_speed_changed(self, speed):
        if self.player.loaded:
            self.player.set_speed(speed)

    def _poll_progress(self):
        if self.player.is_finished():
            self.progress_timer.stop()
            self.player_bar.set_play_label("\u25b6 Play")
            self.player_bar.set_position(0)
            self.player.seek(0)
            self.statusBar().showMessage("Finished")
            return
        self.player_bar.set_position(self.player.get_position())

    # ---------- theme ----------

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self._apply_theme()

    def _apply_theme(self):
        self.setStyleSheet(DARK_THEME if self.dark_mode else LIGHT_THEME)
        self.theme_btn.setText("\U0001f319 Dark" if self.dark_mode else "\u2600\ufe0f Light")

    # ---------- misc ----------

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.toggle_playback()
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self.progress_timer.stop()
        self.player.stop()
        if self._active_worker is not None and self._active_worker.is_running():
            self._active_worker.stop_and_wait()
        super().closeEvent(event)
