from pathlib import Path
from typing import Callable, Dict, Optional

from codelens import config


READERS: Dict[str, Callable[[Path], Optional[str]]] = {}


def _register_document_readers() -> None:
    try:
        from codelens.extractors.pdf_reader import extract_pdf
        READERS[".pdf"] = extract_pdf
    except ImportError:
        pass                      
    try:
        from codelens.extractors.word_reader import extract_docx
        READERS[".docx"] = extract_docx
    except ImportError:
        pass
    try:
        from codelens.extractors.excel_reader import extract_xlsx
        READERS[".xlsx"] = extract_xlsx
    except ImportError:
        pass

_register_document_readers()


def looks_like_text(raw: bytes) -> bool:
    """Binary files (images, programs) almost always contain a zero byte."""
    return b"\x00" not in raw[:4096]


def read_text(path: Path) -> Optional[str]:
    """Return the file's text, or None if it is not a text file."""
    raw = path.read_bytes()
    if not looks_like_text(raw):
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")

    
def read_file(path: Path) -> Optional[str]:
    suffix = path.suffix.lower()
    if suffix in READERS:
        text = READERS[suffix](path)
    elif suffix in config.DOCUMENT_EXTENSIONS:
        return None               

    else:
        text = read_text(path)
    if text is not None and len(text) > config.MAX_TEXT_CHARS:
        text = text[:config.MAX_TEXT_CHARS]      
    return text