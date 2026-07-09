"""
NotesPanel - rich-text notes editor with a small formatting toolbar
(bold/italic/underline/color/clear) plus new/save/clear-all actions.
"""

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextCharFormat, QTextCursor, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QColorDialog, QMessageBox, QFileDialog,
)


class NotesPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("\U0001f4dd Notes")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        layout.addWidget(self._build_format_toolbar())

        self.editor = QTextEdit()
        self.editor.setFont(QFont("Segoe UI", 11))
        self.editor.setPlaceholderText("Take notes here...")
        self.editor.setAcceptRichText(True)
        layout.addWidget(self.editor)

        layout.addLayout(self._build_action_row())

    def _build_format_toolbar(self):
        toolbar = QWidget()
        toolbar.setFixedHeight(40)
        row = QHBoxLayout(toolbar)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(5)

        btn_style = (
            "font-size: 15px; background-color: #3a3a6e; "
            "color: white; border-radius: 4px;"
        )

        bold_btn = QPushButton(" B ")
        bold_btn.setFixedSize(40, 32)
        bold_btn.setStyleSheet(f"font-weight: bold; {btn_style}")
        bold_btn.setToolTip("Bold")
        bold_btn.clicked.connect(self.toggle_bold)
        row.addWidget(bold_btn)

        italic_btn = QPushButton(" I ")
        italic_btn.setFixedSize(40, 32)
        italic_btn.setStyleSheet(f"font-style: italic; {btn_style}")
        italic_btn.setToolTip("Italic")
        italic_btn.clicked.connect(self.toggle_italic)
        row.addWidget(italic_btn)

        underline_btn = QPushButton(" U ")
        underline_btn.setFixedSize(40, 32)
        underline_btn.setStyleSheet(f"text-decoration: underline; {btn_style}")
        underline_btn.setToolTip("Underline")
        underline_btn.clicked.connect(self.toggle_underline)
        row.addWidget(underline_btn)

        color_btn = QPushButton(" \U0001f3a8 ")
        color_btn.setFixedSize(42, 32)
        color_btn.setStyleSheet(btn_style)
        color_btn.setToolTip("Text Color")
        color_btn.clicked.connect(self.pick_color)
        row.addWidget(color_btn)

        clear_btn = QPushButton(" \U0001f5d1 ")
        clear_btn.setFixedSize(42, 32)
        clear_btn.setStyleSheet(btn_style)
        clear_btn.setToolTip("Clear Formatting")
        clear_btn.clicked.connect(self.clear_formatting)
        row.addWidget(clear_btn)

        row.addStretch()
        return toolbar

    def _build_action_row(self):
        row = QHBoxLayout()
        new_btn = QPushButton("\U0001f4c4 New")
        new_btn.clicked.connect(self.new_note)
        row.addWidget(new_btn)

        save_btn = QPushButton("\U0001f4be Save")
        save_btn.clicked.connect(self.save_notes)
        row.addWidget(save_btn)

        clear_all_btn = QPushButton("\U0001f5d1\ufe0f Clear All")
        clear_all_btn.clicked.connect(self.clear_notes)
        row.addWidget(clear_all_btn)

        row.addStretch()
        return row

    # ---------- formatting ----------

    def toggle_bold(self):
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            fmt = QTextCharFormat()
            weight = QFont.Normal if cursor.charFormat().fontWeight() == QFont.Bold else QFont.Bold
            fmt.setFontWeight(weight)
            cursor.mergeCharFormat(fmt)
        else:
            current = self.editor.fontWeight()
            self.editor.setFontWeight(QFont.Normal if current == QFont.Bold else QFont.Bold)

    def toggle_italic(self):
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            fmt = QTextCharFormat()
            fmt.setFontItalic(not cursor.charFormat().fontItalic())
            cursor.mergeCharFormat(fmt)
        else:
            self.editor.setFontItalic(not self.editor.fontItalic())

    def toggle_underline(self):
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            fmt = QTextCharFormat()
            fmt.setFontUnderline(not cursor.charFormat().fontUnderline())
            cursor.mergeCharFormat(fmt)
        else:
            self.editor.setFontUnderline(not self.editor.fontUnderline())

    def pick_color(self):
        color = QColorDialog.getColor()
        if not color.isValid():
            return
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            cursor.mergeCharFormat(fmt)
        else:
            self.editor.setTextColor(color)

    def clear_formatting(self):
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.Document)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("black"))
        fmt.setBackground(Qt.transparent)
        fmt.setFontWeight(QFont.Normal)
        fmt.setFontItalic(False)
        fmt.setFontUnderline(False)
        cursor.mergeCharFormat(fmt)

    # ---------- actions ----------

    def new_note(self):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.editor.append(f"\n\n--- New Note: {timestamp} ---\n")

    def save_notes(self):
        content = self.editor.toHtml()
        if not self.editor.toPlainText().strip():
            QMessageBox.information(self, "Empty Notes", "Nothing to save.")
            return None

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Notes", str(Path.home() / "notes.html"),
            "HTML Files (*.html);;Text Files (*.txt);;All Files (*.*)",
        )
        if not file_path:
            return None

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                if file_path.endswith(".html"):
                    f.write(content)
                else:
                    f.write(self.editor.toPlainText())
            return file_path
        except OSError as e:
            QMessageBox.critical(self, "Error", f"Failed to save notes:\n{e}")
            return None

    def clear_notes(self):
        reply = QMessageBox.question(
            self, "Clear Notes", "Clear all notes?", QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.editor.clear()
