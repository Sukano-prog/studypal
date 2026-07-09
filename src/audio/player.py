"""
AudioPlayer - callback-driven playback with pause/resume/seek/speed.

Design notes:
- Uses a sounddevice.OutputStream in callback mode so playback runs on
  PortAudio's own thread. All shared state is protected by a single lock.
- "Speed" here is implemented as a playback-rate multiplier (resampling
  on read), not a pitch-preserving time-stretch. This is a deliberate,
  documented simplification: it's cheap, has no external deps beyond
  numpy, and is good enough for spoken-word content. If true
  pitch-preserving speed control is needed later, swap _read_block's
  resampling for a phase-vocoder / WSOLA implementation.
- The class never touches Qt widgets directly. Callers (e.g. a QTimer
  in the GUI thread) should poll get_position()/is_finished() instead
  of this class pushing updates into widgets from a worker thread.
"""

import threading
import numpy as np
import sounddevice as sd


class AudioPlayer:
    def __init__(self):
        self._lock = threading.Lock()
        self._audio = None          # mono/stereo float32 array, shape (n, channels)
        self._sr = None
        self._channels = 1
        self._pos = 0.0              # read position in source-sample units (float, for fractional speed)
        self._speed = 1.0
        self._playing = False
        self._paused = False
        self._stream = None
        self._finished = False

    # ---------- loading ----------

    def load(self, audio, sr):
        """audio: 1-D (mono) or 2-D (n, channels) float array."""
        with self._lock:
            self.stop_stream_locked()
            audio = np.asarray(audio, dtype=np.float32)
            if audio.ndim == 1:
                audio = audio.reshape(-1, 1)
            self._audio = audio
            self._sr = sr
            self._channels = audio.shape[1]
            self._pos = 0.0
            self._speed = 1.0
            self._finished = False

    @property
    def duration(self):
        with self._lock:
            if self._audio is None or self._sr is None:
                return 0.0
            return len(self._audio) / self._sr

    @property
    def loaded(self):
        with self._lock:
            return self._audio is not None

    @property
    def is_playing(self):
        with self._lock:
            return self._playing and not self._paused

    @property
    def is_paused(self):
        with self._lock:
            return self._paused

    # ---------- transport ----------

    def play(self):
        """Start playback from current position, or resume if paused."""
        with self._lock:
            if self._audio is None:
                return
            self._paused = False
            self._finished = False
            if self._stream is None:
                self._open_stream_locked()
            self._playing = True

    def pause(self):
        with self._lock:
            self._paused = True

    def stop(self):
        with self._lock:
            self.stop_stream_locked()
            self._pos = 0.0
            self._playing = False
            self._paused = False
            self._finished = False

    def seek(self, seconds):
        with self._lock:
            if self._audio is None or self._sr is None:
                return
            max_seconds = len(self._audio) / self._sr
            seconds = max(0.0, min(seconds, max_seconds))
            self._pos = seconds * self._sr
            self._finished = False

    def set_speed(self, speed):
        with self._lock:
            self._speed = max(0.25, min(4.0, float(speed)))

    def get_position(self):
        with self._lock:
            if self._sr is None:
                return 0.0
            return self._pos / self._sr

    def is_finished(self):
        with self._lock:
            return self._finished

    # ---------- internals ----------

    def _open_stream_locked(self):
        def callback(outdata, frames, time_info, status):
            with self._lock:
                if self._audio is None or self._paused:
                    outdata[:] = 0
                    return
                block, advanced = self._read_block_locked(frames)
                outdata[:len(block)] = block
                if len(block) < frames:
                    outdata[len(block):] = 0
                self._pos += advanced
                if self._pos >= len(self._audio):
                    self._finished = True
                    self._playing = False
                    raise sd.CallbackStop()

        self._stream = sd.OutputStream(
            samplerate=self._sr,
            channels=self._channels,
            callback=callback,
            dtype="float32",
        )
        self._stream.start()

    def _read_block_locked(self, frames):
        """Read `frames` output samples, resampled by self._speed, advancing
        self._pos by the corresponding number of *source* samples."""
        audio = self._audio
        n = len(audio)
        src_needed = frames * self._speed
        start = self._pos
        end = min(start + src_needed, n)
        if end <= start:
            return np.zeros((0, self._channels), dtype=np.float32), 0.0

        src_indices = np.linspace(start, end, num=frames, endpoint=False)
        src_indices = np.clip(src_indices, 0, n - 1)
        idx_floor = src_indices.astype(np.int64)
        idx_ceil = np.clip(idx_floor + 1, 0, n - 1)
        frac = (src_indices - idx_floor).astype(np.float32).reshape(-1, 1)

        block = audio[idx_floor] * (1 - frac) + audio[idx_ceil] * frac
        advanced = end - start
        return block.astype(np.float32), advanced

    def stop_stream_locked(self):
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
