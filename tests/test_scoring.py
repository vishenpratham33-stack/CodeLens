import math

from codelens.index import InvertedIndex
from codelens.scoring import idf, tf_idf_score


def make_index():
    index = InvertedIndex()
    index.add_document(0, "a.py", ["the", "heap", "the", "heap", "heap"])
    index.add_document(1, "b.py", ["the", "sort"])
    index.add_document(2, "c.py", ["the", "list"])
    return index


def test_rare_word_has_bigger_idf():
    index = make_index()
    assert idf(index, "heap") > idf(index, "the")


def test_idf_of_unknown_word_is_zero():
    assert idf(make_index(), "zebra") == 0.0


def test_idf_value():
    index = make_index()           #3 documents, "heap" is in 1 of them
    assert math.isclose(idf(index, "heap"), math.log(1 + 3 / 1))


def test_more_mentions_score_higher():
    index = InvertedIndex()
    index.add_document(0, "a.py", ["cat", "x1"])
    index.add_document(1, "b.py", ["cat", "cat", "cat"])
    assert tf_idf_score(index, 1, ["cat"]) > tf_idf_score(index, 0, ["cat"])


def test_missing_word_adds_nothing():
    index = make_index()
    assert tf_idf_score(index, 1, ["heap"]) == 0.0
    assert tf_idf_score(index, 0, []) == 0.0