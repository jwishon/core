"""Service call operations for Home Assistant REST API."""

from cli_anything.homeassistant.core.session import HASession


class ServiceClient:
    def __init__(self, session: HASession):
        self.session = session

    def list_all(self) -> list:
        """GET /api/services — all registered services."""
        return self.session.get("services") or []

    def list_by_domain(self, domain: str) -> list:
        """Filter services to a single domain."""
        all_services = self.list_all()
        return [s for s in all_services if s.get("domain") == domain]

    def call(self, domain: str, service: str, service_data: dict = None,
             return_response: bool = False) -> list | dict | None:
        """POST /api/services/{domain}/{service}

        service_data may contain special keys:
          - entity_id / area_id / device_id  → targeting
          - everything else → service parameters
        """
        payload = service_data or {}
        params = {"return_response": "true"} if return_response else None
        result = self.session.post(f"services/{domain}/{service}", json=payload, params=params)
        return result
