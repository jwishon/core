"""Configuration management for cli-anything-homeassistant."""

import json
import os
from pathlib import Path


class ConfigError(Exception):
    pass


class Config:
    DEFAULT_CONFIG_FILE = Path.home() / ".config" / "cli-anything-homeassistant" / "config.json"

    def __init__(self, config_path: Path = None):
        self.config_path = Path(config_path) if config_path else self.DEFAULT_CONFIG_FILE
        self._data: dict = {}
        self._load()

    def _load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._data = {}

    def save(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self._data, f, indent=2)

    @property
    def url(self) -> str:
        return os.environ.get("HA_URL", self._data.get("url", "")).rstrip("/")

    @url.setter
    def url(self, value: str):
        self._data["url"] = value.rstrip("/")

    @property
    def token(self) -> str:
        return os.environ.get("HA_TOKEN", self._data.get("token", ""))

    @token.setter
    def token(self, value: str):
        self._data["token"] = value

    def api_base(self) -> str:
        if not self.url:
            raise ConfigError("HA URL not configured. Run: cli-anything-homeassistant config set --url <url>")
        return f"{self.url}/api"

    def auth_headers(self) -> dict:
        if not self.token:
            raise ConfigError("Token not configured. Run: cli-anything-homeassistant config set --token <token>")
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "token": "***" if self.token else "",
            "config_path": str(self.config_path),
        }
