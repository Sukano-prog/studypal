"""Annotation system for StudyPal — bookmarks, highlights, notes, tags."""
from .models import Annotation, AnnotationType
from .repository import AnnotationRepository

__all__ = ["Annotation", "AnnotationType", "AnnotationRepository"]
