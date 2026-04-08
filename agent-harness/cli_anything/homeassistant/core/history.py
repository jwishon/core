"""History and logbook queries for Home Assistant REST API."""

from cli_anything.homeassistant.core.session import HASession


class HistoryClient:
    def __init__(self, session: HASession):
        self.session = session

    def get(self, entity_ids: list[str] = None,
            start: str = None, end: str = None,
            significant_changes_only: bool = False,
            minimal_response: bool = True) -> list:
        """GET /api/history/period[/{start_time}]

        Returns list of lists (one per entity_id), each containing state dicts.
        entity_ids: list of entity IDs to query (None = all)
        start: ISO 8601 start datetime string (None = 24h ago)
        end: ISO 8601 end datetime string (None = now)
        """
        path = f"history/period/{start}" if start else "history/period"
        params = {}
        if entity_ids:
            params["filter_entity_id"] = ",".join(entity_ids)
        if end:
            params["end_time"] = end
        if significant_changes_only:
            params["significant_changes_only"] = "true"
        if minimal_response:
            params["minimal_response"] = "true"
        return self.session.get(path, params=params) or []


class LogbookClient:
    def __init__(self, session: HASession):
        self.session = session

    def list(self, entity_id: str = None,
             start: str = None, end: str = None,
             period: int = None) -> list:
        """GET /api/logbook[/{start_time}]

        Returns list of logbook entry dicts.
        entity_id: filter to single entity
        start: ISO 8601 start datetime
        end: ISO 8601 end datetime
        period: hours to look back (default 1 in HA)
        """
        path = f"logbook/{start}" if start else "logbook"
        params = {}
        if entity_id:
            params["entity"] = entity_id
        if end:
            params["end_time"] = end
        if period is not None:
            params["period"] = period
        return self.session.get(path, params=params) or []
