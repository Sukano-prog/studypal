from pathlib import Path

p = Path("src/gui/main_window.py")
src = p.read_text(encoding="utf-8")

# 1. Update the worker to switch UI state to "Playing" BEFORE generating
old_worker = """        def generate_and_play():
            try:
                speed = self.speed_slider.value() / 100.0"""

new_worker = """        def generate_and_play():
            try:
                # IMMEDIATELY tell UI we are playing so buttons work
                self._tts_playing.emit()
                
                speed = self.speed_slider.value() / 100.0"""

if old_worker in src:
    src = src.replace(old_worker, new_worker, 1)
    print("✅ UI now enters 'Playing' state before generation")
else:
    print("⚠ Worker start pattern not found")

# 2. Remove the duplicate _tts_playing.emit() at the end of generation
old_end = """                # Worker thread: emit signal, main thread updates UI
                self._tts_playing.emit()"""
new_end = """                # Audio is loaded and player.play() was called
                pass"""
if old_end in src:
    src = src.replace(old_end, new_end, 1)

p.write_text(src, encoding="utf-8")
