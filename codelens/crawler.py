"""Step 1 of CodeLens: find files, filter them, and read their text."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional
from codelens import config

@dataclass
class Document:
    """one readable file, ready for the next step(tokenizing)."""

    doc_id: int
    path: str             # relative to the chosen folder, always with "/"
    size: int             # in bytes
    modified: float        #last-modified time (second since 1970)
    text: str


def is_inside(root: Path, candidate: Path) -> bool:
    """REturn True only if candidate really lives inside root.
    
    resolve( removes tricks like "../.." and follows shortcuts, so a sneaky path cannot escape the folder the user chose.
    """
    try:
        candidate.resolve() .relative_to(root.resolve())
        return True
    except ValueError:
        return False

def looks_like_text(raw: bytes) -> bool:
    """binary files (images, programs) almost always contain azero byte."""
    return b"\x00" not in raw[:4096]


def read_text(path: Path) -> Optional[str]:
    """Return the file's text, or None if itis not a text file."""
    raw = path.read_bytes()
    if not looks_like_text(raw):
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        # latin-1 can decode any byte, so this fallback never crashes.
        return raw.decode("latin-1")
    
def crawl(root_folder: str) -> Iterator[Document]:
    """Walk through root_folder and yield one Document per good file.
    
    This is a Generator: it hands over one file at a time instead of loading everything into memory. that is whaty lets CodeLens scale.
    """
    root = Path(root_folder).resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Not a folder: {root}")

    doc_id = 0
    for current_dir, dir_names, file_names in os.walk(root):
        # Editing dir_names in place tells os.walk to skip those folders.
        dir_names[:] = sorted(
            d for d in dir_names if d not in config.IGNORED_DIRS
        )

        for name in sorted(file_names):
            path = Path(current_dir) / name

            if path.suffix.lower() not in config.ALLOWED_EXTENSIONS:
                continue
            if path.is_symlink() or not is_inside(root, path):
                continue

            try:
                info = path.stat()
                if info.st_size > config.MAX_FILE_SIZE_BYTES:
                    continue
                text = read_text(path)
            except OSError:
                continue  # locked or unreadable file: skip, don't crash
            if text is None:
                continue


            yield Document(
                doc_id=doc_id,
                path=path.relative_to(root).as_posix(),
                size=info.st_size,
                modified=info.st_mtime,
                text=text,
            )
            doc_id += 1