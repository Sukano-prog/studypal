"""Data models for annotations."""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class AnnotationType(str, Enum):
    # User-created
    BOOKMARK = "bookmark"
    HIGHLIGHT = "highlight"
    NOTE = "note"
    VOICE_NOTE = "voice_note"
    QUESTION = "question"

    # Auto-detected audio events
    SILENCE = "silence"
    MUSIC = "music"
    NOISE = "noise"
    APPLAUSE = "applause"
    LAUGHTER = "laughter"
    SPEAKER_CHANGE = "speaker_change"


@dataclass
class Annotation:
    """A single annotation anchored to a document.

    Anchoring strategy:
      - doc_hash: SHA-256 of source document content (survives re-parse)
      - char_start / char_end: offsets into the source text
      - line_number: cached for fast rendering (may drift if doc edited)
      - audio_ms: optional timestamp for audio-synced documents
    """
    doc_hash: str
    char_start: int
    char_end: int
    type: AnnotationType

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    line_number: Optional[int] = None
    audio_ms: Optional[int] = None
    color: Optional[str] = None       # hex, e.g. "#FFEB3B"
    content: Optional[str] = None     # text or path to voice file
    tags: list = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        d = asdict(self)
        d["type"] = self.type.value
        return d

    @classmethod
    def from_row(cls, row: dict) -> "Annotation":
        import json
        return cls(
            id=row["id"],
            doc_hash=row["doc_hash"],
            char_start=row["char_start"],
            char_end=row["char_end"],
            type=AnnotationType(row["type"]),
            line_number=row.get("line_number"),
            audio_ms=row.get("audio_ms"),
            color=row.get("color"),
            content=row.get("content"),
            tags=json.loads(row.get("tags") or "[]"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )
