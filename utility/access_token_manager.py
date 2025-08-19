import threading
import requests

class AccessTokenManager:
    """
    Thread-safe access token manager for API calls.
    - Holds the current access token
    - Requests a new token only when the old one is None or expired (401)
    - Supports parallel threads without token stampede
    """

    def __init__(self, api_actions, token_seed, tenant_iam_url, get_access_token_endpoint):
        self.api_actions = api_actions
        self.token_seed = token_seed
        self.tenant_iam_url = tenant_iam_url
        self.get_access_token_endpoint = get_access_token_endpoint
        self.access_token = None
        self._lock = threading.Lock()

    def _renew_locked(self):
        """Renew the access token. Must be called while holding the lock."""
        self.access_token = self.api_actions.get_access_token(
            self.token_seed, self.tenant_iam_url, self.get_access_token_endpoint
        )
        print("[AccessTokenManager] Access token renewed.")

    def ensure_token(self):
        """Return a valid token. Lazily initialize if None."""
        if self.access_token is None:
            with self._lock:
                if self.access_token is None:
                    self._renew_locked()
        return self.access_token

    def request_with_retry(self, func, *args, **kwargs):
        """
        Call the given api_actions function as: func(access_token, *args, **kwargs).
        If a 401 Unauthorized occurs, refresh the token once and retry.
        """
        self.ensure_token()
        try:
            return func(self.access_token, *args, **kwargs)
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else None
            if status == 401:
                with self._lock:
                    self._renew_locked()
                return func(self.access_token, *args, **kwargs)
            raise
        except Exception as e:
            # Some clients may attach status_code on generic Exceptions
            if getattr(e, "status_code", None) == 401 or "401" in str(e):
                with self._lock:
                    self._renew_locked()
                return func(self.access_token, *args, **kwargs)
            raise
