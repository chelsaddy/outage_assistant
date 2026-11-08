"""In-memory sliding-window rate limits.

Counts live in this process, which is right for a single API process (the default). With more than
one worker or server, move the counts to a shared store such as Redis so every process sees them.
"""
import math
import os
import threading
import time
from collections import deque


class RateLimiter:
    """At most `limit` hits per `window` seconds for each key."""

    def __init__(self, limit: int, window: float):
        self.limit = limit
        self.window = window
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        q = self._hits.setdefault(key, deque())
        while q and q[0] <= now - self.window:
            q.popleft()
        return q

    def retry_after(self, key: str, now: float | None = None) -> float:
        """Seconds until the next hit is allowed; 0 if allowed now."""
        now = time.monotonic() if now is None else now
        with self._lock:
            q = self._prune(key, now)
            return 0.0 if len(q) < self.limit else q[0] + self.window - now

    def record(self, key: str, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        with self._lock:
            self._prune(key, now).append(now)
            if len(self._hits) > 10_000:  # drop idle keys so memory stays bounded
                for k in [k for k, q in self._hits.items() if not q or q[-1] <= now - self.window]:
                    del self._hits[k]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def check_and_record(limits: list[tuple[RateLimiter, str]]) -> int:
    """Record one hit against every (limiter, key) pair, unless any is over its limit.

    Returns 0 if the hit was allowed, otherwise the whole seconds to wait (for Retry-After).
    """
    wait = max(limiter.retry_after(key) for limiter, key in limits)
    if wait > 0:
        return max(1, math.ceil(wait))
    for limiter, key in limits:
        limiter.record(key)
    return 0


def _env_int(name: str, default: int) -> int:
    return int(os.environ.get(name) or default)


# POST /chat: every message costs model calls.
CHAT_PER_MINUTE = RateLimiter(_env_int("CHAT_RATE_PER_MINUTE", 10), 60)          # per client
CHAT_PER_DAY = RateLimiter(_env_int("CHAT_RATE_PER_DAY", 100), 24 * 3600)         # per client
CHAT_GLOBAL_PER_DAY = RateLimiter(_env_int("CHAT_GLOBAL_PER_DAY", 2000), 24 * 3600)  # everyone together
