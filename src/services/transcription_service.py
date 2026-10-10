"""High-level service: audio file -> transcript + translation (with caching)."""
import hashlib
import json
from pathlib import Path

from stt import WhisperEngine, Translator, load_audio


# Cache lives in ~/.cache/studypal/stt/ (matches v2's TTS cache location)
CACHE_DIR = Path.home() / ".cache" / "studypal" / "stt"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _file_hash(path: Path, chunk_size: int = 65536) -> str:
    """MD5 of the file contents — used as cache key."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


class TranscriptionService:
    """Orchestrates transcription and optional translation."""

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self.whisper = WhisperEngine(model_size=model_size)
        self.translator = Translator()

    # ---------- cache helpers ----------

    def _cache_path(self, audio_hash: str, target_language: str, model_size: str) -> Path:
        """Cache key = audio hash + target language + model size."""
        suffix = f"{audio_hash}_{target_language or 'none'}_{model_size}.json"
        return CACHE_DIR / suffix

    # ---------- main pipeline ----------

    def process(
        self,
        audio_path: str,
        target_language: str = None,
        progress_callback=None,
        use_cache: bool = True,
    ) -> dict:
        """
        Full pipeline: audio -> transcript -> (optional) translation.

        Args:
            audio_path: path to audio file
            target_language: e.g. "sw" for Swahili. None = no translation.
            progress_callback: callable(percent: float, info: str) for UI updates
            use_cache: if True, return cached result when available
        """
        path = load_audio(audio_path)
        audio_hash = _file_hash(path)
        cache_file = self._cache_path(audio_hash, target_language, self.model_size)

        # --- Cache hit? ---
        if use_cache and cache_file.exists():
            if progress_callback:
                progress_callback(100.0, "Loaded from cache")
            try:
                data = json.loads(cache_file.read_text())
                data["_cached"] = True
                print(f"[STT Cache] HIT: {cache_file.name}")
                return data
            except Exception as e:
                print(f"[STT Cache] Failed to read cache, regenerating: {e}")

        # --- Cache miss: transcribe ---
        print(f"[STT Cache] MISS: {cache_file.name}")
        result = self.whisper.transcribe(
            str(path),
            progress_callback=progress_callback,
        )

        transcript = result["text"].strip()
        detected = result.get("language", "unknown")

        output = {
            "audio_file": str(path),
            "transcript": transcript,
            "detected_language": detected,
            "translation": None,
            "target_language": target_language,
            "segments": result.get("segments", []),
            "_cached": False,
        }

        # --- Optional translation ---
        if target_language and target_language != detected:
            if progress_callback:
                progress_callback(100.0, "Translating...")
            try:
                output["translation"] = self.translator.translate(
                    transcript, from_code=detected, to_code=target_language
                )
            except ValueError as e:
                output["translation"] = f"[Translation unavailable: {e}]"

        # --- Save to cache ---
        try:
            cache_file.write_text(json.dumps(output, ensure_ascii=False))
            print(f"[STT Cache] Saved: {cache_file.name}")
        except Exception as e:
            print(f"[STT Cache] Failed to write cache: {e}")

        return output

    # ---------- exports ----------

    def export_txt(self, result: dict, out_path: str = None) -> str:
        """Export transcript + translation to a .txt file."""
        if out_path is None:
            base = Path(result["audio_file"]).stem
            out_path = f"{base}_transcript.txt"

        lines = [
            f"Source: {result['audio_file']}",
            f"Detected language: {result['detected_language']}",
            "",
            "=" * 50,
            "TRANSCRIPT",
            "=" * 50,
            result["transcript"],
        ]

        if result.get("translation"):
            lines += [
                "",
                "=" * 50,
                f"TRANSLATION ({result['target_language']})",
                "=" * 50,
                result["translation"],
            ]

        Path(out_path).write_text("\n".join(lines), encoding="utf-8")
        return out_path

    def export_srt(self, result: dict, out_path: str = None) -> str:
        """Export timestamped segments as .srt subtitles."""
        if out_path is None:
            base = Path(result["audio_file"]).stem
            out_path = f"{base}.srt"

        def fmt(t):
            h, m, s = int(t // 3600), int((t % 3600) // 60), t % 60
            return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")

        lines = []
        for i, seg in enumerate(result.get("segments", []), 1):
            lines += [
                str(i),
                f"{fmt(seg['start'])} --> {fmt(seg['end'])}",
                seg["text"].strip(),
                "",
            ]

        Path(out_path).write_text("\n".join(lines), encoding="utf-8")
        return out_path

    # ---------- cache management ----------

    def clear_cache(self) -> int:
        """Delete all cached transcriptions. Returns count deleted."""
        count = 0
        for f in CACHE_DIR.glob("*.json"):
            f.unlink()
            count += 1
        return count

    def cache_size_mb(self) -> float:
        """Total size of cache in MB."""
        total = sum(f.stat().st_size for f in CACHE_DIR.glob("*.json"))
        return total / (1024 * 1024)
