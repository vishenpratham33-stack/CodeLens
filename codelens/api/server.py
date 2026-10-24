"""Step 7 (Part B) of CodeLens: the web API, with accounts and safety rules.

Every route except register, login and health needs a login token.
Every user searches ONLY their own workspace folder.
"""

import base64
import binascii
import os
import re
import secrets
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from codelens import config
from codelens.crawler import is_inside
from codelens.index import InvertedIndex
from codelens.library import Library
from codelens.search import (find_snippet, ranked_phrase_search,
                             ranked_search, snippet_in_file)
from codelens.security.ratelimit import SlidingWindowLimiter
from codelens.security.tokens import create_token, verify_token
from codelens.security.users import InvalidInput, UserExists, UserStore
from codelens.tokenizer import tokenize
from codelens.trie import build_trie
from codelens.typo import correct_words
from codelens.updater import update_index

bearer_scheme = HTTPBearer(auto_error=False)   # makes the Authorize button appear on /docs
TOKEN_LIFETIME_SECONDS = 3600
REFRESH_SECONDS = 2.0        # how often a search looks for changed files
FILE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
UNSAFE_NAME_CHARS = re.compile(r"[^A-Za-z0-9_.-]+")
LIBRARY_TOKEN_SECONDS = 7 * 24 * 3600     # "My files" mode: stay logged in for a week
MAX_UPLOAD_DOCUMENT_BYTES = 10_000_000


class Credentials(BaseModel):
    username: str = Field(max_length=40)
    password: str = Field(max_length=128)


class FileUpload(BaseModel):
    name: str = Field(max_length=100)
    content: str = ""                              # text files
    content_base64: Optional[str] = None           # any file (PDF, Word, Excel, text)


class OpenRequest(BaseModel):
    path: str = Field(max_length=1000)


def clean_upload_name(name: str) -> Optional[str]:
    """A safe file name, or None if the name looks like an attack.

    Path tricks are refused. Harmless oddities (spaces, brackets) are replaced by "_".
    """
    if any(c in name for c in "/\\:") or ".." in name or name.startswith("."):
        return None
    cleaned = UNSAFE_NAME_CHARS.sub("_", name).lstrip("._-")
    return cleaned if FILE_NAME_RE.match(cleaned) else None


def open_with_default_app(path: str) -> None:
    """Open a file the way a double-click would (only ever used on this computer)."""
    if sys.platform.startswith("win"):
        os.startfile(path)                       # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def is_local_request(request: Request) -> bool:
    """True only for a request made from THIS computer, straight to the server.

    A request that came through a tunnel or proxy (Tailscale, a reverse proxy)
    also shows up as 127.0.0.1, so we check the Host header and the forwarding
    headers too.
    """
    ip = request.client.host if request.client else ""
    host = (request.headers.get("host") or "").rsplit(":", 1)[0].strip("[]").lower()
    forwarded = any(h in request.headers for h in
                    ("x-forwarded-for", "forwarded", "x-real-ip", "tailscale-user-login"))
    return ip in ("127.0.0.1", "::1") and host in ("127.0.0.1", "localhost", "::1") and not forwarded


def load_or_create_secret(data_dir: Path) -> bytes:
    """The signing secret: from the environment, or a random one kept in a file."""
    from_env = os.environ.get("CODELENS_SECRET")
    if from_env:
        return from_env.encode("utf-8")
    path = data_dir / "secret.key"
    if path.exists():
        return path.read_bytes()
    data_dir.mkdir(parents=True, exist_ok=True)
    value = secrets.token_bytes(32)
    path.write_bytes(value)
    try:
        os.chmod(path, 0o600)            # only the owner may read it (Linux, Mac)
    except OSError:
        pass
    return value


