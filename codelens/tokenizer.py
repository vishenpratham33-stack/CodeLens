"""Step 2 of CodeLens: turn raw text into clean list of words(tokens)
The SAME function is used for file text and for the user's search query.
Ifthe two were tokenized differently, searches would miss files.
"""

import re
from typing import Dict, List

from codelens import config

# Runs of letters and digits. An underscore is NOT included, so it acts as a
# Seperator: max_file_size -> max | file | size
_WORD_RE = re.compile(r"[A-Za-z0-9]+")

# Splits one run into pieces at CamelCase borders. tried in this order:
#   1) a block of capitals that is followed by a capital+lowercase (HTTP|Response)
#   2) an optional capital letter followed by lowercase letters (get , Response)
#   3) a block of capitals (HTML)
#   4) a block of digits (2)
_CAMEL_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+")

def tokenize(text: str, remove_stop_words: bool = False) -> List[str]:
    """Return the token of text, in order, duplicates included.
     
     Order and duplicates are kept on purpose: later we needthem for
     count word (TF-IDF) and for phase search.
    """
    tokens: List[str] =[]
    for chunk in _WORD_RE.findall(text):
        for part in _CAMEL_RE.findall(chunk):
            word = part.lower()
            if len(word) < config.MIN_TOKEN_LENGTH:
                continue
            if remove_stop_words and word in config.STOP_WORDS:
                continue
            tokens.append(word)
    return tokens

def count_terms(tokens: List[str]) -> Dict[str , int]:
    """Counts how many times each word appears (a hash map in action)."""
    counts: Dict[str , int] = {}
    for word in tokens:
        counts[word] = counts.get(word, 0) + 1 
    return counts