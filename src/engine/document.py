"""
Document loader - supports TXT, PDF, DOCX.
"""

from pathlib import Path
from pypdf import PdfReader
import docx


class DocumentLoadError(Exception):
    pass


def load_document(file_path):
    """Return plain text content of a document. Raises DocumentLoadError
    with a user-facing message on failure."""
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    if not file_path.exists():
        raise DocumentLoadError(f"File not found: {file_path}")

    if suffix == ".txt":
        return _load_txt(file_path)
    elif suffix == ".pdf":
        return _load_pdf(file_path)
    elif suffix == ".docx":
        return _load_docx(file_path)
    else:
        raise DocumentLoadError(f"Unsupported file type: {suffix or '(none)'}")


def _load_txt(file_path):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except OSError as e:
        raise DocumentLoadError(f"Failed to read text file: {e}") from e
    if not content.strip():
        raise DocumentLoadError("File is empty.")
    return content


def _load_pdf(file_path):
    try:
        reader = PdfReader(str(file_path))
    except Exception as e:
        raise DocumentLoadError(f"Failed to open PDF: {e}") from e

    pages = []
    for page in reader.pages:
        try:
            text = page.extract_text()
        except Exception:
            text = None
        if text:
            pages.append(text)

    if not pages:
        raise DocumentLoadError(
            "No extractable text found in PDF (it may be a scanned image)."
        )
    return "\n\n".join(pages)


def _load_docx(file_path):
    try:
        doc = docx.Document(str(file_path))
    except Exception as e:
        raise DocumentLoadError(f"Failed to open DOCX: {e}") from e

    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    if not paragraphs:
        raise DocumentLoadError("No text found in DOCX.")
    return "\n\n".join(paragraphs)
