"""E2E tests for cli-anything-homeassistant.

Live tests require HA_URL and HA_TOKEN environment variables.
Skipped automatically when not set.
Subprocess tests require the installed CLI binary or Python module.
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

from cli_anything.homeassistant.utils.config import Config
from cli_anything.homeassistant.core.session import HASession
from cli_anything.homeassistant.core.entities import EntityClient
from cli_anything.homeassistant.core.services import ServiceClient
from cli_anything.homeassistant.core.templates import TemplateClient
from cli_anything.homeassistant.core.events import EventClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

LIVE = pytest.mark.skipif(
    not (os.environ.get("HA_URL") and os.environ.get("HA_TOKEN")),
    reason="HA_URL and HA_TOKEN must be set for live E2E tests",
)


def live_config() -> Config:
    return Config()  # reads from env


def _resolve_cli(name: str) -> str | None:
    if os.environ.get("CLI_ANYTHING_FORCE_INSTALLED") == "1":
        resolved = shutil.which(name)
        if not resolved:
            raise RuntimeError(f"CLI '{name}' not found on PATH. Run: pip install -e .")
        return resolved
    return None


def run_cli(*args, env=None) -> subprocess.CompletedProcess:
    resolved = _resolve_cli("cli-anything-homeassistant")
    if resolved:
        cmd = [resolved] + list(args)
    else:
        cmd = [sys.executable, "-m", "cli_anything.homeassistant.homeassistant_cli"] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


# ---------------------------------------------------------------------------
# Subprocess Tests (no live HA needed)
# ---------------------------------------------------------------------------

class TestCLISubprocess:
    def test_help(self):
        r = run_cli("--help")
        assert r.returncode == 0
        assert "Usage" in r.stdout

    def test_config_show_json(self):
        r = run_cli("--json", "config", "show")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "success" in data

    def test_entity_help(self):
        r = run_cli("entity", "--help")
        assert r.returncode == 0
        assert "list" in r.stdout

    def test_service_help(self):
        r = run_cli("service", "--help")
        assert r.returncode == 0
        assert "call" in r.stdout

    def test_event_help(self):
        r = run_cli("event", "--help")
        assert r.returncode == 0

    def test_template_help(self):
        r = run_cli("template", "--help")
        assert r.returncode == 0
        assert "render" in r.stdout

    def test_history_help(self):
        r = run_cli("history", "--help")
        assert r.returncode == 0

    def test_logbook_help(self):
        r = run_cli("logbook", "--help")
        assert r.returncode == 0

    def test_json_error_no_url(self):
        env = os.environ.copy()
        env.pop("HA_URL", None)
        env.pop("HA_TOKEN", None)
        r = run_cli("--json", "config", "check", env=env)
        assert r.returncode != 0

    def test_repl_help(self):
        r = run_cli("repl", "--help")
        assert r.returncode == 0


# ---------------------------------------------------------------------------
# Live E2E Tests
# ---------------------------------------------------------------------------

@LIVE
class TestLiveEntities:
    def test_list_states(self):
        c = EntityClient(HASession(config=live_config()))
        states = c.list_all()
        assert isinstance(states, list)
        assert len(states) > 0
        assert "entity_id" in states[0]

    def test_get_state(self):
        c = EntityClient(HASession(config=live_config()))
        states = c.list_all()
        if not states:
            pytest.skip("No entities available")
        eid = states[0]["entity_id"]
        state = c.get(eid)
        assert state["entity_id"] == eid

    def test_get_config(self):
        c = EntityClient(HASession(config=live_config()))
        cfg = c.get_config()
        assert "version" in cfg or "components" in cfg

    def test_get_api_status(self):
        c = EntityClient(HASession(config=live_config()))
        status = c.get_api_status()
        assert "message" in status or "ha_version" in status


@LIVE
class TestLiveServices:
    def test_list_services(self):
        c = ServiceClient(HASession(config=live_config()))
        services = c.list_all()
        assert isinstance(services, list)
        domains = [s["domain"] for s in services]
        assert "homeassistant" in domains

    def test_call_check_config(self):
        c = ServiceClient(HASession(config=live_config()))
        # homeassistant.check_config is a safe read-only service
        result = c.call("homeassistant", "check_config")
        # Just verify it doesn't raise; result may be None or a list


@LIVE
class TestLiveTemplates:
    def test_render_simple(self):
        c = TemplateClient(HASession(config=live_config()))
        result = c.render("{{ 1 + 1 }}")
        assert result.strip() == "2"

    def test_render_states_call(self):
        c = TemplateClient(HASession(config=live_config()))
        # Just verify template engine is working
        result = c.render("{{ now().year }}")
        assert "202" in result  # year 2026+


@LIVE
class TestLiveEvents:
    def test_list_events(self):
        c = EventClient(HASession(config=live_config()))
        events = c.list_all()
        assert isinstance(events, list)
        types = [e.get("event") for e in events]
        assert "state_changed" in types

    def test_fire_custom_event(self):
        c = EventClient(HASession(config=live_config()))
        result = c.fire("cli_anything_test_event", {"source": "e2e_test"})
        assert result is not None
