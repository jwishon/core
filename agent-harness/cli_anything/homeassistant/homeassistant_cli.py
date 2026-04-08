"""cli-anything-homeassistant — CLI harness for Home Assistant REST API."""

import json
import sys
import click

from cli_anything.homeassistant.utils.config import Config, ConfigError
from cli_anything.homeassistant.utils.output import OutputFormatter
from cli_anything.homeassistant.core.session import HASession, APIError
from cli_anything.homeassistant.core.entities import EntityClient
from cli_anything.homeassistant.core.services import ServiceClient
from cli_anything.homeassistant.core.events import EventClient
from cli_anything.homeassistant.core.templates import TemplateClient
from cli_anything.homeassistant.core.history import HistoryClient, LogbookClient


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

pass_ctx = click.make_pass_decorator(dict, ensure=True)


def make_session(ctx_obj: dict) -> HASession:
    return HASession(config=ctx_obj.get("config") or Config())


def fmt(ctx_obj: dict) -> OutputFormatter:
    return OutputFormatter(json_mode=ctx_obj.get("json_mode", False))


def die(err, formatter: OutputFormatter):
    if isinstance(err, APIError):
        click.echo(formatter.error(str(err), code=err.status_code), err=True)
        sys.exit(1)
    if isinstance(err, ConfigError):
        click.echo(formatter.error(str(err), code=2), err=True)
        sys.exit(2)
    raise err


# ---------------------------------------------------------------------------
# Root CLI
# ---------------------------------------------------------------------------

@click.group()
@click.option("--json", "json_mode", is_flag=True, default=False, help="Output as JSON.")
@click.option("--url", envvar="HA_URL", default=None, help="HA instance URL.")
@click.option("--token", envvar="HA_TOKEN", default=None, help="Long-lived access token.")
@click.option("--config-file", default=None, type=click.Path(), help="Alternate config file.")
@click.pass_context
def cli(ctx, json_mode, url, token, config_file):
    """cli-anything-homeassistant — Home Assistant CLI harness."""
    ctx.ensure_object(dict)
    config = Config(config_path=config_file) if config_file else Config()
    if url:
        config.url = url
    if token:
        config.token = token
    ctx.obj["config"] = config
    ctx.obj["json_mode"] = json_mode


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------

@cli.group()
def config():
    """Manage CLI configuration."""


@config.command("set")
@click.option("--url", default=None)
@click.option("--token", default=None)
@pass_ctx
def config_set(ctx, url, token):
    """Save URL and token to config file."""
    c = ctx["config"]
    if url:
        c.url = url
    if token:
        c.token = token
    c.save()
    click.echo(fmt(ctx).success({"message": "Saved.", "config": c.to_dict()}))


@config.command("show")
@pass_ctx
def config_show(ctx):
    """Show current configuration."""
    click.echo(fmt(ctx).success(ctx["config"].to_dict()))


@config.command("check")
@pass_ctx
def config_check(ctx):
    """Verify connection to Home Assistant."""
    f = fmt(ctx)
    try:
        data = EntityClient(make_session(ctx)).get_api_status()
        click.echo(f.success({"message": "Connection OK", "ha_version": data.get("ha_version", "unknown")}))
    except (APIError, ConfigError) as e:
        die(e, f)


# ---------------------------------------------------------------------------
# entity
# ---------------------------------------------------------------------------

@cli.group()
def entity():
    """Entity state management."""


@entity.command("list")
@click.option("--domain", default=None, help="Filter by domain (e.g. light, switch).")
@click.option("--area", default=None, help="Filter by area ID.")
@pass_ctx
def entity_list(ctx, domain, area):
    """List entity states."""
    f = fmt(ctx)
    try:
        session = make_session(ctx)
        client = EntityClient(session)
        if domain:
            states = client.list_by_domain(domain)
        else:
            states = client.list_all()

        if ctx["json_mode"]:
            click.echo(f.success(states, meta={"count": len(states)}))
        else:
            rows = [
                {
                    "entity_id": s.get("entity_id", ""),
                    "state": s.get("state", ""),
                    "friendly_name": (s.get("attributes") or {}).get("friendly_name", ""),
                    "last_changed": (s.get("last_changed") or "")[:19],
                }
                for s in states
            ]
            f.print_table(rows,
                          ["entity_id", "state", "friendly_name", "last_changed"],
                          ["Entity ID", "State", "Name", "Last Changed"])
    except (APIError, ConfigError) as e:
        die(e, f)


