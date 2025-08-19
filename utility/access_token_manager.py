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
        raw_token = self.api_actions.get_access_token(
            self.token, self.tenant_iam_url, self.access_token_endpoint
        )

        if not raw_token or not isinstance(raw_token, str) or raw_token.strip() == "":
            self.log.error(f"Failed to generate access token. API returned: {raw_token!r}")
            raise Exception("Access token renewal failed")

        new_token_info = {
            "access_token": raw_token.strip(),
            "expires_in": 3600  # default 1 hour
        }

        self.access_token = new_token_info["access_token"]
        self._expiry = time.time() + new_token_info["expires_in"] - 10
        self.log.info(
            f"Access token renewed successfully at {time.strftime('%X')} "
            f"(length={len(self.access_token)})"
        )

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
                self.log.error(f"HTTPError: {e.response.status_code} - {e.response.text}")
                status = e.response.status_code if e.response else None
                if status == 401 and attempt == 0:
                    self.log.info("401 detected, renewing access token and retrying...")
                    with self._lock:
                        self._renew_locked()
                    continue
                raise
