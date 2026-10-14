from codelens.index import InvertedIndex
from codelens.search import (intersect_sorted, search_all, search_any, union_sorted)

def make_index():
    index = InvertedIndex()
    index.add_document(0, "a.py", ["cat", "dog"])
    index.add_document(1, "b.py", ["dog", "bird"])
    index.add_document(2, "c.py", ["cat", "dog", "bird"])
    return index


def test_intersect_sorted():
    assert intersect_sorted([1, 3, 5,7], [3, 4, 5 ,8]) == [3, 5]
    assert intersect_sorted([1, 2], [3, 4]) == []
    assert intersect_sorted([], [1, 2]) == []

def test_union_sorted():
    assert union_sorted([1, 3, 5], [2, 3, 6]) == [1, 2, 3, 5, 6]
    assert union_sorted([], [4]) == [4]


def test_search_all_needs_every_word():
    index = make_index()
    assert search_all(index, "cat dog") == [0, 2]
    assert search_all(index, "dog bird") == [1, 2]
    assert search_all(index, "cat dog bird") == [2]


def test_search_any_needs_one_word():
    index = make_index()
    assert search_any(index, "cat bird") == [0, 1, 2]
    assert search_any(index, "cat") == [0, 2]


def test_unknown_word_and_empty_query():
    index = make_index()
    assert search_all(index, "zebra") == []
    assert search_all(index, "cat zebra") == []
    assert search_all(index, "") == []
    assert search_any(index, "") == []

def test_query_is_tokenized_like_the_files():
    index = make_index()
    assert search_all(index, "CAT, Dog!") == [0, 2]