"""In-process sliding-window rate limiter for expensive AI endpoints.

Keyed by authenticated user ID. This is per-process: with several backend instances,
each enforces its own window. For multi-instance deployments, swap in a shared store
(e.g. Redis) behind the same interface.
"""

import time
from collections import defaultdict, deque
from threading import Lock

from app.core.exceptions import RateLimitError


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float = 60.0, what: str = "AI requests") -> None:
        self.limit = limit
        self.what = what
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                retry_after = int(self.window - (now - hits[0])) + 1
                raise RateLimitError(
                    f"Too many {self.what}. Please wait {retry_after} seconds and try again.",
                    details={"retry_after_seconds": retry_after},
                )
            hits.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
