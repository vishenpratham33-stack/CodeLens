from codelens.security.tokens import create_token, verify_token


SECRET = b"a-test-secret-of-some-length-1234"


def test_valid_token_returns_the_user():
    token = create_token("alice", SECRET, ttl_seconds=60, now=1000)
    assert verify_token(token, SECRET, now=1030) == "alice"


def test_expired_token_is_refused():
    token = create_token("alice", SECRET, ttl_seconds=60, now=1000)
    assert verify_token(token, SECRET, now=1061) is None


def test_wrong_secret_is_refused():
    token = create_token("alice", SECRET, now=1000)
    assert verify_token(token, b"another-secret-xxxxxxxxxxxx", now=1001) is None


def test_changing_the_payload_breaks_the_signature():
    token = create_token("alice", SECRET, now=1000)
    other = create_token("mallory", SECRET, now=1000)
    forged = other.split(".")[0] + "." + token.split(".")[1]
    assert verify_token(forged, SECRET, now=1001) is None

    
def test_garbage_never_crashes():
    for bad in ["", "abc", "a.b", "...", "not a token at all", "a.b.c"]:
        assert verify_token(bad, SECRET) is None