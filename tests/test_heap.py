import random

import pytest

from codelens.heap import MinHeap, top_k


def test_pop_gives_smallest_first():
    heap = MinHeap()
    for n in [5, 3, 8, 1, 9, 2]:
        heap.push(n)
    assert[heap.pop() for _ in range(6)] == [1, 2, 3, 5, 8, 9]


def test_peek_does_not_remove():
    heap = MinHeap()
    heap.push(4)
    heap.push(2)
    assert heap.peek() == 2
    assert len(heap) == 2


def test_empty_heap_raises():
    heap = MinHeap()
    with pytest.raises(IndexError):
        heap.pop()
    with pytest.raises(IndexError):
        heap.peek()


def test_top_k_basics():
    scored = [(5.0, 0), (1.0, 1), (9.0, 2), (3.0, 3), (7.0, 4)]
    assert top_k(scored, 3) == [(9.0, 2), (7.0, 4), (5.0, 0)]


def test_top_k_ties_prefer_smaller_doc_id():
    scored = [(2.0, 5), (2.0, 1), (2.0, 3)]
    assert top_k(scored, 2) == [(2.0, 1), (2.0, 3)]


def test_top_k_edge_cases():
    assert top_k([], 5) == []
    assert top_k([(1.0, 0)], 0) == []
    assert top_k([(1.0, 0), (2.0, 1)], 10) == [(2.0, 1), (1.0, 0)]


def test_top_k_matches_sorting_on_random_data():
    rng = random.Random(7)
    scored = [(rng.random(), i) for i in range(200)]
    expected = sorted(scored, key=lambda pair: (-pair[0], pair[1]))[:10]
    assert top_k(scored, 10) == expected
