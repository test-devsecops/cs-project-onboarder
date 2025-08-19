import threading
import time
import requests

class AccessTokenManager:
    def __init__(self, api_actions, token, tenant_iam_url, access_token_endpoint, log):
        self.api_actions = api_actions
        self.tenant_iam_url = tenant_iam_url
        self.access_token_endpoint = access_token_endpoint
        self._lock = threading.Lock()
        self.token = token
        self.access_token = None
        self._expiry = 0  # Unix timestamp when token expires
        self.log = log

    def _renew_locked(self):
        """Renew the access token. Must be called inside a lock."""
        new_token_info = self.api_actions.get_access_token(self.token, self.tenant_iam_url, self.access_token_endpoint)
        
        if not new_token_info or "access_token" not in new_token_info:
            self.log.error(f"Failed to renew token, API returned: {new_token_info}")
            raise Exception("Access token renewal failed")
        
        self.access_token = new_token_info["access_token"]
        self._expiry = time.time() + new_token_info.get("expires_in", 3600) - 10
        self.log.info(f"Access token renewed successfully at {time.strftime('%X')}")

    def ensure_token(self):
        """Ensure the token is valid and renew if expired."""
        if self.access_token is None or time.time() >= self._expiry:
            with self._lock:
                if self.access_token is None or time.time() >= self._expiry:
                    self._renew_locked()
        return self.access_token

    def request_with_retry(self, func, *args, **kwargs):
        """Call a function with automatic access token renewal on 401."""
        for attempt in range(2):
            token = self.ensure_token()
            try:
                return func(token, *args, **kwargs)
            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response else None
                if status == 401 and attempt == 0:
                    self.log.info("401 detected, renewing access token and retrying...")
                    with self._lock:
                        self._renew_locked()
                    continue
                raise
