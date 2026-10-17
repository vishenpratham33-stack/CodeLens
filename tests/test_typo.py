import random

from codelens.index import InvertedIndex
from codelens.typo import (correct_words, default_max_distance, edit_distance, suggest_corrections)


def test_known_distances():
    assert edit_distance("kitten", "sitting") == 3
    assert edit_distance("tokenise", "tokenize") == 1
    assert edit_distance("serach", "search") == 2      # a swap costs 2
    assert edit_distance("abc", "abc") == 0


def test_empty_words():
    assert edit_distance("", "abc") == 3
    assert edit_distance("abc", "") == 3
    assert edit_distance("", "") == 0


def test_distance_is_symmetric_on_random_words():
    rng = random.Random(3)
    for _ in range(100):
        a = "".join(rng.choice("abc") for _ in range(rng.randint(0, 7)))
        b = "".join(rng.choice("abc") for _ in range(rng.randint(0, 7)))
        assert edit_distance(a, b) ==edit_distance(b, a)


def test_early_stop_returns_limit_plus_one():
    assert edit_distance("abcdef", "uvwxyz", max_distance=2) == 3
    assert edit_distance("a", "abcdefgh", max_distance=2) == 3
    assert edit_distance("tokenise", "tokenize", max_distance=2) == 1


def test_default_limit_depends_on_length():
    assert default_max_distance("cat") == 1
    assert default_max_distance("search") == 2


def make_index():
    index = InvertedIndex()
    index.add_document(0, "a.py", ["tokenize", "token", "search"])
    index.add_document(1, "b.py", ["tokenize", "tokens", "search"])
    index.add_document(2, "c.py", ["search", "tokens"])
    return index


def test_suggest_finds_close_words():
    assert suggest_corrections(make_index(), "tokenise")[0] == "tokenize"
    assert suggest_corrections(make_index(), "serch") == ["search"]


def test_suggest_prefers_popular_words_on_a_tie():
    # "token" (in 1 file) and "tokens" (in 2 files) are both 1 steop from "tokent".
    assert suggest_corrections(make_index(), "tokent")[0] == "tokens"


def test_suggest_nothing_when_far_away():
    assert suggest_corrections(make_index(), "zebra") == []


def test_correct_words():
    fixed, changes = correct_words(make_index(), ["tokenise", "search", "zebra"])
    assert fixed == ["tokenize", "search", "zebra"]
    assert changes == [("tokenise", "tokenize")]