@entity.command("get")
@click.argument("entity_id")
@pass_ctx
def entity_get(ctx, entity_id):
    """Get state of a single entity."""
    f = fmt(ctx)
    try:
        data = EntityClient(make_session(ctx)).get(entity_id)
        if ctx["json_mode"]:
            click.echo(f.success(data))
        else:
            attrs = data.get("attributes", {})
            lines = [
                f"  entity_id:    {data.get('entity_id')}",
                f"  state:        {data.get('state')}",
                f"  last_changed: {data.get('last_changed', '')[:19]}",
                f"  last_updated: {data.get('last_updated', '')[:19]}",
                "",
                "  attributes:",
            ]
            for k, v in attrs.items():
                lines.append(f"    {k}: {v}")
            click.echo("\n".join(lines))
    except (APIError, ConfigError) as e:
        die(e, f)


@entity.command("set")
@click.argument("entity_id")
@click.option("--state", required=True, help="New state value.")
@click.option("--attr", multiple=True, help="Attribute as key=value (repeatable).")
@click.option("--force", is_flag=True, default=False, help="Force update even if unchanged.")
@pass_ctx
def entity_set(ctx, entity_id, state, attr, force):
    """Set entity state (admin only)."""
    f = fmt(ctx)
    try:
        attributes = {}
        for a in attr:
            k, _, v = a.partition("=")
            attributes[k.strip()] = v.strip()
        data = EntityClient(make_session(ctx)).set_state(
            entity_id, state, attributes=attributes or None, force_update=force
        )
        click.echo(f.success(data))
    except (APIError, ConfigError) as e:
        die(e, f)


@entity.command("watch")
@click.option("--domain", default=None, help="Filter by domain.")
@click.option("--entity", "entity_ids", multiple=True, help="Specific entity IDs to watch.")
@pass_ctx
def entity_watch(ctx, domain, entity_ids):
    """Stream live state_changed events (Ctrl-C to stop)."""
    f = fmt(ctx)
    try:
        filters = list(entity_ids)
        for ev in EventClient(make_session(ctx)).stream(restrict=["state_changed"]):
            new_state = ev.get("data", {}).get("new_state") or {}
            eid = new_state.get("entity_id", "")
            if domain and not eid.startswith(f"{domain}."):
                continue
            if filters and eid not in filters:
                continue
            if ctx["json_mode"]:
                print(json.dumps(ev, default=str))
            else:
                state_val = new_state.get("state", "")
                friendly = (new_state.get("attributes") or {}).get("friendly_name", "")
                print(f"{eid}  →  {state_val}  ({friendly})")
    except KeyboardInterrupt:
        pass
    except (APIError, ConfigError) as e:
        die(e, f)


# ---------------------------------------------------------------------------
# service
# ---------------------------------------------------------------------------

@cli.group()
def service():
    """Service calls."""


@service.command("list")
@click.option("--domain", default=None, help="Filter by domain.")
@pass_ctx
def service_list(ctx, domain):
    """List available services."""
    f = fmt(ctx)
    try:
        client = ServiceClient(make_session(ctx))
        services = client.list_by_domain(domain) if domain else client.list_all()
        if ctx["json_mode"]:
            click.echo(f.success(services))
        else:
            rows = []
            for svc_domain in services:
                d = svc_domain.get("domain", "")
                for name, info in (svc_domain.get("services") or {}).items():
                    rows.append({
                        "domain": d,
                        "service": name,
                        "description": (info.get("description") or "")[:60],
                    })
            f.print_table(rows, ["domain", "service", "description"], ["Domain", "Service", "Description"])
    except (APIError, ConfigError) as e:
        die(e, f)


@service.command("call")
@click.argument("domain")
@click.argument("service_name")
@click.option("--target", multiple=True,
              help="Target as key=value (entity_id=light.x, area_id=kitchen, device_id=abc).")
