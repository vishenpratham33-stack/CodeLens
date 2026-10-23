import pytest
from fastapi.testclient import TestClient

from codelens.api.server import create_app

SECRET = b"test-secret-test-secret-test-secret"


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path / "data", secret=SECRET)
    return TestClient(app)


def sign_up(client, name="alice", password="a long password"):
    assert client.post("/api/register", json={"username": name, "password": password}).status_code == 201
    reply = client.post("/api/login", json={"username": name, "password": password})
    assert reply.status_code == 200
    return {"Authorization": "Bearer " + reply.json()["token"]}


def upload(client, headers, name, content):
    return client.post("/api/files", json={"name": name, "content": content}, headers=headers)


def test_health_needs_no_login(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_register_login_and_me(client):
    headers = sign_up(client)
    assert client.get("/api/me", headers=headers).json()["username"] == "alice"


def test_duplicate_and_weak_registration(client):
    sign_up(client)
    assert client.post("/api/register", json={"username": "ALICE", "password": "another password"}).status_code == 409
    assert client.post("/api/register", json={"username": "bob", "password": "short"}).status_code == 400
    assert client.post("/api/register", json={"username": "../x", "password": "a long password"}).status_code == 400

    
def test_wrong_password_and_unknown_user_look_the_same(client):
    sign_up(client)
    wrong = client.post("/api/login", json={"username": "alice", "password": "wrong password"})
    unknown = client.post("/api/login", json={"username": "nobody", "password": "wrong password"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_routes_need_a_token(client):
    for method, url in [("get", "/api/me"), ("get", "/api/files"), ("get", "/api/search?q=x"), ("post", "/api/index")]:
        assert getattr(client, method)(url).status_code == 401
    bad = {"Authorization": "Bearer not.a.token"}
    assert client.get("/api/me", headers=bad).status_code == 401


def test_upload_index_and_search(client):
    headers = sign_up(client)
    assert upload(client, headers, "notes.py", "def getUserName():\n      return 'x'\n").status_code == 201
    reply = client.get("/api/search?q=user name", headers=headers).json()
    assert reply["total"] == 1
    assert reply["results"][0]["path"] == "notes.py"
    assert reply["results"][0]["line"] == 1


def test_typo_correction_in_the_api(client):
    headers = sign_up(client)
    upload(client, headers, "a.py", "def inverted_index(): pass")
    reply = client.get("/api/search?q=invertd", headers=headers).json()
    assert reply["corrections"] == [{"typed": "invertd", "used": "inverted"}]
    assert reply["total"] == 1


def test_phrase_and_suggest(client):
    headers = sign_up(client)
    upload(client, headers, "a.txt", "sliding window technique")
    upload(client, headers, "b.txt", "window sliding trick")
    phrase = client.get("/api/search?q=sliding window&phrase=true", headers=headers).json()
    assert [r["path"] for r in phrase["results"]] == ["a.txt"]
    words = client.get("/api/suggest?prefix=sl", headers=headers).json()["suggestions"]
    assert words[0]["word"] == "sliding"


def test_users_cannot_see_each_others_files(client):
    alice = sign_up(client, "alice")
    bob = sign_up(client, "bob", "another long one")
    upload(client, alice, "secret.txt", "treasure map location")
    assert client.get("/api/search?q=treasure", headers=bob).json()["total"] == 0
    assert client.get("/api/files", headers=bob).json() == {"files": []}
    assert client.get("/api/search?q=treasure", headers=alice).json()["total"] == 1


def test_bad_upload_names_are_refused(client):
    headers = sign_up(client)
    for name in ["../escape.txt", "..\\escape.txt", "sub/dir.txt", ".hidden.txt", "run.exe", "noextension", "a" * 200 + ".txt", "C:evil.txt"]:
        assert upload(client, headers, name, "x").status_code in (400, 422), name


def test_big_upload_is_refused(client):
    headers = sign_up(client)
    assert upload(client, headers, "big.txt", "a" * 1_000_001).status_code == 413


def test_delete(client):
    headers = sign_up(client)
    upload(client, headers, "a.txt", "hello world")
    assert client.delete("/api/files/a.txt", headers=headers).status_code == 200
    assert client.delete("/api/files/a.txt", headers=headers).status_code == 404
    assert client.delete("/api/files/..%2Fusers.json", headers=headers).status_code in (404, 422)


def test_search_input_limits(client):
    headers = sign_up(client)
    assert client.get("/api/search?q=", headers=headers).status_code == 422
    assert client.get("/api/search?q=" + "a" * 201, headers=headers).status_code == 422
    assert client.get("/api/search?q=x&limit=500", headers=headers).status_code == 422


def test_login_is_rate_limited(tmp_path):
    app = create_app(tmp_path / "data", secret=SECRET, limits={"login_user": (3, 60)})
    client = TestClient(app)
    client.post("/api/register", json={"username": "alice", "password": "a long password"})
    codes = [client.post("/api/login", json={"username": "alice", "password": "bad bad bad"}).status_code
            for _ in range(5)]
    assert codes == [401, 401, 401, 429, 429]
    blocked = client.post("/api/login", json={"username": "alice", "password": "a long password"})
    assert blocked.status_code == 429 and "Retry-After" in blocked.headers


def test_search_is_rate_limited(tmp_path):
    app = create_app(tmp_path / "data", secret=SECRET, limits={"search": (2, 60)})
    client = TestClient(app)
    headers = sign_up(client)
    codes = [client.get("/api/search?q=x", headers=headers).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_safety_headers_are_present(client):
    headers = client.get("/api/health").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in headers["content-security-policy"]



def test_shared_folder_mode(tmp_path):
    shared = tmp_path / "docs"
    shared.mkdir()
    (shared / "report.txt").write_text("quarterly invoice summary", encoding="utf-8")
    client = TestClient(create_app(tmp_path / "data", secret=SECRET, shared_folder=str(shared)))
    headers = sign_up(client)
    assert client.get("/api/search?q=invoice", headers=headers).json()["total"] == 1
    assert upload(client, headers, "x.txt", "no").status_code == 403
    assert client.delete("/api/files/report.txt", headers=headers).status_code == 403


def test_new_files_show_up_in_later_searches(client):
    headers = sign_up(client)
    upload(client, headers, "a.txt", "alpha beta")
    assert client.get("/api/search?q=gamma", headers=headers).json()["total"] == 0
    upload(client, headers, "b.txt", "gamma delta") 
    assert client.get("/api/search?q=gamma", headers=headers).json()["total"] == 1
    client.delete("/api/files/b.txt", headers=headers)
    assert client.get("/api/search?q=gamma", headers=headers).json()["total"] == 0