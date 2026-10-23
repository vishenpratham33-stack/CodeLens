
from typing import Dict, List, Set

from codelens.crawler import crawl
from codelens.tokenizer import tokenize

class InvertedIndex:
    def __init__(self) -> None:
        # word -> {doc_id: [positions of that word inside the document]}
        self.postings: Dict[str, Dict[int, List[int]]] = {}
        # doc_id -> facts about the file (path, size, ...)
        self.docs: Dict[int, dict] = {}
        self._last_doc_id = -1

    def add_document(self, doc_id: int, path: str, tokens: List[str], size: int = 0, modified: float = 0.0) -> None:
        if doc_id <= self._last_doc_id:
            raise ValueError("doc_id must keep increasing")
        self._last_doc_id = doc_id

        self.docs[doc_id] = {
            "path": path,
            "size": size,
            "modified": modified,
            "length": len(tokens),
        }
        for position, word in enumerate(tokens):
            self.postings.setdefault(word, {}).setdefault(doc_id, []).append(position)


    @property
    def next_doc_id(self) -> int:
        return self._last_doc_id + 1

    def remove_documents(self, doc_ids: Set[int]) -> None:
        if not doc_ids:
            return
        for doc_id in doc_ids:
            self.docs.pop(doc_id, None)
        for word in list(self.postings):
            entry = self.postings[word]
            for doc_id in doc_ids:
                entry.pop(doc_id, None)
            if not entry:
                del self.postings[word]   

    def to_dict(self) -> dict:
        return {
            "docs": {str(i): meta for i, meta in self.docs.items()},
            "postings": {
                word: {str(i): positions for i, positions in entry.items()}
                for word, entry in self.postings.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InvertedIndex":
        index = cls()
        index.docs = {int(i): meta for i, meta in data["docs"].items()}
        index.postings = {
            word: {int(i): list(pos) for i, pos in sorted(
                entry.items(), key=lambda pair: int(pair[0]))}
            for word, entry in data["postings"].items()
        }
        index._last_doc_id = max(index.docs, default=-1)
        return index


    def doc_ids(self, word: str) -> List[int]:
        return list(self.postings.get(word, {}))

    
    def positions(self, word: str, doc_id: int) -> list[int]:
        return self.postings.get(word, {}).get(doc_id, [])


    def doc_frequency(self, word: str) -> int:
        return len(self.postings.get(word, {}))

    @property
    def doc_count(self) -> int:
        return len(self.docs)

    @property
    def vocabulary_size(self) -> int:
        return len(self.postings)
    
def build_index(folder: str) -> InvertedIndex:
    index = InvertedIndex()
    for doc in crawl(folder):
        index.add_document(
            doc.doc_id, doc.path, tokenize(doc.text), doc.size, doc.modified
        )
    return index