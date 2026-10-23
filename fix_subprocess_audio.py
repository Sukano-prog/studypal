from pathlib import Path

p = Path("src/audio/player.py")
src = p.read_text(encoding="utf-8")

# Replace the Windows playback logic to use a subprocess
old_play = """        if IS_WINDOWS:
            # winsound only accepts int16 WAV files
            audio_int16 = (np.clip(audio_float32, -1.0, 1.0) * 32767).astype(np.int16)
            sf.write(self._temp_wav, audio_int16, self.sample_rate, subtype='PCM_16')
            winsound.PlaySound(self._temp_wav, winsound.SND_FILENAME | winsound.SND_ASYNC)"""

new_play = """        if IS_WINDOWS:
            # Write WAV, then play via PowerShell subprocess to avoid VM driver deadlock
            audio_int16 = (np.clip(audio_float32, -1.0, 1.0) * 32767).astype(np.int16)
            sf.write(self._temp_wav, audio_int16, self.sample_rate, subtype='PCM_16')
            
            # Use subprocess to play, so Python doesn't block on the audio driver
            import subprocess
            ps_cmd = f'(New-Object Media.SoundPlayer "{self._temp_wav}").PlaySync()'
            self._play_process = subprocess.Popen(
                ["powershell", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )"""

if old_play in src:
    src = src.replace(old_play, new_play, 1)
    print("✅ Windows playback now uses subprocess to avoid driver deadlock")
else:
    print("⚠ Windows playback pattern not found")

# Update _stop_hardware to kill the subprocess
old_stop = """        if IS_WINDOWS:
            winsound.PlaySound(None, 0)  # 0 = stop, do NOT use SND_PURGE (hangs on Windows VM)"""

new_stop = """        if IS_WINDOWS:
            if hasattr(self, '_play_process') and self._play_process is not None:
                self._play_process.terminate()
                self._play_process = None"""

if old_stop in src:
    src = src.replace(old_stop, new_stop, 1)
    print("✅ Stop now terminates the subprocess")
else:
    print("⚠ Stop pattern not found")

p.write_text(src, encoding="utf-8")
