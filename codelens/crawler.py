"""Step 1 of CodeLens: find files, filter them, and read their text."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

from codelens import config
from codelens.reader import read_file


@dataclass
class FileInfo:
    """What we know about a file without reading it."""
    path: str           # relative to chosen folder, always with "/"
    full_path: Path
    size: int           # bytes
    modified: float     # last-modified time (seconds since 1970)


@dataclass
class Document:
    """one readable file, ready for the next step(tokenizing)."""

    doc_id: int
    path: str             # relative to the chosen folder, always with "/"
    size: int             # in bytes
    modified: float        #last-modified time (second since 1970)
    text: str


def is_inside(root: Path, candidate: Path) -> bool:
    """Return True only if candidate really lives inside root.
    
    resolve( removes tricks like "../.." and follows shortcuts, so a sneaky path cannot escape the folder the user chose.
    """
    try:
        candidate.resolve() .relative_to(root.resolve())
        return True
    except ValueError:
        return False


def list_files(root_folder: str) -> Iterator[FileInfo]:
    """Walk  through root_folder and yield every file we MAY read.
    
    Only the file name, date and size are looked at here. Nothing is opened, so listing thousands of files is fast.
    """
    root = Path(root_folder).resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"not a folder: {root}")

    for current_dir, dir_names, file_names in os.walk(root):
        # Editing dir_names in place tells os.walk to skip those folders.
        dir_names[:] = sorted(
            d for d in dir_names if d not in config.IGNORED_DIRS
        )

        for name in sorted(file_names):
            path = Path(current_dir) / name
            suffix = path.suffix.lower()
            is_document = suffix in config.DOCUMENT_EXTENSIONS

            if suffix not in config.ALLOWED_EXTENSIONS and not is_document:
                continue
            if path.is_symlink() or not is_inside(root, path):
                continue

            try:
                info = path.stat()
            except OSError:
                continue                  # locked or unreadable: skip it
            limit = (config.MAX_DOCUMENT_SIZE_BYTES if is_document
                     else config.MAX_FILE_SIZE_BYTES)
            if info.st_size > limit:
                continue

            yield FileInfo(
                path=path.relative_to(root).as_posix(),
                full_path=path,
                size=info.st_size,
                modified=info.st_mtime,
            )

    
def crawl(root_folder: str) -> Iterator[Document]:
    """List the files, read thier text, and yield one Document per good file.
    
    This is a Generator: it hands over one file at a time instead of loading everything into memory. that is what lets CodeLens scale.
    """

    doc_id = 0
    for info in list_files(root_folder):
        try:
            text = read_file(info.full_path)
        except OSError:
            continue
        if text is None:
            continue

        yield Document(
            doc_id=doc_id,
            path=info.path,
            size=info.size,
            modified=info.modified,
            text=text,
        )
        doc_id += 1