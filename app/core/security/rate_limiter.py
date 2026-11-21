import threading
import time
from collections import deque
from collections.abc import Callable

from app.exceptions import TooManyRequestsError


class RateLimiter:
    CLEANUP_EVERY = 500

    def __init__(self, limit: int, window_seconds: int = 60, clock: Callable[[], float] = time.monotonic):
        self.limit = limit
        self.window_seconds = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._calls = 0

    @property
    def enabled(self) -> bool:
        return self.limit > 0

    def hit(self, key: str) -> None:
        if not self.enabled:
            return
        now = self._clock()
        with self._lock:
            self._calls += 1
            if self._calls % self.CLEANUP_EVERY == 0:
                self._purge(now)
            hits = self._hits.setdefault(key, deque())
            self._drop_expired(hits, now)
            if len(hits) >= self.limit:
                retry_after = max(1, int(hits[0] + self.window_seconds - now) + 1)
                raise TooManyRequestsError(retry_after)
            hits.append(now)

    def _drop_expired(self, hits: deque[float], now: float) -> None:
        while hits and now - hits[0] >= self.window_seconds:
            hits.popleft()

    def _purge(self, now: float) -> None:
        for key in list(self._hits):
            self._drop_expired(self._hits[key], now)
            if not self._hits[key]:
                del self._hits[key]
