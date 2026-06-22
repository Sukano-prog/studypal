"""
Main window - Clean version
"""

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from pathlib import Path
import threading
import json

from engine.tts import TTSManager
from engine.document import load_document
from audio.player import AudioPlayer


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("StudyPal")
        self.setMinimumSize(1000, 700)
        
        # Core
        self.tts = TTSManager()
        self.player = AudioPlayer()
        self.current_text = ""
        self.is_playing = False
        self.dark_mode = True
        self.current_file = ""
        self.recent_files = []
        self.max_recent = 10
        self.audio_data = None
        self.sample_rate = None
        
        # Load recent files
        self.load_recent_files()
        
        # Setup UI
        self.setup_ui()
        self.apply_theme()
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
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
        
        # Voice selection
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
        layout.addWidget(self.text_display)
        
        # Controls
        controls = QHBoxLayout()
        
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self.play_text)
        controls.addWidget(self.play_btn)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_playback)
        controls.addWidget(self.stop_btn)
        
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
        
        # Formatting row with icons
        format_row = QHBoxLayout()
        format_row.setSpacing(5)
        
        # Bold
        bold_btn = QPushButton("𝐁")
        bold_btn.setFixedSize(36, 30)
        bold_btn.setStyleSheet("font-weight: bold; font-size: 14px;")
        bold_btn.setToolTip("Bold")
        bold_btn.clicked.connect(self.toggle_bold)
        format_row.addWidget(bold_btn)
        
        # Italic
        italic_btn = QPushButton("𝑰")
        italic_btn.setFixedSize(36, 30)
        italic_btn.setStyleSheet("font-style: italic; font-size: 14px;")
        italic_btn.setToolTip("Italic")
        italic_btn.clicked.connect(self.toggle_italic)
        format_row.addWidget(italic_btn)
        
        # Underline
        underline_btn = QPushButton("U")
        underline_btn.setFixedSize(36, 30)
        underline_btn.setStyleSheet("text-decoration: underline; font-size: 14px; font-weight: bold;")
        underline_btn.setToolTip("Underline")
        underline_btn.clicked.connect(self.toggle_underline)
        format_row.addWidget(underline_btn)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Sunken)
        sep.setFixedHeight(25)
        format_row.addWidget(sep)
        
        # Color
        color_btn = QPushButton("🎨")
        color_btn.setFixedSize(36, 30)
        color_btn.setToolTip("Color")
        color_btn.clicked.connect(self.pick_color)
        format_row.addWidget(color_btn)
        
        # Clear formatting
        clear_btn = QPushButton("🗑️")
        clear_btn.setFixedSize(36, 30)
        clear_btn.setToolTip("Clear Formatting")
        clear_btn.clicked.connect(self.clear_formatting)
        format_row.addWidget(clear_btn)
        
        format_row.addStretch()
        notes_layout.addLayout(format_row)

        # Notes display
        self.notes_display = QTextEdit()
        self.notes_display.setFont(QFont("Segoe UI", 11))
        self.notes_display.setPlaceholderText("Take notes here...")
        self.notes_display.setAcceptRichText(True)
        notes_layout.addWidget(self.notes_display)
        
        # Save/Clear buttons
        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_notes)
        btn_row.addWidget(save_btn)
        clear_all_btn = QPushButton("Clear All")
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
    
    # ========== END FORMATTING METHODS ==========
    
    def on_voice_changed(self, voice):
        self.tts.set_voice(voice)
        self.statusBar().showMessage(f"Voice changed to: {voice}", 2000)
        self.audio_data = None
        self.sample_rate = None
    
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
            if self.is_playing:
                self.stop_playback()
            else:
                self.play_text()
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
            self.audio_data = None
            self.sample_rate = None
            
            self.setWindowTitle(f"StudyPal - {Path(file_path).name}")
            self.statusBar().showMessage(f"Loaded: {Path(file_path).name}")
            self.add_recent_file(file_path)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
    
    def on_speed_changed(self, value):
        speed = value / 100.0
        self.speed_label.setText(f"{speed:.1f}x")
    
    def play_text(self):
        text = self.text_display.toPlainText().strip()
        if not text:
            return
        
        self.play_btn.setEnabled(False)
        self.play_btn.setText("Generating...")
        self.statusBar().showMessage("Generating speech...")
        
        def generate_and_play():
            try:
                speed = self.speed_slider.value() / 100.0
                audio, sr = self.tts.generate_audio(text, speed)
                self.audio_data = audio
                self.sample_rate = sr
                self.player.play(audio, sr)
                
                self.is_playing = True
                self.play_btn.setText("Playing...")
                self.stop_btn.setEnabled(True)
                self.statusBar().showMessage("Playing...")
                
            except Exception as e:
                self.play_btn.setText("Play")
                self.play_btn.setEnabled(True)
                QMessageBox.critical(self, "Error", str(e))
                self.statusBar().showMessage("Error")
        
        threading.Thread(target=generate_and_play, daemon=True).start()
    
    def stop_playback(self):
        self.is_playing = False
        self.player.stop()
        self.play_btn.setText("Play")
        self.play_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.statusBar().showMessage("Stopped")
    
    def save_notes(self):
        content = self.notes_display.toHtml()
        if not content.strip():
            QMessageBox.information(self, "Empty Notes", "Nothing to save.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Notes",
            str(Path.home() / "notes.txt"),
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
