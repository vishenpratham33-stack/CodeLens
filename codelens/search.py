"""Step 3 of CodeLens: answwering a query with the inverted index"""

from pathlib import Path
from typing import List, Optional, Tuple

from codelens.crawler import is_inside, read_text
from codelens.index import InvertedIndex
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


def find_snippet(root: str, path: str, words: List[str]) -> Optional[Tuple[int, str]]:
    """First line of the file that contains one of the words."""
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
    for line_no, line in enumerate(text.splitlines(), start=1):
        if wanted & set(tokenize(line)):
            return line_no, line.strip()[:100]
    return None