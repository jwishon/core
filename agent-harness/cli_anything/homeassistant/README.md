# cli-anything-homeassistant

A complete, agent-friendly CLI harness for [Home Assistant](https://www.home-assistant.io/).

## Installation

```bash
cd core/agent-harness
pip install -e .
```

## Quick Start

```bash
# Configure
cli-anything-homeassistant config set \
  --url http://homeassistant.local:8123 \
  --token <your_long_lived_token>

# Verify
cli-anything-homeassistant config check

# List all lights
cli-anything-homeassistant entity list --domain light

# Turn on a light
cli-anything-homeassistant service call light turn_on \
  --target entity_id=light.bedroom_lamp --param brightness=200

# Render template
cli-anything-homeassistant template render "{{ states('sensor.temperature') }}"

# JSON output (for agents)
cli-anything-homeassistant --json entity list --domain light
```

## Commands

| Command | Description |
|---------|-------------|
| `config set/show/check` | Manage configuration |
| `entity list/get/set/watch` | Entity state management |
| `service list/call` | Service calls |
| `event list/fire/stream` | Event management |
| `template render` | Jinja2 template rendering |
| `history get` | State history queries |
| `logbook list` | Logbook entries |
| `repl` | Interactive REPL |

See [skills/SKILL.md](skills/SKILL.md) for the full agent skill definition.
