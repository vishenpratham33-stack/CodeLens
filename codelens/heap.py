"""step 4 (Part A) of CodeLens: a min-heap, and "the best K" built on it.

A heap is a tree stored in a plain list. in a MIN-heap every parent is smaller than (or equal to) its children, so the smallest item is always at index 0. For the item at index i:
    parent         -> (i - 1) // 2
    left child     -> 2 * i + 1
    right child    -> 2 * i + 2
"""

from typing import List, Tuple


class MinHeap:
    def __init__(self) -> None:
        self._items: list = []

    def __len__(self) -> int:
        return len(self._items)

    def peek(self):
        """Look at the smallest item without removing it."""
        if not self._items:
            raise IndexError("peek from empty heap")
        return self._items[0]

    def push(self, item) -> None:
        items = self._items
        items.append(item)
        i = len(items) - 1
        # Bubble up: swap with the parent while smaller than it.
        while i >  0:
            parent = (i - 1) // 2
            if items[parent] <= items[i]:
                break 
            items[parent], items[i] = items[i], items[parent]
            i = parent

    def pop(self):
        """Remove and return the smallest item."""
        items = self._items
        if not items:
            raise IndexError("pop from empty heap")
        smallest = items[0]
        last = items.pop()
        if items:
            items[0] = last
            i = 0
            size = len(items)
            # Sink down: swap with the smallest child untill in place.
            while True:
                left = 2 * i + 1
                right = left + 1
                best = i
                if left < size and items[left] < items[best]:
                    best = left
                if right < size and items[right] < items[best]:
                    best = right
                if best == i:
                    break
                items [best], items[i] = items[i], items[best]
                i = best
        return smallest


def top_k(scored: List[Tuple[float, int]], k: int) -> List[Tuple[float, int]]:
    """Return the k best (score, doc_id) pairs, best first.
    
    We keep a min-heap of size k. The weakest of the current best k sits on top, so when a new item arrives and the heap is too big, we throw the weakest away. Cost: about n * log(k), not n * log(n).
    """
    if k <= 0:
        return[]
    heap = MinHeap()
    for score, doc_id in scored:
        # -doc_id: when two scores are equal, the SMALLER doc_id wins.
        heap.push((score, -doc_id))
        if len(heap) > k:
            heap.pop()

    best_last: List[Tuple[float, int]] = []
    while len(heap):
        score, negative_id = heap.pop()
        best_last.append((score, -negative_id))
    best_last.reverse()          # the heap gave weakest first
    return best_last