@click.option("--param", multiple=True, help="Service parameter as key=value.")
@click.option("--return-response", is_flag=True, default=False, help="Return service response.")
@pass_ctx
def service_call(ctx, domain, service_name, target, param, return_response):
    """Call a service.

    Examples:\n
      service call light turn_on --target entity_id=light.bedroom --param brightness=200\n
      service call climate set_temperature --target entity_id=climate.living --param temperature=22
    """
    f = fmt(ctx)
    try:
        data: dict = {}
        # Parse target keys (entity_id, area_id, device_id go into target sub-dict)
        target_keys = {"entity_id", "area_id", "device_id"}
        service_data: dict = {}
        for t in target:
            k, _, v = t.partition("=")
            k = k.strip()
            if k in target_keys:
                # HA REST API accepts entity_id directly at top level or nested
                service_data[k] = v.strip()
            else:
                service_data[k] = v.strip()
        for p in param:
            k, _, v = p.partition("=")
            k = k.strip()
            v = v.strip()
            # Try to coerce numeric values
            try:
                service_data[k] = int(v)
            except ValueError:
                try:
                    service_data[k] = float(v)
                except ValueError:
                    # Handle comma-separated lists (e.g. rgb_color=255,0,0)
                    if "," in v:
                        try:
                            service_data[k] = [int(x) for x in v.split(",")]
                        except ValueError:
                            service_data[k] = v
                    else:
                        service_data[k] = v

        result = ServiceClient(make_session(ctx)).call(
            domain, service_name, service_data=service_data, return_response=return_response
        )
        if result is None:
            click.echo(f.success({"message": f"Service {domain}.{service_name} called."}))
        else:
            click.echo(f.success(result))
    except (APIError, ConfigError) as e:
        die(e, f)


# ---------------------------------------------------------------------------
# event
# ---------------------------------------------------------------------------

@cli.group()
def event():
    """Event management."""


@event.command("list")
@pass_ctx
def event_list(ctx):
    """List event types and listener counts."""
    f = fmt(ctx)
    try:
        events = EventClient(make_session(ctx)).list_all()
        if ctx["json_mode"]:
            click.echo(f.success(events))
        else:
            rows = [{"event": e.get("event", ""), "listeners": e.get("listener_count", 0)} for e in events]
            f.print_table(rows, ["event", "listeners"], ["Event Type", "Listeners"])
    except (APIError, ConfigError) as e:
        die(e, f)


@event.command("fire")
@click.argument("event_type")
@click.option("--data", multiple=True, help="Event data as key=value.")
@pass_ctx
def event_fire(ctx, event_type, data):
    """Fire a custom event."""
    f = fmt(ctx)
    try:
        payload = {}
        for d in data:
            k, _, v = d.partition("=")
            payload[k.strip()] = v.strip()
        result = EventClient(make_session(ctx)).fire(event_type, payload)
        click.echo(f.success(result or {"message": f"Event '{event_type}' fired."}))
    except (APIError, ConfigError) as e:
        die(e, f)


@event.command("stream")
@click.option("--filter", "filters", default=None, help="Comma-separated event types to filter.")
@pass_ctx
def event_stream(ctx, filters):
    """Stream live events from Home Assistant (Ctrl-C to stop)."""
    f = fmt(ctx)
    restrict = [x.strip() for x in filters.split(",")] if filters else None
    try:
        for ev in EventClient(make_session(ctx)).stream(restrict=restrict):
            if ctx["json_mode"]:
                print(json.dumps(ev, default=str))
            else:
                etype = ev.get("event_type", ev.get("_type", "unknown"))
                edata = ev.get("data", {})
                print(f"[{etype}] {json.dumps(edata, default=str)[:120]}")
    except KeyboardInterrupt:
        pass
    except (APIError, ConfigError) as e:
        die(e, f)


# ---------------------------------------------------------------------------
# template
# ---------------------------------------------------------------------------

@cli.group()
def template():
    """Jinja2 template rendering."""


@template.command("render")
@click.argument("template_str", required=False)
@click.option("--file", "template_file", default=None, type=click.Path(exists=True),
              help="Read template from file.")
@click.option("--var", multiple=True, help="Template variable as key=value.")
@pass_ctx
def template_render(ctx, template_str, template_file, var):
    """Render a Jinja2 template.

    Examples:\n
      template render "{{ states('light.bedroom') }}"\n
      template render "{{ state_attr('climate.living_room', 'temperature') }}"
    """
    f = fmt(ctx)
    try:
        if template_file:
            with open(template_file) as fh:
                tmpl = fh.read()
        elif template_str:
            tmpl = template_str
        else:
            click.echo(f.error("Provide a template string or --file"), err=True)
            sys.exit(1)
        variables = {}
        for v in var:
            k, _, val = v.partition("=")
            variables[k.strip()] = val.strip()
        result = TemplateClient(make_session(ctx)).render(tmpl, variables=variables or None)
        if ctx["json_mode"]:
            click.echo(f.success({"result": result}))
        else:
            click.echo(result)
    except (APIError, ConfigError) as e:
        die(e, f)


