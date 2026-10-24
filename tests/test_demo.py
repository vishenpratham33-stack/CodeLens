from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from codelens.__main__ import missing_folders
from codelens.api.server import create_app
from codelens.library import Library

SECRET = b"test-secret-test-secret-test-secret"
SAMPLES = Path(__file__).resolve().parent.parent / "sample_docs"


def login(client, name, password):
    return client.post("/api/login", json={"username": name, "password": password})


def test_demo_login_is_created_and_shown(tmp_path):
    client = TestClient(create_app(tmp_path / "data", secret=SECRET, demo_login="demo:CodeLens-demo-2026"))
    health = client.get("/api/health").json()
    assert health["demo"]["username"] == "demo"
    assert health["demo"]["password"] == "CodeLens-demo-2026"
    assert login(client, "demo", "CodeLens-demo-2026").status_code == 200


def test_starting_twice_with_the_same_demo_account_is_fine(tmp_path):
    for _ in range(2):
        client = TestClient(create_app(tmp_path / "data", secret=SECRET, demo_login="demo:CodeLens-demo-2026"))
        assert login(client, "demo", "CodeLens-demo-2026").status_code == 200


def test_no_demo_means_no_credentials_in_health(tmp_path):
    client = TestClient(create_app(tmp_path / "data", secret=SECRET, demo_login=""))
    assert "demo" not in client.get("/api/health").json()


def test_many_visitors_can_log_into_the_demo_account(tmp_path):
    client = TestClient(create_app(tmp_path / "data", secret=SECRET, demo_login="demo:CodeLens-demo-2026"))
    codes = [login(client, "demo", "CodeLens-demo-2026").status_code for _ in range(12)]
    assert set(codes) == {200}


def test_missing_folders_are_reported(tmp_path):
    assert missing_folders([str(tmp_path)]) == []
    assert missing_folders([r"C:\path\to\your\folder", str(tmp_path)]) == [r"C:\path\to\your\folder"]


def test_a_missing_folder_does_not_stop_the_others(tmp_path):
    real = tmp_path / "docs"
    real.mkdir()
    (real / "a.txt").write_text("alpha beta", encoding="utf-8")
    library = Library([real, tmp_path / "nope"], tmp_path / "store")
    library.sync()
    status = library.status()
    assert status["state"] == "ready" and status["files"] == 1
    assert status["missing"] == [str((tmp_path / "nope").resolve())]


def test_only_missing_folders_gives_a_clear_error(tmp_path):
    library = Library([tmp_path / "nope"], tmp_path / "store")
    library.sync()
    status = library.status()
    assert status["state"] == "error" and "None of the folders exists" in status["error"]


@pytest.mark.skipif(not SAMPLES.is_dir(), reason="sample_docs folder not present")
def test_the_suggested_demo_searches_find_what_they_promise(tmp_path):
    client = TestClient(create_app(tmp_path / "data", secret=SECRET, shared_folder=str(SAMPLES),
                                   demo_login="demo:CodeLens-demo-2026"))
    token = login(client, "demo", "CodeLens-demo-2026").json()["token"]
    headers = {"Authorization": "Bearer " + token}

    def names(query, **extra):
        reply = client.get("/api/search", params={"q": query, **extra}, headers=headers).json()
        return [r["path"].rsplit("/", 1)[-1] for r in reply["results"]], reply

    assert names("invoice")[0][0] == "invoice_march_2026.txt"
    assert names("sliding window", phrase="true")[0] == ["python_sliding_window.py"]
    assert "recipe_masala_chai.txt" in names("masala chai")[0]
    assert "budget_2026.xlsx" in names("budget rent")[0]            # inside an Excel file
    assert "travel_itinerary_goa.pdf" in names("goa beach")[0]      # inside a PDF
    assert "resume_sample.docx" in names("software developer")[0]   # inside a Word file
    found, reply = names("electricty")                              # a typo
    assert reply["corrections"] == [{"typed": "electricty", "used": "electricity"}]
    assert "electricity_bill_october.txt" in found
