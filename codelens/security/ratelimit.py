import time
from collections import deque
from typing import Callable, Deque, Dict


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: float, clock: Callable[[], float] = time.monotonic) -> None:
        self.limit = limit
        self.window = window_seconds
        self.clock = clock
        self._hits: Dict[str, Deque[float]] = {}


    def _forget_old(self, key: str, now: float) -> Deque[float]:
        queue = self._hits.setdefault(key, deque())
        while queue and now - queue[0] >= self.window:
            queue.popleft()
        return queue

    
    def allow(self, key: str) -> bool:
        """Count this request if allowed. False means: too many, refuse it."""
        now = self.clock()
        queue = self._forget_old(key, now)
        if len(queue) >= self.limit:
            return False
        queue.append(now)
        return True

    
    def retry_after(self, key: str) -> float:
        """Seconds until the oldest request leaves the window (0 if free now)."""
        now = self.clock()
        queue = self._forget_old(key, now)
        if len(queue) < self.limit:
            return 0.0
        return max(0.0, self.window - (now - queue[0]))