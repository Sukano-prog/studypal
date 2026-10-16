"""High-level service: audio file -> transcript + translation (with caching)."""
import hashlib
import json
from pathlib import Path

from stt import WhisperEngine, Translator, load_audio
from annotations import AnnotationRepository
from annotations.detectors import find_silences, build_silence_annotations
from utils.paths import get_cache_dir


# STT cache — OS-appropriate via utils.paths
CACHE_DIR = get_cache_dir() / "stt"
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

    def __init__(self, model_size: str = "base", source_language: str = None):
        self.model_size = model_size
        self.source_language = source_language
        self.whisper = WhisperEngine(model_size=model_size)
        self.translator = Translator()
        self.annotations = AnnotationRepository()

    def _detect_and_store_silences(self, result: dict, audio_hash: str):
        """Find silence gaps and store them as annotations.

        Runs after transcription. Skips gracefully if no segments
        or if the transcript is empty.
        """
        segments = result.get("segments") or []
        if not segments:
            return 0

        # Total duration from last segment's end (approximation)
        total_duration = max(s.get("end", 0) for s in segments)

        silences = find_silences(
            segments,
            total_duration=total_duration,
            min_duration=1.5,
        )
        if not silences:
            return 0

        # Build a char map from segments so we can anchor silences inline
        char_map = []
        char_pos = 0
        for s in segments:
            text = s.get("text", "")
            char_start = char_pos
            char_end = char_pos + len(text)
            char_map.append({
                "start": s.get("start", 0),
                "end": s.get("end", 0),
                "char_start": char_start,
                "char_end": char_end,
            })
            char_pos = char_end + 1  # +1 for the space we join with

        annotations = build_silence_annotations(
            silences,
            doc_hash=audio_hash,
            transcript_text=result.get("transcript", ""),
            char_map=char_map,
        )

        # Remove old auto-detected silences for this doc, then insert new
        try:
            existing = self.annotations.list_for_doc(audio_hash)
            for a in existing:
                if a.type.value == "silence" and "auto-detected" in (a.tags or []):
                    self.annotations.delete(a.id)
        except Exception as e:
            print(f"[silence] Could not clear old: {e}")

        for a in annotations:
            self.annotations.add(a)

        print(f"[silence] Created {len(annotations)} silence annotations")
        return len(annotations)

    # ---------- cache helpers ----------

    def _cache_path(self, audio_hash: str, source_language: str,
                    target_language: str, model_size: str) -> Path:
        """Cache key = audio hash + source lang + target lang + model size."""
        src = source_language or "auto"
        tgt = target_language or "none"
        suffix = f"{audio_hash}_{src}_{tgt}_{model_size}.json"
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
        cache_file = self._cache_path(
            audio_hash, self.source_language, target_language, self.model_size,
        )

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
            language=self.source_language,
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

        # --- Detect silences and store as annotations ---
        try:
            self._detect_and_store_silences(result, audio_hash)
        except Exception as e:
            print(f"[silence] Detection failed: {e}")

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
