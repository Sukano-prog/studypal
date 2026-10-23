"""Annotation sidebar panel for the Listen/Read tab.

Shows all annotations for the current document, filterable, clickable to
jump the transcript cursor to the annotation's position.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QComboBox, QPushButton, QMessageBox,
)

from annotations import AnnotationType


# Icon per annotation type
TYPE_ICONS = {
    "bookmark": "📌",
    "highlight": "🖍",
    "note": "📝",
    "voice_note": "🎙",
    "question": "❓",
    "silence": "🔇",
    "music": "🎵",
    "noise": "🔊",
    "applause": "👏",
    "laughter": "😄",
    "speaker_change": "🗣",
}

FILTER_OPTIONS = [
    ("All", None),
    ("Bookmarks", "bookmark"),
    ("Highlights", "highlight"),
    ("Notes", "note"),
    ("Silences", "silence"),
    ("Music", "music"),
    ("Noise", "noise"),
]


class AnnotationPanel(QWidget):
    """Right-side dock listing annotations for the current transcript."""

    # Emitted when user clicks an annotation — main view should jump cursor
    annotation_clicked = Signal(int, int)   # char_start, char_end
    # Emitted when user deletes an annotation
    annotation_deleted = Signal(str)        # annotation id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._repo = None
        self._doc_hash = None
        self._items = []
        self._build_ui()

    def set_repo(self, repo):
        self._repo = repo

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Header
        self.header = QLabel("Annotations")
        self.header.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.header)

        # Filter dropdown
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Show:"))
        self.filter_combo = QComboBox()
        for label, value in FILTER_OPTIONS:
            self.filter_combo.addItem(label, value)
        self.filter_combo.currentIndexChanged.connect(self._apply_filter)
        filter_row.addWidget(self.filter_combo, 1)
        layout.addLayout(filter_row)

        # List widget
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        layout.addWidget(self.list_widget, 1)

        # Bottom buttons
        btn_row = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        btn_row.addWidget(self.refresh_btn)

        self.clear_btn = QPushButton("Clear all")
        self.clear_btn.clicked.connect(self._clear_all)
        btn_row.addWidget(self.clear_btn)

        layout.addLayout(btn_row)

    # ---------- public API ----------

    def load_doc(self, doc_hash: str):
        """Set the current document and load its annotations."""
        self._doc_hash = doc_hash
        self.refresh()

    def refresh(self):
        """Reload annotations from DB and re-render list."""
        self.list_widget.clear()
        self._items = []

        if not self._repo or not self._doc_hash:
            self.header.setText("Annotations (0)")
            return

        try:
            items = self._repo.list_for_doc(self._doc_hash)
        except Exception as e:
            print(f"[panel] Failed to load annotations: {e}")
            return

        self._items = items
        self._render_list()
        self.header.setText(f"Annotations ({len(items)})")

    # ---------- internals ----------

    def _render_list(self):
        active_filter = self.filter_combo.currentData()
        shown = 0

        for ann in self._items:
            if active_filter and ann.type.value != active_filter:
                continue

            shown += 1
            icon = TYPE_ICONS.get(ann.type.value, "•")
            line_str = f"L{ann.line_number}" if ann.line_number else f"{ann.audio_ms/1000:.1f}s" if ann.audio_ms else "?"
            content = ann.content or ann.type.value

            # Truncate content
            if len(content) > 40:
                content = content[:37] + "..."

            text = f"{icon}  {line_str}  {content}"

            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, ann.id)
            item.setData(Qt.UserRole + 1, ann.char_start)
            item.setData(Qt.UserRole + 2, ann.char_end)

            # Color background by type
            if ann.type.value == "silence":
                item.setForeground(Qt.gray)
            elif ann.color:
                # Booksmarks/highlights: use stored hex color as background
                try:
                    from PySide6.QtGui import QColor, QBrush
                    item.setBackground(QBrush(QColor(ann.color)))
                except Exception:
                    pass

            self.list_widget.addItem(item)

        if shown == 0:
            empty = QListWidgetItem("No annotations yet")
            empty.setForeground(Qt.gray)
            empty.setFlags(Qt.NoItemFlags)  # non-selectable
            self.list_widget.addItem(empty)

    def _apply_filter(self):
        self._render_list()

    def _on_item_clicked(self, item):
        ann_id = item.data(Qt.UserRole)
        if not ann_id:
            return
        char_start = item.data(Qt.UserRole + 1) or 0
        char_end = item.data(Qt.UserRole + 2) or 0
        self.annotation_clicked.emit(char_start, char_end)

    def _clear_all(self):
        if not self._repo or not self._doc_hash:
            return
        count = len(self._items)
        if count == 0:
            return
        answer = QMessageBox.question(
            self,
            "Clear annotations",
            f"Delete all {count} annotations for this file?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        deleted = self._repo.delete_for_doc(self._doc_hash)
        print(f"[panel] Deleted {deleted} annotations")
        self.refresh()
