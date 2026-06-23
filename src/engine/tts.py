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
import platform

class WindowsTTS:
    def __init__(self):
        import pyttsx3
        self.engine = pyttsx3.init()
    
    def generate(self, text, speed=1.0):
        self.engine.setProperty('rate', int(speed * 150))
        self.engine.say(text)
        self.engine.runAndWait()
        import numpy as np
        return np.array([0]), 22050

class TTSGenerator:
    # Available voice models
    VOICE_MODELS = {
        "Sarah (Female, Natural)": {
            "model": "en_US-lessac-medium",
            "file": "en_US-lessac-medium.onnx",
            "description": "Natural female voice"
        },
        "Michael (Male, Natural)": {
            "model": "en_US-ryan-medium",
            "file": "en_US-ryan-medium.onnx",
            "description": "Natural male voice"
        }
    }
    
    def __init__(self):
        self.voice_dir = Path.home() / ".local/share/piper"
        self.cache_dir = Path.home() / ".cache/studypal"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Detect available voices
        self.available_voices = []
        for voice_name, voice_info in self.VOICE_MODELS.items():
            model_path = self.voice_dir / voice_info["file"]
            if model_path.exists():
                self.available_voices.append(voice_name)
        
        self.current_voice = self.available_voices[0] if self.available_voices else None
        self.available = len(self.available_voices) > 0
        
        if not self.available:
            print("WARNING: No Piper models found.")
    
    def get_voice_list(self):
        return self.available_voices
    
    def set_voice(self, voice_name):
        if voice_name in self.available_voices:
            self.current_voice = voice_name
            return True
        return False
    
    def get_cache_key(self, text, speed, voice):
        content = f"{text}|{speed:.2f}|{voice}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def generate(self, text, speed=1.0):
        if not self.available or self.current_voice is None:
            raise Exception("No voice available")
        
        # If text is short, generate directly
        if len(text) <= 3000:
            return self._generate_chunk(text, speed)
        
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
        
        # Generate each chunk
        all_audio = []
        sr = None
        
        for i, chunk in enumerate(chunks):
            print(f"Generating chunk {i+1}/{len(chunks)}...")
            audio, sr = self._generate_chunk(chunk, speed)
            all_audio.append(audio)
        
        return np.concatenate(all_audio), sr
    
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
    
    def get_voice_list(self):
        return self.available_voices
    
    def set_voice(self, voice):
        return True
    
    def generate_audio(self, text, speed=1.0):
        return self.tts.generate(text, speed)
