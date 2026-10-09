"""
Exponential backoff retry helper for Gemini API calls.
Free tier returns 429 on rate-limit hits — this wraps any async call
with retry + jittered exponential backoff instead of failing immediately.
"""
import asyncio
import random
from functools import wraps
from typing import Callable, TypeVar, Awaitable

T = TypeVar("T")


class RateLimitError(Exception):
    """Raised when the underlying API signals a 429 / quota exceeded."""
    pass


def with_backoff(
    max_retries: int = 4,
    base_delay: float = 1.0,
    max_delay: float = 16.0,
):
    """
    Decorator for async functions that call the Gemini API.
    Retries on RateLimitError with exponential backoff + jitter:
    1s, 2s, 4s, 8s (capped at max_delay), each ± up to 25% jitter.
    """
    def decorator(fn: Callable[..., Awaitable[T]]):
        @wraps(fn)
        async def wrapper(*args, **kwargs) -> T:
            last_exc: Exception | None = None
            for attempt in range(max_retries + 1):
                try:
                    return await fn(*args, **kwargs)
                except RateLimitError as exc:
                    last_exc = exc
                    if attempt == max_retries:
                        break
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = delay * random.uniform(-0.25, 0.25)
                    await asyncio.sleep(delay + jitter)
            raise last_exc  # exhausted retries
        return wrapper
    return decorator
