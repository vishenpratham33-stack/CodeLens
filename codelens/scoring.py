"""Step 4 (Part A) of CodeLens: how good is a match? TF - IDF scoring.

TF (Term Frequency)           : how often the word appears in THIS File 
IDF (inverse doc. frequency)  : how RARE the word is across ALL files 
score = TF part x IDF, ADDED up over the words of the query.
"""

import math
from typing import List

from codelens.index import InvertedIndex

def idf(index: InvertedIndex, word: str) -> float:
    """Rare words get a big number, common words a small one."""
    df = index.doc_frequency(word)
    if df == 0:
        return 0.0
    # The "1 +" keeps the value above zero even for a word found in every file.
    return math.log(1 + index.doc_count / df)

def tf_idf_score(index: InvertedIndex, doc_id: int, words: List[str]) -> float:
    """Total score of one document for the given query words."""
    total = 0.0
    for word in words:
        count = len(index.positions(word, doc_id))
        if count:
            # log: ten mentions are NOT ten times more relevant that one.
            total += (1 + math.log(count)) * idf(index, word)
    return total
