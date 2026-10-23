from dataclasses import dataclass
from typing import Tuple

from codelens.crawler import list_files
from codelens.index import InvertedIndex, build_index
from codelens.reader import read_file
from codelens.storage import load_index, save_index
from codelens.tokenizer import tokenize


@dataclass
class UpdateReport:
    mode: str 
    added: int = 0
    changed: int = 0
    removed: int = 0


def update_index(folder: str, rebuild: bool = False) -> Tuple[InvertedIndex, UpdateReport]:
    index = None if rebuild else load_index(folder)
    if index is None:
        index = build_index(folder)
        save_index(index, folder)
        return index, UpdateReport("built", added=index.doc_count)

    on_disk = {info.path: info for info in list_files(folder)}
    known = {meta["path"]: doc_id for doc_id, meta in index.docs.items()}

    old_ids = set()
    to_read = []
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

    if not old_ids and not to_read:
        return index, UpdateReport("loaded")

    index.remove_documents(old_ids)
    report = UpdateReport("updated", removed=len(old_ids))
    for info, was_known in sorted(to_read, key=lambda pair: pair[0].path):
        try:
            text = read_file(info.full_path)
        except OSError:
            continue
        if text is None:
            continue
        index.add_document(index.next_doc_id, info.path, tokenize(text), info.size, info.modified)
        if was_known:
            report.changed += 1
            report.removed -= 1
        else:
            report.added += 1

    if report.added == report.changed == report.removed == 0:
        return index, UpdateReport("loaded")
    
    save_index(index, folder)
    return index, report
    