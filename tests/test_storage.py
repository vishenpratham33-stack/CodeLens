import json 

from codelens.index import InvertedIndex
from codelens.storage import index_path, load_index, save_index


def make_index():
    index = InvertedIndex()
    index.add_document(0, "a.py", ["cat", "dog", "cat"], size=10, modified=1.5)
    index.add_document(1, "b.py", ["dog", "bird"], size=20, modified=2.5)
    return index


def test_dict_round_trip_keeps_numbers_as_numbers():
    original = make_index()
    copy = InvertedIndex.from_dict(json.loads(json.dumps(original.to_dict())))
    assert copy.postings == original.postings
    assert copy.docs == original.docs
    assert copy.doc_ids("dog") == [0, 1]
    assert copy.next_doc_id == 2


def test_save_and_load(tmp_path):
    save_index(make_index(), str(tmp_path))
    loaded = load_index(str(tmp_path))
    assert loaded is not None
    assert loaded.positions("cat", 0) == [0, 2]
    assert loaded.docs[1]["path"] == "b.py"


def test_no_temporary_file_is_left_behind(tmp_path):
    save_index(make_index(), str(tmp_path))
    names = [p.name for p in index_path(str(tmp_path)).parent.iterdir()]
    assert names == ["index.json"]


def test_missing_file_gives_none(tmp_path):
    assert load_index(str(tmp_path)) is None


def test_damaged_file_gives_none(tmp_path):
    path = index_path(str(tmp_path))
    path.parent.mkdir(parents=True)
    path.write_text("{ this is not json", encoding="utf-8")
    assert load_index(str(tmp_path)) is None


def test_wrong_version_gives_none(tmp_path):
    path = index_path(str(tmp_path))
    path.parent.mkdir(parents=True)
    path.write_text('{"version": 999, "docs": {}, "postings: {}}', encoding="utf-8")
    assert load_index(str(tmp_path)) is None


def test_remove_documents():
    index = make_index()
    index.remove_documents({0})
    assert index.doc_ids("dog") == [1]
    assert "cat" not in index.postings
    assert index.doc_ids("dog") == [1]
    assert 0 not in index.docs


def test_new_id_keeps_increasing_after_a_removal():
    index = make_index()
    index.remove_documents({0})
    index.add_document(index.next_doc_id, "c.py", ["dog"])
    assert index.doc_ids("dog") == [1, 2]