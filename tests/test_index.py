import pytest

from codelens.index import InvertedIndex, build_index

def make_index():
    index = InvertedIndex()
    index.add_document(0, "a.py", ["cat", "dog", "cat"])
    index.add_document(1, "b.py", ["dog", "bird"])
    return index


def test_doc_ids_for_a_word():
    index = make_index()
    assert index.doc_ids("dog") == [0, 1]
    assert index.doc_ids("cat") == [0]
    assert index.doc_ids("bird") == [1]


def test_unknown_word_gives_empty_list():
    assert make_index().doc_ids("zebra") == []


def test_positions_are_remembered():
    index = make_index()
    assert index.positions("cat", 0) == [0, 2]
    assert index.positions("cat", 1) == []    


def test_counts():
    index = make_index()
    assert index.doc_count == 2
    assert index.vocabulary_size == 3
    assert index.doc_frequency("dog") == 2


def test_doc_ids_must_increase():
    index = make_index()
    with pytest.raises(ValueError):
        index.add_document(1, "c.py", ["x1"])


def test_build_index_from_folder(tmp_path):
    (tmp_path / "one.py").write_text("def getUserName(): pass", encoding="utf-8")
    (tmp_path / "two.md").write_text("the user name is here", encoding="utf-8")
    index = build_index(str(tmp_path))
    assert index.doc_count == 2
    assert index.doc_ids("user") ==[0, 1]
    assert index.doc_ids("get") == [0]