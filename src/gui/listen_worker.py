"""QThread worker for transcription + translation (keeps UI responsive)."""
from PySide6.QtCore import QThread, Signal


class ListenWorker(QThread):
    """Runs TranscriptionService.process() in a background thread."""

    progress = Signal(str)        # status text
    progress_pct = Signal(int)    # 0-100
    finished = Signal(dict)       # result dict
    error = Signal(str)           # error message

    def __init__(self, service, audio_path: str, target_language: str = None):
        super().__init__()
        self.service = service
        self.audio_path = audio_path
        self.target_language = target_language

    def run(self):
        try:
            self.progress.emit("Transcribing audio...")
            self.progress_pct.emit(0)

            def cb(pct, info):
                self.progress_pct.emit(int(pct))
                self.progress.emit(info)

            result = self.service.process(
                self.audio_path,
                target_language=self.target_language,
                progress_callback=cb,
            )
            self.progress_pct.emit(100)
            self.progress.emit("Done.")
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
