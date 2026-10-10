"""Whisper-based speech-to-text engine.

Uses faster-whisper (CTranslate2) when available — 4-8x faster on CPU.
Falls back to openai-whisper if faster-whisper isn't installed.
"""
from pathlib import Path

# Try faster-whisper first (much faster on CPU)
try:
    from faster_whisper import WhisperModel
    HAS_FASTER = True
except ImportError:
    HAS_FASTER = False
    import whisper  # type: ignore


class WhisperEngine:
    """Wraps Whisper for local transcription.

    Backend:
      - faster-whisper if installed (recommended)
      - openai-whisper otherwise
    """

    def __init__(self, model_size: str = "base"):
        """
        model_size: tiny, base, small, medium, large-v3
        - tiny  : fastest (~4-6 sec/min on i5-4300U)
        - base  : good balance (~8-12 sec/min)
        - small : better accuracy, slower (~25-35 sec/min)
        """
        self.model_size = model_size
        self._model = None
        self._backend = "faster-whisper" if HAS_FASTER else "openai-whisper"

    @property
    def model(self):
        """Lazy-load the model."""
        if self._model is None:
            print(f"[Whisper] Loading '{self.model_size}' ({self._backend})...")
            if HAS_FASTER:
                # compute_type=int8 is much faster on CPU with minimal quality loss
                self._model = WhisperModel(
                    self.model_size,
                    device="cpu",
                    compute_type="int8",
                )
            else:
                self._model = whisper.load_model(self.model_size)  # type: ignore
        return self._model

    def transcribe(
        self,
        audio_path: str,
        language: str = None,
        progress_callback=None,
    ) -> dict:
        """
        Transcribe an audio file.

        Args:
            audio_path: path to audio
            language: force a language code (e.g. "en"), or None to auto-detect
            progress_callback: optional callable(percent: float, info: str)

        Returns:
            {
                "text": "full transcript",
                "language": "en",
                "segments": [{"start": 0.0, "end": 2.5, "text": "..."}]
            }
        """
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio not found: {path}")

        print(f"[Whisper] Transcribing {path.name} ({self._backend})...")

        if HAS_FASTER:
            return self._transcribe_faster(path, language, progress_callback)
        else:
            return self._transcribe_openai(path, language, progress_callback)

    # ---------- faster-whisper path ----------

    def _transcribe_faster(self, path: Path, language, progress_callback) -> dict:
        segments_iter, info = self.model.transcribe(
            str(path),
            language=language,
            beam_size=1,           # faster; use 5 for better accuracy
            vad_filter=True,       # skip silence — big speedup
            vad_parameters={"min_silence_duration_ms": 500},
        )

        # info.duration tells us the total; segments carry their end time
        total_duration = getattr(info, "duration", None) or 0.0
        detected_lang = getattr(info, "language", "unknown")
        print(f"[Whisper] Detected language: {detected_lang}")

        collected_segments = []
        full_text_parts = []

        for seg in segments_iter:
            collected_segments.append({
                "start": float(seg.start),
                "end": float(seg.end),
                "text": seg.text.strip(),
            })
            full_text_parts.append(seg.text)

            if progress_callback and total_duration > 0:
                pct = min(100.0, (seg.end / total_duration) * 100.0)
                progress_callback(pct, f"{pct:.0f}%  ({len(collected_segments)} segments)")

        if progress_callback:
            progress_callback(100.0, "Done")

        return {
            "text": " ".join(full_text_parts).strip(),
            "language": detected_lang,
            "segments": collected_segments,
        }

    # ---------- openai-whisper fallback ----------

    def _transcribe_openai(self, path: Path, language, progress_callback) -> dict:
        if progress_callback:
            progress_callback(0.0, "Transcribing (no progress info)...")
        result = self.model.transcribe(  # type: ignore
            str(path),
            language=language,
            task="transcribe",
            verbose=False,
        )
        if progress_callback:
            progress_callback(100.0, "Done")
        print(f"[Whisper] Detected language: {result.get('language')}")
        return result
