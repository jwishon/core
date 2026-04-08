---
name: cli-anything-homeassistant
description: CLI harness for Home Assistant — controls entities, calls services, fires events, renders templates, queries history and logbook via the HA REST API
version: 0.1.0
install: pip install -e path/to/core/agent-harness
binary: cli-anything-homeassistant
requires:
  - HA_URL: Base URL of your HA instance (e.g. http://homeassistant.local:8123)
  - HA_TOKEN: Long-lived access token (Profile → Long-lived access tokens)
---

# cli-anything-homeassistant

A complete CLI harness for [Home Assistant](https://www.home-assistant.io/) — the open-source home automation platform. Wraps the HA REST API (`/api/`) with an agent-friendly, stateful command-line interface.

## Setup

```bash
pip install -e path/to/core/agent-harness

# Configure
cli-anything-homeassistant config set --url http://homeassistant.local:8123 --token <token>

# Or via environment variables
export HA_URL=http://homeassistant.local:8123
export HA_TOKEN=<your_long_lived_token>

# Verify
cli-anything-homeassistant config check
```

### Generating a Token

1. In HA: click your profile avatar (bottom-left)
2. Scroll to **Long-lived access tokens** → **Create Token**
3. Copy the token (shown only once)

## Command Groups

| Group | Description |
|-------|-------------|
| `config` | Manage connection settings |
| `entity` | List/get/set entity states, watch live |
| `service` | List and call services |
| `event` | List, fire, and stream events |
| `template` | Render Jinja2 templates |
| `history` | Query state history |
| `logbook` | Query logbook entries |
| `area` | Show HA config/areas |
| `repl` | Interactive REPL session |

## Global Flags

| Flag | Description |
|------|-------------|
| `--json` | Output as JSON `{"success": true, "data": ...}` |
| `--url URL` | Override HA URL for this invocation |
| `--token TOKEN` | Override token for this invocation |
| `--config-file PATH` | Use alternate config file |

## Agent Usage Guide

### Always use `--json` for agent operations

```bash
cli-anything-homeassistant --json entity list --domain light
cli-anything-homeassistant --json entity get light.bedroom_lamp
cli-anything-homeassistant --json service call light turn_on --target entity_id=light.bedroom_lamp --param brightness=200
```

### Response structure

```json
{"success": true, "data": [...], "meta": {"count": 12}}
```

### Error structure

```json
{"success": false, "error": "Entity not found", "code": 404}
```

## Examples

### Entity Management

```bash
# List all entities
cli-anything-homeassistant entity list

# Filter by domain
cli-anything-homeassistant entity list --domain light
cli-anything-homeassistant entity list --domain climate

# Get entity details
cli-anything-homeassistant entity get light.bedroom_lamp
cli-anything-homeassistant entity get climate.living_room

# Set entity state (admin only)
cli-anything-homeassistant entity set light.bedroom_lamp --state on --attr brightness=200
cli-anything-homeassistant entity set input_boolean.vacation_mode --state on

# Watch live state changes
cli-anything-homeassistant entity watch --domain light
cli-anything-homeassistant entity watch --entity light.bedroom_lamp --entity switch.fan
```

### Service Calls

```bash
# List all services
cli-anything-homeassistant service list

# Filter by domain
cli-anything-homeassistant service list --domain light

# Turn on/off lights
cli-anything-homeassistant service call light turn_on --target entity_id=light.bedroom_lamp
cli-anything-homeassistant service call light turn_off --target entity_id=light.bedroom_lamp
cli-anything-homeassistant service call light toggle --target entity_id=light.bedroom_lamp

# Set brightness and color
cli-anything-homeassistant service call light turn_on \
  --target entity_id=light.bedroom_lamp \
  --param brightness=200 \
  --param rgb_color="255,128,0"

# Climate control
cli-anything-homeassistant service call climate set_temperature \
  --target entity_id=climate.living_room \
  --param temperature=22

cli-anything-homeassistant service call climate set_hvac_mode \
  --target entity_id=climate.living_room \
  --param hvac_mode=heat

# Media player
cli-anything-homeassistant service call media_player volume_set \
  --target entity_id=media_player.living_room \
  --param volume_level=0.5

cli-anything-homeassistant service call media_player media_play \
  --target entity_id=media_player.living_room

# Switch
cli-anything-homeassistant service call switch toggle --target entity_id=switch.fan

# Trigger automation
cli-anything-homeassistant service call automation trigger \
  --target entity_id=automation.morning_routine

# Call script
cli-anything-homeassistant service call script goodnight

# Reload all
cli-anything-homeassistant service call homeassistant reload_all
```

### Events

```bash
# List event types
cli-anything-homeassistant event list

# Fire custom event
cli-anything-homeassistant event fire my_custom_event --data key=value

# Stream all events
cli-anything-homeassistant event stream

# Stream filtered events
cli-anything-homeassistant event stream --filter state_changed,my_event
```

### Templates

```bash
# Render template string
cli-anything-homeassistant template render "{{ states('light.bedroom_lamp') }}"
cli-anything-homeassistant template render "{{ state_attr('climate.living_room', 'temperature') }}"
cli-anything-homeassistant template render "{{ now().strftime('%Y-%m-%d') }}"

# Count entities in a domain
cli-anything-homeassistant template render "{{ states.light | list | length }}"

# Render from file
cli-anything-homeassistant template render --file my_template.j2
```

### History

```bash
# Get last 24h history for an entity
cli-anything-homeassistant history get light.bedroom_lamp

# Multiple entities with time range
cli-anything-homeassistant history get light.bedroom_lamp sensor.temperature \
  --start "2026-04-06T00:00:00" --end "2026-04-07T00:00:00"

# Significant changes only
cli-anything-homeassistant history get climate.living_room --significant-only
```

### Logbook

```bash
# Recent logbook entries
cli-anything-homeassistant logbook list

# Filter to specific entity, last 24h
cli-anything-homeassistant logbook list --entity light.bedroom_lamp --period 24

# With time range
cli-anything-homeassistant logbook list \
  --start "2026-04-06T00:00:00" --end "2026-04-07T00:00:00"
```

### Interactive REPL

```bash
cli-anything-homeassistant repl
ha> entity list --domain light
ha> service call light turn_on --target entity_id=light.bedroom_lamp --param brightness=255
ha> template render "{{ states('sensor.temperature') }}"
ha> exit
```

## Entity Domain Reference

| Domain | States | Key Service Calls |
|--------|--------|------------------|
| `light` | on, off | `turn_on` (brightness, rgb_color), `turn_off`, `toggle` |
| `switch` | on, off | `turn_on`, `turn_off`, `toggle` |
| `sensor` | numeric/string | read-only |
| `binary_sensor` | on, off | read-only |
| `climate` | off, heat, cool, auto | `set_temperature`, `set_hvac_mode`, `set_fan_mode` |
| `media_player` | playing, paused, idle | `media_play`, `media_pause`, `volume_set`, `select_source` |
| `cover` | open, closed | `open_cover`, `close_cover`, `set_cover_position` |
| `automation` | on, off | `trigger`, `turn_on`, `turn_off` |
| `script` | on, off | `{script_name}` |
| `input_boolean` | on, off | `turn_on`, `turn_off`, `toggle` |
| `input_number` | numeric | `set_value` |
| `input_select` | option | `select_option` |
| `person` | home, not_home | read-only |

## Error Codes

| Exit Code | Meaning |
|-----------|---------|
| 0 | Success |
| 1 | API error (HTTP 4xx/5xx) |
| 2 | Configuration error (missing URL or token) |
