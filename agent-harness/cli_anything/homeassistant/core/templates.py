"""Template rendering for Home Assistant REST API."""

from cli_anything.homeassistant.core.session import HASession


class TemplateClient:
    def __init__(self, session: HASession):
        self.session = session

    def render(self, template: str, variables: dict = None) -> str:
        """POST /api/template — render a Jinja2 template (admin only)."""
        payload = {"template": template}
        if variables:
            payload["variables"] = variables
        result = self.session.post("template", json=payload)
        # HA returns rendered text as a plain string in the response body
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            return result.get("result", str(result))
        return str(result) if result is not None else ""
