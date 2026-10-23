import pytest

from codelens.security.users import InvalidInput, UserExists, UserStore


def test_register_and_verify(tmp_path):
    store = UserStore(tmp_path / "users.json")
    assert store.register("  Alice_1 ", "a long password") == "alice_1"
    assert store.verify("alice_1", "a long password")
    assert store.verify("ALICE_1", "a long password")  
    assert not store.verify("alice_1", "wrong password!")


def test_unknown_user_is_refused():
    store = UserStore("does-not-matter.json")
    assert not store.verify("nobody", "whatever-password")


def test_rules_for_names_and_passwords(tmp_path):
    store = UserStore(tmp_path / "users.json")
    for bad_name in ["ab", "has space", "../etc", "x" * 21, "man-u"]:
        with pytest.raises(InvalidInput):
            store.register(bad_name, "a long password")
    with pytest.raises(InvalidInput):
        store.register("alice", "short")
    with pytest.raises(InvalidInput):
        store.register("alice", "x" * 129)


def test_duplicate_name(tmp_path):
    store = UserStore(tmp_path / "users.json")
    store.register("alice", "a long password")
    with pytest.raises(UserExists):
        store.register("Alice", "another password")


def test_accounts_survive_a_restart_and_hold_no_plain_password(tmp_path):
    path = tmp_path / "users.json"
    UserStore(path).register("alice", "my secret phrase")
    assert "my secret phrase" not in path.read_text(encoding="utf-8")
    assert UserStore(path).verify("alice", "my secret phrase")