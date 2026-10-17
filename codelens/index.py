"""Step 3 of CodeLens: the inverted index.

A normal index maps file -> words.
An INVERTED index flips it: word -> files that contain it.
That flip is what makes searching fast.
"""

from typing import Dict, List

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
        """Add one file. doc_ids must arrive in increasing order."""
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


    def doc_ids(self, word: str) -> List[int]:
        """Sorted list of documents that contain word (empty if none)."""
        #dictionaries remember insertion order, and ids were added in
        #increasing order, so this list is already sorted.
        return list(self.postings.get(word, {}))

    
    def positions(self, word: str, doc_id: int) -> list[int]:
        return self.postings.get(word, {}).get(doc_id, [])


    def doc_frequency(self, word: str) -> int:
        """In how many documents does word appear?"""
        return len(self.postings.get(word, {}))

    @property
    def doc_count(self) -> int:
        return len(self.docs)

    @property
    def vocabulary_size(self) -> int:
        return len(self.postings)
    
def build_index(folder: str) -> InvertedIndex:
    """Crawl a folder, tokeenize every file, and return the finished index."""
    index = InvertedIndex()
    for doc in crawl(folder):
        index.add_document(
            doc.doc_id, doc.path, tokenize(doc.text), doc.size, doc.modified
        )
    return index