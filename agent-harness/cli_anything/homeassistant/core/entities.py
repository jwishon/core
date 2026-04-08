"""Entity state operations for Home Assistant REST API."""

from cli_anything.homeassistant.core.session import HASession


class EntityClient:
    def __init__(self, session: HASession):
        self.session = session

    def list_all(self) -> list:
        """GET /api/states — all entity states."""
        return self.session.get("states") or []

    def list_by_domain(self, domain: str) -> list:
        """Filter states by domain prefix."""
        states = self.list_all()
        return [s for s in states if s.get("entity_id", "").startswith(f"{domain}.")]

    def list_by_area(self, area_id: str, area_map: dict) -> list:
        """Filter states to entities in a given area (requires area_map entity_id->area_id)."""
        states = self.list_all()
        return [s for s in states if area_map.get(s.get("entity_id")) == area_id]

    def get(self, entity_id: str) -> dict:
        """GET /api/states/{entity_id}"""
        return self.session.get(f"states/{entity_id}")

    def set_state(self, entity_id: str, state: str, attributes: dict = None, force_update: bool = False) -> dict:
        """POST /api/states/{entity_id} — set/create state (admin only)."""
        payload = {"state": state, "force_update": force_update}
        if attributes:
            payload["attributes"] = attributes
        return self.session.post(f"states/{entity_id}", json=payload)

    def delete(self, entity_id: str) -> None:
        """DELETE /api/states/{entity_id} (admin only)."""
        self.session.delete(f"states/{entity_id}")

    def get_config(self) -> dict:
        """GET /api/config"""
        return self.session.get("config")

    def get_error_log(self) -> str:
        """GET /api/error_log (admin only)."""
        return self.session.get("error_log")

    def get_api_status(self) -> dict:
        """GET /api/ — basic status check."""
        return self.session.get("")

    def get_core_state(self) -> dict:
        """GET /api/core/state"""
        return self.session.get("core/state")
