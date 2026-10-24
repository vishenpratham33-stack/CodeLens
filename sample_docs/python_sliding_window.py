"""Sliding window: the largest sum of k consecutive numbers."""


def max_window_sum(numbers, k):
    """Keep the sum of the current window and slide it one step at a time."""
    if k <= 0 or len(numbers) < k:
        return 0
    window = sum(numbers[:k])
    best = window
    for i in range(k, len(numbers)):
        window += numbers[i] - numbers[i - k]   # add the new number, drop the old one
        best = max(best, window)
    return best


print(max_window_sum([2, 1, 5, 1, 3, 2], 3))   # prints 9
