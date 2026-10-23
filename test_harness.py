"""
Comprehensive test harness for StudyPal on Windows.
Runs each subsystem in isolation, logs detailed state, and reports failures.
"""
import sys
import os
import traceback
import logging
from pathlib import Path

# ── Set up logging ──────────────────────────────────────────
LOG_FILE = Path("C:/Users/vboxuser/Documents/studypal/test_run.log")
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("studypal-test")


def section(name):
    log.info("")
    log.info("=" * 70)
    log.info(f"TEST: {name}")
    log.info("=" * 70)


def run_test(name, func, *args, **kwargs):
    section(name)
    try:
        result = func(*args, **kwargs)
        log.info(f"✅ PASS: {name}")
        return result
    except Exception as e:
        log.error(f"❌ FAIL: {name}")
        log.error(f"   {type(e).__name__}: {e}")
        log.error("Full traceback:")
        for line in traceback.format_exc().splitlines():
            log.error(f"   {line}")
        return None


# ── Test 1: Imports ────────────────────────────────────────
def test_imports():
    log.info("Importing every module...")
    import numpy as np
    log.info(f"  numpy: {np.__version__}")

    import soundfile as sf
    log.info(f"  soundfile: {sf.__version__}")

    import PySide6
    log.info(f"  PySide6: {PySide6.__version__}")

    from services.transcription_service import TranscriptionService
    log.info("  TranscriptionService: imported")

    from engine.tts import TTSManager
    log.info("  TTSManager: imported")

    from annotations import AnnotationRepository, AnnotationType
    log.info(f"  AnnotationType: {[t.value for t in AnnotationType]}")

    from audio.player import AudioPlayer
    log.info("  AudioPlayer: imported")

    from stt import WhisperEngine, Translator
    log.info("  WhisperEngine, Translator: imported")

    log.info("All imports OK")


# ── Test 2: Annotation DB ──────────────────────────────────
def test_annotation_db():
    from annotations import AnnotationRepository, Annotation, AnnotationType
    repo = AnnotationRepository()
    log.info("DB initialized")

    test_ann = Annotation(
        doc_hash="test_hash_abc123",
        char_start=0,
        char_end=10,
        type=AnnotationType.BOOKMARK,
        line_number=1,
        content="Test bookmark",
    )
    repo.add(test_ann)
    log.info(f"Added annotation: {test_ann.id[:8]}")

    items = repo.list_for_doc("test_hash_abc123")
    log.info(f"Retrieved {len(items)} annotations for test hash")

    repo.delete_for_doc("test_hash_abc123")
    log.info("Cleaned up")


# ── Test 3: TTS (no playback, just generation) ────────────
def test_tts_generation():
    from engine.tts import TTSManager
    tts = TTSManager()
    log.info(f"Available voices: {len(tts.available_voices)}")

    result = tts.generate_audio("Hello, this is a test.", speed=1.0)
    log.info(f"Generated audio: type={type(result)}")

    if len(result) == 3:
        audio, sr, chunk_timings = result
    else:
        audio, sr = result
        chunk_timings = None

    log.info(f"  sample_rate={sr}, duration={len(audio)/sr:.2f}s")
    log.info(f"  dtype={audio.dtype}")

    import numpy as np
    if audio.dtype not in [np.float32, np.int16]:
        log.warning(f"  ⚠ audio dtype is {audio.dtype}, not float32/int16")


# ── Test 4: AudioPlayer state machine ─────────────────────
def test_audio_player():
    import numpy as np
    import time
    from audio.player import AudioPlayer

    sr = 44100
    audio = (0.3 * np.sin(2 * np.pi * 440 * np.linspace(0, 1, sr))).astype(np.float32)

    p = AudioPlayer()
    p.load(audio, sr)
    log.info(f"Loaded {len(audio)/sr:.2f}s audio")

    log.info("Playing...")
    p.play()
    time.sleep(0.3)
    log.info(f"  is_playing={p.is_playing}, pos={p.get_position():.2f}")

    log.info("Pausing...")
    p.pause()
    log.info(f"  is_paused={p.is_paused}, pos={p.get_position():.2f}")

    log.info("Resuming...")
    p.play()
    time.sleep(0.2)
    log.info(f"  is_playing={p.is_playing}, pos={p.get_position():.2f}")

    log.info("Stopping...")
    p.stop()
    log.info(f"  is_playing={p.is_playing}, pos={p.get_position():.2f}")

    log.info("Replaying...")
    p.play()
    time.sleep(0.2)
    log.info(f"  is_playing={p.is_playing}, pos={p.get_position():.2f}")
    p.stop()


# ── Test 5: Translator ────────────────────────────────────
def test_translator():
    from stt import Translator
    t = Translator()
    langs = t.available_languages()
    log.info(f"Available languages: {langs}")

    result = t.translate("Habari yako", from_code="sw", to_code="en")
    log.info(f"SW->EN 'Habari yako': '{result}'")

    result = t.translate("Hello", from_code="en", to_code="sw")
    log.info(f"EN->SW 'Hello': '{result}'")


# ── Test 6: Transcription (small clip) ────────────────────
def test_transcription():
    from services.transcription_service import TranscriptionService

    audio_path = Path("audio/sw_synthetic.wav")
    if not audio_path.exists():
        log.warning(f"Skipping: {audio_path} not found")
        log.info("Trying alternate paths...")
        for candidate in ["audio/test.wav", "test.wav", "audio/sw_test_60s.wav"]:
            if Path(candidate).exists():
                audio_path = Path(candidate)
                log.info(f"  Using: {audio_path}")
                break
        else:
            log.warning("No audio file found — skipping transcription test")
            return

    svc = TranscriptionService(model_size="medium", source_language="sw")
    log.info(f"Service created with model=base, lang=en")
    log.info(f"Transcribing {audio_path}...")

    result = svc.process(str(audio_path), use_cache=False)

    log.info(f"Transcription complete:")
    log.info(f"  detected_language: {result.get('detected_language')}")
    log.info(f"  segments: {len(result.get('segments', []))}")
    log.info(f"  transcript (first 200 chars): {result['transcript'][:200]}")


# ── Run all tests ─────────────────────────────────────────
if __name__ == "__main__":
    log.info("=" * 70)
    log.info("StudyPal Comprehensive Test Harness")
    log.info(f"Python: {sys.version}")
    log.info(f"Working dir: {os.getcwd()}")
    log.info("=" * 70)

    run_test("Imports", test_imports)
    run_test("Annotation DB", test_annotation_db)
    run_test("TTS Generation", test_tts_generation)
    run_test("AudioPlayer", test_audio_player)
    run_test("Translator", test_translator)
    run_test("Transcription", test_transcription)

    log.info("")
    log.info("=" * 70)
    log.info(f"Test run complete. Log saved to {LOG_FILE}")
    log.info("=" * 70)
