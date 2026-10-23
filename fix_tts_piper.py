from pathlib import Path
p = Path("src/engine/tts.py")
src = p.read_text(encoding="utf-8")

# Find and replace the TTSManager.__init__ logic
old_init = '''if platform.system() == "Windows":
            self.tts = WindowsTTS()
            self.available_voices = ["Windows TTS"]
        else:
            self.tts = TTSGenerator()
            self.available_voices = self.tts.get_voice_list()'''

new_init = '''# Try Piper first — it works on both platforms if voices are installed
        try:
            candidate = TTSGenerator()
            voices = candidate.get_voice_list()
            if voices:
                self.tts = candidate
                self.available_voices = voices
            else:
                print("[TTS] Piper has no voices; falling back to WindowsTTS")
                self.tts = WindowsTTS()
                self.available_voices = ["Windows TTS"]
        except Exception as e:
            print(f"[TTS] Piper unavailable ({e}); falling back to WindowsTTS")
            self.tts = WindowsTTS()
            self.available_voices = ["Windows TTS"]'''

if old_init in src:
    src = src.replace(old_init, new_init, 1)
    p.write_text(src, encoding="utf-8")
    print("✅ TTSManager now tries Piper first on all platforms")
else:
    print("⚠ Pattern not found — current TTSManager.__init__:")
    idx = src.find("class TTSManager")
    if idx >= 0:
        print(src[idx:idx + 800])
