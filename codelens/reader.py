"""Reading the text of one file. The only place that knows how to open files.

Everything else (crawler, updater, snippets) call read_files() and does not care what kind of file it is. That single door is what let us add PDF, Word and Excel later without touching the rest of the engine.
"""

from pathlib import Path
from typing import Optional

from codelens import config


def looks_like_text(raw: bytes) -> bool:
    """Binary files (images, programs) almos always contain a zero byte."""
    return b"\x00" not in raw[:4096]


def read_text(path: Path) -> Optional[str]:
    """Return the file's text, or None if it is not a text file."""
    raw = path.read_bytes()
    if not looks_like_text(raw):
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        # latin-1 can decode any byte, so this fallback never crashes.
        return raw.decode("latin-1")


def read_file(path: Path) -> Optional[str]:
    """The text of any supported file, or None if it cannot be read."""
    if path.suffix.lower() in config.DOCUMENT_EXTENSIONS:
        return None               # documents: supported from Part B on
    return read_text(path)