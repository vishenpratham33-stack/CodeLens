from codelens.index import InvertedIndex
from codelens.search import find_snippet, ranked_search


def make_index():
    index = InvertedIndex()
    index.add_document(0, "a.py", ["the", "heap", "sort", "the"])
    index.add_document(1, "b.py", ["heap", "heap", "heap", "the"])
    index.add_document(2, "c.py", ["the", "sort", "sort"])
    return index


def test_best__match_comes_first():
    total, top = ranked_search(make_index(), "heap")
    assert total == 2
    assert [doc_id for _, doc_id in top] == [1, 0]


def test_limit_k_is_respected():
    total, top = ranked_search(make_index(), "the", k=2)
    assert total == 3
    assert len(top) == 2


def test_any_mode():
    total, top = ranked_search(make_index(), "heap sort", match_any=True)
    assert total == 3


def test_no_match():
    assert ranked_search(make_index(), "zebra") == (0, [])


def test_snippet_prefers_the_line_with_most_words(tmp_path):
    (tmp_path / "f.py").write_text("import heap\n\nnothing here\nheap sort together\n", encoding="utf-8")
    assert find_snippet(str(tmp_path), "f.py", ["heap", "sort"]) == (4, "heap sort together")


def test_snippet_none_when_no_word(tmp_path):
    (tmp_path / "f.py").write_text("hello world\n", encoding="utf-8")
    assert find_snippet(str(tmp_path), "f.py", ["zebra"]) is None