from codelens.tokenizer import count_terms, tokenize

def test_lpwercases_and_splits_on_spaces():
    assert tokenize("Hello World") == ["hello", "world"]

def test_snake_case_is_split():
    assert tokenize("max_file_size") == ["max", "file", "size"]

def test_camel_case_is_split():
    assert tokenize("getUserName") == ["get", "user", "name"]

def test_acronyms_stay_together():
    assert tokenize("getHTTPResponse") == ["get", "http", "response"]

def test_digits_are_seperate_tokens():
    assert tokenize("sha256") == ["sha", "256"]

def test_short_tokens_are_dropped():
    assert tokenize("a b cd x1") == ["cd"]

def test_punctuation_is_ignored():
    assert tokenize("def search(query): return x.y") == ["def", "search", "query", "return"]

def test_order_and_duplicates_are_kept():
    assert tokenize("the cat the") == ["the", "cat", "the"]

def test_stop_words_only_removed_when_asked():
    assert tokenize("the cat") == ["the", "cat"]
    assert tokenize("the cat", remove_stop_words = True) == ["cat"]

def test_empty_gives_empty_list():
    assert tokenize("") == []
    assert tokenize("     \n\t") == []

def test_count_terms():
    assert count_terms(["a1", "b2", "a1"]) == {"a1": 2, "b2": 1}