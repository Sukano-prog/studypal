"""
TTSWorker - runs TTSManager.generate_audio() on a QThread and reports
back via signals.

Lifecycle note: the previous version relied on Python reference
counting to keep the QThread alive (a plain attribute on MainWindow
that got set to None as soon as `finished`/`error` fired). That's
unsafe: QThread.quit() only *requests* the thread's event loop stop;
the OS thread may still be shutting down when the Python object gets
garbage collected, which crashes with "QThread: Destroyed while
thread is still running". Two things fix this:

1. The QThread is parented to a long-lived Qt object (MainWindow),
   so Qt's own ownership keeps the C++ object alive regardless of
   Python refcounts.
2. We only let the caller drop its reference after `thread.finished`
   actually fires (exposed here as the `done` signal) -- not after
   `finished`/`error`, which fire *before* the thread has fully
   stopped.
"""

from PySide6.QtCore import QObject, QThread, Signal


class _Worker(QObject):
    finished = Signal(object, object)  # audio, sample_rate
    error = Signal(str)

    def __init__(self, tts_manager, text, speed):
        super().__init__()
        self.tts_manager = tts_manager
        self.text = text
        self.speed = speed

    def run(self):
        try:
            audio, sr = self.tts_manager.generate_audio(self.text, self.speed)
            self.finished.emit(audio, sr)
        except Exception as e:
            self.error.emit(str(e))


class TTSWorker(QObject):
    finished = Signal(object, object)
    error = Signal(str)
    done = Signal()  # thread has fully stopped; safe to release the last reference

    def __init__(self, tts_manager, text, speed, parent=None):
        super().__init__(parent)
        self._thread = QThread(self)
        self._inner = _Worker(tts_manager, text, speed)
        self._inner.moveToThread(self._thread)

        self._thread.started.connect(self._inner.run)
        self._inner.finished.connect(self.finished)
        self._inner.error.connect(self.error)
        self._inner.finished.connect(self._thread.quit)
        self._inner.error.connect(self._thread.quit)
        self._thread.finished.connect(self._inner.deleteLater)
        self._thread.finished.connect(self.done)

    def start(self):
        self._thread.start()

    def is_running(self):
        return self._thread.isRunning()

    def stop_and_wait(self, timeout_ms=5000):
        """Used on app shutdown to make sure the thread is fully stopped
        before the process exits."""
        if self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(timeout_ms)
