import base64
import hashlib
import hmac
import json
import time
from typing import Optional


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(payload: str, secret: bytes) -> str:
    return hmac.new(secret, payload.encode("ascii"), hashlib.sha256).hexdigest()


def create_token(username: str, secret: bytes, ttl_seconds: int = 3600, now: Optional[float] = None) -> str:
    now = time.time() if now is None else now
    body = json.dumps({"sub": username, "exp": int(now + ttl_seconds)}, separators=(",", ":")).encode("utf-8")
    payload = _b64encode(body)
    return payload + "." + _sign(payload, secret)


def verify_token(token: str, secret: bytes, now: Optional[float] = None) -> Optional[str]:
    now = time.time() if now is None else now
    try:
        payload, signature = token.split(".")
        if not hmac.compare_digest(signature, _sign(payload, secret)):
            return None
        data = json.loads(_b64decode(payload))
        if int(data["exp"]) < now:
            return None
        return str(data["sub"])
    except (ValueError, KeyError, TypeError):
        return None