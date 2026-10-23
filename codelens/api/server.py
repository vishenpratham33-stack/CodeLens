"""Step 7 (Part B) of CodeLens: the web API, with accounts and safety rules.
Every route except register, login and health needs a login token.
Every user searches ONLY their own workspace folder.
"""
import os
import re
import secrets
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from codelens import config
from codelens.crawler import is_inside
from codelens.index import InvertedIndex
from codelens.search import (find_snippet, ranked_phrase_search, ranked_search)
from codelens.security.ratelimit import SlidingWindowLimiter
from codelens.security.tokens import create_token, verify_token
from codelens.security.users import InvalidInput, UserExists, UserStore
from codelens.tokenizer import tokenize
from codelens.trie import build_trie
from codelens.typo import correct_words
from codelens.updater import update_index


TOKEN_LIFETIME_SECONDS = 3600
REFRESH_SECONDS = 2.0        
FILE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")


class Credentials(BaseModel):
    username: str = Field(max_length=40)
    password: str = Field(max_length=128)


class FileUpload(BaseModel):
    name: str = Field(max_length=100)
    content: str


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
        os.chmod(path, 0o600)
    except OSError:
        pass
    return value


def create_app(data_dir, secret: Optional[bytes] = None,
               shared_folder: Optional[str] = None,
               web_dir: Optional[Path] = None,
               limits: Optional[dict] = None) -> FastAPI:
    data_dir = Path(data_dir)
    secret = secret or load_or_create_secret(data_dir)
    store = UserStore(data_dir / "users.json")
    index_lock = threading.Lock()
    cache: Dict[str, Tuple[InvertedIndex, float]] = {}

    cfg = {"login": (10, 60), "login_user": (5, 60), "register": (5, 60), "search": (60, 60)}
    cfg.update(limits or {})
    login_limiter = SlidingWindowLimiter(*cfg["login"])
    login_user_limiter = SlidingWindowLimiter(*cfg["login_user"])
    register_limiter = SlidingWindowLimiter(*cfg["register"])
    search_limiter = SlidingWindowLimiter(*cfg["search"])


    app = FastAPI(title="CodeLens", version="1.0")



    def too_many(limiter: SlidingWindowLimiter, key: str) -> None:
        if not limiter.allow(key):
                wait = int(limiter.retry_after(key)) + 1
                raise HTTPException(429, "Too many requests. Try again later.", headers={"Retry-After": str(wait)})

        
    def client_ip(request: Request) -> str:
        return request.client.host if request.client else "unknown"

    
    def workspace_for(username: str) -> Path:
        if shared_folder:
            return Path(shared_folder)
        folder = data_dir / "workspaces" / username     
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


    def current_user(authorization: Optional[str] = Header(default=None)) -> str:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Please log in.")
        username = verify_token(authorization[7:], secret)
        if username is None or not store.exists(username):
            raise HTTPException(401, "Please log in again.")
        return username

    
    @app.middleware("http")
    async def safety_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if not request.url.path.startswith(("/docs", "/openapi")): response.headers["Content-Security-Policy"] = ("default-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
        return response

    
    @app.get("/api/health")
    def health():
        return {"status": "ok"}
    
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
            raise HTTPException(401, "Wrong username or password.")
        name = body.username.strip().lower()
        token = create_token(name, secret, TOKEN_LIFETIME_SECONDS)
        return {"token": token, "expires_in": TOKEN_LIFETIME_SECONDS, "username": name}

    @app.get("/api/me")
    def me(user: str = Depends(current_user)):
        return {"username": user, "shared_folder": bool(shared_folder)}
   
    @app.get("/api/files")
    def list_files_route(user: str = Depends(current_user)):
        folder = workspace_for(user)
        names = sorted(p.name for p in folder.iterdir()
                        if p.is_file() and p.suffix.lower() in config.ALLOWED_EXTENSIONS)
        return {"files": names}

    @app.post("/api/files", status_code=201)
    def upload(body: FileUpload, user: str = Depends(current_user)):
        if shared_folder:
            raise HTTPException(403, "Uploads are off: this server searches a shared folder.")
        suffix = Path(body.name).suffix.lower()
        if not FILE_NAME_RE.match(body.name) or suffix not in config.ALLOWED_EXTENSIONS:
            raise HTTPException(400, "Bad file name or file type.")
        data = body.content.encode("utf-8")
        if len(data) > config.MAX_FILE_SIZE_BYTES:
            raise HTTPException(413, "File too big.")
        folder = workspace_for(user)
        target = folder / body.name
        if not is_inside(folder, target):
            raise HTTPException(400, "Bad file name.")
        target.write_bytes(data)
        mark_stale(folder)
        return {"saved": body.name, "bytes": len(data)}
    
    @app.delete("/api/files/{name}")
    def delete(name: str, user: str = Depends(current_user)):
        if shared_folder:
            raise HTTPException(403, "Deleting is off: this server searches a shared folder.")
        folder = workspace_for(user)
        target = folder / name
        if not FILE_NAME_RE.match(name) or not is_inside(folder, target) or not target.is_file():
            raise HTTPException(404, "No such file.")
        target.unlink()
        mark_stale(folder)
        return {"deleted": name}
   
    @app.post("/api/index")
    def reindex(user: str = Depends(current_user)):
        folder = workspace_for(user)
        with index_lock:
            key = str(folder.resolve())
            index, report = update_index(key, current=cache[key][0] if key in cache else None)
            cache[key] = (index, time.monotonic())
        return {"mode": report.mode, "added": report.added, "changed": report.changed, "removed": report.removed, "files": index.doc_count, "words": index.vocabulary_size}
    
    @app.get("/api/search")
    def search(q: str = Query(min_length=1, max_length=200),
            limit: int = Query(10, ge=1, le=50),
            phrase: bool = False,
            any_word: bool = Query(False, alias="any"),
            user: str = Depends(current_user)):
        too_many(search_limiter, user)
        folder = workspace_for(user)
        started = time.perf_counter()
        with index_lock:                      
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
        with index_lock:
            index = get_index(workspace_for(user))
            words = build_trie(index).suggest(prefix.lower(), limit)
            suggestions = [{"word": w, "files": index.doc_frequency(w)} for w in words]
        return {"suggestions": suggestions}

    
    if web_dir is not None and Path(web_dir).is_dir():
        app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")
        @app.get("/", include_in_schema=False)
        def home():
            return FileResponse(Path(web_dir) / "index.html")
    else:
        @app.get("/", include_in_schema=False)
        def home_without_page():
            return JSONResponse({"name": "CodeLens API", "docs": "/docs"})
        
    return app