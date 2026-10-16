"""Automatic event detectors — silence for now, music/speaker later.

These functions take data from the STT pipeline (VAD segments, timings)
and produce Annotation objects that live in the same DB as manual ones.
"""
from typing import Optional
from .models import Annotation, AnnotationType


def find_silences(
    segments: list[dict],
    total_duration: Optional[float] = None,
    min_duration: float = 1.5,
    pad: float = 0.0,
) -> list[dict]:
    """Find silence gaps between speech segments.

    Args:
        segments: Whisper output — [{start, end, text}, ...]
        total_duration: optional, to also detect trailing silence
        min_duration: minimum silence length to record (seconds)
        pad: subtract this many seconds from each side of the gap
             (useful to avoid clipping word edges)

    Returns:
        List of dicts: [{start, end, duration}, ...]
    """
    if not segments or len(segments) < 2:
        return []

    # Sort by start time to be safe
    sorted_segs = sorted(segments, key=lambda s: s["start"])

    gaps = []
    for i in range(len(sorted_segs) - 1):
        gap_start = sorted_segs[i]["end"]
        gap_end = sorted_segs[i + 1]["start"]
        duration = gap_end - gap_start

        if duration < min_duration:
            continue

        # Apply padding to trim word edges
        if pad > 0 and duration > 2 * pad:
            gap_start += pad
            gap_end -= pad
            duration = gap_end - gap_start

        gaps.append({
            "start": round(gap_start, 2),
            "end": round(gap_end, 2),
            "duration": round(duration, 2),
        })

    # Optional: trailing silence after last speech
    if total_duration and sorted_segs:
        trailing = total_duration - sorted_segs[-1]["end"]
        if trailing >= min_duration:
            gaps.append({
                "start": round(sorted_segs[-1]["end"], 2),
                "end": round(total_duration, 2),
                "duration": round(trailing, 2),
            })

    return gaps


def build_silence_annotations(
    silences: list[dict],
    doc_hash: str,
    transcript_text: str,
    char_map: Optional[list[dict]] = None,
) -> list[Annotation]:
    """Turn silence gaps into Annotation objects.

    Args:
        silences: output of find_silences()
        doc_hash: file hash for the audio
        transcript_text: full transcript, for anchoring
        char_map: optional mapping from audio seconds -> char offset
                  If None, silences are anchored to char 0 (they still
                  show in the annotation list, just not inline).

    Returns:
        List of Annotation objects ready for repo.add()
    """
    annotations = []

    for idx, s in enumerate(silences):
        # Anchor: if we have a char map, use it; else anchor to start
        char_start = 0
        char_end = 0
        if char_map:
            char_start = _time_to_char(s["start"], char_map)
            char_end = _time_to_char(s["end"], char_map)
            # Ensure at least a 1-char span so highlighting has something to grab
            if char_end <= char_start:
                char_end = char_start + 1

        ann = Annotation(
            doc_hash=doc_hash,
            char_start=char_start,
            char_end=char_end,
            type=AnnotationType.SILENCE,
            audio_ms=int(s["start"] * 1000),
            color="#9E9E9E",
            content=f"🔇 Silence ({s['duration']:.1f}s)",
            tags=["auto-detected"],
        )
        annotations.append(ann)

    return annotations


def _time_to_char(time_sec: float, char_map: list[dict]) -> int:
    """Convert an audio timestamp to a character offset using a mapping.

    char_map format: [{"start": 0.0, "end": 2.5, "char_start": 0, "char_end": 45}, ...]
    """
    for entry in char_map:
        if entry["start"] <= time_sec <= entry["end"]:
            # Linear interpolation within the segment
            span = entry["end"] - entry["start"]
            if span <= 0:
                return entry["char_start"]
            ratio = (time_sec - entry["start"]) / span
            offset = int(entry["char_start"] + ratio * (entry["char_end"] - entry["char_start"]))
            return max(0, offset)
    # Fallback: after last segment, return end of last
    if char_map:
        return char_map[-1].get("char_end", 0)
    return 0
