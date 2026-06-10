"""MCP tools: groups and fixtures."""

from server.core import data


def register(mcp):
    @mcp.tool
    def get_group(group: str) -> dict:
        """Return the four teams in a group (A-L)."""
        groups = data.load_groups()
        g = group.upper()
        if g not in groups:
            return {"error": f"Unknown group '{group}'. Use A-L."}
        return {"group": g, "teams": groups[g]}

    @mcp.tool
    def get_group_fixtures(group: str) -> dict:
        """Return the 6 round-robin matchups for a group."""
        g = group.upper()
        if g not in data.load_groups():
            return {"error": f"Unknown group '{group}'. Use A-L."}
        return {"group": g, "fixtures": data.group_fixtures(g)}
