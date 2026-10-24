"""Step 3 of CodeLens: answering a query with the inverted index."""

import math
from pathlib import Path
from typing import List, Optional, Tuple

from codelens.crawler import is_inside
from codelens.heap import top_k
from codelens.index import InvertedIndex
from codelens.reader import read_file
from codelens.scoring import idf, tf_idf_score
from codelens.tokenizer import tokenize


def intersect_sorted(a: List[int], b: List[int]) -> List[int]:
    """Items found in BOTH sorted lists, using two pointers (one pass)."""
    i = j = 0
    out: List[int] = []
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            out.append(a[i])
            i += 1
            j += 1
        elif a[i] < b[j]:
            i += 1
        else:
            j += 1
    return out


def union_sorted(a: List[int], b: List[int]) -> List[int]:
    """Items found in EITHER sorted list, without repeats (a merge)."""
    i = j = 0
    out: List[int] = []
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            out.append(a[i])
            i += 1
            j += 1
        elif a[i] < b[j]:
            out.append(a[i])
            i += 1
        else:
            out.append(b[j])
            j += 1
    out.extend(a[i:])
    out.extend(b[j:])
    return out


def search_all(index: InvertedIndex, query: str) -> List[int]:
    """AND search: documents that contain EVERY word of the query."""
    words = list(dict.fromkeys(tokenize(query)))   # unique, same order
    if not words:
        return []
    lists = [index.doc_ids(word) for word in words]
    lists.sort(key=len)            # start with the shortest list: fastest
    result = lists[0]
    for other in lists[1:]:
        if not result:
            break                  # nothing left, no need to continue
        result = intersect_sorted(result, other)
    return result


def search_any(index: InvertedIndex, query: str) -> List[int]:
    """OR search: documents that contain AT LEAST ONE word of the query."""
    result: List[int] = []
    for word in dict.fromkeys(tokenize(query)):
        result = union_sorted(result, index.doc_ids(word))
    return result


def ranked_search(index: InvertedIndex, query: str, k: int = 10,
                  match_any: bool = False) -> Tuple[int, List[Tuple[float, int]]]:
    """Find matches, score them, and keep only the best k.

    Returns (how many files matched in total, [(score, doc_id), ...]).
    """
    words = list(dict.fromkeys(tokenize(query)))
    doc_ids = search_any(index, query) if match_any else search_all(index, query)
    scored = [(tf_idf_score(index, doc_id, words), doc_id) for doc_id in doc_ids]
    return len(doc_ids), top_k(scored, k)


def phrase_positions(index: InvertedIndex, words: List[str], doc_id: int) -> List[int]:
    """Where does the exact phrase start inside this document?

    Words must sit next to each other, in order. Example: for the phrase
    "sliding window" a start position p is good if "sliding" is at p and
    "window" is at p + 1.
    """
    if not words:
        return []
    starts = set(index.positions(words[0], doc_id))
    for offset in range(1, len(words)):
        here = set(index.positions(words[offset], doc_id))
        starts = {p for p in starts if p + offset in here}
        if not starts:
            return []
    return sorted(starts)


def search_phrase(index: InvertedIndex, query: str) -> List[int]:
    """Documents that contain the query words next to each other, in order."""
    words = tokenize(query)                      # keep order AND repeats
    if not words:
        return []
    candidates = search_all(index, query)        # first: files with every word
    return [d for d in candidates if phrase_positions(index, words, d)]


def ranked_phrase_search(index: InvertedIndex, query: str, k: int = 10
                         ) -> Tuple[int, List[Tuple[float, int]]]:
    """Phrase search, best k first. The phrase is scored like ONE rare word."""
    words = tokenize(query)
    doc_ids = search_phrase(index, query)
    # A phrase is rarer than any of its words, so we add their IDF values.
    phrase_idf = sum(idf(index, word) for word in dict.fromkeys(words))
    scored = []
    for doc_id in doc_ids:
        times = len(phrase_positions(index, words, doc_id))
        scored.append(((1 + math.log(times)) * phrase_idf, doc_id))
    return len(doc_ids), top_k(scored, k)


def snippet_in_file(full_path: Path, words: List[str]) -> Optional[Tuple[int, str]]:
    """The line of the file that contains the MOST of the query words."""
    try:
        text = read_file(full_path)
    except OSError:
        return None
    if text is None:
        return None

    wanted = set(words)
    best_line_no = 0
    best_text = ""
    best_hits = 0
    for line_no, line in enumerate(text.splitlines(), start=1):
        hits = len(wanted & set(tokenize(line)))
        if hits > best_hits:           # ">" keeps the FIRST line on a tie
            best_line_no, best_text, best_hits = line_no, line.strip()[:100], hits
    if best_hits == 0:
        return None
    return best_line_no, best_text


def find_snippet(root: str, path: str, words: List[str]) -> Optional[Tuple[int, str]]:
    """Like snippet_in_file, for a path relative to root (checked to stay inside root)."""
    root_path = Path(root).resolve()
    full = root_path / path
    if not is_inside(root_path, full):
        return None
    return snippet_in_file(full, words)
