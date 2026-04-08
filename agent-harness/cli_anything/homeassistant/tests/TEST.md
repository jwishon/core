# cli-anything-homeassistant Test Plan

## Test Suites

### 1. Unit Tests (`test_core.py`) — no live HA needed

#### Config
- `test_defaults_empty` — empty config when no file/env
- `test_save_and_reload` — persists to disk correctly
- `test_env_override` — HA_URL / HA_TOKEN env vars override file
- `test_api_base` — correct URL construction
- `test_api_base_no_url_raises` — ConfigError when URL missing
- `test_auth_headers` — Bearer token header
- `test_auth_headers_no_token_raises` — ConfigError when token missing
- `test_url_strips_slash` — trailing slash removed
- `test_to_dict_masks_token` — token shows as `***`

#### OutputFormatter
- `test_json_success_dict/list/meta` — JSON wrapping
- `test_json_error` — error format with code
- `test_human_dict/list/error` — readable text output
- `test_table_empty/renders/json_mode` — table rendering

#### HASession
- `test_get_success/404/401` — HTTP methods and error raising
- `test_post_success/empty_response` — POST handling
- `test_delete_success` — DELETE no error
- `test_error_message_from_json` — extracts message from body

#### EntityClient
- `test_list_all/by_domain` — state listing and filtering
- `test_get` — single entity
- `test_set_state` — POST with state and attributes
- `test_delete` — DELETE entity
- `test_get_config/api_status/core_state` — meta endpoints

#### ServiceClient
- `test_list_all/by_domain` — service listing
- `test_call_returns_states` — service call with data
- `test_call_empty_response` — None result
- `test_call_with_return_response` — query param set

#### EventClient
- `test_list_all` — event types
- `test_fire/fire_no_data` — event firing

#### TemplateClient
- `test_render_returns_string` — string response
- `test_render_with_variables` — variables passed
- `test_render_dict_response` — dict result coerced to string

#### HistoryClient
- `test_get_all/with_entity_filter/with_time_range/significant_only` — query params
- `test_get_returns_empty_list_on_none` — safe None handling

#### LogbookClient
- `test_list_all/with_entity_filter/with_period/with_start_in_url` — queries

#### CLI (CliRunner)
- `test_help` — CLI starts correctly
- `test_config_set` — saves to file
- `test_config_show_json` — JSON output
- `test_entity_list/get_json` — entity commands
- `test_service_call_json` — service call
- `test_template_render_json` — template render
- `test_missing_url_error` — config error handling
- `test_*_subcommands_exist` — all groups have expected subcommands

### 2. Subprocess Tests (`test_full_e2e.py::TestCLISubprocess`)

- `test_help` — binary responds to `--help`
- `test_config_show_json` — returns valid JSON
- `test_entity/service/event/template/history/logbook/repl_help` — all groups accessible
- `test_json_error_no_url` — error exits non-zero

### 3. Live E2E Tests (require `HA_URL` + `HA_TOKEN`)

- `TestLiveEntities` — list, get, config, status
- `TestLiveServices` — list services, call check_config
- `TestLiveTemplates` — render arithmetic, render now()
- `TestLiveEvents` — list events, fire custom event

---

## Test Results

**Run date:** 2026-04-07
**Platform:** Windows 11, Python 3.14.3, pytest 9.0.3

| Suite | Passed | Skipped | Failed |
|-------|--------|---------|--------|
| Unit tests (`test_core.py`) | 67 | 0 | 0 |
| Subprocess E2E (`TestCLISubprocess`) | 10 | 0 | 0 |
| Live E2E (require `HA_URL`+`HA_TOKEN`) | 0 | 10 | 0 |
| **Total** | **77** | **10** | **0** |

**Pass rate: 100% (of runnable tests)**

Live E2E tests skipped — set `HA_URL` and `HA_TOKEN` to run them:

```bash
HA_URL=http://homeassistant.local:8123 HA_TOKEN=<token> pytest cli_anything/homeassistant/tests/test_full_e2e.py
```
