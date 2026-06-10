"""MCP tools: team ratings."""

from server.core import data


def register(mcp):
    @mcp.tool
    def list_teams() -> list[str]:
        """List all 48 teams competing at the 2026 World Cup."""
        return data.all_teams()

    @mcp.tool
    def get_team_rating(team: str) -> dict:
        """Return the Elo rating and group letter for a national team."""
        try:
            return {
                "team": team,
                "rating": data.rating_of(team),
                "group": data.group_of(team),
            }
        except KeyError as exc:
            return {"error": str(exc)}
