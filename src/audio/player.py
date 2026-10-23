"""Audio player ΓÇö Windows winsound backend to avoid VM audio deadlocks.

sounddevice (PortAudio) and simpleaudio both hang in this VirtualBox VM
when starting playback. winsound is a native Windows API that plays WAV
files reliably and never hangs.

Pause/resume is implemented by stopping the WAV playback and restarting
from a cropped WAV at the paused sample offset.
"""

import sys
import os
import time
import threading
import tempfile
import numpy as np

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import winsound
    import soundfile as sf
else:
    import sounddevice as sd


class AudioPlayer:
    def __init__(self):
        self.audio_data = None
        self.sample_rate = 44100
        self.speed = 1.0
        self.base_duration = 0.0
        self.duration = 0.0
        self._is_playing = False
        self._is_paused = False
        self._start_time = 0.0
        self._pause_position = 0.0
        self._lock = threading.RLock()  # RLock is reentrant
        self._temp_wav = os.path.join(tempfile.gettempdir(), "_studypal_play.wav")

    def load(self, audio_data, sample_rate):
        with self._lock:
            self.stop()
            self.audio_data = np.asarray(audio_data, dtype=np.float32)
            self.sample_rate = sample_rate
            self.base_duration = len(self.audio_data) / sample_rate
            self.duration = self.base_duration / self.speed
            self._pause_position = 0.0

    def play(self):
        with self._lock:
            if self.audio_data is None:
                return
            if self._is_playing and not self._is_paused:
                return

            # Stop whatever is currently playing
            self._stop_hardware()

            if self._is_paused:
                # Resume: crop from paused position
                start_sample = int(self._pause_position * self.sample_rate)
                remaining = self.audio_data[start_sample:]
                if len(remaining) == 0:
                    return
                self._play_samples(remaining)
                self._start_time = time.time() - (self._pause_position / self.speed)
                self._is_paused = False
            else:
                self._play_samples(self.audio_data)
                self._start_time = time.time()
                self._pause_position = 0.0

            self._is_playing = True

    def pause(self):
        with self._lock:
            if not self._is_playing or self._is_paused:
                return
            self._pause_position = self.get_position()
            self._stop_hardware()
            self._is_paused = True
            self._is_playing = False

    def stop(self):
        with self._lock:
            self._stop_hardware()
            self._is_playing = False
            self._is_paused = False
            self._pause_position = 0.0

    def get_position(self):
        with self._lock:
            if self._is_paused:
                return self._pause_position
            if not self._is_playing:
                return 0.0
            elapsed = time.time() - self._start_time
            pos = elapsed * self.speed
            if pos >= self.duration:
                self._is_playing = False
                return self.duration
            return pos

    def play_from(self, position):
        with self._lock:
            self._stop_hardware()
            self._pause_position = position
            self._is_paused = True
            self._is_playing = False
        self.play()

    @property
    def is_playing(self):
        return self._is_playing

    @property
    def is_paused(self):
        return self._is_paused

    # ---------- hardware abstraction ----------

    def _play_samples(self, audio_float32):
        """Write float32 audio to temp WAV and play it."""
        if IS_WINDOWS:
            # winsound only accepts int16 WAV files
            audio_int16 = (np.clip(audio_float32, -1.0, 1.0) * 32767).astype(np.int16)
            sf.write(self._temp_wav, audio_int16, self.sample_rate, subtype='PCM_16')
            winsound.PlaySound(self._temp_wav, winsound.SND_FILENAME | winsound.SND_ASYNC)
        else:
            sd.play(audio_float32, int(self.sample_rate * self.speed))

    def _stop_hardware(self):
        """Kill whatever audio is currently playing."""
        if IS_WINDOWS:
            winsound.PlaySound(None, 0)  # 0 = stop, do NOT use SND_PURGE (hangs on Windows VM)
        else:
            sd.stop()
