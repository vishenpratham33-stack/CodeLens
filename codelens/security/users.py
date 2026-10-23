import json
import os
import re
import threading
from pathlib import Path
from typing import Dict, Optional


from codelens.security.passwords import hash_password, verify_password


USERNAME_RE = re.compile(r"^[a-z0-9_]{3,20}$")
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


class InvalidInput(ValueError):
    pass


class UserExists(ValueError):
    pass


_dummy_hash: Optional[str] = None


def _dummy() -> str:
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = hash_password("not-a-real-password")
    return _dummy_hash


class UserStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        self._users: Dict[str, dict] = self._load()


    def _load(self) -> Dict[str, dict]:
        try:
            with open(self.path, "r", encoding="utf-8") as handle: data = json.load(handle)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

        
    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_name(self.path.name + ".tmp")
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(self._users, handle)
        os.replace(temp, self.path)


    def exists(self, username: str) -> bool:
        return username in self._users

    
    def register(self, username: str, password: str) -> str:
        username = username.strip().lower()
        if not USERNAME_RE.match(username):
            raise InvalidInput("Username: 3 to 20 letters, digits or underscores.")
        if not (MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH):
            raise InvalidInput(
                f"Password: {MIN_PASSWORD_LENGTH} to {MAX_PASSWORD_LENGTH} characters.")
        with self._lock:
            if username in self._users:
                raise UserExists("That username is taken.")
            self._users[username] = {"hash": hash_password(password)}
            self._save()
        return username

    
    def verify(self, username: str, password: str) -> bool:
        username = username.strip().lower()
        record = self._users.get(username)
        stored = record["hash"] if record else _dummy()
        matches = verify_password(password, stored)
        return matches and record is not None