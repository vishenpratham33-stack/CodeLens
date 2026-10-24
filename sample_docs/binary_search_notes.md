# Binary search

Works on a sorted list. Compare the middle item with the target, then throw away
half of the list. It takes O(log n) steps. A common bug: computing the middle as
(low + high) // 2 is fine in Python, but can overflow in other languages.
