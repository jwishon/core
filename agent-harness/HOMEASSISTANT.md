# Home Assistant CLI Harness — Standard Operating Procedures

## Overview

Home Assistant is an open-source home automation platform. This CLI harness wraps the Home Assistant REST API (`/api/`) to provide a stateful, agent-friendly command-line interface for managing entities, calling services, firing events, rendering templates, and querying history/logbook.

## Installation

```bash
cd core/agent-harness
pip install -e .
cli-anything-homeassistant --help
```

## Configuration

Config stored in `~/.config/cli-anything-homeassistant/config.json`.

### Initial Setup

```bash
# Set HA URL and long-lived access token
cli-anything-homeassistant config set --url http://homeassistant.local:8123 --token <your_token>

# Verify connection
cli-anything-homeassistant config check
```

### Generating a Long-Lived Access Token

1. In Home Assistant UI: click your profile (bottom-left)
2. Scroll to **Long-lived access tokens**
3. Click **Create Token**, give it a name
4. Copy the token — it won't be shown again

### Environment Variables

| Variable | Description |
|----------|-------------|
| `HA_URL` | Home Assistant base URL (e.g. `http://homeassistant.local:8123`) |
| `HA_TOKEN` | Long-lived access token |

## Authentication

All API calls use `Authorization: Bearer <token>` header.

## Command Groups

### `config` — Session Configuration

```bash
cli-anything-homeassistant config set --url <url> --token <token>
cli-anything-homeassistant config show
cli-anything-homeassistant config check
```

### `entity` — Entity State Management

```bash
# List all entities (optionally filter by domain)
cli-anything-homeassistant entity list [--domain light] [--area kitchen]

# Get a single entity state
cli-anything-homeassistant entity get light.bedroom_lamp

# Set entity state (admin only)
cli-anything-homeassistant entity set light.bedroom_lamp --state on --attr brightness=200

# Watch entity states in real time (SSE stream)
cli-anything-homeassistant entity watch [--domain light] [--entity light.bedroom_lamp]
```

### `service` — Service Calls

```bash
# List all available services
cli-anything-homeassistant service list [--domain light]

# Call a service
cli-anything-homeassistant service call light turn_on --target entity_id=light.bedroom_lamp
cli-anything-homeassistant service call light turn_on \
  --target entity_id=light.bedroom_lamp \
  --param brightness=200 --param rgb_color="255,0,0"

# Common shortcuts
cli-anything-homeassistant service call switch toggle --target entity_id=switch.fan
cli-anything-homeassistant service call climate set_temperature \
  --target entity_id=climate.living_room --param temperature=22
```

### `event` — Events

```bash
# List event types and listener counts
cli-anything-homeassistant event list

# Fire a custom event
cli-anything-homeassistant event fire my_custom_event --data key=value --data other=data

# Stream live events (SSE)
cli-anything-homeassistant event stream [--filter state_changed,my_event]
```

### `template` — Jinja2 Templates

```bash
# Render a template
cli-anything-homeassistant template render "{{ states('light.bedroom_lamp') }}"
cli-anything-homeassistant template render "{{ state_attr('climate.living_room', 'temperature') }}"
cli-anything-homeassistant template render --file my_template.j2
```

### `history` — State History

```bash
# Get history for entities over the last 24h
cli-anything-homeassistant history get light.bedroom_lamp
cli-anything-homeassistant history get light.bedroom_lamp sensor.temperature \
  --start "2026-04-06T00:00:00" --end "2026-04-07T00:00:00"
```

### `logbook` — Logbook Entries

```bash
# Get logbook entries
cli-anything-homeassistant logbook list [--entity light.bedroom_lamp] [--period 24]
cli-anything-homeassistant logbook list --start "2026-04-06T00:00:00"
```

### `area` — Area Registry

```bash
cli-anything-homeassistant area list
```

### `repl` — Interactive REPL

```bash
cli-anything-homeassistant repl
ha> entity list --domain light
ha> service call light turn_on --target entity_id=light.bedroom_lamp --param brightness=255
ha> exit
```

## Output Modes

All commands support `--json` for machine-readable output:

```bash
cli-anything-homeassistant --json entity list --domain light
cli-anything-homeassistant --json entity get light.bedroom_lamp
```

JSON success format:
```json
{"success": true, "data": {...}, "meta": {...}}
```

JSON error format:
```json
{"success": false, "error": "message", "code": 401}
```

## Common Service Patterns

### Lights
```bash
# Turn on with brightness
service call light turn_on --target entity_id=light.X --param brightness=200

# Set color
service call light turn_on --target entity_id=light.X --param rgb_color="255,128,0"

# Set color temperature
service call light turn_on --target entity_id=light.X --param color_temp_kelvin=4000
```

### Climate
```bash
service call climate set_temperature --target entity_id=climate.X --param temperature=22
service call climate set_hvac_mode --target entity_id=climate.X --param hvac_mode=heat
```

### Media Player
```bash
service call media_player volume_set --target entity_id=media_player.X --param volume_level=0.5
service call media_player media_play --target entity_id=media_player.X
```

## Entity Domains Reference

| Domain | State Values | Key Attributes |
|--------|-------------|----------------|
| `light` | on, off | brightness, rgb_color, color_temp_kelvin |
| `switch` | on, off | device_class |
| `sensor` | numeric/string | unit_of_measurement, device_class |
| `binary_sensor` | on, off | device_class |
| `climate` | off, heat, cool, heat_cool, auto | temperature, hvac_mode, hvac_action |
| `media_player` | playing, paused, idle, off | volume_level, media_title |
| `cover` | open, closed, opening, closing | current_position |
| `automation` | on, off | last_triggered |
| `script` | on, off | — |
| `person` | home, not_home | gps_accuracy, latitude, longitude |
| `input_boolean` | on, off | friendly_name |
| `input_number` | numeric | min, max, step, unit_of_measurement |
| `input_select` | option name | options |

## Error Handling

| HTTP Status | Meaning |
|-------------|---------|
| 401 | Invalid or missing token |
| 403 | Insufficient permissions |
| 404 | Entity/resource not found |
| 400 | Bad request (invalid template, bad service data) |

Exit codes: 0 = success, 1 = API error, 2 = config error.
