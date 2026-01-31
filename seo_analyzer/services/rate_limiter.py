"""
Thread-safe Rate Limiter for API calls
"""
import time
import threading
from typing import Optional


class RateLimiter:
    """
    Thread-safe rate limiter using token bucket algorithm

    Ensures API calls don't exceed specified rate limits:
    - Maximum requests per second
    - Maximum concurrent requests
    """

    def __init__(self, max_requests_per_second: float = 4.0, max_concurrent: int = 4):
        """
        Initialize rate limiter

        Args:
            max_requests_per_second: Maximum API calls per second (default: 4)
            max_concurrent: Maximum concurrent API calls (default: 4)
        """
        self.max_requests_per_second = max_requests_per_second
        self.min_interval = 1.0 / max_requests_per_second  # seconds between requests

        # Semaphore for concurrent request limiting
        self.semaphore = threading.Semaphore(max_concurrent)

        # Lock for thread-safe access to last_request_time
        self.lock = threading.Lock()
        self.last_request_time = 0.0

    def acquire(self) -> None:
        """
        Acquire permission to make an API call
        Blocks until rate limit allows the request
        """
        # First, acquire semaphore (limit concurrent requests)
        self.semaphore.acquire()

        # Then, ensure minimum time interval between requests
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time

            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)

            self.last_request_time = time.time()

    def release(self) -> None:
        """
        Release the semaphore after API call completes
        """
        self.semaphore.release()

    def __enter__(self):
        """Context manager entry"""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()
        return False


class BatchRateLimiter:
    """
    Rate limiter optimized for batch operations
    Allows burst of requests up to a limit, then enforces rate
    """

    def __init__(
        self,
        max_requests_per_second: float = 4.0,
        max_concurrent: int = 4,
        burst_size: int = 10
    ):
        """
        Initialize batch rate limiter

        Args:
            max_requests_per_second: Average requests per second
            max_concurrent: Maximum concurrent requests
            burst_size: Maximum burst size before rate limiting kicks in
        """
        self.rate = max_requests_per_second
        self.max_concurrent = max_concurrent
        self.burst_size = burst_size

        # Token bucket
        self.tokens = float(burst_size)
        self.last_update = time.time()

        # Semaphore and lock
        self.semaphore = threading.Semaphore(max_concurrent)
        self.lock = threading.Lock()

    def _add_tokens(self) -> None:
        """Add tokens based on time elapsed"""
        current_time = time.time()
        elapsed = current_time - self.last_update

        # Add tokens based on rate
        tokens_to_add = elapsed * self.rate
        self.tokens = min(self.burst_size, self.tokens + tokens_to_add)
        self.last_update = current_time

    def acquire(self) -> None:
        """Acquire permission to make an API call"""
        # Acquire semaphore first
        self.semaphore.acquire()

        # Then check token bucket
        with self.lock:
            self._add_tokens()

            # If no tokens available, wait
            while self.tokens < 1.0:
                # Calculate wait time
                wait_time = (1.0 - self.tokens) / self.rate
                time.sleep(wait_time)
                self._add_tokens()

            # Consume one token
            self.tokens -= 1.0

    def release(self) -> None:
        """Release the semaphore"""
        self.semaphore.release()

    def __enter__(self):
        """Context manager entry"""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()
        return False
