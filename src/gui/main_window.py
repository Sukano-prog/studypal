"""
Main window - Complete with formatting, seekable slider, speed, pause/resume
"""

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from pathlib import Path
import threading
import json
import sounddevice as sd
import time
import re

from engine.tts import TTSManager
from engine.document import load_document
from audio.player import AudioPlayer
from gui.listen_view import ListenView
from datetime import datetime


class ClickableSlider(QSlider):
    """QSlider that jumps to the clicked position instead of only dragging."""
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Jump to clicked position
            value = QStyle.sliderValueFromPosition(
                self.minimum(), self.maximum(),
                event.position().x(), self.width()
            )
            self.setValue(value)
            self.sliderPressed.emit()
            self.sliderMoved.emit(value)
            self.sliderReleased.emit()
            event.accept()
        else:
            super().mousePressEvent(event)


class MainWindow(QMainWindow):
    _tts_playing = Signal()
    _tts_cancelled = Signal()
    _tts_error = Signal(str)

    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("StudyPal")
        self.setMinimumSize(1000, 700)
        
        # Core
        self.tts = TTSManager()
        self.player = AudioPlayer()
        self.current_text = ""
        self.is_playing = False
        self.is_paused = False
        self.dark_mode = True
        self.current_file = ""
        self.recent_files = []
        self.max_recent = 10
        self.audio_data = None
        self.sample_rate = None
        self.current_speed = 1.0
        self.is_seeking = False
        self._seek_in_progress = False
        self._speed_timer = None
        self.progress_thread = None
        self._loop_running = False
        self.stop_progress = False
        
        # Load recent files
        self.load_recent_files()
        
        # Setup UI
        self.setup_ui()
        self._tts_playing.connect(self._on_tts_playing)
        self._tts_cancelled.connect(self._on_tts_cancelled)
        self._tts_error.connect(self._on_tts_error)
        self.apply_theme()
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer_layout = QVBoxLayout(central)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()

        # --- Tab 1: Read to Me (existing UI) ---
        read_widget = QWidget()
        layout = QVBoxLayout(read_widget)
        
        # Toolbar
        toolbar = QWidget()
        toolbar.setFixedHeight(50)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(5, 5, 5, 5)
        toolbar_layout.setSpacing(10)
        
        open_btn = QPushButton("📂 Open")
        open_btn.clicked.connect(self.open_file)
        open_btn.setStyleSheet("font-weight: bold; padding: 6px 16px;")
        toolbar_layout.addWidget(open_btn)
        
        self.recent_combo = QComboBox()
        self.recent_combo.setPlaceholderText("Recent Files")
        self.recent_combo.setMinimumWidth(150)
        self.recent_combo.currentIndexChanged.connect(self.on_recent_selected)
        toolbar_layout.addWidget(self.recent_combo)
        
        voice_label = QLabel("Voice:")
        toolbar_layout.addWidget(voice_label)
        
        self.voice_combo = QComboBox()
        self.voice_combo.addItems(self.tts.get_voice_list())
        self.voice_combo.setMinimumWidth(200)
        self.voice_combo.currentTextChanged.connect(self.on_voice_changed)
        toolbar_layout.addWidget(self.voice_combo)
        
        toolbar_layout.addStretch()
        
        self.theme_btn = QPushButton("🌙 Dark")
        self.theme_btn.setCheckable(True)
        self.theme_btn.setChecked(True)
        self.theme_btn.clicked.connect(self.toggle_theme)
        toolbar_layout.addWidget(self.theme_btn)
        
        layout.addWidget(toolbar)
        
        # Text display
        self.text_display = QTextEdit()
        self.text_display.setFont(QFont("Segoe UI", 12))
        self.text_display.setPlaceholderText("Load a document...")
        self.text_display.setReadOnly(True)
        self.text_display.setMouseTracking(True)
        # Double-click a sentence to start playback from there
        self.text_display.mouseDoubleClickEvent = self._on_text_double_click
        layout.addWidget(self.text_display)
        
        # Progress slider
        slider_layout = QHBoxLayout()
        
        self.time_label = QLabel("00:00")
        slider_layout.addWidget(self.time_label)
        
        self.progress_slider = ClickableSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.setValue(0)
        self.progress_slider.setEnabled(False)
        self.progress_slider.sliderPressed.connect(self.on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self.on_slider_released)
        slider_layout.addWidget(self.progress_slider)
        
        self.duration_label = QLabel("00:00")
        slider_layout.addWidget(self.duration_label)
        
        layout.addLayout(slider_layout)
        
        # Controls
        controls = QHBoxLayout()
        
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self.toggle_playback)
        controls.addWidget(self.play_btn)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_playback)
        controls.addWidget(self.stop_btn)

        self.save_audio_btn = QPushButton("💾 Save Audio")
        self.save_audio_btn.setEnabled(False)
        self.save_audio_btn.clicked.connect(self.save_audio)
        controls.addWidget(self.save_audio_btn)
        
        controls.addStretch()
        
        controls.addWidget(QLabel("Speed:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(50, 200)
        self.speed_slider.setValue(100)
        self.speed_slider.setFixedWidth(100)
        controls.addWidget(self.speed_slider)
        self.speed_label = QLabel("1.0x")
        controls.addWidget(self.speed_label)
        self.speed_slider.valueChanged.connect(self.on_speed_changed)
        
        layout.addLayout(controls)
        
        # Notes panel
        notes_panel = QWidget()
        notes_panel.setMaximumWidth(400)
        notes_layout = QVBoxLayout(notes_panel)
        
        notes_label = QLabel("📝 Notes")
        notes_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        notes_layout.addWidget(notes_label)
        
        # Formatting toolbar
        format_toolbar = QWidget()
        format_toolbar.setFixedHeight(40)
        format_layout = QHBoxLayout(format_toolbar)
        format_layout.setContentsMargins(0, 0, 0, 0)
        format_layout.setSpacing(5)
        
        # Bold
        bold_btn = QPushButton(" B ")
        bold_btn.setFixedSize(40, 32)
        bold_btn.setStyleSheet("font-weight: bold; font-size: 15px; background-color: #3a3a6e; color: white; border-radius: 4px;")
        bold_btn.setToolTip("Bold")
        bold_btn.clicked.connect(self.toggle_bold)
        format_layout.addWidget(bold_btn)
        
        # Italic
        italic_btn = QPushButton(" I ")
        italic_btn.setFixedSize(40, 32)
        italic_btn.setStyleSheet("font-style: italic; font-size: 15px; background-color: #3a3a6e; color: white; border-radius: 4px;")
        italic_btn.setToolTip("Italic")
        italic_btn.clicked.connect(self.toggle_italic)
        format_layout.addWidget(italic_btn)
        
        # Underline
        underline_btn = QPushButton(" U ")
        underline_btn.setFixedSize(40, 32)
        underline_btn.setStyleSheet("text-decoration: underline; font-size: 15px; background-color: #3a3a6e; color: white; border-radius: 4px;")
        underline_btn.setToolTip("Underline")
        underline_btn.clicked.connect(self.toggle_underline)
        format_layout.addWidget(underline_btn)
        
        # Color
        color_btn = QPushButton(" 🎨 ")
        color_btn.setFixedSize(42, 32)
        color_btn.setStyleSheet("font-size: 15px; background-color: #3a3a6e; color: white; border-radius: 4px;")
        color_btn.setToolTip("Text Color")
        color_btn.clicked.connect(self.pick_color)
        format_layout.addWidget(color_btn)
        
        # Clear
        clear_btn = QPushButton(" 🗑 ")
        clear_btn.setFixedSize(42, 32)
        clear_btn.setStyleSheet("font-size: 15px; background-color: #3a3a6e; color: white; border-radius: 4px;")
        clear_btn.setToolTip("Clear Formatting")
        clear_btn.clicked.connect(self.clear_formatting)
        format_layout.addWidget(clear_btn)
        
        format_layout.addStretch()
        notes_layout.addWidget(format_toolbar)
        
        self.notes_display = QTextEdit()
        self.notes_display.setFont(QFont("Segoe UI", 11))
        self.notes_display.setPlaceholderText("Take notes here...")
        self.notes_display.setAcceptRichText(True)
        notes_layout.addWidget(self.notes_display)
        
        btn_row = QHBoxLayout()
        new_btn = QPushButton("📄 New")
        new_btn.clicked.connect(self.new_note)
        btn_row.addWidget(new_btn)
        save_btn = QPushButton("💾 Save")
        save_btn.clicked.connect(self.save_notes)
        btn_row.addWidget(save_btn)
        clear_all_btn = QPushButton("🗑️ Clear All")
        clear_all_btn.clicked.connect(self.clear_notes)
        btn_row.addWidget(clear_all_btn)
        btn_row.addStretch()
        notes_layout.addLayout(btn_row)
        
        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(central)
        splitter.addWidget(notes_panel)
        splitter.setSizes([750, 350])
        self.setCentralWidget(splitter)
        
        self.statusBar().showMessage("Ready")
    
    # ========== FORMATTING METHODS ==========
    
        # Register Tab 1
        self.tabs.addTab(read_widget, "📖 Read to Me")

        # --- Tab 2: Listen to Me ---
        self.listen_view = ListenView()
        self.tabs.addTab(self.listen_view, "🎙️ Listen to Me")

        outer_layout.addWidget(self.tabs)

    def toggle_bold(self):
        cursor = self.notes_display.textCursor()
        if cursor.hasSelection():
            fmt = QTextCharFormat()
            fmt.setFontWeight(QFont.Bold)
            cursor.mergeCharFormat(fmt)
        else:
            current = self.notes_display.fontWeight()
            self.notes_display.setFontWeight(QFont.Bold if current != QFont.Bold else QFont.Normal)
    
    def toggle_italic(self):
        cursor = self.notes_display.textCursor()
        if cursor.hasSelection():
            fmt = QTextCharFormat()
            fmt.setFontItalic(True)
            cursor.mergeCharFormat(fmt)
        else:
            self.notes_display.setFontItalic(not self.notes_display.fontItalic())
    
    def toggle_underline(self):
        cursor = self.notes_display.textCursor()
        if cursor.hasSelection():
            fmt = QTextCharFormat()
            fmt.setFontUnderline(True)
            cursor.mergeCharFormat(fmt)
        else:
            self.notes_display.setFontUnderline(not self.notes_display.fontUnderline())
    
    def new_note(self):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.notes_display.append(f"\n\n--- New Note: {timestamp} ---\n")
        self.statusBar().showMessage("New note created", 2000)

    def pick_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            cursor = self.notes_display.textCursor()
            if cursor.hasSelection():
                fmt = QTextCharFormat()
                fmt.setForeground(color)
                cursor.mergeCharFormat(fmt)
            else:
                self.notes_display.setTextColor(color)
    
    def clear_formatting(self):
        cursor = self.notes_display.textCursor()
        cursor.select(QTextCursor.Document)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("black"))
        fmt.setBackground(Qt.transparent)
        fmt.setFontWeight(QFont.Normal)
        fmt.setFontItalic(False)
        fmt.setFontUnderline(False)
        cursor.mergeCharFormat(fmt)
        self.notes_display.setTextCursor(cursor)
    
    # ========== END FORMATTING ==========
    
    # ========== READ-ALONG ==========

    def _split_into_sentences(self, text):
        """Return list of (start_char, end_char, sentence_text)."""
        sentences = []
        # Split on sentence boundaries + keep paragraphs
        pattern = re.compile(r'[^.!?\n]+[.!?]?\s*|\n+')
        for match in pattern.finditer(text):
            s, e = match.span()
            chunk = text[s:e]
            if chunk.strip():
                sentences.append((s, e, chunk))
        return sentences

    def _build_sentence_map(self):
        """Build sentence -> (char range, time range).

        If we have real TTS chunk timings, use them for accurate sync.
        Otherwise, fall back to character-count estimation."""
        text = self.text_display.toPlainText()
        if not text or self.audio_data is None:
            self._sentence_map = []
            return

        sentences = self._split_into_sentences(text)
        total_duration = len(self.audio_data) / self.sample_rate

        # --- Preferred: use real chunk timings from TTS ---
        if getattr(self, "_chunk_timings", None):
            self._build_map_from_chunks(sentences, total_duration)
            return

        # --- Fallback: char-count estimate (old behavior) ---
        total_chars = sum(len(s[2]) for s in sentences)
        self._sentence_map = []
        cursor_time = 0.0
        for (s, e, chunk) in sentences:
            frac = len(chunk) / total_chars if total_chars else 0
            seg_dur = frac * total_duration
            self._sentence_map.append({
                "start_char": s,
                "end_char": e,
                "start_time": cursor_time,
                "end_time": cursor_time + seg_dur,
            })
            cursor_time += seg_dur

        self._last_highlighted_idx = -1

    def _build_map_from_chunks(self, sentences, total_duration):
        """Align sentence char ranges with real TTS chunk time ranges."""
        chunks = self._chunk_timings

        # Full plain text and running char offset
        full_text = self.text_display.toPlainText()
        text_pos = 0

        self._sentence_map = []
        chunk_idx = 0
        chunk_char_start = 0  # char offset in full_text where current chunk begins

        for (s, e, chunk_text) in sentences:
            # Advance to the chunk that contains this sentence
            while chunk_idx < len(chunks):
                current_chunk = chunks[chunk_idx]
                chunk_char_end = chunk_char_start + len(current_chunk["text"])
                if s < chunk_char_end:
                    # This sentence lives (at least partly) inside chunk_idx
                    chunk_start_time = current_chunk["start"]
                    chunk_end_time = current_chunk["end"]
                    chunk_char_len = max(1, len(current_chunk["text"]))

                    # Interpolate sentence's time within the chunk by char fraction
                    local_start = (s - chunk_char_start) / chunk_char_len
                    local_end = (e - chunk_char_start) / chunk_char_len
                    start_time = chunk_start_time + local_start * (chunk_end_time - chunk_start_time)
                    end_time = chunk_start_time + local_end * (chunk_end_time - chunk_start_time)

                    self._sentence_map.append({
                        "start_char": s,
                        "end_char": e,
                        "start_time": start_time,
                        "end_time": end_time,
                    })
                    break
                else:
                    # Sentence belongs to a later chunk
                    chunk_char_start = chunk_char_end
                    chunk_idx += 1
            else:
                # Ran out of chunks — assign last known time
                last = self._sentence_map[-1] if self._sentence_map else {"end_time": total_duration}
                self._sentence_map.append({
                    "start_char": s,
                    "end_char": e,
                    "start_time": last["end_time"],
                    "end_time": total_duration,
                })

        self._last_highlighted_idx = -1

    def _highlight_sentence(self, idx):
        """Highlight sentence at index; auto-scroll to keep it visible."""
        if not getattr(self, "_sentence_map", None):
            return
        if idx == getattr(self, "_last_highlighted_idx", -1):
            return

        sel = QTextEdit.ExtraSelection()
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#fff59d"))
        fmt.setForeground(QColor("#000000"))
        sel.format = fmt

        if idx < 0:
            # Clear highlight (end of playback)
            self.text_display.setExtraSelections([])
            self._last_highlighted_idx = -1
            return

        if idx >= len(self._sentence_map):
            return

        item = self._sentence_map[idx]
        # IMPORTANT: use a DETACHED cursor (document-only, not widget-bound)
        # so QTextEdit never auto-scrolls to "keep the cursor visible"
        cursor = QTextCursor(self.text_display.document())
        cursor.setPosition(item["start_char"])
        cursor.setPosition(item["end_char"], QTextCursor.KeepAnchor)
        sel.cursor = cursor

        self.text_display.setExtraSelections([sel])
        self._last_highlighted_idx = idx

        # Auto-scroll WITHOUT moving the caret (setTextCursor causes jumps)
        self._scroll_sentence_into_view(item["start_char"], item["end_char"])

    def _scroll_sentence_into_view(self, start_char, end_char):
        """Scroll so the current sentence sits ~30% from the top.

        Uses documentLayout().blockBoundingRect() — does NOT call cursorRect(),
        which would trigger QTextEdit's internal ensureCursorVisible() and cause
        the widget to jump to the top on every tick.
        """
        try:
            doc = self.text_display.document()
            scrollbar = self.text_display.verticalScrollBar()
            viewport_h = self.text_display.viewport().height()

            # Find the block (paragraph) that contains start_char
            block = doc.findBlock(start_char)
            if not block.isValid():
                return

            # Y position of this block in document coordinates (no side effects)
            layout = doc.documentLayout()
            rect = layout.blockBoundingRect(block)
            top_y = rect.top()

            current = scrollbar.value()

            # Comfort zone: don't scroll unless sentence is outside it
            comfort_top = current + viewport_h * 0.15
            comfort_bottom = current + viewport_h * 0.70

            if top_y < comfort_top or top_y > comfort_bottom:
                # Place the sentence ~30% from the top of the viewport
                desired_scroll = int(top_y - viewport_h * 0.30)
                scrollbar.setValue(max(0, desired_scroll))
        except Exception as e:
            print(f"[scroll] {e}")

    def _char_pos_to_time(self, char_pos):
        """Return the time (seconds) corresponding to a character position."""
        if not getattr(self, "_sentence_map", None):
            return 0.0
        for item in self._sentence_map:
            if item["start_char"] <= char_pos <= item["end_char"]:
                # Interpolate within the sentence for precision
                span_chars = max(1, item["end_char"] - item["start_char"])
                span_time = item["end_time"] - item["start_time"]
                frac = (char_pos - item["start_char"]) / span_chars
                return item["start_time"] + frac * span_time
        # Fallback: end of audio
        return self._sentence_map[-1]["end_time"] if self._sentence_map else 0.0

    def _on_text_double_click(self, event):
        """Double-click anywhere in text_display: jump playback to that point."""
        cursor = self.text_display.cursorForPosition(event.pos())
        char_pos = cursor.position()

        if self.audio_data is None:
            return QTextEdit.mouseDoubleClickEvent(self.text_display, event)

        target_time = self._char_pos_to_time(char_pos)

        # Find which sentence owns this char position (directly, not via player)
        target_idx = self._sentence_idx_for_char(char_pos)

        # Pause the update loop while we rearrange things
        self.is_seeking = True
        self._seek_in_progress = True

        if self.is_playing and not self.is_paused:
            # Already playing: just seek; don't call play() (would reset)
            self.player.seek(target_time)
        else:
            # Not playing: start from target position
            self.player.play_from(target_time)
            self.is_playing = True
            self.is_paused = False
            self.play_btn.setText("⏸ Pause")
            self.stop_btn.setEnabled(True)
            self.stop_progress = False
            if self.progress_thread is None or not self.progress_thread.is_alive():
                self.progress_thread = threading.Thread(
                    target=self.update_progress_loop, daemon=True
                )
                self.progress_thread.start()

        # Update UI using the TARGET values, not player.get_position()
        self.progress_slider.setValue(
            int((target_time / max(0.01, self.player.duration)) * 1000)
        )
        self.time_label.setText(self.format_time(target_time))

        # Force highlight to the target sentence directly
        self._last_highlighted_idx = -1
        if target_idx >= 0:
            self._highlight_sentence(target_idx)

        # Release the seeking flag after the audio position stabilizes
        QTimer.singleShot(200, self._release_seek_flag)

        self.statusBar().showMessage(
            f"Jumped to {self.format_time(target_time)}", 2000
        )

    def _release_seek_flag(self):
        # Re-sync once with now-stable position
        self._last_highlighted_idx = -1
        idx = self._current_sentence_idx()
        self._highlight_sentence(idx)
        # Release both flags
        self.is_seeking = False
        self._seek_in_progress = False

    def _sentence_idx_for_char(self, char_pos):
        """Return the sentence index that contains char_pos."""
        if not getattr(self, "_sentence_map", None):
            return -1
        for i, item in enumerate(self._sentence_map):
            if item["start_char"] <= char_pos <= item["end_char"]:
                return i
        # Fallback: nearest previous sentence
        best = -1
        for i, item in enumerate(self._sentence_map):
            if item["end_char"] <= char_pos:
                best = i
            else:
                break
        return best

    def _clear_readalong(self):
        self.text_display.setExtraSelections([])
        self._last_highlighted_idx = -1

    def _current_sentence_idx(self):
        if not getattr(self, "_sentence_map", None):
            return -1
        t = self.player.get_position()
        sm = self._sentence_map

        # Exact match
        for i, item in enumerate(sm):
            if item["start_time"] <= t <= item["end_time"]:
                return i

        # Before first sentence → highlight the first
        if t < sm[0]["start_time"]:
            return 0

        # After last sentence → highlight the last
        if t >= sm[-1]["end_time"]:
            return len(sm) - 1

        # Between sentences (gap) → nearest previous sentence
        for i in range(len(sm) - 1):
            if sm[i]["end_time"] <= t < sm[i + 1]["start_time"]:
                return i

        return -1

    def format_time(self, seconds):
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def _ensure_progress_loop(self):
        """Start the progress loop ONLY if one isn't already running."""
        if getattr(self, "_loop_running", False):
            return
        if self.progress_thread is not None and self.progress_thread.is_alive():
            return
        self.progress_thread = threading.Thread(
            target=self.update_progress_loop, daemon=True
        )
        self.progress_thread.start()

    def update_progress_loop(self):
        # READ-ALONG: guard attributes for first run
        if not hasattr(self, "_sentence_map"):
            self._sentence_map = []
        if not hasattr(self, "_last_highlighted_idx"):
            self._last_highlighted_idx = -1

        # SINGLETON GUARD: if another loop is already running, bail immediately
        if getattr(self, "_loop_running", False):
            print("[LOOP] another loop already running — exiting this one")
            return
        self._loop_running = True
        try:
            self._progress_loop_inner()
        finally:
            self._loop_running = False

    def _progress_loop_inner(self):
        while self.is_playing and not self.stop_progress:
            try:
                # Gate on BOTH flags (thread visibility workaround)
                if (not self.is_paused
                        and not self.is_seeking
                        and not getattr(self, "_seek_in_progress", False)):
                    current_time = self.player.get_position()
                    duration = self.player.duration
                    if duration > 0 and current_time >= 0:
                        progress = int((current_time / duration) * 1000)
                        if progress > 1000:
                            progress = 1000
                        self.progress_slider.setValue(progress)
                        self.time_label.setText(self.format_time(current_time))
                        self.duration_label.setText(self.format_time(duration))
                        self._highlight_sentence(self._current_sentence_idx())

                        # Detect end-of-audio and clean up
                        if current_time >= duration - 0.05:
                            self.is_playing = False
                            self.play_btn.setText("▶ Play")
                            self.stop_btn.setEnabled(False)
                            self.progress_slider.setValue(1000)
                            self._clear_readalong()
                            self.statusBar().showMessage("Playback finished")
                            break
            except:
                pass
            time.sleep(0.1)
    
    def toggle_playback(self):
        if self.is_playing and not self.is_paused:
            self.pause_playback()
        elif self.is_playing and self.is_paused:
            self.resume_playback()
        else:
            self.play_text()
    
    def pause_playback(self):
        if self.is_playing and not self.is_paused:
            self.is_paused = True
            self.player.pause()
            self.play_btn.setText("▶ Resume")
            self.stop_progress = True
            self.statusBar().showMessage("Paused")
    
    def resume_playback(self):
        if self.is_playing and self.is_paused:
            self.is_paused = False
            self.player.play()
            self.play_btn.setText("⏸ Pause")
            self.stop_progress = False
            if self.progress_thread is None or not self.progress_thread.is_alive():
                self._ensure_progress_loop()
            self.statusBar().showMessage("Resumed")
    
    def _on_tts_playing(self):
        self.play_btn.setText("⏸ Pause")
        self.play_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.save_audio_btn.setEnabled(True)
        self.progress_slider.setEnabled(True)
        if self.audio_data is not None and self.sample_rate:
            self.duration_label.setText(self.format_time(len(self.audio_data) / self.sample_rate))
        self.statusBar().showMessage("Playing...")
        self.stop_progress = False
        if self.progress_thread is None or not self.progress_thread.is_alive():
            self._ensure_progress_loop()

    def _on_tts_cancelled(self):
        print("[UI] Generation cancelled by user")
        self.play_btn.setText("▶ Play")
        self.play_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.statusBar().showMessage("Cancelled")

    def _on_tts_error(self, msg):
        self.play_btn.setText("▶ Play")
        self.play_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", msg)
        self.statusBar().showMessage("Error")

    def play_text(self):
        text = self.text_display.toPlainText().strip()
        if not text:
            return
        
        if self.audio_data is not None:
            self.is_playing = True
            self.is_paused = False
            self.progress_slider.setEnabled(True)
            self.player.play()
            self.play_btn.setText("⏸ Pause")
            self.stop_btn.setEnabled(True)
            self.save_audio_btn.setEnabled(True)
            self.statusBar().showMessage("Playing...")
            self.stop_progress = False
            # READ-ALONG: only rebuild if text changed
            if not getattr(self, "_sentence_map", None) or \
               getattr(self, "_last_text_hash", None) != hash(text):
                self._build_sentence_map()
                self._last_text_hash = hash(text)
            if self.progress_thread is None or not self.progress_thread.is_alive():
                self._ensure_progress_loop()
            return
        
        self.play_btn.setEnabled(False)
        self.play_btn.setText("Generating...")
        self.statusBar().showMessage("Generating speech... (click Stop to cancel)")
        # Enable the Stop button NOW so the user can abort generation
        self.stop_btn.setEnabled(True)
        self.stop_progress = False
        if hasattr(self.tts, "reset_cancel"):
            self.tts.reset_cancel()
        
        def generate_and_play():
            try:
                speed = self.speed_slider.value() / 100.0
                self.current_speed = speed
                result = self.tts.generate_audio(text, speed)
                # Handle both 2-tuple and 3-tuple returns
                if len(result) == 3:
                    audio, sr, chunk_timings = result
                else:
                    audio, sr = result
                    chunk_timings = None
                self.audio_data = audio
                self.sample_rate = sr
                self._chunk_timings = chunk_timings   # READ-ALONG: real timing
                self.player.load(audio, sr)
                self.player.speed = speed
                self.duration_label.setText(self.format_time(len(audio) / sr))
                self._build_sentence_map()   # READ-ALONG: prep sentence timing
                
                self.player.play()
                self.is_playing = True
                self.is_paused = False
                self.progress_slider.setEnabled(True)
                
                # Worker thread: emit signal, main thread updates UI
                self._tts_playing.emit()
                
            except RuntimeError as e:
                if "TTS_CANCELLED" in str(e):
                    self._tts_cancelled.emit()
                    return
                self._tts_error.emit(str(e))
            except Exception as e:
                self._tts_error.emit(str(e))

        threading.Thread(target=generate_and_play, daemon=True).start()
    
    def stop_playback(self):
        self.is_playing = False
        self.is_paused = False
        self.stop_progress = True
        # Also cancel any in-flight TTS generation
        if hasattr(self.tts, "cancel"):
            self.tts.cancel()
        self.player.stop()
        self.progress_slider.setValue(0)
        self.progress_slider.setEnabled(False)
        self._clear_readalong()   # READ-ALONG: remove highlight
        self.time_label.setText("00:00")
        self.play_btn.setText("▶ Play")
        self.play_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.statusBar().showMessage("Stopped")
    
    def on_slider_pressed(self):
        self.is_seeking = True
        self._seek_in_progress = True
    
    def on_slider_released(self):
        if self.audio_data is not None:
            value = self.progress_slider.value()
            position = (value / 1000) * len(self.audio_data) / self.sample_rate
            self.player.seek(position)
            self.time_label.setText(self.format_time(position))
            # Refresh highlight immediately
            self._last_highlighted_idx = -1
            self._highlight_sentence(self._current_sentence_idx())
        # Delay releasing the seek flag so update loop doesn't fight us
        QTimer.singleShot(500, lambda: (setattr(self, "is_seeking", False), setattr(self, "_seek_in_progress", False)))
    
    def on_speed_changed(self, value):
        speed = value / 100.0
        self.speed_label.setText(f"{speed:.1f}x")
        self.current_speed = speed
        
        if self._speed_timer:
            self._speed_timer.stop()
        self._speed_timer = QTimer()
        self._speed_timer.setSingleShot(True)
        self._speed_timer.timeout.connect(lambda: self._apply_speed(speed))
        self._speed_timer.start(100)
    
    def _apply_speed(self, speed):
        old_speed = getattr(self, "current_speed", 1.0) or 1.0
        self.player.set_speed(speed)
        self.current_speed = speed

        # Rescale sentence map to match new perceived duration
        if getattr(self, "_sentence_map", None) and old_speed > 0:
            factor = old_speed / speed
            for item in self._sentence_map:
                item["start_time"] *= factor
                item["end_time"] *= factor
            self._last_highlighted_idx = -1

        self.statusBar().showMessage(f"Speed: {speed:.2f}x", 1500)


    def _rescale_sentence_map_for_speed(self, new_speed):
        """Rescale sentence times from base_duration to new duration."""
        if not self._sentence_map:
            return
        # base times assumed at speed 1.0
        factor = 1.0 / new_speed
        for item in self._sentence_map:
            item["start_time"] *= factor
            item["end_time"] *= factor


    def on_voice_changed(self, voice):
        print(f"[VOICE] changed to: {voice}")
        self.tts.set_voice(voice)
        self.statusBar().showMessage(f"Voice changed to: {voice}", 2000)
        # Invalidate in-memory audio so next Play regenerates with new voice
        self.audio_data = None
        self.sample_rate = None
        # Also stop the player — it may still hold old audio
        try:
            self.player.stop()
            self.player.audio_data = None
        except Exception:
            pass
        self.is_playing = False
        self.is_paused = False
        self.play_btn.setText("▶ Play")
        self.stop_btn.setEnabled(False)
        self.save_audio_btn.setEnabled(False)
        # Force play_text to regenerate by clearing any cached "already playing" state
        self._last_text_hash = None
        print(f"[VOICE] audio_data cleared, player stopped")
    
    def load_recent_files(self):
        config_file = Path.home() / ".studypal_recent.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    self.recent_files = data.get("recent", [])
                    self.update_recent_menu()
            except:
                self.recent_files = []
    
    def save_recent_files(self):
        config_file = Path.home() / ".studypal_recent.json"
        try:
            with open(config_file, 'w') as f:
                json.dump({"recent": self.recent_files[:self.max_recent]}, f)
        except:
            pass
    
    def add_recent_file(self, file_path):
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[:self.max_recent]
        self.save_recent_files()
        self.update_recent_menu()
    
    def update_recent_menu(self):
        self.recent_combo.clear()
        self.recent_combo.addItem("📂 Recent Files")
        for file_path in self.recent_files:
            name = Path(file_path).name
            self.recent_combo.addItem(f"📄 {name}")
    
    def on_recent_selected(self, index):
        if index > 0:
            file_path = self.recent_files[index - 1]
            if Path(file_path).exists():
                self.load_document(file_path)
            else:
                QMessageBox.warning(self, "File Not Found", f"File no longer exists:\n{file_path}")
                self.recent_files.pop(index - 1)
                self.save_recent_files()
                self.update_recent_menu()
    
    def apply_theme(self):
        if self.dark_mode:
            self.setStyleSheet("""
                QMainWindow { background-color: #1a1a2e; }
                QWidget { background-color: #1a1a2e; color: #e0e0ff; }
                QTextEdit { background-color: #0f3460; color: #e0e0ff; border: 1px solid #2a2a4e; border-radius: 4px; padding: 10px; }
                QPushButton { background-color: #2a2a4e; color: #e0e0ff; border: none; padding: 8px 16px; border-radius: 4px; }
                QPushButton:hover { background-color: #3a3a6e; }
                QPushButton:disabled { background-color: #1a1a3e; color: #666; }
                QProgressBar { border: 1px solid #2a2a4e; border-radius: 4px; background-color: #16213e; color: #e0e0ff; }
                QProgressBar::chunk { background-color: #6C63FF; border-radius: 4px; }
                QMenuBar { background-color: #1a1a2e; color: #e0e0ff; }
                QMenuBar::item:selected { background-color: #2a2a4e; }
                QMenu { background-color: #1a1a2e; color: #e0e0ff; border: 1px solid #2a2a4e; }
                QMenu::item:selected { background-color: #2a2a4e; }
                QSplitter::handle { background-color: #2a2a4e; }
                QStatusBar { background-color: #0d1b2a; color: #8899bb; }
                QLabel { color: #e0e0ff; }
                QComboBox { background-color: #16213e; color: #e0e0ff; border: 1px solid #2a2a4e; padding: 4px 8px; border-radius: 4px; }
                QComboBox:hover { border-color: #6C63FF; }
                QComboBox::drop-down { border: none; }
                QComboBox QAbstractItemView { background-color: #16213e; color: #e0e0ff; selection-background-color: #6C63FF; }
                QSlider::groove:horizontal { border: 1px solid #2a2a4e; background: #16213e; height: 4px; border-radius: 2px; }
                QSlider::handle:horizontal { background: #6C63FF; border: none; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }
            """)
            self.theme_btn.setText("🌙 Dark")
        else:
            self.setStyleSheet("""
                QMainWindow { background-color: #f5f7fa; }
                QWidget { background-color: #f5f7fa; color: #2d3436; }
                QTextEdit { background-color: white; color: #2d3436; border: 1px solid #dfe6e9; border-radius: 4px; padding: 10px; }
                QPushButton { background-color: #e8ecf0; color: #2d3436; border: none; padding: 8px 16px; border-radius: 4px; }
                QPushButton:hover { background-color: #d5dbe0; }
                QPushButton:disabled { background-color: #e8ecf0; color: #999; }
                QProgressBar { border: 1px solid #dfe6e9; border-radius: 4px; background-color: white; color: #2d3436; }
                QProgressBar::chunk { background-color: #6C63FF; border-radius: 4px; }
                QMenuBar { background-color: #f5f7fa; color: #2d3436; }
                QMenuBar::item:selected { background-color: #e8ecf0; }
                QMenu { background-color: white; color: #2d3436; border: 1px solid #dfe6e9; }
                QMenu::item:selected { background-color: #e8ecf0; }
                QSplitter::handle { background-color: #dfe6e9; }
                QStatusBar { background-color: #e8ecf0; color: #636e72; }
                QLabel { color: #2d3436; }
                QComboBox { background-color: white; color: #2d3436; border: 1px solid #dfe6e9; padding: 4px 8px; border-radius: 4px; }
                QComboBox:hover { border-color: #6C63FF; }
                QComboBox::drop-down { border: none; }
                QComboBox QAbstractItemView { background-color: white; color: #2d3436; selection-background-color: #6C63FF; selection-color: white; }
                QSlider::groove:horizontal { border: 1px solid #dfe6e9; background: #e8ecf0; height: 4px; border-radius: 2px; }
                QSlider::handle:horizontal { background: #6C63FF; border: none; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }
            """)
            self.theme_btn.setText("☀️ Light")
    
    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.toggle_playback()
            event.accept()
            return
        super().keyPressEvent(event)
    
    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Document", str(Path.home()),
            "All Files (*.*);;Text Files (*.txt);;PDF Files (*.pdf);;Word Files (*.docx)"
        )
        if not file_path:
            return
        self.load_document(file_path)
    
    def load_document(self, file_path):
        try:
            content = load_document(file_path)
            self.current_text = content
            self.current_file = file_path
            
            self.text_display.setText(content)
            self.play_btn.setEnabled(True)
            self.play_btn.setText("▶ Play")
            self.is_playing = False
            self.is_paused = False
            self.audio_data = None
            self.sample_rate = None
            self.progress_slider.setValue(0)
            self.progress_slider.setEnabled(False)
            self.time_label.setText("00:00")
            self.duration_label.setText("00:00")
            
            self.setWindowTitle(f"StudyPal - {Path(file_path).name}")
            self.statusBar().showMessage(f"Loaded: {Path(file_path).name}")
            self.add_recent_file(file_path)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
    
    def save_audio(self):
        """Save currently-generated TTS audio to WAV or MP3."""
        if self.audio_data is None:
            QMessageBox.information(self, "No Audio",
                                    "Play the document first to generate audio.")
            return

        # Default filename from the current document
        base = Path(self.current_file).stem if self.current_file else "studypal_speech"
        default_name = f"{base}.wav"

        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save Audio",
            str(Path.home() / default_name),
            "WAV Audio (*.wav);;MP3 Audio (*.mp3)",
        )
        if not path:
            return

        try:
            import soundfile as sf
            import subprocess
            import tempfile
            import os

            if path.lower().endswith(".mp3"):
                # Write WAV to temp, convert via ffmpeg
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp_wav = tmp.name
                sf.write(tmp_wav, self.audio_data, self.sample_rate)
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
                # Native WAV
                if not path.lower().endswith(".wav"):
                    path += ".wav"
                sf.write(path, self.audio_data, self.sample_rate)

            size_mb = os.path.getsize(path) / (1024 * 1024)
            self.statusBar().showMessage(
                f"Audio saved: {Path(path).name} ({size_mb:.1f} MB)", 5000
            )
            QMessageBox.information(
                self, "Saved",
                f"Audio saved to:\n{path}\n\nSize: {size_mb:.2f} MB"
            )
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", f"Could not save audio:\n{e}")

    def save_notes(self):
        content = self.notes_display.toHtml()
        if not content.strip():
            QMessageBox.information(self, "Empty Notes", "Nothing to save.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Notes",
            str(Path.home() / "notes.html"),
            "HTML Files (*.html);;Text Files (*.txt);;All Files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    if file_path.endswith('.html'):
                        f.write(content)
                    else:
                        f.write(self.notes_display.toPlainText())
                self.statusBar().showMessage(f"Notes saved to: {Path(file_path).name}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save notes:\n{e}")
    
    def clear_notes(self):
        reply = QMessageBox.question(self, "Clear Notes", "Clear all notes?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.notes_display.clear()
            self.statusBar().showMessage("Notes cleared", 2000)
