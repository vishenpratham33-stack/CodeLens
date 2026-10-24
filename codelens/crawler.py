"""Step 1 of CodeLens: find files, filter them, and read their text."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from codelens import config
from codelens.reader import read_file


@dataclass
class FileInfo:
    """What we know about a file WITHOUT reading it."""

    path: str          # relative to the chosen folder, always with "/"
    full_path: Path
    size: int          # bytes
    modified: float    # last-modified time (seconds since 1970)


@dataclass
class Document:
    """One readable file, ready for the next step (tokenizing)."""

    doc_id: int
    path: str
    size: int
    modified: float
    text: str


def is_inside(root: Path, candidate: Path) -> bool:
    """Return True only if candidate really lives inside root.

    resolve() removes tricks like "../.." and follows shortcuts, so a
    sneaky path cannot escape the folder the user chose.
    """
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


# Windows marks OneDrive "online only" files with these flags. Opening such a
# file would make OneDrive DOWNLOAD it, so we must never touch them.
CLOUD_ONLY_FLAGS = 0x1000 | 0x40000 | 0x400000


def is_cloud_only(stat_result) -> bool:
    """True for a file that exists only in the cloud (not on this computer yet)."""
    return bool(getattr(stat_result, "st_file_attributes", 0) & CLOUD_ONLY_FLAGS)


def list_files(root_folder: str, absolute: bool = False) -> Iterator[FileInfo]:
    """Walk through root_folder and yield every file we MAY read.

    Only the file's name, size and date are looked at here. Nothing is
    opened, so listing thousands of files is fast.
    With absolute=True the paths are full paths (used when several
    folders are searched together).
    """
    root = Path(root_folder).resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Not a folder: {root}")

    for current_dir, dir_names, file_names in os.walk(root):
        # Editing dir_names in place tells os.walk to skip those folders.
        dir_names[:] = sorted(
            d for d in dir_names
            if d not in config.IGNORED_DIRS and not d.startswith(".")
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
            if is_cloud_only(info):
                continue
            limit = (config.MAX_DOCUMENT_SIZE_BYTES if is_document
                     else config.MAX_FILE_SIZE_BYTES)
            if info.st_size > limit:
                continue

            yield FileInfo(
                path=path.as_posix() if absolute else path.relative_to(root).as_posix(),
                full_path=path,
                size=info.st_size,
                modified=info.st_mtime,
            )


def crawl(root_folder: str) -> Iterator[Document]:
    """List the files, read their text, and yield one Document per good file.

    This is a generator: it hands over one file at a time instead of
    loading everything into memory. That is what lets CodeLens scale.
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
