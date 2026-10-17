"""Step 5 of CodeLens: forgive typos with edit distance.

Edit distance = the fewest single-letter changes(insert, delete or replace on letter) that turns one word into another.
    tokenise - tokenize    : 1 changes (s -> z)
    serach -> search       : 2 changes (swap counts as two)
"""

from typing import List, Optional, Tuple
from codelens.index import InvertedIndex


def edit_distance(a: str, b: str, max_distance: Optional[int] = None) -> int:
    """Levenshtein distance between a and b.
    
    if max_distance is given we stop early and return max_distance + 1 as soon as we know the real answer is bigger. That saves a lot of work when we compare a typo with thousands of words.
    """
    if a == b:
        return 0
    if max_distance is not None and abs(len(a) - len(b)) > max_distance:
        return max_distance + 1
    if len(a) < len(b):
        a, b = b, a                          # keep b the shorter word

    # previous[j] = distance between the first i-1 letters of a and the first j letters of b.
    previous = list(range(len(b) + 1))
    for i, letter_a in enumerate(a, start=1):
        current = [i]
        for j, letter_b in enumerate(b, start=1):
            cost = 0 if letter_a == letter_b else 1
            current.append(min(
                previous[j] + 1,                    # delete a letter
                current[j - 1] + 1,                 #insert a letter 
                previous[j - 1] + cost,             #replace (or keep) a letter
            ))
        if max_distance is not None and min(current) > max_distance:
            return max_distance + 1          # every part is already too long
        previous = current
    return previous[-1]


def default_max_distance(word: str) -> int:
    """Short words get a strict limit, or everything looks 'close'."""
    return 1 if len(word) <= 4 else 2


def suggest_corrections(index: InvertedIndex, word: str, max_distance: Optional[int] = None, limit: int = 3) -> List[str]:
    """Words of the index that are close to 'word', best first."""
    if max_distance is None:
        max_distance = default_max_distance(word)

    candidates: List[Tuple[int, int, str]] = []
    for known in index.postings:
        distance = edit_distance(word, known, max_distance)
        if distance <= max_distance:
            # closest first, then the more popular word, then alphabetical
            candidates.append((distance, -index.doc_frequency(known), known))
    candidates.sort()
    return [known for _, _, known in candidates[:limit]]


def correct_words(index: InvertedIndex, words: List[str]) -> Tuple[List[str], List[Tuple[str, str]]]:
    """Replace every unknown word by its best correction,  if there is one.
    
    Returns (the new list of words, [(typed, replaced_by), ...]).
    """
    fixed: List[str] = []
    changes: List[Tuple[str, str]] = []
    for word in words:
        if index.doc_frequency(word) > 0:
            fixed.append(word)
            continue
        options = suggest_corrections(index, word, limit=1)
        if options:
            fixed.append(options[0])
            changes.append((word, options[0]))
        else:
            fixed.append(word)                 # no idea: keep it as typed
    return fixed, changes