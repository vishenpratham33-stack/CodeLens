import time

from codelens.crawler import is_cloud_only, list_files
from codelens.library import Library, default_roots
from codelens.search import search_all


def write(folder, name, text):
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def wait_until(condition, seconds=10):
    end = time.time() + seconds
    while time.time() < end:
        if condition():
            return True
        time.sleep(0.05)
    return False


def test_two_folders_are_searched_together(tmp_path):
    docs, desk = tmp_path / "docs", tmp_path / "desk"
    write(docs, "cv.txt", "curriculum vitae python developer")
    write(desk, "notes.txt", "shopping list and python tips")
    library = Library([docs, desk], tmp_path / "store")
    library.sync()
    hits = search_all(library.index, "python")
    paths = sorted(library.index.docs[d]["path"] for d in hits)
    assert sorted(p.rsplit("/", 1)[-1] for p in paths) == ["cv.txt", "notes.txt"]
    assert all(p.count("/") > 1 for p in paths)              # full paths, not relative


def test_status_after_the_first_pass(tmp_path):
    write(tmp_path / "docs", "a.txt", "alpha beta")
    library = Library([tmp_path / "docs"], tmp_path / "store")
    library.sync()
    status = library.status()
    assert status["state"] == "ready"
    assert status["files"] == 1 and status["pending"] == 0


def test_a_saved_index_is_used_at_the_next_start(tmp_path):
    write(tmp_path / "docs", "a.txt", "alpha beta")
    Library([tmp_path / "docs"], tmp_path / "store").sync()
    second = Library([tmp_path / "docs"], tmp_path / "store")
    second.sync()
    assert second.status()["files"] == 1
    assert len(search_all(second.index, "alpha")) == 1


def test_new_changed_and_deleted_files_are_noticed(tmp_path):
    folder = tmp_path / "docs"
    keep = write(folder, "keep.txt", "alpha beta")
    gone = write(folder, "gone.txt", "gamma delta")
    library = Library([folder], tmp_path / "store")
    library.sync()
    gone.unlink()
    write(folder, "new.txt", "omega sigma")
    import os
    keep.write_text("epsilon zeta", encoding="utf-8")
    os.utime(keep, (1_000_000, 1_000_000))
    library.sync()
    assert search_all(library.index, "gamma") == []
    assert search_all(library.index, "alpha") == []
    assert len(search_all(library.index, "omega")) == 1
    assert len(search_all(library.index, "epsilon")) == 1


def test_background_thread_indexes_and_refreshes(tmp_path):
    folder = tmp_path / "docs"
    write(folder, "a.txt", "alpha beta")
    library = Library([folder], tmp_path / "store", refresh_seconds=0.2)
    library.start()
    try:
        assert wait_until(lambda: library.status()["state"] == "ready")
        write(folder, "b.txt", "brand new words")
        assert wait_until(lambda: library.status()["files"] == 2)
    finally:
        library.stop()


def test_hidden_folders_are_skipped(tmp_path):
    write(tmp_path, "visible.txt", "hello world")
    write(tmp_path / ".secret", "hidden.txt", "hello world")
    assert [f.path for f in list_files(str(tmp_path))] == ["visible.txt"]


def test_cloud_only_files_are_recognised():
    class Fake:
        st_file_attributes = 0x400000          # OneDrive: not downloaded yet
    class Local:
        st_file_attributes = 0x20
    class NotWindows:
        pass
    assert is_cloud_only(Fake())
    assert not is_cloud_only(Local())
    assert not is_cloud_only(NotWindows())


def test_absolute_paths(tmp_path):
    write(tmp_path, "a.txt", "hello")
    [info] = list(list_files(str(tmp_path), absolute=True))
    assert info.path.endswith("/a.txt") and len(info.path) > len("a.txt")


def test_default_roots_returns_real_folders_without_overlap():
    roots = default_roots()
    assert all(r.is_dir() for r in roots)
    assert not any(a != b and a in b.parents for a in roots for b in roots)
