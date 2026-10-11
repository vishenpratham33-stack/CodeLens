import pytest 

from codelens.crawler import crawl, is_inside

def make_tree(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')", encoding="utf-8")
    (tmp_path / "notes.md").write_text("# notes", encoding="utf-8")
    (tmp_path / "photo.png").write_bytes(b"\x89PNG\x00\x00")
    (tmp_path / "fake.py").write_bytes(b"abc\x00def")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "junk.js").write_text("x", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def run(): pass", encoding="utf-8")
    return tmp_path

def test_finds_only_good_files(tmp_path):
    make_tree(tmp_path)
    paths = [d.path for d in crawl(str(tmp_path))]
    assert paths == ["main.py", "notes.md", "src/app.py"]

def test_ids_are_sequesntial(tmp_path):
    make_tree(tmp_path)
    ids = [d.doc_id for d in crawl(str(tmp_path))]
    assert ids == [0, 1, 2]

def test_big_files_are_skipped(tmp_path, monkeypatch):
    (tmp_path / "big.txt").write_text("a" * 100, encoding="utf-8")
    monkeypatch.setattr("codelens.config.MAX_FILE_SIZE_BYTES", 10)
    assert list(crawl(str(tmp_path))) == []

def test_not_a_folder_raises(tmp_path):
    with pytest.raises(NotADirectoryError):
        list(crawl(str(tmp_path / "missing")))

def test_is_inside_blocks_escape(tmp_path):
    inner = tmp_path / "inner"
    inner.mkdir()
    assert is_inside(inner, inner / "a.txt")
    assert not is_inside(inner, tmp_path / "secret.txt")
    assert not is_inside(inner, inner / ".." / "secret.txt")
