"""
TTS engine.

Two backends behind one interface (get_voice_list / set_voice / generate):

- PiperBackend (Linux/macOS): shells out to the `piper` CLI.
- WindowsSapiBackend (Windows): uses pyttsx3, but crucially calls
  `save_to_file()` + `runAndWait()` to render to a WAV file, then reads
  that file back with soundfile. The previous implementation called
  `engine.say()` (which plays live through the OS and returns no audio
  data) and then returned a 1-sample dummy array -- so on Windows the
  app never actually had real audio to play, seek through, or measure
  the duration of. This backend also creates a **fresh pyttsx3.Engine()
  per call** rather than reusing one instance, which avoids a
  well-known SAPI5 hang where calling say()/runAndWait() a second time
  on the same engine instance blocks forever.

Both backends: cache generated audio on disk keyed by (text, speed,
voice), and transparently chunk long text so a single call doesn't
choke the underlying engine.
"""

import hashlib
import os
import platform
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf


class TTSError(Exception):
    pass


# ---------- shared helpers ----------

def _cache_key(text, speed, voice):
    content = f"{text}|{speed:.2f}|{voice}"
    return hashlib.md5(content.encode("utf-8")).hexdigest()[:16]


def _chunk_text(text, max_chars=2500):
    """Split on word boundaries into chunks no longer than max_chars."""
    words = text.split()
    chunks = []
    current, current_len = [], 0
    for word in words:
        if current_len + len(word) + 1 > max_chars and current:
            chunks.append(" ".join(current))
            current, current_len = [], 0
        current.append(word)
        current_len += len(word) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks


class _CachedBackend:
    """Common generate() flow: chunk -> per-chunk cache -> concat."""

    CHUNK_THRESHOLD = 3000

    def __init__(self):
        self.cache_dir = Path.home() / ".cache" / "studypal"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, text, speed=1.0):
        if len(text) <= self.CHUNK_THRESHOLD:
            return self._generate_chunk_cached(text, speed)

        all_audio, sr = [], None
        for chunk in _chunk_text(text):
            audio, sr = self._generate_chunk_cached(chunk, speed)
            all_audio.append(audio)
        return np.concatenate(all_audio), sr

    def _generate_chunk_cached(self, text, speed):
        voice = self.current_voice
        key = _cache_key(text, speed, voice)
        cache_file = self.cache_dir / f"{key}.wav"
        if cache_file.exists():
            audio, sr = sf.read(str(cache_file))
            return audio, sr
        audio, sr = self._generate_chunk(text, speed)
        try:
            sf.write(str(cache_file), audio, sr)
        except Exception:
            pass  # cache is best-effort; not fatal if it fails
        return audio, sr


# ---------- Linux/macOS backend ----------

class PiperBackend(_CachedBackend):
    VOICE_MODELS = {
        "Sarah (Female, Natural)": {
            "file": "en_US-lessac-medium.onnx",
        },
        "Michael (Male, Natural)": {
            "file": "en_US-ryan-medium.onnx",
        },
    }

    def __init__(self):
        super().__init__()
        self.voice_dir = Path.home() / ".local" / "share" / "piper"
        self.available_voices = [
            name for name, info in self.VOICE_MODELS.items()
            if (self.voice_dir / info["file"]).exists()
        ]
        self.current_voice = self.available_voices[0] if self.available_voices else None
        self.available = bool(self.available_voices)

    def get_voice_list(self):
        return self.available_voices

    def set_voice(self, voice_name):
        if voice_name in self.available_voices:
            self.current_voice = voice_name
            return True
        return False

    def generate(self, text, speed=1.0):
        if not self.available or self.current_voice is None:
            raise TTSError(
                "No Piper voice models found. Install voices under "
                f"{self.voice_dir}"
            )
        return super().generate(text, speed)

    def _generate_chunk(self, text, speed):
        voice_info = self.VOICE_MODELS[self.current_voice]
        model_path = self.voice_dir / voice_info["file"]

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            output_file = tmp.name

        try:
            length_scale = 1.0 / max(speed, 0.01)
            cmd = [
                "piper",
                "--model", str(model_path),
                "--length_scale", str(length_scale),
                "--output_file", output_file,
            ]

            espeak_data = None
            for candidate in (
                "/usr/lib/x86_64-linux-gnu/espeak-ng-data",
                "/usr/share/espeak-ng-data",
            ):
                if os.path.exists(candidate):
                    espeak_data = candidate
                    break
            if espeak_data:
                cmd.extend(["--espeak_data", espeak_data])

            process = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate(text.encode("utf-8"), timeout=120)

            if process.returncode != 0:
                error_msg = stderr.decode(errors="ignore") if stderr else "Unknown error"
                raise TTSError(f"Piper error: {error_msg}")

            audio, sr = sf.read(output_file)
            return audio, sr

        except subprocess.TimeoutExpired:
            process.kill()
            raise TTSError("TTS generation timed out")
        finally:
            if os.path.exists(output_file):
                try:
                    os.unlink(output_file)
                except OSError:
                    pass


# ---------- Windows backend ----------

class WindowsSapiBackend(_CachedBackend):
    def __init__(self):
        super().__init__()
        self.available_voices = []
        self.current_voice = None
        self._voice_id_by_name = {}
        self.available = False

        try:
            import pyttsx3
        except ImportError:
            return

        try:
            probe = pyttsx3.init()
            for v in probe.getProperty("voices"):
                name = v.name or v.id
                self._voice_id_by_name[name] = v.id
                self.available_voices.append(name)
            probe.stop()
        except Exception:
            self.available_voices = []

        if self.available_voices:
            self.current_voice = self.available_voices[0]
            self.available = True

    def get_voice_list(self):
        return self.available_voices

    def set_voice(self, voice_name):
        if voice_name in self._voice_id_by_name:
            self.current_voice = voice_name
            return True
        return False

    def generate(self, text, speed=1.0):
        if not self.available:
            raise TTSError(
                "No Windows SAPI5 voices available (pyttsx3 not installed "
                "or no voices registered)."
            )
        return super().generate(text, speed)

    def _generate_chunk(self, text, speed):
        import pyttsx3  # local import: only needed on this backend

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            output_file = tmp.name

        try:
            # Fresh engine per call avoids the known SAPI5 hang where a
            # second say()/runAndWait() on a reused engine instance blocks.
            engine = pyttsx3.init()
            try:
                voice_id = self._voice_id_by_name.get(self.current_voice)
                if voice_id:
                    engine.setProperty("voice", voice_id)
                # SAPI5 words-per-minute; 150 wpm ~= 1.0x baseline
                engine.setProperty("rate", int(150 * max(speed, 0.1)))
                engine.save_to_file(text, output_file)
                engine.runAndWait()
            finally:
                engine.stop()

            if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                raise TTSError("SAPI5 did not produce an audio file.")

            audio, sr = sf.read(output_file)
            return audio, sr
        finally:
            if os.path.exists(output_file):
                try:
                    os.unlink(output_file)
                except OSError:
                    pass


# ---------- unified manager ----------

class TTSManager:
    """Facade the GUI talks to; picks the right backend for the platform."""

    def __init__(self):
        if platform.system() == "Windows":
            self.backend = WindowsSapiBackend()
        else:
            self.backend = PiperBackend()

    @property
    def available(self):
        return self.backend.available

    def get_voice_list(self):
        return self.backend.get_voice_list()

    def set_voice(self, voice_name):
        return self.backend.set_voice(voice_name)

    def generate_audio(self, text, speed=1.0):
        return self.backend.generate(text, speed)
