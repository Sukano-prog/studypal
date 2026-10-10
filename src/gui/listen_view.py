"""'Listen to Me' panel: audio upload -> transcript -> translation."""
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QTextEdit, QFileDialog, QProgressBar, QSplitter,
    QMessageBox, QGroupBox, QApplication
)
from PySide6.QtCore import Qt

from services.transcription_service import TranscriptionService
from gui.listen_worker import ListenWorker


# Human-readable names and flags for every language we support
LANGUAGE_META = {
    "en": ("English", "🇬🇧"),
    "sw": ("Swahili", "🇰🇪"),
    "fr": ("French", "🇫🇷"),
    "es": ("Spanish", "🇪🇸"),
    "de": ("German", "🇩🇪"),
    "pt": ("Portuguese", "🇵🇹"),
    "ar": ("Arabic", "🇸🇦"),
    "zh": ("Chinese", "🇨🇳"),
    "hi": ("Hindi", "🇮🇳"),
}

MODELS = ["tiny", "base", "small", "medium"]


class ListenView(QWidget):
    """Audio -> Text -> Translation panel."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._service = None
        self._worker = None
        self._current_result = None
        self._current_audio_path = None

        self._build_ui()

    # ---------- language dropdown ----------

    def _populate_language_dropdown(self, source_lang=None):
        """Populate the target-language dropdown.

        If `source_lang` is given, only show languages we can translate TO
        from that source. Otherwise show everything installed.
        """
        self.lang_combo.clear()
        self.lang_combo.addItem("🚫 None (transcribe only)", None)

        # Get installed target languages from the translator service
        try:
            installed = set(self._get_service().translator.available_languages())
        except Exception as e:
            print(f"[langs] Could not load installed languages: {e}")
            installed = set(LANGUAGE_META.keys())

        # Filter: if source is known, exclude it; otherwise show all installed
        targets = sorted(
            code for code in installed
            if code in LANGUAGE_META and code != source_lang
        )

        for code in targets:
            name, flag = LANGUAGE_META[code]
            self.lang_combo.addItem(f"{flag} {name}", code)

        print(f"[langs] dropdown → {targets} (source={source_lang})")

    # ---------- UI construction ----------

    def _build_ui(self):
        root = QVBoxLayout(self)

        # --- Controls ---
        controls = QGroupBox("Audio Input")
        c_layout = QVBoxLayout(controls)

        file_row = QHBoxLayout()
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color: #888;")
        browse_btn = QPushButton("📁 Choose Audio File")
        browse_btn.clicked.connect(self.choose_audio)
        file_row.addWidget(browse_btn)
        file_row.addWidget(self.file_label, 1)
        c_layout.addLayout(file_row)

        opt_row = QHBoxLayout()
        opt_row.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(MODELS)
        self.model_combo.setCurrentText("base")
        opt_row.addWidget(self.model_combo)

        opt_row.addSpacing(20)
        opt_row.addWidget(QLabel("Translate to:"))
        self.lang_combo = QComboBox()
        self.lang_combo.setMinimumWidth(200)
        self._populate_language_dropdown(source_lang=None)
        opt_row.addWidget(self.lang_combo)
        opt_row.addStretch()
        c_layout.addLayout(opt_row)

        # Action buttons row 1: transcribe / cancel / cached badge
        action_row = QHBoxLayout()

        self.transcribe_btn = QPushButton("▶ Transcribe")
        self.transcribe_btn.clicked.connect(self.start_transcription)
        self.transcribe_btn.setEnabled(False)
        action_row.addWidget(self.transcribe_btn)

        self.cancel_btn = QPushButton("✖ Cancel")
        self.cancel_btn.clicked.connect(self.cancel_transcription)
        self.cancel_btn.setEnabled(False)
        action_row.addWidget(self.cancel_btn)

        self.cached_badge = QLabel("")
        self.cached_badge.setStyleSheet("color: #2a9d8f; font-weight: bold;")
        action_row.addWidget(self.cached_badge)

        action_row.addStretch()

        self.copy_btn = QPushButton("📋 Copy")
        self.copy_btn.clicked.connect(self.copy_transcript)
        self.copy_btn.setEnabled(False)
        action_row.addWidget(self.copy_btn)

        self.notes_btn = QPushButton("📝 Send to Notes")
        self.notes_btn.clicked.connect(self.send_to_notes)
        self.notes_btn.setEnabled(False)
        action_row.addWidget(self.notes_btn)

        self.read_btn = QPushButton("🔊 Read Aloud")
        self.read_btn.clicked.connect(self.read_aloud)
        self.read_btn.setEnabled(False)
        action_row.addWidget(self.read_btn)

        self.save_audio_btn = QPushButton("💾 Save Audio")
        self.save_audio_btn.clicked.connect(self.save_audio)
        self.save_audio_btn.setEnabled(False)
        action_row.addWidget(self.save_audio_btn)

        c_layout.addLayout(action_row)

        # Action buttons row 2: exports
        export_row = QHBoxLayout()
        self.export_txt_btn = QPushButton("💾 Export TXT")
        self.export_txt_btn.clicked.connect(self.export_txt)
        self.export_txt_btn.setEnabled(False)
        export_row.addWidget(self.export_txt_btn)

        self.export_srt_btn = QPushButton("💾 Export SRT")
        self.export_srt_btn.clicked.connect(self.export_srt)
        self.export_srt_btn.setEnabled(False)
        export_row.addWidget(self.export_srt_btn)

        self.clear_cache_btn = QPushButton("🗑 Clear Cache")
        self.clear_cache_btn.clicked.connect(self.clear_cache)
        export_row.addWidget(self.clear_cache_btn)

        export_row.addStretch()
        c_layout.addLayout(export_row)

        # Progress bar + status
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        c_layout.addWidget(self.progress)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666;")
        c_layout.addWidget(self.status_label)

        root.addWidget(controls)

        # --- Results ---
        results_splitter = QSplitter(Qt.Orientation.Horizontal)

        t_box = QGroupBox("📝 Transcript")
        t_layout = QVBoxLayout(t_box)
        self.transcript_view = QTextEdit()
        self.transcript_view.setPlaceholderText("Transcript will appear here...")
        t_layout.addWidget(self.transcript_view)
        results_splitter.addWidget(t_box)

        tr_box = QGroupBox("🌍 Translation")
        tr_layout = QVBoxLayout(tr_box)
        self.translation_view = QTextEdit()
        self.translation_view.setPlaceholderText(
            "Translation will appear here (choose a language above)..."
        )
        tr_layout.addWidget(self.translation_view)
        results_splitter.addWidget(tr_box)

        results_splitter.setSizes([500, 500])
        root.addWidget(results_splitter, 1)

    # ---------- service ----------

    def _get_service(self) -> TranscriptionService:
        if self._service is None:
            model = self.model_combo.currentText()
            self._service = TranscriptionService(model_size=model)
        return self._service

    # ---------- file picking ----------

    def choose_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Audio File", "",
            "Audio (*.mp3 *.wav *.m4a *.flac *.ogg *.mp4 *.webm)",
        )
        if not path:
            return
        self._current_audio_path = path
        self.file_label.setText(Path(path).name)
        self.file_label.setStyleSheet("color: #000;")
        self.transcribe_btn.setEnabled(True)

    # ---------- transcription ----------

    def start_transcription(self):
        if not self._current_audio_path:
            return

        self.transcript_view.clear()
        self.translation_view.clear()
        self.cached_badge.setText("")
        self.transcribe_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.export_txt_btn.setEnabled(False)
        self.export_srt_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
        self.notes_btn.setEnabled(False)
        self.read_btn.setEnabled(False)
        self.save_audio_btn.setEnabled(False)
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.status_label.setText("Starting...")

        target_lang = self.lang_combo.currentData()

        try:
            service = self._get_service()
        except Exception as e:
            self._on_error(f"Failed to load model: {e}")
            return

        self._worker = ListenWorker(
            service,
            self._current_audio_path,
            target_language=target_lang,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.progress_pct.connect(self._on_progress_pct)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def cancel_transcription(self):
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait(1000)
            self.status_label.setText("Cancelled.")
            self.progress.setVisible(False)
            self.transcribe_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)

    def _on_progress(self, msg: str):
        self.status_label.setText(msg)

    def _on_progress_pct(self, pct: int):
        self.progress.setValue(pct)

    def _on_finished(self, result: dict):
        # Refresh target-language dropdown using the detected source language
        detected = result.get("detected_language")
        if detected:
            self._populate_language_dropdown(source_lang=detected)

        self.progress.setValue(100)
        self.transcribe_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self._current_result = result

        self.transcript_view.setPlainText(result["transcript"])

        if result.get("translation"):
            self.translation_view.setPlainText(result["translation"])
        else:
            self.translation_view.setPlainText(
                "(No translation requested or unavailable)"
            )

        if result.get("_cached"):
            self.cached_badge.setText("⚡ Loaded from cache")
            self.status_label.setText("Loaded from cache (instant).")
        else:
            self.cached_badge.setText("")
            self.status_label.setText("Done.")

        self.export_txt_btn.setEnabled(True)
        self.export_srt_btn.setEnabled(True)
        self.copy_btn.setEnabled(True)
        self.notes_btn.setEnabled(True)
        self.read_btn.setEnabled(True)
        self.save_audio_btn.setEnabled(True)

    def _on_error(self, msg: str):
        self.progress.setVisible(False)
        self.status_label.setText(f"Error: {msg}")
        self.transcribe_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        QMessageBox.critical(self, "Transcription Error", msg)

    # ---------- action buttons ----------

    def copy_transcript(self):
        if not self._current_result:
            return
        QApplication.clipboard().setText(self._current_result["transcript"])
        self.status_label.setText("Copied to clipboard.")

    def send_to_notes(self):
        """Push transcript into the Read tab's notes panel."""
        if not self._current_result:
            return
        # Walk up to the MainWindow to reach its notes panel
        mw = self.window()
        if hasattr(mw, "notes_display"):
            existing = mw.notes_display.toPlainText().strip()
            sep = "\n\n" if existing else ""
            mw.notes_display.setPlainText(existing + sep + self._current_result["transcript"])
            self.status_label.setText("Sent to Notes.")
        else:
            QMessageBox.information(self, "Not available", "Notes panel not found.")

    def read_aloud(self):
        """Send transcript to Read tab AND start playback automatically."""
        if not self._current_result:
            return

        mw = self.window()
        if not (hasattr(mw, "text_display") and hasattr(mw, "play_text")):
            QMessageBox.information(self, "Not available", "Read tab not found.")
            return

        # 1. Stop any existing playback
        try:
            if hasattr(mw, "stop_playback"):
                mw.stop_playback()
        except Exception:
            pass

        # 2. Clear cached audio so play_text() will regenerate for the new text
        mw.audio_data = None
        mw.sample_rate = None
        if hasattr(mw, "_sentence_map"):
            mw._sentence_map = []
        if hasattr(mw, "_chunk_timings"):
            mw._chunk_timings = None
        if hasattr(mw, "_last_text_hash"):
            mw._last_text_hash = None

        # 3. Load the transcript into the Read tab
        mw.text_display.setPlainText(self._current_result["transcript"])

        # 4. Switch to the Read tab
        if hasattr(mw, "tabs"):
            mw.tabs.setCurrentIndex(0)

        # 5. Auto-start playback after the tab switch settles
        #    (QTimer 0 = "as soon as the event loop is ready")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(50, mw.play_text)

        self.status_label.setText("Starting playback in Read tab...")

    def save_audio(self):
        """Generate TTS from the transcript and save as WAV/MP3."""
        if not self._current_result:
            return

        transcript = self._current_result.get("transcript", "").strip()
        translation = self._current_result.get("translation")
        target_lang = self._current_result.get("target_language")

        # Ask user: transcript or translation?
        use_translation = False
        if translation:
            reply = QMessageBox.question(
                self,
                "Which Text?",
                "Save audio of:\n\n"
                f"  • Yes = Translation ({target_lang or 'translated'})\n"
                f"  • No  = Original transcript\n",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            )
            if reply == QMessageBox.Cancel:
                return
            use_translation = (reply == QMessageBox.Yes)

        text_to_speak = translation if use_translation else transcript

        # Pick the right voice
        mw = self.window()
        if not hasattr(mw, "tts"):
            QMessageBox.critical(self, "Error", "TTS engine not available.")
            return

        # Decide voice: translation -> target language voice, else current
        lang_code = target_lang if use_translation else self._current_result.get("detected_language")
        voice_name = None
        if hasattr(mw.tts, "find_voice_for_lang") and lang_code:
            voice_name = mw.tts.find_voice_for_lang(lang_code)

        try:
            if voice_name:
                mw.tts.set_voice(voice_name)
        except Exception:
            pass

        # Ask for save path
        base = Path(self._current_audio_path).stem if self._current_audio_path else "studypal"
        suffix = "_translation" if use_translation else "_transcript"
        default_name = f"{base}{suffix}.wav"

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Audio",
            str(Path.home() / default_name),
            "WAV Audio (*.wav);;MP3 Audio (*.mp3)",
        )
        if not path:
            return

        # Generate + save (may take a moment)
        self.status_label.setText("Generating audio...")
        self.save_audio_btn.setEnabled(False)

        try:
            speed = 1.0
            # Use main window's speed if available
            if hasattr(mw, "speed_slider"):
                speed = mw.speed_slider.value() / 100.0

            audio, sr = mw.tts.generate_audio(text_to_speak, speed)

            import soundfile as sf
            import subprocess
            import tempfile
            import os

            if path.lower().endswith(".mp3"):
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp_wav = tmp.name
                sf.write(tmp_wav, audio, sr)
                try:
                    subprocess.run(
                        ["ffmpeg", "-y", "-i", tmp_wav, path],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                finally:
                    try:
                        os.unlink(tmp_wav)
                    except Exception:
                        pass
            else:
                if not path.lower().endswith(".wav"):
                    path += ".wav"
                sf.write(path, audio, sr)

            size_mb = os.path.getsize(path) / (1024 * 1024)
            self.status_label.setText(f"Saved: {Path(path).name} ({size_mb:.1f} MB)")
            QMessageBox.information(
                self, "Saved",
                f"Audio saved to:\n{path}\n\nSize: {size_mb:.2f} MB"
            )
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", f"Could not save audio:\n{e}")
            self.status_label.setText("Save failed.")
        finally:
            self.save_audio_btn.setEnabled(True)

    def export_txt(self):
        if not self._current_result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Transcript", "transcript.txt", "Text (*.txt)"
        )
        if not path:
            return
        self._get_service().export_txt(self._current_result, path)
        QMessageBox.information(self, "Saved", f"Saved to:\n{path}")

    def export_srt(self):
        if not self._current_result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Subtitles", "subtitles.srt", "Subtitles (*.srt)"
        )
        if not path:
            return
        self._get_service().export_srt(self._current_result, path)
        QMessageBox.information(self, "Saved", f"Saved to:\n{path}")

    def clear_cache(self):
        try:
            svc = self._get_service()
            n = svc.clear_cache()
            QMessageBox.information(self, "Cache cleared", f"Removed {n} cached transcription(s).")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
