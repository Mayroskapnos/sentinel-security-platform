import time
from collections import defaultdict, deque

from app.core.errors import AppError


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, *, maximum: int, window_seconds: int) -> None:
        now = time.monotonic()
        requests = self._requests[key]
        while requests and now - requests[0] >= window_seconds:
            requests.popleft()
        if len(requests) >= maximum:
            raise AppError(
                "ASSISTANT_RATE_LIMITED",
                "The Investigation Assistant request limit was reached. Try again shortly.",
                429,
            )
        requests.append(now)

    def reset(self) -> None:
        self._requests.clear()


assistant_rate_limiter = SlidingWindowRateLimiter()