def create_app(data_dir, secret: Optional[bytes] = None,
               shared_folder: Optional[str] = None,
               web_dir: Optional[Path] = None,
               limits: Optional[dict] = None,
               library: Optional[Library] = None,
               file_opener: Callable[[str], None] = open_with_default_app,
               demo_login: Optional[str] = None) -> FastAPI:
    data_dir = Path(data_dir)
    secret = secret or load_or_create_secret(data_dir)
    if library is None and shared_folder:
        # an existing folder searched for every user: the same engine as "My files"
        library = Library([shared_folder], data_dir / "library")
        library.sync()
    token_seconds = LIBRARY_TOKEN_SECONDS if library else TOKEN_LIFETIME_SECONDS
    store = UserStore(data_dir / "users.json")
    index_lock = threading.Lock()
    cache: Dict[str, Tuple[InvertedIndex, float]] = {}   # folder -> (index, when it was checked)

    # A public demo: one shared account, shown on the login page ("name:password").
    demo_login = demo_login if demo_login is not None else os.environ.get("CODELENS_DEMO_LOGIN", "")
    demo = None
    if ":" in demo_login:
        demo_name, demo_password = demo_login.split(":", 1)
        try:
            demo_name = store.register(demo_name, demo_password)
        except UserExists:
            demo_name = demo_name.strip().lower()
        demo = {"username": demo_name, "password": demo_password,
                "try": ["invoice", "sliding window", "masala chai", "budget rent", "goa beach", "electricty"]}

    cfg = {"login": (10, 60), "login_user": (5, 60), "register": (5, 60), "search": (60, 60)}
    if demo:                                  # many visitors share one account: allow more logins
        cfg.update({"login": (120, 60), "login_user": (60, 60)})
    cfg.update(limits or {})
    login_limiter = SlidingWindowLimiter(*cfg["login"])
    login_user_limiter = SlidingWindowLimiter(*cfg["login_user"])
    register_limiter = SlidingWindowLimiter(*cfg["register"])
    search_limiter = SlidingWindowLimiter(*cfg["search"])

    app = FastAPI(title="CodeLens", version="1.0")

    # ---------- helpers ----------
    def too_many(limiter: SlidingWindowLimiter, key: str) -> None:
        if not limiter.allow(key):
            wait = int(limiter.retry_after(key)) + 1
            raise HTTPException(429, "Too many requests. Try again later.",
                                headers={"Retry-After": str(wait)})

    def client_ip(request: Request) -> str:
        return request.client.host if request.client else "unknown"

    def workspace_for(username: str) -> Path:
        folder = data_dir / "workspaces" / username     # username was validated
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def get_index(folder: Path) -> InvertedIndex:
        """The index of a folder, kept in memory. Call only while holding index_lock."""
        key = str(folder.resolve())
        entry = cache.get(key)
        if entry is None or time.monotonic() - entry[1] > REFRESH_SECONDS:
            index, _ = update_index(key, current=entry[0] if entry else None)
            cache[key] = (index, time.monotonic())
            return index
        return entry[0]

    def mark_stale(folder: Path) -> None:
        """Something changed in this folder: check it again on the next search."""
        key = str(folder.resolve())
        with index_lock:
            if key in cache:
                cache[key] = (cache[key][0], 0.0)

    def current_user(
            credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> str:
        if credentials is None:
            raise HTTPException(401, "Please log in.")
        username = verify_token(credentials.credentials, secret)
        if username is None or not store.exists(username):
            raise HTTPException(401, "Please log in again.")
        return username

    # ---------- safety headers on every answer ----------
    @app.middleware("http")
    async def safety_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if not request.url.path.startswith(("/docs", "/openapi")):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
        return response

    # ---------- accounts ----------
    @app.get("/api/health")
    def health():
        return {"status": "ok", **({"demo": demo} if demo else {})}

    @app.post("/api/register", status_code=201)
    def register(body: Credentials, request: Request):
        too_many(register_limiter, client_ip(request))
        try:
            name = store.register(body.username, body.password)
        except InvalidInput as error:
            raise HTTPException(400, str(error))
        except UserExists as error:
            raise HTTPException(409, str(error))
        return {"username": name}

    @app.post("/api/login")
    def login(body: Credentials, request: Request):
        too_many(login_limiter, client_ip(request))
        too_many(login_user_limiter, body.username.strip().lower())
        if not store.verify(body.username, body.password):
            # the SAME answer for a wrong name and a wrong password
            raise HTTPException(401, "Wrong username or password.")
        name = body.username.strip().lower()
        token = create_token(name, secret, token_seconds)
        return {"token": token, "expires_in": token_seconds, "username": name}

    @app.get("/api/me")
    def me(request: Request, user: str = Depends(current_user)):
        return {"username": user, "mode": "library" if library else "workspace",
                "shared_folder": bool(library),            # kept for older pages
                "can_open": bool(library) and is_local_request(request)}

    # ---------- files of the user ----------
    @app.get("/api/files")
    def list_files_route(user: str = Depends(current_user)):
        folder = workspace_for(user)
        if library:
            return {"files": []}
        names = sorted(p.name for p in folder.iterdir()
                       if p.is_file() and (p.suffix.lower() in config.ALLOWED_EXTENSIONS
                                           or p.suffix.lower() in config.DOCUMENT_EXTENSIONS))
        return {"files": names}

    @app.post("/api/files", status_code=201)
    def upload(body: FileUpload, user: str = Depends(current_user)):
        if library:
            raise HTTPException(403, "Uploads are off: this server finds the files by itself.")
        name = clean_upload_name(body.name)
        suffix = Path(name).suffix.lower() if name else ""
        is_document = suffix in config.DOCUMENT_EXTENSIONS
        if not name or (suffix not in config.ALLOWED_EXTENSIONS and not is_document):
            raise HTTPException(400, "Bad file name or file type.")
        if body.content_base64 is not None:
            try:
                data = base64.b64decode(body.content_base64, validate=True)
            except (binascii.Error, ValueError):
                raise HTTPException(400, "The file data is not valid base64.")
        else:
            data = body.content.encode("utf-8")
        limit = MAX_UPLOAD_DOCUMENT_BYTES if is_document else config.MAX_FILE_SIZE_BYTES
        if len(data) > limit:
            raise HTTPException(413, "File too big.")
        folder = workspace_for(user)
        target = folder / name
        if not is_inside(folder, target):
            raise HTTPException(400, "Bad file name.")
        target.write_bytes(data)
        mark_stale(folder)
        return {"saved": name, "bytes": len(data)}

    @app.delete("/api/files/{name}")
    def delete(name: str, user: str = Depends(current_user)):
        if library:
            raise HTTPException(403, "Deleting is off: this server finds the files by itself.")
        folder = workspace_for(user)
        target = folder / name
        if not FILE_NAME_RE.match(name) or not is_inside(folder, target) or not target.is_file():
            raise HTTPException(404, "No such file.")
        target.unlink()
        mark_stale(folder)
        return {"deleted": name}

    # ---------- the engine ----------
    trie_cache: Dict[str, object] = {"key": None, "trie": None}

    def acquire_index(user: str):
        """(lock, index, folder). In My files mode the Library owns the index."""
        if library:
            if library.index is None:
                raise HTTPException(503, "CodeLens is still starting up. Try again in a moment.")
            return library.lock, library.index, None
        folder = workspace_for(user)
        return index_lock, None, folder

    @app.post("/api/index")
    def reindex(user: str = Depends(current_user)):
        if library:
            library.refresh_now()
            return {"mode": "library", **library.status()}
        folder = workspace_for(user)
        with index_lock:
            key = str(folder.resolve())
            index, report = update_index(key, current=cache[key][0] if key in cache else None)
            cache[key] = (index, time.monotonic())
        return {"mode": report.mode, "added": report.added, "changed": report.changed,
                "removed": report.removed, "files": index.doc_count,
                "words": index.vocabulary_size}

    @app.get("/api/library")
    def library_status(user: str = Depends(current_user)):
        if not library:
            raise HTTPException(404, "This server is not in My files mode.")
        return library.status()

    @app.get("/api/search")
    def search(q: str = Query(min_length=1, max_length=200),
               limit: int = Query(10, ge=1, le=50),
               phrase: bool = False,
               any_word: bool = Query(False, alias="any"),
               user: str = Depends(current_user)):
        too_many(search_limiter, user)
        started = time.perf_counter()
        lock, index, folder = acquire_index(user)
        with lock:                            # one search at a time: the index may be updating
            if index is None:
                index = get_index(folder)
            fixed, changes = correct_words(index, tokenize(q))
            text = " ".join(fixed)
            if phrase:
                total, best = ranked_phrase_search(index, text, limit)
            else:
                total, best = ranked_search(index, text, limit, any_word)
            words = list(dict.fromkeys(fixed))
            results = []
            for score, doc_id in best:
                path = index.docs[doc_id]["path"]
                if library:
                    snippet = snippet_in_file(Path(path), words)
                else:
                    snippet = find_snippet(str(folder), path, words)
                results.append({
                    "path": path,
                    "score": round(score, 2),
                    "line": snippet[0] if snippet else None,
                    "snippet": snippet[1] if snippet else None,
                })
        return {
            "query": q,
            "words": words,
            "corrections": [{"typed": a, "used": b} for a, b in changes],
            "total": total,
            "results": results,
            "ms": round((time.perf_counter() - started) * 1000, 2),
        }

    @app.get("/api/suggest")
    def suggest(prefix: str = Query(min_length=1, max_length=40),
                limit: int = Query(5, ge=1, le=20),
                user: str = Depends(current_user)):
        too_many(search_limiter, user)
        lock, index, folder = acquire_index(user)
        with lock:
            if index is None:
                index = get_index(folder)
            key = (id(index), index.doc_count, index.vocabulary_size)
            if trie_cache["key"] != key:               # build the trie only when the index changed
                trie_cache["key"], trie_cache["trie"] = key, build_trie(index)
            words = trie_cache["trie"].suggest(prefix.lower(), limit)
            suggestions = [{"word": w, "files": index.doc_frequency(w)} for w in words]
        return {"suggestions": suggestions}

    # ---------- My files mode: open and download ----------
    def indexed_path_or_404(path: str) -> Path:
        """Only files that are in the index can be opened or downloaded, nothing else."""
        if not library or not library.contains(path):
            raise HTTPException(404, "No such file.")
        full = Path(path)
        if not full.is_file() or not any(is_inside(root, full) for root in library.roots):
            raise HTTPException(404, "No such file.")
        return full

    @app.post("/api/open")
    def open_file(body: OpenRequest, request: Request, user: str = Depends(current_user)):
        if not is_local_request(request):
            raise HTTPException(403, "Files can be opened only on the computer where CodeLens runs.")
        full = indexed_path_or_404(body.path)
        file_opener(str(full))
        return {"opened": full.name}

    @app.get("/api/download")
    def download(path: str = Query(max_length=1000), user: str = Depends(current_user)):
        too_many(search_limiter, user)
        full = indexed_path_or_404(path)
        return FileResponse(full, filename=full.name)

    # ---------- the web page (Section 8) ----------
    if web_dir is not None and Path(web_dir).is_dir():
        app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")

        @app.get("/", include_in_schema=False)
        def home():
            return FileResponse(Path(web_dir) / "index.html")

        @app.get("/sw.js", include_in_schema=False)
        def service_worker():
            # served from the root, so it can control the whole site
            return FileResponse(Path(web_dir) / "sw.js", media_type="application/javascript",
                                headers={"Cache-Control": "no-cache"})
    else:
        @app.get("/", include_in_schema=False)
        def home_without_page():
            return JSONResponse({"name": "CodeLens API", "docs": "/docs"})

    return app
