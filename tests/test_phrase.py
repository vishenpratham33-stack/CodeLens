from codelens.index import InvertedIndex, build_index
from codelens.search import (phrase_positions, ranked_phrase_search, search_phrase)


def make_index():
    index = InvertedIndex()
    index.add_document(0, "a.py", ["sliding", "window", "size"])
    index.add_document(1, "b.py", ["window", "sliding"])
    index.add_document(2, "c.py", ["to", "be", "or", "not", "to", "be"])
    index.add_document(3, "d.py", ["sliding", "big", "window"])
    return index


def test_phrase_positions_in_order():
    index = make_index()
    assert phrase_positions(index, ["sliding", "window"], 0) == [0]
    assert phrase_positions(index, ["sliding", "window"], 1) == []      # wrong order
    assert phrase_positions(index, ["sliding", "window"], 3) == []      # not adjacent


def test_phrase_can_repeat_in_a_document():
    assert phrase_positions(make_index(), ["to", "be"], 2) == [0, 4]


def test_three_word_phrases():
    index = make_index()
    assert phrase_positions(index, ["sliding", "window", "size"], 0) == [0]
    assert phrase_positions(index, ["sliding", "window", "big"], 0) == []


def test_search_phrase():
    index = make_index()
    assert search_phrase(index, "sliding window") == [0]
    assert search_phrase(index, "window sliding") == [1]


def test_single_word_phrase_is_is_a_normal_search():
    assert search_phrase(make_index(), "sliding") == [0, 1, 3]


def test_unknown_word_and_empty_query():
    index = make_index()
    assert search_phrase(index, "sliding zebra") == []
    assert search_phrase(index, "") == []


def test_more_occurances_rank_higher():
    index = InvertedIndex()
    index.add_document(0, "a.py", ["to", "be", "x1"])
    index.add_document(1, "b.py", ["to", "be", "or", "to", "be"])
    total, top = ranked_phrase_search(index, "to be")
    assert total == 2
    assert [doc_id for _, doc_id in top] == [1, 0]


def test_camel_case_name_match_phrases(tmp_path):
    (tmp_path / "a.py").write_text("def getUserName(): pass", encoding="utf-8")
    index = build_index(str(tmp_path))
    assert search_phrase(index, "user name") == [0]