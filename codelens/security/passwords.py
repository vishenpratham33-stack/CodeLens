import hashlib
import hmac
import os
SCRYPT_N = 2 ** 14 
SCRYPT_R = 8
SCRYPT_P = 1
SALT_BYTES = 16
KEY_BYTES = 32


def hash_password(password: str, n: int = SCRYPT_N) -> str:
    salt = os.urandom(SALT_BYTES)        # a NEW random salt for every password
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt,
                            n=n, r=SCRYPT_R, p=SCRYPT_P, dklen=KEY_BYTES)
    return f"scrypt${n}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n_text, salt_hex, digest_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        n = int(n_text)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt,
                                n=n, r=SCRYPT_R, p=SCRYPT_P, dklen=len(expected))
    except (ValueError, TypeError):
        return False

    return hmac.compare_digest(actual, expected)