"""Resilience primitives: circuit breaker, token bucket, retry."""

from __future__ import annotations

import asyncio
import random
import threading
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class CircuitOpenError(Exception):
    """Raised when a circuit breaker is open and refuses calls."""


class CircuitBreaker:
    """Fail-fast protection that trips after repeated failures.

    Closed -> open after ``failure_threshold`` consecutive failures. While
    open, calls fail fast with :class:`CircuitOpenError`. After
    ``open_timeout_seconds`` the breaker enters half-open: a single probe is
    allowed, and ``success_threshold`` consecutive successes close it again.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        open_timeout_seconds: float = 30.0,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._success_threshold = success_threshold
        self._open_timeout_seconds = open_timeout_seconds
        self._lock = threading.Lock()
        self._failures = 0
        self._successes = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> str:
        """One of ``closed``, ``open``, ``half_open``."""
        with self._lock:
            if self._opened_at is None:
                return "closed"
            if time.monotonic() - self._opened_at >= self._open_timeout_seconds:
                return "half_open"
            return "open"

    def _is_open(self) -> bool:
        if self._opened_at is None:
            return False
        return time.monotonic() - self._opened_at < self._open_timeout_seconds

    def wrap(self, fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        """Wrap an async callable so every invocation is guarded."""

        async def guarded(*args: object, **kwargs: object) -> T:
            if self._is_open():
                raise CircuitOpenError("Circuit breaker is open.")
            try:
                result = await fn(*args, **kwargs)
            except Exception:
                self.record_failure()
                raise
            self.record_success()
            return result

        return guarded

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0
            if self._opened_at is not None:
                self._successes += 1
                if self._successes >= self._success_threshold:
                    self._opened_at = None
                    self._successes = 0
            else:
                self._successes = 0

    def record_failure(self) -> None:
        with self._lock:
            if self._opened_at is not None:
                return
            self._failures += 1
            if self._failures >= self._failure_threshold:
                self._opened_at = time.monotonic()


class TokenBucket:
    """Thread-safe token bucket used to rate-limit provider calls."""

    def __init__(self, capacity: int = 4, refill_per_second: float = 2.0) -> None:
        self._capacity = float(capacity)
        self._refill = refill_per_second
        self._tokens = float(capacity)
        self._updated = time.monotonic()
        self._lock = threading.Lock()

    async def acquire(self) -> None:
        """Wait until a token is available, then consume it."""
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._updated
                self._tokens = min(
                    self._capacity, self._tokens + elapsed * self._refill
                )
                self._updated = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                wait = (1.0 - self._tokens) / self._refill
            await asyncio.sleep(wait)


async def retry(
    fn: Callable[..., Awaitable[T]],
    *args: object,
    attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 30.0,
    jitter_ratio: float = 0.2,
    **kwargs: object,
) -> T:
    """Retry an async callable with exponential backoff and jitter.

    :class:`CircuitOpenError` is not retried — an open circuit means the
    caller should move on immediately.
    """
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return await fn(*args, **kwargs)
        except CircuitOpenError:
            raise
        except Exception as exc:  # noqa: BLE001 - retry spans arbitrary callables; CircuitOpenError is re-raised
            last_error = exc
            if attempt == attempts - 1:
                break
            delay = min(max_delay, base_delay * (2**attempt))
            jitter = delay * jitter_ratio
            await asyncio.sleep(delay + random.uniform(-jitter, jitter))
    assert last_error is not None
    raise last_error
