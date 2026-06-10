"""MCP tools: real schedule, live scores, head-to-head, injuries (API-Football).

Schedule/live tools fetch fixtures *globally* (not filtered by league/season —
see server/core/football_api.py for why) and keep only World Cup 2026 matches.
"""

from datetime import datetime, timezone

from server.core import data, football_api as api


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _is_world_cup(fx: dict) -> bool:
    return fx["league"]["id"] == api.WORLD_CUP_LEAGUE_ID


def register(mcp):
    @mcp.tool
    def get_match_schedule(date: str | None = None, group: str | None = None) -> dict:
        """Return World Cup 2026 fixtures for a given date (YYYY-MM-DD, default today).

        Note: the underlying API only allows dates within ~1 day of today on the
        free plan. Pass a group letter (A-L) to filter to that group's matches.
        """
        target = date or _today()
        try:
            raw = api.fixtures_on_date(target)
        except api.APIFootballError as exc:
            return {"error": str(exc)}

        wc = [fx for fx in raw if _is_world_cup(fx)]
        simplified = [api.simplify_fixture(fx) for fx in wc]

        if group:
            g = group.upper()
            teams = set(data.load_groups().get(g, []))
            if not teams:
                return {"error": f"Unknown group '{group}'. Use A-L."}
            simplified = [f for f in simplified if f["home"] in teams or f["away"] in teams]

        return {"date": target, "count": len(simplified), "fixtures": simplified}

    @mcp.tool
    def get_live_scores() -> dict:
        """Return currently in-play World Cup 2026 matches with live scores."""
        try:
            raw = api.live_fixtures()
        except api.APIFootballError as exc:
            return {"error": str(exc)}

        wc = [fx for fx in raw if _is_world_cup(fx)]
        return {"count": len(wc), "matches": [api.simplify_fixture(fx) for fx in wc]}

    @mcp.tool
    def get_head_to_head(team_a: str, team_b: str, last: int = 5) -> dict:
        """Return the last `last` meetings between two national teams (any competition)."""
        try:
            raw = api.head_to_head(team_a, team_b)
        except api.APIFootballError as exc:
            return {"error": str(exc)}

        raw_sorted = sorted(raw, key=lambda fx: fx["fixture"]["date"], reverse=True)
        return {
            "team_a": team_a,
            "team_b": team_b,
            "matches": [api.simplify_fixture(fx) for fx in raw_sorted[:last]],
        }

    @mcp.tool
    def get_team_news(team: str, date: str | None = None) -> dict:
        """Return the injury list for a national team on a given date (default today)."""
        target = date or _today()
        try:
            raw = api.injuries(team, target)
        except api.APIFootballError as exc:
            return {"error": str(exc)}

        players = [
            {
                "player": item["player"]["name"],
                "type": item["player"]["type"],
                "reason": item["player"]["reason"],
            }
            for item in raw
        ]
        return {"team": team, "date": target, "injuries": players}
