import os

from codelens.crawler import crawl
from codelens.search import search_all
from codelens.storage import index_path
from codelens.updater import update_index


def write(folder, name, text):
    path = folder / name
    path.write_text(text, encoding="utf-8")
    return path


def test_first_run_builds_and_saves(tmp_path):
    write(tmp_path, "a.py", "def getUserName(): pass")
    index, report = update_index(str(tmp_path))
    assert report.mode == "built"
    assert report.added == 1
    assert index_path(str(tmp_path)).exists()


def test_second_run_loads_without_changes(tmp_path):
    write(tmp_path, "a.py", "alpha beta")
    update_index(str(tmp_path))
    index, report = update_index(str(tmp_path))
    assert report.mode == "loaded"
    assert search_all(index, "alpha") == [0]


def test_new_file_is_added(tmp_path):
    write(tmp_path, "a.py", "alpha beta")
    update_index(str(tmp_path))
    write(tmp_path, "b.py", "gamma delta")
    index, report = update_index(str(tmp_path))
    assert (report.mode, report.added, report.changed, report.removed) == ("updated", 1, 0, 0)
    assert len(search_all(index, "gamma")) == 1


def test_changed_file_is_read_again(tmp_path):
    path = write(tmp_path, "a.py", "alpha beta")
    update_index(str(tmp_path))
    path.write_text("omega sigma", encoding="utf-8")
    os.utime(path, (1_000_000, 1_000_000))  
    index, report = update_index(str(tmp_path))
    assert (report.added, report.changed, report.removed) == (0, 1, 0)
    assert search_all(index, "alpha") == []      
    assert len(search_all(index, "omega")) == 1


def test_deleted_file_is_forgotten(tmp_path):
    write(tmp_path, "a.py", "alpha beta")
    gone = write(tmp_path, "b.py", "gamma delta")
    update_index(str(tmp_path))
    gone.unlink()
    index, report = update_index(str(tmp_path))
    assert (report.added, report.changed, report.removed) == (0, 0, 1)
    assert search_all(index, "gamma") == []
    assert len(search_all(index, "alpha")) == 1


def test_rebuild_ignores_the_saved_index(tmp_path):
    write(tmp_path, "a.py", "alpha beta")
    update_index(str(tmp_path))
    _, report = update_index(str(tmp_path), rebuild=True)
    assert report.mode == "built"


def test_the_saved_index_is_never_indexed(tmp_path):
    write(tmp_path, "a.py", "alpha beta")
    update_index(str(tmp_path))
    paths = [doc.path for doc in crawl(str(tmp_path))]
    assert paths == ["a.py"]

    
def test_damaged_saved_index_is_rebuilt(tmp_path):
    write(tmp_path, "a.py", "alpha beta")
    update_index(str(tmp_path))
    index_path(str(tmp_path)).write_text("garbage", encoding="utf-8")
    index, report = update_index(str(tmp_path))
    assert report.mode == "built"
    assert len(search_all(index, "alpha")) == 1