"""Load and validate audio files."""
from pathlib import Path

SUPPORTED_FORMATS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".mp4", ".webm"}


def load_audio(audio_path: str) -> Path:
    """Validate an audio file and return its Path."""
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")
    if path.suffix.lower() not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported format: {path.suffix}. "
            f"Supported: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )
    return path


def is_supported(audio_path: str) -> bool:
    """Check if a file has a supported audio extension."""
    return Path(audio_path).suffix.lower() in SUPPORTED_FORMATS
