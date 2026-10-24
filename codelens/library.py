"""The "My files" mode: CodeLens finds the files by itself.

A Library watches a list of folders (by default Documents, Desktop and
Downloads), indexes them in the background, and keeps the index fresh.
The user never uploads anything: they only type what they remember.
"""

import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Union

from codelens.crawler import FileInfo, list_files
from codelens.index import InvertedIndex
from codelens.storage import load_index, save_index
from codelens.updater import apply_changes, plan_changes, read_changes

BATCH_SIZE = 100          # documents added per short lock, so searches never wait long


def default_roots() -> List[Path]:
    """The usual places where people keep their files (only those that exist)."""
    home = Path.home()
    names = ["Documents", "Desktop", "Downloads"]
    candidates = [home / name for name in names]
    candidates += [home / "OneDrive" / name for name in names]   # Windows with OneDrive
    found: List[Path] = []
    for folder in candidates:
        try:
            resolved = folder.resolve()
        except OSError:
            continue
        if resolved.is_dir() and resolved not in found:
            found.append(resolved)
    # drop a folder that lies inside another one in the list (it would be read twice)
    return [f for f in found if not any(o != f and o in f.parents for o in found)]


class Library:

    def __init__(self, roots: List[Union[str, Path]], store_dir: Union[str, Path],
                 refresh_seconds: float = 120.0) -> None:
        self.roots = [Path(r).resolve() for r in roots]
        self.store_dir = str(store_dir)
        self.refresh_seconds = refresh_seconds
        self.index: Optional[InvertedIndex] = None
        self.lock = threading.RLock()             # held while the index is read or changed
        self._status = {"state": "starting", "pending": 0, "updated": None, "error": None}
        self._status_lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ----- what the page shows -----
    def status(self) -> dict:
        with self._status_lock:
            info = dict(self._status)
        with self.lock:
            info["files"] = self.index.doc_count if self.index else 0
            info["words"] = self.index.vocabulary_size if self.index else 0
        info["roots"] = [str(r) for r in self.roots]
        return info

    def _set(self, **changes) -> None:
        with self._status_lock:
            self._status.update(changes)

    # ----- one pass over the folders -----
    def sync(self) -> None:
        """Make the index match the disk. Safe to run while searches happen."""
        try:
            self._set(state="scanning", error=None)
            on_disk: Dict[str, FileInfo] = {}
            for root in self.roots:
                for info in list_files(str(root), absolute=True):
                    on_disk[info.path] = info
                    if self._stop.is_set():
                        return

            first_time = self.index is None
            if first_time:
                loaded = load_index(self.store_dir)      # instant start if saved before
                with self.lock:
                    self.index = loaded or InvertedIndex()
            index = self.index

            with self.lock:
                old_ids, to_read = plan_changes(index, on_disk)
            changed_something = bool(old_ids) or first_time

            self._set(state="indexing", pending=len(to_read))
            with self.lock:
                index.remove_documents(old_ids)
            batch = []
            done = 0
            for item in read_changes(to_read):             # slow part: NOT holding the lock
                batch.append(item)
                done += 1
                if len(batch) >= BATCH_SIZE:
                    self._add_batch(index, batch)
                    batch = []
                    self._set(pending=len(to_read) - done)
                    changed_something = True
                if self._stop.is_set():
                    return
            if batch:
                self._add_batch(index, batch)
                changed_something = True

            if changed_something or to_read:
                with self.lock:
                    save_index(index, self.store_dir)
            self._set(state="ready", pending=0, updated=time.time())
        except Exception as error:                         # keep the program alive
            self._set(state="error", error=str(error))

    def _add_batch(self, index: InvertedIndex, batch: list) -> None:
        with self.lock:
            apply_changes(index, set(), iter(batch))

    # ----- background life -----
    def start(self) -> None:
        """Index in the background, and look for changes now and then."""
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._loop, name="library", daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            self.sync()
            self._wake.wait(self.refresh_seconds)
            self._wake.clear()

    def refresh_now(self) -> None:
        self._wake.set()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def contains(self, path: str) -> bool:
        """Is this exact path one of the indexed files? (the only files we ever hand out)"""
        with self.lock:
            return self.index is not None and any(meta["path"] == path for meta in self.index.docs.values())