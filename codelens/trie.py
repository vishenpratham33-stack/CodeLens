"""Step 4 (Part B) of CodeLens: a trie, for autocomplete.

A trie is a tree of letters. Words that start the same share the same path, so "car", "card" and "cat" all begin with the path c -> a.
"""

from typing import Dict, List, Tuple

from codelens.index import InvertedIndex


class TrieNode:
    def __init__(self) -> None:
        self.children: Dict[str, "TrieNode"] = {}
        self.is_word = False
        self.weight = 0          # how popular the word editing here is

class Trie:
    def __init__(self) -> None:
        self.root = TrieNode()

    def insert(self, word: str, weight: int = 1) -> None:
        node = self.root 
        for letter in word:
            if letter not in node.children:
                    node.children[letter] = TrieNode()
            node = node.children[letter]
        node.is_word = True
        node.weight = weight

    def _find(self, prefix: str):
        """Walk down the letters of prefix; return the node, or None."""
        node = self.root
        for letter in prefix:
            node = node.children.get(letter)
            if node is None:
                return None
        return node

    def contains(self, word: str) -> bool:
        node = self._find(word)
        return node is not None and node.is_word

    def starts_with(self, prefix: str) -> bool:
        return self._find(prefix) is not None 

    def suggest(self, prefix: str, limit: int = 5) -> List[str]:
        """Up to 'limit' words that start with prefix,, most popular first."""
        start = self._find(prefix)
        if start is None:
            return[]

        found: List[Tuple[int, str]] = []
        stack = [(start, prefix)]         # explore the sub-tree
        while stack:
            node, text = stack.pop()
            if node.is_word:
                found.append((node.weight, text))
            for letter, child in node.children.items():
                stack.append((child, text + letter))

        # Popular first; same popularity -> alphabetical.
        found.sort(key=lambda pair: (-pair[0], pair[1]))
        return [text for _, text in found[:limit]]


def build_trie(index: InvertedIndex) -> Trie:
    """One trie holding every word of the index, weighted by popularity."""
    trie = Trie()
    for word in index.postings:
        trie.insert(word, index.doc_frequency(word))
    return trie