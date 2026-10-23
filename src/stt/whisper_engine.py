"""Whisper-based speech-to-text engine.

Uses faster-whisper (CTranslate2) when available — 4-8x faster on CPU.
Falls back to openai-whisper if faster-whisper isn't installed.
"""
from pathlib import Path

from utils.paths import get_models_dir

try:
    from faster_whisper import WhisperModel
    HAS_FASTER = True
except ImportError:
    HAS_FASTER = False
    import whisper  # type: ignore


# ---------------------------------------------------------------------------
# Language-specific tuning
# ---------------------------------------------------------------------------
LOW_RESOURCE_LANGUAGES = {
    "sw", "yo", "ha", "am", "zu", "so", "rw", "ig",
    "ur", "ta", "te", "ml",
}

MIN_MODEL_BY_LANG = {
    "sw": "medium", "yo": "small", "ha": "small", "am": "small",
    "zu": "small", "so": "small", "rw": "small", "ig": "small",
}

# Local model directories — checked before HF cache.
# Populated by the user manually (medium is too big for auto-download).
LOCAL_MODEL_DIRS = {
    "medium": get_models_dir() / "medium",
}

INITIAL_PROMPTS = {
    "sw": (
        "Hii ni rekodi ya Kiswahili sanifu. Maneno ya kitaalamu, "
        "majina ya mahali, na istilahi za Kiswahili zinaweza kutokea. "
        "Tafadhali andika kwa Kiswahili."
    ),
}


def tune_model_for_language(requested: str, language: str | None) -> str:
    """Return the model size we should actually use for this language."""
    if language in LOW_RESOURCE_LANGUAGES:
        floor = MIN_MODEL_BY_LANG.get(language, "small")
        order = ["tiny", "base", "small", "medium", "large-v3"]
        try:
            if order.index(requested) < order.index(floor):
                return floor
        except ValueError:
            pass
    return requested


class WhisperEngine:
    """Wraps Whisper for local transcription."""

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None
        self._loaded_size = None
        self._backend = "faster-whisper" if HAS_FASTER else "openai-whisper"

    def _resolve_model_source(self):
        """Return a path if we have a local model dir, else the model size name."""
        local = LOCAL_MODEL_DIRS.get(self.model_size)
        if local and local.exists() and (local / "model.bin").exists():
            print(f"[Whisper] Using local model at {local}")
            return str(local)
        return self.model_size

    @property
    def model(self):
        if self._model is None:
            source = self._resolve_model_source()
            print(f"[Whisper] Loading '{self.model_size}' from '{source}' ({self._backend})...")
            if HAS_FASTER:
                self._model = WhisperModel(
                    source, device="cpu", compute_type="int8",
                    local_files_only=(source == self.model_size),
                )
            else:
                self._model = whisper.load_model(source)  # type: ignore
            self._loaded_size = self.model_size
        return self._model

    def _ensure_model(self, target_size: str):
        if self._loaded_size != target_size:
            self._model = None
            self.model_size = target_size

    def transcribe(self, audio_path: str, language: str = None,
                   progress_callback=None) -> dict:
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio not found: {path}")

        effective = tune_model_for_language(self.model_size, language)
        if effective != self.model_size:
            print(f"[Whisper] Auto-upgrading {self.model_size} -> {effective} for '{language}'")
            self._ensure_model(effective)

        print(f"[Whisper] Transcribing {path.name} "
              f"({self._backend}, model={self.model_size}, lang={language or 'auto'})...")

        if HAS_FASTER:
            return self._transcribe_faster(path, language, progress_callback)
        return self._transcribe_openai(path, language, progress_callback)

    def _transcribe_faster(self, path, language, progress_callback):
        prompt = INITIAL_PROMPTS.get(language) if language else None
        segments_iter, info = self.model.transcribe(
            str(path),
            language=language,
            initial_prompt=prompt,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
            condition_on_previous_text=True,
            temperature=0.0,
        )
        total_duration = getattr(info, "duration", None) or 0.0
        detected = getattr(info, "language", "unknown")
        print(f"[Whisper] Detected language: {detected}")

        collected, parts = [], []
        for seg in segments_iter:
            collected.append({
                "start": float(seg.start), "end": float(seg.end),
                "text": seg.text.strip(),
            })
            parts.append(seg.text)
            if progress_callback and total_duration > 0:
                pct = min(100.0, (seg.end / total_duration) * 100.0)
                progress_callback(pct, f"{pct:.0f}%  ({len(collected)} segments)")

        if progress_callback:
            progress_callback(100.0, "Done")

        return {
            "text": " ".join(parts).strip(),
            "language": detected,
            "segments": collected,
        }

    def _transcribe_openai(self, path, language, progress_callback):
        prompt = INITIAL_PROMPTS.get(language) if language else None
        if progress_callback:
            progress_callback(0.0, "Transcribing...")
        result = self.model.transcribe(  # type: ignore
            str(path),
            language=language,
            initial_prompt=prompt,
            task="transcribe",
            beam_size=5,
            condition_on_previous_text=True,
            temperature=0.0,
            verbose=False,
        )
        if progress_callback:
            progress_callback(100.0, "Done")
        return result