# ---------------------------------------------------------------------------
# history
# ---------------------------------------------------------------------------

@cli.group()
def history():
    """State history queries."""


@history.command("get")
@click.argument("entity_ids", nargs=-1)
@click.option("--start", default=None, help="Start datetime (ISO 8601).")
@click.option("--end", default=None, help="End datetime (ISO 8601).")
@click.option("--significant-only", is_flag=True, default=False)
@pass_ctx
def history_get(ctx, entity_ids, start, end, significant_only):
    """Get state history for entities."""
    f = fmt(ctx)
    try:
        result = HistoryClient(make_session(ctx)).get(
            entity_ids=list(entity_ids) or None,
            start=start, end=end,
            significant_changes_only=significant_only,
        )
        if ctx["json_mode"]:
            click.echo(f.success(result))
        else:
            for entity_history in result:
                if not entity_history:
                    continue
                eid = entity_history[0].get("entity_id", "?") if entity_history else "?"
                click.echo(f"\n{eid} ({len(entity_history)} records):")
                for s in entity_history[:20]:
                    ts = (s.get("last_changed") or "")[:19]
                    state = s.get("state", "")
                    click.echo(f"  {ts}  {state}")
                if len(entity_history) > 20:
                    click.echo(f"  ... ({len(entity_history) - 20} more)")
    except (APIError, ConfigError) as e:
        die(e, f)


# ---------------------------------------------------------------------------
# logbook
# ---------------------------------------------------------------------------

@cli.group()
def logbook():
    """Logbook entries."""


@logbook.command("list")
@click.option("--entity", default=None, help="Filter to entity ID.")
@click.option("--start", default=None, help="Start datetime (ISO 8601).")
@click.option("--end", default=None, help="End datetime (ISO 8601).")
@click.option("--period", default=None, type=int, help="Hours to look back.")
@pass_ctx
def logbook_list(ctx, entity, start, end, period):
    """List logbook entries."""
    f = fmt(ctx)
    try:
        entries = LogbookClient(make_session(ctx)).list(
            entity_id=entity, start=start, end=end, period=period
        )
        if ctx["json_mode"]:
            click.echo(f.success(entries, meta={"count": len(entries)}))
        else:
            rows = [
                {
                    "when": (e.get("when") or "")[:19],
                    "name": e.get("name", ""),
                    "message": e.get("message", ""),
                    "entity_id": e.get("entity_id", ""),
                }
                for e in entries
            ]
            f.print_table(rows, ["when", "name", "message", "entity_id"],
                          ["When", "Name", "Message", "Entity ID"])
    except (APIError, ConfigError) as e:
        die(e, f)


# ---------------------------------------------------------------------------
# area (via config endpoint)
# ---------------------------------------------------------------------------

@cli.group()
def area():
    """Area information (read-only via config)."""


@area.command("list")
@pass_ctx
def area_list(ctx):
    """Show HA config (includes location, unit system, etc.)."""
    f = fmt(ctx)
    try:
        data = EntityClient(make_session(ctx)).get_config()
        click.echo(f.success(data))
    except (APIError, ConfigError) as e:
        die(e, f)


# ---------------------------------------------------------------------------
# REPL
# ---------------------------------------------------------------------------

@cli.command("repl")
@pass_ctx
def repl(ctx):
    """Start interactive REPL session."""
    import shlex
    click.echo("cli-anything-homeassistant REPL. Type 'exit' or Ctrl-D to quit.")
    while True:
        try:
            line = input("ha> ").strip()
        except (EOFError, KeyboardInterrupt):
            click.echo("\nBye!")
            break
        if not line:
            continue
        if line in ("exit", "quit"):
            click.echo("Bye!")
            break
        try:
            args = shlex.split(line)
            if ctx.get("json_mode") and "--json" not in args:
                args = ["--json"] + args
            cli.main(args=args, standalone_mode=False, obj=dict(ctx))
        except SystemExit:
            pass
        except Exception as e:
            click.echo(f"Error: {e}", err=True)


def main():
    cli()


if __name__ == "__main__":
    main()
