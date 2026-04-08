"""Event operations for Home Assistant REST API."""

import json
from cli_anything.homeassistant.core.session import HASession


class EventClient:
    def __init__(self, session: HASession):
        self.session = session

    def list_all(self) -> list:
        """GET /api/events — event listener counts."""
        return self.session.get("events") or []

    def fire(self, event_type: str, event_data: dict = None) -> dict:
        """POST /api/events/{event_type}"""
        return self.session.post(f"events/{event_type}", json=event_data or {})

    def stream(self, restrict: list[str] = None):
        """GET /api/stream — SSE event stream.

        Yields parsed event dicts as they arrive.
        restrict: list of event types to filter (e.g. ['state_changed'])
        """
        params = {}
        if restrict:
            params["restrict"] = ",".join(restrict)
        resp = self.session.stream_get("stream", params=params)
        resp.raise_for_status()
        buf = ""
        for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
            buf += chunk
            while "\n\n" in buf:
                block, buf = buf.split("\n\n", 1)
                event = {}
                for line in block.splitlines():
                    if line.startswith("data:"):
                        raw = line[5:].strip()
                        try:
                            event = json.loads(raw)
                        except json.JSONDecodeError:
                            event = {"raw": raw}
                    elif line.startswith("event:"):
                        event["_type"] = line[6:].strip()
                if event:
                    yield event
