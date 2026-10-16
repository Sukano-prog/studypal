# StudyPal

Advanced study assistant with offline text-to-speech and multilingual transcription.

## Features

- Text-to-speech — 12 multilingual voices via Piper, fully offline
- Speech-to-text — Whisper-based, supports 99 languages
- Kiswahili support — auto-upgrades to medium Whisper model for accuracy
- Annotations — bookmarks, highlights, notes, tags on transcript lines
- Auto event detection — silence gaps (music/speaker detection planned)
- Translation — Argos Translate for translating transcripts
- Cancel anything — abort TTS generation or transcription mid-flight

## Requirements

- Python 3.12 (3.10-3.12 supported; 3.13 not yet tested)
- Linux / macOS / Windows
- ~2 GB disk for Whisper models + Piper voices
- Piper binary installed separately (see below)

## Installation

### 1. Clone the repository

    git clone https://github.com/Sukano-prog/studypal.git
    cd studypal

### 2. Create a virtual environment

    python3.12 -m venv venv

    # Linux / macOS
    source venv/bin/activate

    # Windows
    venv\Scripts\activate

### 3. Install dependencies

    pip install --upgrade pip
    pip install -r requirements.txt

### 4. Install the Piper TTS binary

Piper is not on PyPI. Download from:

    https://github.com/rhasspy/piper/releases

Place the `piper` executable on your PATH:
- Linux / macOS: /usr/local/bin/piper
- Windows: add the folder to your system PATH

Verify:

    piper --version
    # Should print: 1.2.0 (or newer)

### 5. Download Piper voices

Voices go in ~/.local/share/piper/ (Linux/macOS) or
%LOCALAPPDATA%\piper\ (Windows).

Get them from: https://huggingface.co/rhasspy/piper-voices

Each voice needs two files:
- <voice>.onnx — the model
- <voice>.onnx.json — the config

Example: en_US-lessac-medium.onnx + en_US-lessac-medium.onnx.json

StudyPal detects installed voices at startup.

### 6. Run

    python run.py

## Model downloads (automatic)

### Whisper speech-to-text models

Download on first use. Sizes:
- tiny — 75 MB (fastest, lowest quality)
- base — 145 MB (default)
- small — 500 MB
- medium — 1.5 GB (recommended for Kiswahili)
- large-v3 — 3 GB (slowest, best quality)

For Kiswahili, the medium model is strongly recommended. StudyPal
will auto-upgrade base/tiny requests to medium when transcribing Swahili.

To use a locally downloaded medium model, place it at:

    ~/.local/share/studypal/models/medium/

with model.bin, config.json, tokenizer.json, vocabulary.txt.

### Argos Translate packs

Download on demand from the Listen tab's "Translate to" dropdown.

## Project layout

    src/
    ├── annotations/    SQLite-backed bookmark / highlight / note system
    │   ├── db.py            Schema + connection
    │   ├── detectors.py     Automatic silence detection
    │   ├── models.py        Annotation dataclass + types
    │   └── repository.py    CRUD operations
    ├── audio/          Audio playback (QThread worker)
    ├── engine/         TTS (Piper + Windows pyttsx3 fallback)
    ├── gui/            PySide6 interface
    ├── services/       High-level orchestration
    └── stt/            Whisper speech-to-text

## Offline-first

StudyPal is designed to work without internet:
- STT models run locally (faster-whisper/CT2)
- TTS voices run locally (Piper)
- Translation packs run locally (Argos)
- Annotations stored in SQLite

Internet is only needed for:
- First-time model downloads
- Argos pack downloads

## Optional: openai-whisper fallback

By default, StudyPal uses faster-whisper (CTranslate2). If you need
the original OpenAI Whisper as a fallback:

    pip install openai-whisper

This pulls in PyTorch (~3 GB with CUDA libs), so it's not in the
default requirements.txt.

## Known limitations

- CPU-only transcription is slow on medium/large models.
  A GPU drops 12-min audio from 29 min to under a minute.
- Speaker diarization not yet implemented.
- Music/noise detection planned via YAMNet (TensorFlow).
- Mobile requires a runtime rewrite (ONNX Runtime for Whisper/Piper).

