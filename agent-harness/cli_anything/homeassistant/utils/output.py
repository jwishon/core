"""Output formatting for cli-anything-homeassistant."""

import json
import sys
from typing import Any


class OutputFormatter:
    def __init__(self, json_mode: bool = False):
        self.json_mode = json_mode

    def success(self, data: Any, meta: dict = None) -> str:
        if self.json_mode:
            payload = {"success": True, "data": data}
            if meta:
                payload["meta"] = meta
            return json.dumps(payload, indent=2, default=str)
        return self._human(data)

    def error(self, message: str, code: int = None) -> str:
        if self.json_mode:
            payload = {"success": False, "error": message}
            if code is not None:
                payload["code"] = code
            return json.dumps(payload, indent=2)
        return f"Error: {message}"

    def _human(self, data: Any) -> str:
        if data is None:
            return ""
        if isinstance(data, str):
            return data
        if isinstance(data, list):
            return "\n".join(self._format_item(i) for i in data)
        if isinstance(data, dict):
            return self._format_item(data)
        return str(data)

    def _format_item(self, item: Any) -> str:
        if isinstance(item, dict):
            return "\n".join(f"  {k}: {v}" for k, v in item.items() if v not in (None, "", []))
        return str(item)

    def print_success(self, data: Any, meta: dict = None):
        print(self.success(data, meta))

    def print_error(self, message: str, code: int = None):
        print(self.error(message, code), file=sys.stderr)

    def print_table(self, rows: list, columns: list, headers: list = None):
        if self.json_mode:
            self.print_success(rows)
            return
        if not rows:
            print("(no results)")
            return
        if headers is None:
            headers = columns
        widths = [len(h) for h in headers]
        for row in rows:
            for i, col in enumerate(columns):
                widths[i] = max(widths[i], len(str(row.get(col, ""))))
        print("  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)))
        print("  ".join("-" * w for w in widths))
        for row in rows:
            print("  ".join(str(row.get(col, "")).ljust(widths[i]) for i, col in enumerate(columns)))
