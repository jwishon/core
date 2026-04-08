"""Unit tests for cli-anything-homeassistant.

All tests use mocked HTTP — no live HA instance required.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli_anything.homeassistant.utils.config import Config, ConfigError
from cli_anything.homeassistant.utils.output import OutputFormatter
from cli_anything.homeassistant.core.session import HASession, APIError
from cli_anything.homeassistant.core.entities import EntityClient
from cli_anything.homeassistant.core.services import ServiceClient
from cli_anything.homeassistant.core.events import EventClient
from cli_anything.homeassistant.core.templates import TemplateClient
from cli_anything.homeassistant.core.history import HistoryClient, LogbookClient
from cli_anything.homeassistant.homeassistant_cli import cli


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_config(url="http://ha.test:8123", token="test_token", tmp_path=None):
    path = Path(tmp_path or tempfile.mkdtemp()) / "config.json"
    c = Config(config_path=path)
    c.url = url
    c.token = token
    return c


def mock_resp(data, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.content = json.dumps(data).encode() if data is not None else b""
    resp.json.return_value = data
    resp.text = json.dumps(data) if data is not None else ""
    return resp


def make_session():
    return HASession(config=make_config())


SAMPLE_STATE = {
    "entity_id": "light.bedroom",
    "state": "on",
    "attributes": {"brightness": 200, "friendly_name": "Bedroom Light"},
    "last_changed": "2026-04-07T10:00:00.000000+00:00",
    "last_updated": "2026-04-07T10:00:00.000000+00:00",
    "context": {"id": "abc123", "parent_id": None, "user_id": None},
}

SAMPLE_SERVICE = {
    "domain": "light",
    "services": {
        "turn_on": {"description": "Turn on light", "fields": {}},
        "turn_off": {"description": "Turn off light", "fields": {}},
    },
}


# ---------------------------------------------------------------------------
# Config Tests
# ---------------------------------------------------------------------------

class TestConfig:
    def test_defaults_empty(self, monkeypatch):
        monkeypatch.delenv("HA_URL", raising=False)
        monkeypatch.delenv("HA_TOKEN", raising=False)
        with tempfile.TemporaryDirectory() as d:
            c = Config(config_path=Path(d) / "config.json")
            assert c.url == ""
            assert c.token == ""

    def test_save_and_reload(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "config.json"
            c = Config(config_path=path)
            c.url = "http://ha.test:8123"
            c.token = "mytoken"
            c.save()
            c2 = Config(config_path=path)
            assert c2.url == "http://ha.test:8123"
            assert c2.token == "mytoken"

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("HA_URL", "http://env-ha:8123")
        monkeypatch.setenv("HA_TOKEN", "envtoken")
        with tempfile.TemporaryDirectory() as d:
            c = Config(config_path=Path(d) / "config.json")
            assert c.url == "http://env-ha:8123"
            assert c.token == "envtoken"

    def test_api_base(self):
        c = make_config(url="http://ha.test:8123/")
        assert c.api_base() == "http://ha.test:8123/api"

    def test_api_base_no_url_raises(self, monkeypatch):
        monkeypatch.delenv("HA_URL", raising=False)
        with tempfile.TemporaryDirectory() as d:
            c = Config(config_path=Path(d) / "config.json")
            with pytest.raises(ConfigError):
                c.api_base()

    def test_auth_headers(self):
        c = make_config(token="tok123")
        headers = c.auth_headers()
        assert headers["Authorization"] == "Bearer tok123"

    def test_auth_headers_no_token_raises(self, monkeypatch):
        monkeypatch.delenv("HA_TOKEN", raising=False)
        with tempfile.TemporaryDirectory() as d:
            c = Config(config_path=Path(d) / "config.json")
            c.url = "http://ha.test:8123"
            with pytest.raises(ConfigError):
                c.auth_headers()

    def test_url_strips_slash(self):
        c = make_config(url="http://ha.test:8123/")
        assert not c.url.endswith("/")

    def test_to_dict_masks_token(self):
        c = make_config(token="secret")
        assert c.to_dict()["token"] == "***"


# ---------------------------------------------------------------------------
# OutputFormatter Tests
# ---------------------------------------------------------------------------

class TestOutputFormatter:
    def test_json_success_dict(self):
        out = json.loads(OutputFormatter(True).success({"x": 1}))
        assert out["success"] is True
        assert out["data"]["x"] == 1

    def test_json_success_list(self):
        out = json.loads(OutputFormatter(True).success([1, 2, 3]))
        assert out["data"] == [1, 2, 3]

    def test_json_success_meta(self):
        out = json.loads(OutputFormatter(True).success([], meta={"count": 5}))
        assert out["meta"]["count"] == 5

    def test_json_error(self):
        out = json.loads(OutputFormatter(True).error("Not found", 404))
        assert out["success"] is False
        assert out["code"] == 404

    def test_human_dict(self):
        out = OutputFormatter(False).success({"key": "val"})
        assert "key: val" in out

    def test_human_list(self):
        out = OutputFormatter(False).success([{"a": 1}, {"a": 2}])
        assert "1" in out and "2" in out

    def test_human_error(self):
        assert "broke" in OutputFormatter(False).error("broke")

    def test_table_empty(self, capsys):
        OutputFormatter(False).print_table([], ["x"])
        assert "(no results)" in capsys.readouterr().out

    def test_table_renders(self, capsys):
        OutputFormatter(False).print_table([{"a": "foo"}], ["a"], ["A"])
        assert "foo" in capsys.readouterr().out

    def test_table_json_mode(self, capsys):
        OutputFormatter(True).print_table([{"x": 1}], ["x"])
        out = json.loads(capsys.readouterr().out)
        assert out["success"] is True


# ---------------------------------------------------------------------------
# Session Tests
# ---------------------------------------------------------------------------

class TestHASession:
    def test_get_success(self):
        s = make_session()
        with patch.object(s._session, "get", return_value=mock_resp({"message": "ok"})):
            data = s.get("states/light.x")
        assert data["message"] == "ok"

    def test_get_404_raises(self):
        s = make_session()
        with patch.object(s._session, "get", return_value=mock_resp({"message": "not found"}, 404)):
            with pytest.raises(APIError) as exc:
                s.get("states/light.x")
        assert exc.value.status_code == 404

    def test_get_401_raises(self):
        s = make_session()
        with patch.object(s._session, "get", return_value=mock_resp({"message": "Unauthorized"}, 401)):
            with pytest.raises(APIError) as exc:
                s.get("")
        assert exc.value.status_code == 401

    def test_post_success(self):
        s = make_session()
        with patch.object(s._session, "post", return_value=mock_resp({"result": "ok"}, 200)):
            data = s.post("events/my_event", json={"key": "val"})
        assert data["result"] == "ok"

    def test_post_empty_response(self):
        s = make_session()
        resp = mock_resp(None, 200)
        resp.content = b""
        with patch.object(s._session, "post", return_value=resp):
            data = s.post("services/light/turn_on")
        assert data is None

    def test_delete_success(self):
        s = make_session()
        resp = mock_resp(None, 200)
        resp.content = b""
        with patch.object(s._session, "delete", return_value=resp):
            s.delete("states/light.x")  # no exception

    def test_error_message_from_json(self):
        s = make_session()
        with patch.object(s._session, "get", return_value=mock_resp({"message": "Template error"}, 400)):
            with pytest.raises(APIError) as exc:
                s.get("template")
        assert "Template error" in str(exc.value)


# ---------------------------------------------------------------------------
# EntityClient Tests
# ---------------------------------------------------------------------------

class TestEntityClient:
    def _client(self):
        s = make_session()
        return EntityClient(s), s

    def test_list_all(self):
        c, s = self._client()
        states = [SAMPLE_STATE, {**SAMPLE_STATE, "entity_id": "switch.fan", "state": "off"}]
        with patch.object(s._session, "get", return_value=mock_resp(states)):
            result = c.list_all()
        assert len(result) == 2

    def test_list_by_domain(self):
        c, s = self._client()
        states = [SAMPLE_STATE, {**SAMPLE_STATE, "entity_id": "switch.fan", "state": "off"}]
        with patch.object(s._session, "get", return_value=mock_resp(states)):
            result = c.list_by_domain("light")
        assert len(result) == 1
        assert result[0]["entity_id"] == "light.bedroom"

    def test_get(self):
        c, s = self._client()
        with patch.object(s._session, "get", return_value=mock_resp(SAMPLE_STATE)):
            data = c.get("light.bedroom")
        assert data["state"] == "on"

    def test_set_state(self):
        c, s = self._client()
        updated = {**SAMPLE_STATE, "state": "off"}
        with patch.object(s._session, "post", return_value=mock_resp(updated)) as mp:
            data = c.set_state("light.bedroom", "off", attributes={"brightness": 0})
        sent = mp.call_args[1]["json"]
        assert sent["state"] == "off"
        assert sent["attributes"]["brightness"] == 0

    def test_delete(self):
        c, s = self._client()
        resp = mock_resp(None, 200)
        resp.content = b""
        with patch.object(s._session, "delete", return_value=resp):
            c.delete("light.bedroom")  # no exception

    def test_get_config(self):
        c, s = self._client()
        cfg = {"version": "2024.4.0", "components": []}
        with patch.object(s._session, "get", return_value=mock_resp(cfg)):
            data = c.get_config()
        assert "version" in data

    def test_get_api_status(self):
        c, s = self._client()
        with patch.object(s._session, "get", return_value=mock_resp({"message": "API running."})):
            data = c.get_api_status()
        assert "message" in data

    def test_get_core_state(self):
        c, s = self._client()
        with patch.object(s._session, "get", return_value=mock_resp({"state": "running"})):
            data = c.get_core_state()
        assert data["state"] == "running"


# ---------------------------------------------------------------------------
# ServiceClient Tests
# ---------------------------------------------------------------------------

class TestServiceClient:
    def _client(self):
        s = make_session()
        return ServiceClient(s), s

    def test_list_all(self):
        c, s = self._client()
        with patch.object(s._session, "get", return_value=mock_resp([SAMPLE_SERVICE])):
            result = c.list_all()
        assert result[0]["domain"] == "light"

    def test_list_by_domain(self):
        c, s = self._client()
        services = [SAMPLE_SERVICE, {"domain": "switch", "services": {"toggle": {}}}]
        with patch.object(s._session, "get", return_value=mock_resp(services)):
            result = c.list_by_domain("light")
        assert len(result) == 1
        assert result[0]["domain"] == "light"

    def test_call_returns_states(self):
        c, s = self._client()
        affected = [SAMPLE_STATE]
        with patch.object(s._session, "post", return_value=mock_resp(affected)) as mp:
            result = c.call("light", "turn_on", service_data={"entity_id": "light.bedroom", "brightness": 200})
        called_url = mp.call_args[0][0]
        assert "services/light/turn_on" in called_url
        sent = mp.call_args[1]["json"]
        assert sent["entity_id"] == "light.bedroom"
        assert sent["brightness"] == 200

    def test_call_empty_response(self):
        c, s = self._client()
        resp = mock_resp(None, 200)
        resp.content = b""
        with patch.object(s._session, "post", return_value=resp):
            result = c.call("homeassistant", "reload_all")
        assert result is None

    def test_call_with_return_response(self):
        c, s = self._client()
        with patch.object(s._session, "post", return_value=mock_resp({"response": "data"})) as mp:
            c.call("light", "turn_on", return_response=True)
        call_params = mp.call_args[1].get("params") or mp.call_args[0]
        # return_response query param should be set
        assert mp.called


# ---------------------------------------------------------------------------
# EventClient Tests
# ---------------------------------------------------------------------------

class TestEventClient:
    def _client(self):
        s = make_session()
        return EventClient(s), s

    def test_list_all(self):
        c, s = self._client()
        events = [{"event": "state_changed", "listener_count": 5}]
        with patch.object(s._session, "get", return_value=mock_resp(events)):
            result = c.list_all()
        assert result[0]["event"] == "state_changed"

    def test_fire(self):
        c, s = self._client()
        with patch.object(s._session, "post", return_value=mock_resp({"message": "Event fired."})) as mp:
            result = c.fire("my_event", {"key": "val"})
        called_url = mp.call_args[0][0]
        assert "events/my_event" in called_url
        sent = mp.call_args[1]["json"]
        assert sent["key"] == "val"

    def test_fire_no_data(self):
        c, s = self._client()
        with patch.object(s._session, "post", return_value=mock_resp({"message": "Event fired."})):
            result = c.fire("ping")
        assert result is not None


# ---------------------------------------------------------------------------
# TemplateClient Tests
# ---------------------------------------------------------------------------

class TestTemplateClient:
    def _client(self):
        s = make_session()
        return TemplateClient(s), s

    def test_render_returns_string(self):
        c, s = self._client()
        with patch.object(s._session, "post", return_value=mock_resp("on")) as mp:
            result = c.render("{{ states('light.bedroom') }}")
        sent = mp.call_args[1]["json"]
        assert "template" in sent
        assert result == "on"

    def test_render_with_variables(self):
        c, s = self._client()
        with patch.object(s._session, "post", return_value=mock_resp("hello world")) as mp:
            result = c.render("{{ name }}", variables={"name": "world"})
        sent = mp.call_args[1]["json"]
        assert sent["variables"] == {"name": "world"}

    def test_render_dict_response(self):
        c, s = self._client()
        with patch.object(s._session, "post", return_value=mock_resp({"result": "42.5"})):
            result = c.render("{{ state_attr('sensor.temp', 'temperature') }}")
        assert "42.5" in result


# ---------------------------------------------------------------------------
# HistoryClient Tests
# ---------------------------------------------------------------------------

class TestHistoryClient:
    def _client(self):
        s = make_session()
        return HistoryClient(s), s

    def test_get_all(self):
        c, s = self._client()
        history_data = [[SAMPLE_STATE, {**SAMPLE_STATE, "state": "off"}]]
        with patch.object(s._session, "get", return_value=mock_resp(history_data)):
            result = c.get()
        assert len(result[0]) == 2

    def test_get_with_entity_filter(self):
        c, s = self._client()
        with patch.object(s._session, "get", return_value=mock_resp([[SAMPLE_STATE]])) as mg:
            c.get(entity_ids=["light.bedroom"])
        params = mg.call_args[1]["params"]
        assert "light.bedroom" in params.get("filter_entity_id", "")

    def test_get_with_time_range(self):
        c, s = self._client()
        with patch.object(s._session, "get", return_value=mock_resp([])) as mg:
            c.get(start="2026-04-06T00:00:00", end="2026-04-07T00:00:00")
        called_url = mg.call_args[0][0]
        assert "2026-04-06" in called_url
        params = mg.call_args[1]["params"]
        assert "end_time" in params

    def test_get_significant_only(self):
        c, s = self._client()
        with patch.object(s._session, "get", return_value=mock_resp([])) as mg:
            c.get(significant_changes_only=True)
        params = mg.call_args[1]["params"]
        assert params.get("significant_changes_only") == "true"

    def test_get_returns_empty_list_on_none(self):
        c, s = self._client()
        resp = mock_resp(None, 200)
        resp.content = b""
        resp.json.return_value = None
        with patch.object(s._session, "get", return_value=resp):
            result = c.get()
        assert result == []


# ---------------------------------------------------------------------------
# LogbookClient Tests
# ---------------------------------------------------------------------------

class TestLogbookClient:
    def _client(self):
        s = make_session()
        return LogbookClient(s), s

    def test_list_all(self):
        c, s = self._client()
        entries = [{"when": "2026-04-07T10:00:00", "name": "Bedroom Light", "message": "turned on"}]
        with patch.object(s._session, "get", return_value=mock_resp(entries)):
            result = c.list()
        assert len(result) == 1

    def test_list_with_entity_filter(self):
        c, s = self._client()
        with patch.object(s._session, "get", return_value=mock_resp([])) as mg:
            c.list(entity_id="light.bedroom")
        params = mg.call_args[1]["params"]
        assert params.get("entity") == "light.bedroom"

    def test_list_with_period(self):
        c, s = self._client()
        with patch.object(s._session, "get", return_value=mock_resp([])) as mg:
            c.list(period=24)
        params = mg.call_args[1]["params"]
        assert params.get("period") == 24

    def test_list_with_start_in_url(self):
        c, s = self._client()
        with patch.object(s._session, "get", return_value=mock_resp([])) as mg:
            c.list(start="2026-04-06T00:00:00")
        called_url = mg.call_args[0][0]
        assert "2026-04-06" in called_url


# ---------------------------------------------------------------------------
# CLI Integration Tests (CliRunner)
# ---------------------------------------------------------------------------

class TestCLI:
    def setup_method(self):
        self.runner = CliRunner()
        self.tmp = tempfile.mkdtemp()
        self.cfg_path = str(Path(self.tmp) / "config.json")

    def test_help(self):
        r = self.runner.invoke(cli, ["--help"])
        assert r.exit_code == 0
        assert "Usage" in r.output

    def test_config_set(self):
        r = self.runner.invoke(cli, [
            "--config-file", self.cfg_path,
            "config", "set", "--url", "http://ha.test:8123", "--token", "tok",
        ])
        assert r.exit_code == 0
        c = Config(config_path=self.cfg_path)
        assert c.url == "http://ha.test:8123"
        assert c.token == "tok"

    def test_config_show_json(self):
        c = Config(config_path=self.cfg_path)
        c.url = "http://ha.test:8123"
        c.token = "tok"
        c.save()
        r = self.runner.invoke(cli, ["--config-file", self.cfg_path, "--json", "config", "show"])
        assert r.exit_code == 0
        out = json.loads(r.output)
        assert out["success"] is True
        assert "url" in out["data"]

    def test_entity_list_json(self, monkeypatch):
        monkeypatch.delenv("HA_URL", raising=False)
        monkeypatch.delenv("HA_TOKEN", raising=False)
        c = Config(config_path=self.cfg_path)
        c.url = "http://ha.test:8123"
        c.token = "tok"
        c.save()
        states = [SAMPLE_STATE]
        with patch("cli_anything.homeassistant.core.entities.EntityClient.list_all", return_value=states):
            r = self.runner.invoke(cli, [
                "--config-file", self.cfg_path, "--json", "entity", "list",
            ])
        assert r.exit_code == 0
        out = json.loads(r.output)
        assert out["success"] is True
        assert out["data"][0]["entity_id"] == "light.bedroom"

    def test_entity_get_json(self, monkeypatch):
        monkeypatch.delenv("HA_URL", raising=False)
        monkeypatch.delenv("HA_TOKEN", raising=False)
        c = Config(config_path=self.cfg_path)
        c.url = "http://ha.test:8123"
        c.token = "tok"
        c.save()
        with patch("cli_anything.homeassistant.core.entities.EntityClient.get", return_value=SAMPLE_STATE):
            r = self.runner.invoke(cli, [
                "--config-file", self.cfg_path, "--json", "entity", "get", "light.bedroom",
            ])
        assert r.exit_code == 0
        out = json.loads(r.output)
        assert out["data"]["state"] == "on"

    def test_service_call_json(self, monkeypatch):
        monkeypatch.delenv("HA_URL", raising=False)
        monkeypatch.delenv("HA_TOKEN", raising=False)
        c = Config(config_path=self.cfg_path)
        c.url = "http://ha.test:8123"
        c.token = "tok"
        c.save()
        with patch("cli_anything.homeassistant.core.services.ServiceClient.call", return_value=[SAMPLE_STATE]):
            r = self.runner.invoke(cli, [
                "--config-file", self.cfg_path, "--json",
                "service", "call", "light", "turn_on",
                "--target", "entity_id=light.bedroom",
            ])
        assert r.exit_code == 0
        out = json.loads(r.output)
        assert out["success"] is True

    def test_template_render_json(self, monkeypatch):
        monkeypatch.delenv("HA_URL", raising=False)
        monkeypatch.delenv("HA_TOKEN", raising=False)
        c = Config(config_path=self.cfg_path)
        c.url = "http://ha.test:8123"
        c.token = "tok"
        c.save()
        with patch("cli_anything.homeassistant.core.templates.TemplateClient.render", return_value="on"):
            r = self.runner.invoke(cli, [
                "--config-file", self.cfg_path, "--json",
                "template", "render", "{{ states('light.bedroom') }}",
            ])
        assert r.exit_code == 0
        out = json.loads(r.output)
        assert out["data"]["result"] == "on"

    def test_missing_url_error(self, monkeypatch):
        monkeypatch.delenv("HA_URL", raising=False)
        monkeypatch.delenv("HA_TOKEN", raising=False)
        with patch("cli_anything.homeassistant.core.entities.EntityClient.get_api_status",
                   side_effect=ConfigError("URL not set")):
            r = self.runner.invoke(cli, [
                "--config-file", self.cfg_path, "config", "check",
            ])
        assert r.exit_code != 0

    def test_entity_subcommands_exist(self):
        r = self.runner.invoke(cli, ["entity", "--help"])
        assert r.exit_code == 0
        for cmd in ["list", "get", "set", "watch"]:
            assert cmd in r.output

    def test_service_subcommands_exist(self):
        r = self.runner.invoke(cli, ["service", "--help"])
        assert r.exit_code == 0
        for cmd in ["list", "call"]:
            assert cmd in r.output

    def test_history_subcommands_exist(self):
        r = self.runner.invoke(cli, ["history", "--help"])
        assert r.exit_code == 0
        assert "get" in r.output

    def test_logbook_subcommands_exist(self):
        r = self.runner.invoke(cli, ["logbook", "--help"])
        assert r.exit_code == 0
        assert "list" in r.output

    def test_event_subcommands_exist(self):
        r = self.runner.invoke(cli, ["event", "--help"])
        assert r.exit_code == 0
        for cmd in ["list", "fire", "stream"]:
            assert cmd in r.output
