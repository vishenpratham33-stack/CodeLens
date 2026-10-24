"""Step 6 of CodeLens: keep the saved index up to date.

Reading a file costs far more than looking at its size and date. So we
read only the files that are NEW or CHANGED, and forget the deleted ones.

The work is split in three small steps, so that a long-running program
(the "My files" mode) can do the slow step without blocking searches:
    plan_changes  : compare the index with the disk        (fast)
    read_changes  : read and tokenize the changed files    (slow)
    apply_changes : update the index                       (fast)
"""

from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Set, Tuple

from codelens.crawler import FileInfo, list_files
from codelens.index import InvertedIndex
from codelens.reader import read_file
from codelens.storage import load_index, save_index
from codelens.tokenizer import tokenize


@dataclass
class UpdateReport:
    mode: str          # "built", "loaded" or "updated"
    added: int = 0
    changed: int = 0
    removed: int = 0


def plan_changes(index: InvertedIndex,
                 on_disk: Dict[str, FileInfo]) -> Tuple[Set[int], List[Tuple[FileInfo, bool]]]:
    """Which documents must be forgotten, and which files must be read?"""
    known = {meta["path"]: doc_id for doc_id, meta in index.docs.items()}
    old_ids: Set[int] = set()             # deleted or changed documents
    to_read: List[Tuple[FileInfo, bool]] = []   # (file, was it already known?)
    for path, doc_id in known.items():
        info = on_disk.get(path)
        meta = index.docs[doc_id]
        if info is None:
            old_ids.add(doc_id)
        elif info.size != meta["size"] or info.modified != meta["modified"]:
            old_ids.add(doc_id)
            to_read.append((info, True))
    for path, info in on_disk.items():
        if path not in known:
            to_read.append((info, False))
    to_read.sort(key=lambda pair: pair[0].path)    # same folder, same ids
    return old_ids, to_read


def read_changes(to_read: List[Tuple[FileInfo, bool]]) -> Iterator[Tuple[FileInfo, bool, List[str]]]:
    """Read and tokenize the files one by one (a generator: low memory)."""
    for info, was_known in to_read:
        try:
            text = read_file(info.full_path)
        except OSError:
            continue
        if text is None:
            continue                       # unreadable: stays forgotten
        yield info, was_known, tokenize(text)


def apply_changes(index: InvertedIndex, old_ids: Set[int],
                  new_docs: Iterator[Tuple[FileInfo, bool, List[str]]]) -> UpdateReport:
    """Forget the old documents and add the new ones."""
    index.remove_documents(old_ids)
    report = UpdateReport("updated", removed=len(old_ids))
    for info, was_known, tokens in new_docs:
        index.add_document(index.next_doc_id, info.path, tokens, info.size, info.modified)
        if was_known:
            report.changed += 1
            report.removed -= 1            # it was removed AND re-added
        else:
            report.added += 1
    if report.added == report.changed == report.removed == 0:
        report.mode = "loaded"             # nothing really changed
    return report


def update_index(folder: str, rebuild: bool = False,
                 current: Optional[InvertedIndex] = None) -> Tuple[InvertedIndex, UpdateReport]:
    """Return an up-to-date index for the folder, doing as little work as possible.

    `current` is an index you already hold in memory (a server keeps one).
    Then we skip reading the saved file, which is the slowest part.
    """
    if rebuild:
        index = None
    else:
        index = current if current is not None else load_index(folder)
    first_time = index is None
    if first_time:
        index = InvertedIndex()

    on_disk = {info.path: info for info in list_files(folder)}
    old_ids, to_read = plan_changes(index, on_disk)
    if not first_time and not old_ids and not to_read:
        return index, UpdateReport("loaded")

    report = apply_changes(index, old_ids, read_changes(to_read))
    if first_time:
        save_index(index, folder)
        return index, UpdateReport("built", added=index.doc_count)
    if report.mode == "updated":
        save_index(index, folder)
    return index, report