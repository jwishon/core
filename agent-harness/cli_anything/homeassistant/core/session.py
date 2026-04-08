"""HTTP session for Home Assistant REST API."""

import requests
from typing import Any
from cli_anything.homeassistant.utils.config import Config, ConfigError


class APIError(Exception):
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


class HASession:
    """Thin wrapper around requests.Session for HA API calls."""

    def __init__(self, config: Config = None):
        self.config = config or Config()
        self._session = requests.Session()

    def _headers(self) -> dict:
        return self.config.auth_headers()

    def _url(self, path: str) -> str:
        return f"{self.config.api_base()}/{path.lstrip('/')}"

    def _raise(self, resp: requests.Response):
        if resp.status_code >= 400:
            try:
                msg = resp.json().get("message", resp.text)
            except Exception:
                msg = resp.text or f"HTTP {resp.status_code}"
            raise APIError(msg, status_code=resp.status_code)

    def get(self, path: str, params: dict = None) -> Any:
        resp = self._session.get(self._url(path), headers=self._headers(), params=params, timeout=30)
        self._raise(resp)
        if not resp.content:
            return None
        return resp.json()

    def post(self, path: str, json: dict = None, params: dict = None) -> Any:
        resp = self._session.post(self._url(path), headers=self._headers(), json=json or {}, params=params, timeout=30)
        self._raise(resp)
        if not resp.content:
            return None
        try:
            return resp.json()
        except Exception:
            return resp.text

    def post_raw(self, path: str, json: dict = None) -> requests.Response:
        """Return raw response (used for SSE streams)."""
        return self._session.post(self._url(path), headers=self._headers(), json=json or {}, timeout=30)

    def delete(self, path: str) -> None:
        resp = self._session.delete(self._url(path), headers=self._headers(), timeout=30)
        self._raise(resp)

    def stream_get(self, path: str, params: dict = None):
        """Return a streaming response for SSE."""
        headers = self._headers()
        headers["Accept"] = "text/event-stream"
        return self._session.get(self._url(path), headers=headers, params=params, stream=True, timeout=None)
