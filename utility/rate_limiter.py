import threading
import time

class RateLimiter:
    def __init__(self, calls_per_second: float):
        self.calls_per_second = calls_per_second
        self._lock = threading.Lock()
        self._last_call = 0.0
        self._repo_locks = {}

    def _get_repo_lock(self, repo_name: str) -> threading.Lock:
        """Get or create a lock specific to a repo."""
        with self._lock:
            if repo_name not in self._repo_locks:
                self._repo_locks[repo_name] = threading.Lock()
            return self._repo_locks[repo_name]

    def acquire(self, repo_name: str = None):
        """Acquire global and optional repo-specific lock, enforcing rate limit."""
        # Global rate limiting
        with self._lock:
            now = time.time()
            wait = max(0, (1 / self.calls_per_second) - (now - self._last_call))
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.time()

        # Per-repo locking
        if repo_name:
            lock = self._get_repo_lock(repo_name)
            lock.acquire()

    def release(self, repo_name: str = None):
        """Release the per-repo lock if acquired."""
        if repo_name:
            lock = self._get_repo_lock(repo_name)
            lock.release()
