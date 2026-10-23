# StudyPal Windows Build — Technical Documentation

**Date:** October 2026
**Environment:** Windows 10/11 in VirtualBox VM (`vboxuser`)
**Python:** 3.12.9
**Repo:** `C:\Users\vboxuser\Documents\studypal`

## Overview

StudyPal is a study assistant with:
- Text-to-Speech (TTS) via Piper
- Speech-to-Text (STT) via faster-whisper
- Bidirectional translation via Argos Translate
- Annotation system with SQLite persistence
- Read-along highlighting during playback

## Dependencies

| Package | Version | Notes |
|---|---|---|
| PySide6 | 6.12.0 | GUI framework |
| faster-whisper | 1.2.1 | STT engine |
| av | 18.1.0 | **Pinned below 19** — 19.x breaks faster-whisper 1.2.1 |
| soundfile | 0.14.0 | WAV reading/writing |
| sounddevice | 0.5.6 | Audio playback (only used on Linux/Mac now) |
| argostranslate | 1.11.0 | Translation engine |
| stanza | 1.10.1 | Argos dependency |
| numpy | 2.5.4 | Array operations |
| pip-system-certs | 5.3 | Windows SSL cert bridge for Python |

## Models & Data

| Component | Path | Size | Notes |
|---|---|---|---|
| Whisper medium model | `%LOCALAPPDATA%\studypal\models\medium\` | 1.5 GB | Downloaded from HuggingFace |
| Piper binary | `%LOCALAPPDATA%\Programs\piper\` | ~30 MB | Added to PATH |
| Piper English voices | `%LOCALAPPDATA%\piper\*.onnx` | ~240 MB | 4 voices (Sarah, Michael, Amy, Sarah Light) |
| Piper Swahili voice | `%LOCALAPPDATA%\piper\sw_CD-lanfrica-medium.onnx` | 60 MB | Hidden from dropdown |
| Argos sw↔en packages | `%LOCALAPPDATA%\argos-translate\packages\` | ~156 MB | Two .argosmodel files |
| Annotations DB | `%LOCALAPPDATA%\studypal\annotations.db` | grows | SQLite, auto-created |

## Critical Fixes Applied

### 1. PyAV Pin (`av<19`)

`faster-whisper 1.2.1` calls `av.open(..., metadata_errors='ignore')`, but PyAV 19.x removed that kwarg. Pinning `av<19` avoids the crash.

### 2. UTF-8 Stdout on Windows (`run.py`)

Windows PowerShell defaults to cp1252 codepage. Python `print()` with Unicode chars (`→`, `▶`, `⏸`, emoji) crashes with `UnicodeEncodeError`. Fixed by reconfiguring `sys.stdout` to UTF-8 at the top of `run.py`.

### 3. Signal-Based Worker Threading (`main_window.py`)

The TTS worker ran in a Python `threading.Thread` and directly touched Qt widgets (`self.play_btn.setText(...)`, `self.duration_label.setText(...)`). On Linux this is tolerated; on Windows Qt 6.12 it crashes with `QObject::setParent: Cannot set parent, new parent is in a different thread` and `Windows fatal exception: access violation`.

**Fix:** Worker emits signals (`_tts_playing`, `_tts_cancelled`, `_tts_error`); main thread handles widget updates.

### 4. `Lock` → `RLock` in AudioPlayer (`player.py`)

`AudioPlayer._lock = threading.Lock()` is **not reentrant**. Methods like `load()`, `play()`, `pause()`, `stop()` call each other while holding the lock, causing deadlocks.

**Fix:** `threading.RLock()`.

This was the root cause of every audio-related bug:
- Stop button did nothing (deadlock in `stop()`)
- "Audio loop" on replay (deadlock in `play()` → `stop()`)
- Retry-after-finish crashed
- Transcription appeared to recurse (worker blocked in `load()`)

### 5. `winsound` Backend for Audio Playback

`sounddevice` (PortAudio) and `simpleaudio` (DirectSound) **both hang indefinitely** when calling `sd.play()` / `sa.play_buffer()` in this VirtualBox VM.

**Fix:** Use `winsound.PlaySound()` as the Windows backend. It's a native Windows API that:
- Never hangs
- Plays WAV files via `SND_FILENAME | SND_ASYNC`
- Stops via `PlaySound(None, 0)` — **not `SND_PURGE`** (which hangs on this VM)
- Pause/resume implemented by stopping + restarting from cropped samples

### 6. Audio Dtype Cast (`player.py`, `main_window.py`)

Piper's TTS output is a numpy `int64` array. `sounddevice` and `soundfile.write` reject `int64`. `winsound` needs `int16` PCM.

**Fix:** Cast to `float32` on load, `int16` when writing to WAV.

### 7. Dropdown Signal Recursion (`listen_view.py`)

`_on_finished` calls `_populate_language_dropdown()`, which modifies `QComboBox`. That fires `currentIndexChanged`, which (via earlier connections) triggers a new transcription. This caused:
- Multiple `[STT Cache] MISS` lines per click
- `maximum recursion depth exceeded`
- Infinite loop of workers starting

**Fix:** `blockSignals(True)` / `blockSignals(False)` around programmatic dropdown updates.

### 8. Concurrent Transcription Guard (`listen_view.py`)

Even with dropdown signals blocked, multiple `start_transcription()` calls could overlap if the user clicked fast or signals fired from elsewhere.

**Fix:** `_is_transcribing` flag — ignore clicks while a worker is running.

## Known Issues / Limitations

1. **Pause is stop-and-restart** (`winsound` doesn't support true pause). Slight click may be audible when resuming.
2. **VM audio may degrade further** — if VirtualBox audio is set to "Null", no fix in code will help. VirtualBox Settings → Audio → "Intel HD Audio" with host driver "Windows DirectSound" usually works.
3. **Argos `sw` models are limited** — "Habari yako" → "Your story" (literal translation). Not a bug, it's the model.
4. **`SND_PURGE` is banned** — use `PlaySound(None, 0)` instead.
5. **`ARGOS_CHUNK_TYPE=MINISBD` must be set** in `translator.py` before Argos import — otherwise Stanza crashes trying to load Swahili's sentence splitter.

## Test Checklist

Run `python test_harness.py` to verify each subsystem. Expected output: all ✅ PASS.

For GUI testing:
1. Launch `python run.py` — window stays open
2. Transcribe → single MISS line, transcript appears
3. Play → audio plays
4. Pause → audio stops, Play resumes from position
5. Stop → resets to 00:00
6. Play again → starts from beginning
7. Let finish → Play again works
8. Right-click transcript → Bookmark → sidebar count increments

## Recovery Notes

If any of these files gets corrupted again:
- `git checkout HEAD -- src/audio/player.py`
- `git checkout HEAD -- src/gui/main_window.py`
- `git checkout HEAD -- src/gui/listen_view.py`

Then re-apply the patches listed above.

## Files Changed from v4.9

- `run.py` — added UTF-8 stdout
- `src/audio/player.py` — full rewrite (winsound, RLock)
- `src/gui/main_window.py` — signals for TTS worker, float32 cast, end-of-audio cleanup
- `src/gui/listen_view.py` — blockSignals, _is_transcribing guard
- `src/stt/translator.py` — modern Argos API, MINISBD env var
- `requirements.txt` — `av<19`, `pip-system-certs`
