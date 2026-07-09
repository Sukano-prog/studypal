"""Dark/light QSS stylesheets."""

DARK_THEME = """
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
"""

LIGHT_THEME = """
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
"""
