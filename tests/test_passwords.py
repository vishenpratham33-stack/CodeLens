from codelens.security.passwords import hash_password, verify_password


def test_correct_password_is_accepted():
    stored = hash_password("correct horse battery")
    assert verify_password("correct horse battery", stored)


def test_wrong_password_is_refused():
    stored = hash_password("correct horse battery")
    assert not verify_password("correct horse batterz", stored)
    assert not verify_password("", stored)


def test_the_password_is_not_in_the_hash():
    stored = hash_password("hunter2hunter2")
    assert "hunter2" not in stored


def test_same_password_gives_different_hashes():
    assert hash_password("same-password") != hash_password("same-password")


def test_garbage_stored_values_never_crash():
    for bad in ["", "abc", "scrypt$x$y$z", "md5$1$aa$bb", "scrypt$16384$zz$zz"]:
        assert verify_password("anything", bad) is False