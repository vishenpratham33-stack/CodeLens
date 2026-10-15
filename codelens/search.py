"""Step 3 of CodeLens: answwering a query with the inverted index"""

from pathlib import Path
from typing import List, Optional, Tuple

from codelens.crawler import is_inside, read_text
from codelens.heap import top_k
from codelens.index import InvertedIndex
from codelens.scoring import tf_idf_score
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
    """"AND search: documents that contain EVERY word of the query."""
    words = list(dict.fromkeys(tokenize(query))) # unique, same order
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

def ranked_search(index: InvertedIndex, query: str, k: int = 10, match_any: bool = False) -> Tuple[int, List[Tuple[float, int]]]:
    """Find matches, score them, and keep only the best k.
    
    Return(how many files matched in total, [(score, doc_id), ...]).
    """
    words = list(dict.fromkeys(tokenize(query)))
    doc_ids = search_any(index, query) if match_any else search_all(index, query)
    scored = [(tf_idf_score(index, doc_id, words), doc_id) for doc_id in doc_ids]
    return len(doc_ids), top_k(scored, k)


def find_snippet(root: str, path: str, words: List[str]) -> Optional[Tuple[int, str]]:
    """The line of the file that contains the MOST of the query words."""
    root_path = Path(root).resolve()
    full = root_path / path
    if not is_inside(root_path, full):
        return None
    try:
        text = read_text(full)
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
        if hits > best_hits:          # ">" keeps the FIRST line on a tie
            best_line_no, best_text, best_hits = line_no, line.strip()[:100], hits
    if best_hits == 0:
        return None
    return best_line_no, best_text