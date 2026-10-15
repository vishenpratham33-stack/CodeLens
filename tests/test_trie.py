from codelens.index import InvertedIndex
from codelens.trie import Trie, build_trie


def make_trie():
    trie = Trie()
    trie.insert("car", 5)
    trie.insert("card", 2)
    trie.insert("cat", 9)
    trie.insert("dog", 1)
    return trie


def test_contains_whole_words_only():
    trie = make_trie()
    assert trie.contains("car")
    assert not trie.contains("ca")       # a prefix, not a word
    assert not trie.contains("cow")


def test_starts_with():
    trie = make_trie()
    assert trie.starts_with("ca")
    assert trie.starts_with("")
    assert not trie.starts_with("x")


def test_suggest_most_popular_first():
    assert make_trie().suggest("ca") == ["cat", "car", "card"]


def test_suggest_limit_and_unknown_prefix():
    trie = make_trie()
    assert trie.suggest("ca", limit=2) == ["cat", "car"]
    assert trie.suggest("zz") == []


def test_suggest_includes_the_prefix_itself():
    assert make_trie().suggest("car") == ["car", "card"]


def test_build_trie_uses_document_frequency():
    index = InvertedIndex()
    index.add_document(0, "a.py", ["token", "tool"])
    index.add_document(1, "b.py", ["tokken", "total"])
    trie = build_trie(index)
    assert trie.suggest("to")[0] == "token"        # in 2 files, the others in 1