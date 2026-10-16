"""
TTS engine with multiple voices and chunking for long texts
"""

import subprocess
import tempfile
import os
from pathlib import Path
import soundfile as sf
import hashlib
import platform
import numpy as np

from utils.paths import get_piper_voices_dir, get_cache_dir

class WindowsTTS:
    def __init__(self):
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.has_pyttsx3 = True
        except:
            self.has_pyttsx3 = False
            print("Warning: pyttsx3 not available")
    
    def generate(self, text, speed=1.0):
        if not self.has_pyttsx3:
            raise Exception("pyttsx3 not available")
        self.engine.setProperty('rate', int(speed * 150))
        self.engine.say(text)
        self.engine.runAndWait()
        import numpy as np
        return np.array([0]), 22050

class TTSGenerator:
    # Available voice models
    VOICE_MODELS = {
        # --- English ---
        "🇬🇧 Sarah (English F)": {
            "model": "en_US-lessac-medium",
            "file": "en_US-lessac-medium.onnx",
            "description": "Natural female voice",
            "lang": "en",
        },
        "🇬🇧 Michael (English M)": {
            "model": "en_US-ryan-medium",
            "file": "en_US-ryan-medium.onnx",
            "description": "Natural male voice",
            "lang": "en",
        },
        "🇬🇧 Sarah Light (English F)": {
            "model": "en_US-lessac-low",
            "file": "en_US-lessac-low.onnx",
            "description": "Faster, lighter female voice",
            "lang": "en",
        },
        "👶 Amy (Kid-friendly English F)": {
            "model": "en_US-amy-low",
            "file": "en_US-amy-low.onnx",
            "description": "Warm, kid-friendly voice",
            "lang": "en",
            "kid_friendly": True,
        },
        # --- Swahili ---
        "🇰🇪 Lanfrica (Swahili F)": {
            "model": "sw_CD-lanfrica-medium",
            "file": "sw_CD-lanfrica-medium.onnx",
            "description": "Swahili female voice",
            "lang": "sw",
        },
        # --- French ---
        "🇫🇷 Siwis (French F)": {
            "model": "fr_FR-siwis-medium",
            "file": "fr_FR-siwis-medium.onnx",
            "description": "French female voice",
            "lang": "fr",
        },
        # --- Spanish ---
        "🇪🇸 DaveFX (Spanish M)": {
            "model": "es_ES-davefx-medium",
            "file": "es_ES-davefx-medium.onnx",
            "description": "Spanish male voice",
            "lang": "es",
        },
        # --- German ---
        "🇩🇪 Thorsten (German M)": {
            "model": "de_DE-thorsten-medium",
            "file": "de_DE-thorsten-medium.onnx",
            "description": "German male voice",
            "lang": "de",
        },
        # --- Portuguese ---
        "🇧🇷 Faber (Portuguese M)": {
            "model": "pt_BR-faber-medium",
            "file": "pt_BR-faber-medium.onnx",
            "description": "Brazilian Portuguese male voice",
            "lang": "pt",
        },
        # --- Arabic ---
        "🇸🇦 Kareem (Arabic M)": {
            "model": "ar_JO-kareem-medium",
            "file": "ar_JO-kareem-medium.onnx",
            "description": "Arabic male voice",
            "lang": "ar",
        },
        # --- Chinese ---
        "🇨🇳 Huayan (Chinese F)": {
            "model": "zh_CN-huayan-medium",
            "file": "zh_CN-huayan-medium.onnx",
            "description": "Mandarin Chinese female voice",
            "lang": "zh",
        },
        # --- Hindi ---
        "🇮🇳 Pratham (Hindi M)": {
            "model": "hi_IN-pratham-medium",
            "file": "hi_IN-pratham-medium.onnx",
            "description": "Hindi male voice",
            "lang": "hi",
        },
    }

    # Only these voices appear in the UI dropdown.
    # All others stay registered + cached on disk — just add them back here to re-enable.
    SHOW_IN_DROPDOWN = [
        "🇬🇧 Sarah (English F)",
        "🇬🇧 Michael (English M)",
        "👶 Amy (Kid-friendly English F)",
    ]
    
    def __init__(self):
        self.voice_dir = get_piper_voices_dir()
        self.cache_dir = get_cache_dir() / "tts"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Detect available voices
        self.available_voices = []
        for voice_name, voice_info in self.VOICE_MODELS.items():
            model_path = self.voice_dir / voice_info["file"]
            if model_path.exists():
                self.available_voices.append(voice_name)
        
        self.current_voice = self.available_voices[0] if self.available_voices else None
        self.available = len(self.available_voices) > 0
        self._cancel_requested = False
        
        if not self.available:
            print("WARNING: No Piper models found.")
    
    def get_voice_list(self):
        """Return only the voices marked visible in SHOW_IN_DROPDOWN."""
        if self.SHOW_IN_DROPDOWN:
            return [v for v in self.available_voices if v in self.SHOW_IN_DROPDOWN]
        return self.available_voices

    @property
    def voices_by_lang(self):
        """Return {lang_code: [voice_name, ...]} for installed voices."""
        result = {}
        for name in self.available_voices:
            lang = self.VOICE_MODELS.get(name, {}).get("lang")
            if lang:
                result.setdefault(lang, []).append(name)
        return result

    def find_voice_for_lang(self, lang_code, kid_friendly=False):
        """Find the best voice for a language. Falls back to English."""
        if not lang_code:
            return None
        # Try exact match
        for name in self.available_voices:
            info = self.VOICE_MODELS.get(name, {})
            if info.get("lang") == lang_code:
                if kid_friendly and info.get("kid_friendly"):
                    return name
                if not kid_friendly:
                    return name
        # No exact match — try English
        if lang_code != "en":
            return self.find_voice_for_lang("en", kid_friendly=kid_friendly)
        return None

    def find_kid_voice(self):
        """Find a kid-friendly voice (usually Amy)."""
        for name in self.available_voices:
            if self.VOICE_MODELS.get(name, {}).get("kid_friendly"):
                return name
        return None

    def set_voice(self, voice_name):
        if voice_name in self.available_voices:
            self.current_voice = voice_name
            return True
        return False
    
    def get_cache_key(self, text, speed, voice):
        content = f"{text}|{speed:.2f}|{voice}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def cancel(self):
        """Request generation to stop at the next chunk boundary."""
        self._cancel_requested = True
        print("[TTS] Cancel requested")

    def reset_cancel(self):
        """Clear the cancel flag before starting a fresh generation."""
        self._cancel_requested = False

    def generate(self, text, speed=1.0):
        if not self.available or self.current_voice is None:
            raise Exception("No voice available")
        
        # If text is short, generate directly (one chunk)
        if len(text) <= 3000:
            if self._cancel_requested:
                raise RuntimeError("TTS_CANCELLED")
            audio, sr = self._generate_chunk(text, speed)
            duration = len(audio) / sr if sr else 0
            return audio, sr, [{"text": text, "start": 0.0, "end": duration}]
        
        # Split long text into chunks
        print(f"Text too long ({len(text)} chars). Splitting into chunks...")
        chunks = []
        words = text.split()
        current_chunk = []
        current_len = 0
        
        for word in words:
            if current_len + len(word) > 2500:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_len = len(word)
            else:
                current_chunk.append(word)
                current_len += len(word) + 1
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        print(f"Generated {len(chunks)} chunks")
        
        # Generate each chunk and record timing
        all_audio = []
        sr = None
        chunk_timings = []
        cumulative_samples = 0
        
        for i, chunk in enumerate(chunks):
            if self._cancel_requested:
                print(f"[TTS] Cancelled at chunk {i+1}/{len(chunks)}")
                raise RuntimeError("TTS_CANCELLED")
            print(f"Generating chunk {i+1}/{len(chunks)}...")
            audio, sr = self._generate_chunk(chunk, speed)
            chunk_samples = len(audio)
            start_sec = cumulative_samples / sr if sr else 0
            end_sec = (cumulative_samples + chunk_samples) / sr if sr else 0
            chunk_timings.append({
                "text": chunk,
                "start": start_sec,
                "end": end_sec,
            })
            all_audio.append(audio)
            cumulative_samples += chunk_samples
        
        return np.concatenate(all_audio), sr, chunk_timings
    
    def _generate_chunk(self, text, speed=1.0):
        """Generate audio for a single chunk"""
        voice_info = self.VOICE_MODELS[self.current_voice]
        cache_key = self.get_cache_key(text, speed, self.current_voice)
        cache_file = self.cache_dir / f"{cache_key}.wav"
        
        if cache_file.exists():
            print(f"Loading from cache: {cache_key}")
            audio, sr = sf.read(str(cache_file))
            return audio, sr
        
        print(f"Generating: {cache_key} ({self.current_voice})")
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            output_file = tmp.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp:
            input_file = tmp.name
            tmp.write(text)
        
        try:
            length_scale = 1.0 / speed
            
            cmd = [
                "piper",
                "--model", str(self.voice_dir / voice_info["file"]),
                "--length_scale", str(length_scale),
                "--output_file", output_file
            ]
            
            if platform.system() != "Windows":
                espeak_data = None
                possible_paths = [
                    "/usr/lib/x86_64-linux-gnu/espeak-ng-data",
                    "/usr/share/espeak-ng-data",
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        espeak_data = path
                        break
                if espeak_data:
                    cmd.extend(["--espeak_data", espeak_data])
            
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            with open(input_file, 'rb') as f:
                text_bytes = f.read()
            
            stdout, stderr = process.communicate(text_bytes, timeout=120)
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise Exception(f"Piper error: {error_msg}")
            
            audio, sr = sf.read(output_file)
            sf.write(str(cache_file), audio, sr)
            
            os.unlink(output_file)
            os.unlink(input_file)
            
            return audio, sr
            
        except subprocess.TimeoutExpired:
            process.kill()
            if os.path.exists(output_file):
                os.unlink(output_file)
            if os.path.exists(input_file):
                os.unlink(input_file)
            raise Exception("TTS generation timed out")
        except Exception as e:
            if os.path.exists(output_file):
                try:
                    os.unlink(output_file)
                except:
                    pass
            if os.path.exists(input_file):
                try:
                    os.unlink(input_file)
                except:
                    pass
            raise Exception(f"TTS failed: {e}")


class TTSManager:
    def __init__(self):
        if platform.system() == "Windows":
            self.tts = WindowsTTS()
            self.available_voices = ["Windows TTS"]
        else:
            self.tts = TTSGenerator()
            self.available_voices = self.tts.get_voice_list()

    def cancel(self):
        """Delegate cancel request to the underlying generator."""
        if hasattr(self.tts, "cancel"):
            self.tts.cancel()

    def reset_cancel(self):
        """Clear cancel flag before starting fresh generation."""
        if hasattr(self.tts, "reset_cancel"):
            self.tts.reset_cancel()

    @property
    def _cancel_requested(self):
        return getattr(self.tts, "_cancel_requested", False)

    def get_voice_list(self):
        return self.available_voices

    @property
    def current_voice(self):
        """Return the currently selected voice name."""
        return getattr(self.tts, "current_voice", None)
    
    def set_voice(self, voice):
        """Delegate to the underlying generator; return True on success."""
        if hasattr(self.tts, "set_voice"):
            return self.tts.set_voice(voice)
        return False
    
    @property
    def voices_by_lang(self):
        if hasattr(self.tts, "voices_by_lang"):
            return self.tts.voices_by_lang
        return {"en": self.available_voices}

    def find_voice_for_lang(self, lang_code, kid_friendly=False):
        if hasattr(self.tts, "find_voice_for_lang"):
            return self.tts.find_voice_for_lang(lang_code, kid_friendly=kid_friendly)
        return None

    def find_kid_voice(self):
        if hasattr(self.tts, "find_kid_voice"):
            return self.tts.find_kid_voice()
        return None

    def generate_audio(self, text, speed=1.0):
        result = self.tts.generate(text, speed)
        # Normalize to always return 3-tuple (audio, sr, chunk_timings)
        if len(result) == 2:
            audio, sr = result
            duration = len(audio) / sr if sr else 0
            return audio, sr, [{"text": text, "start": 0.0, "end": duration}]
        return result
