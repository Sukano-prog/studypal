"""CRUD operations for annotations."""
import json
from datetime import datetime
from typing import Optional
from .db import get_connection, init_db
from .models import Annotation, AnnotationType


class AnnotationRepository:
    """All persistence operations for annotations."""

    def __init__(self):
        init_db()

    # ---------- create ----------

    def add(self, ann: Annotation) -> Annotation:
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO annotations
                   (id, doc_hash, char_start, char_end, line_number, audio_ms,
                    type, color, content, tags, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    ann.id, ann.doc_hash, ann.char_start, ann.char_end,
                    ann.line_number, ann.audio_ms, ann.type.value,
                    ann.color, ann.content, json.dumps(ann.tags),
                    ann.created_at, ann.updated_at,
                ),
            )
            conn.commit()
        return ann

    # ---------- read ----------

    def get(self, ann_id: str) -> Optional[Annotation]:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM annotations WHERE id = ?", (ann_id,)
            ).fetchone()
        return Annotation.from_row(dict(row)) if row else None

    def list_for_doc(self, doc_hash: str) -> list[Annotation]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM annotations WHERE doc_hash = ? ORDER BY char_start",
                (doc_hash,),
            ).fetchall()
        return [Annotation.from_row(dict(r)) for r in rows]

    def list_by_tag(self, tag: str) -> list[Annotation]:
        # Simple LIKE match — good enough for `#exam` style tags
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM annotations WHERE tags LIKE ? ORDER BY created_at DESC",
                (f'%"{tag}"%',),
            ).fetchall()
        return [Annotation.from_row(dict(r)) for r in rows]

    def list_by_type(self, ann_type: AnnotationType) -> list[Annotation]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM annotations WHERE type = ? ORDER BY created_at DESC",
                (ann_type.value,),
            ).fetchall()
        return [Annotation.from_row(dict(r)) for r in rows]

    # ---------- update ----------

    def update(self, ann: Annotation) -> Annotation:
        ann.updated_at = datetime.utcnow().isoformat()
        with get_connection() as conn:
            conn.execute(
                """UPDATE annotations
                   SET char_start=?, char_end=?, line_number=?, audio_ms=?,
                       type=?, color=?, content=?, tags=?, updated_at=?
                   WHERE id=?""",
                (
                    ann.char_start, ann.char_end, ann.line_number, ann.audio_ms,
                    ann.type.value, ann.color, ann.content, json.dumps(ann.tags),
                    ann.updated_at, ann.id,
                ),
            )
            conn.commit()
        return ann

    # ---------- delete ----------

    def delete(self, ann_id: str) -> bool:
        with get_connection() as conn:
            cur = conn.execute("DELETE FROM annotations WHERE id = ?", (ann_id,))
            conn.commit()
            return cur.rowcount > 0

    def delete_for_doc(self, doc_hash: str) -> int:
        with get_connection() as conn:
            cur = conn.execute("DELETE FROM annotations WHERE doc_hash = ?", (doc_hash,))
            conn.commit()
            return cur.rowcount

    # ---------- stats ----------

    def count_for_doc(self, doc_hash: str) -> int:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as c FROM annotations WHERE doc_hash = ?",
                (doc_hash,),
            ).fetchone()
        return row["c"] if row else 0

    def all_tags(self) -> list[str]:
        """Return sorted unique tags across all annotations."""
        with get_connection() as conn:
            rows = conn.execute("SELECT tags FROM annotations").fetchall()
        seen = set()
        for r in rows:
            try:
                seen.update(json.loads(r["tags"] or "[]"))
            except Exception:
                pass
        return sorted(seen)
