from pathlib import Path
from typing import Optional

from pypdf import PdfReader


def extract_pdf(path: Path) -> Optional[str]:
    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            return None
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception:
        return None
    return "\n".join(pages)