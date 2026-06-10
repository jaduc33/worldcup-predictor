"""MCP client — thin async wrapper around FastMCP HTTP transport."""

import json
from typing import Any

from fastmcp import Client

from server.core.config import MCP_URL


class MCPClient:
    """Persistent connection to the worldcup-predictor MCP server."""

    def __init__(self, url: str = MCP_URL):
        self._client = Client(url)

    async def __aenter__(self) -> "MCPClient":
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._client.__aexit__(*args)

    async def list_tools(self) -> list[dict]:
        """Return tools in Anthropic-compatible format."""
        tools = await self._client.list_tools()
        result = []
        for t in tools:
            schema = t.inputSchema if hasattr(t, "inputSchema") else {}
            result.append({
                "name": t.name,
                "description": t.description or "",
                "input_schema": schema or {"type": "object", "properties": {}},
            })
        return result

    async def call_tool(self, name: str, arguments: dict) -> str:
        """Call an MCP tool and return its result as a JSON string."""
        raw = await self._client.call_tool(name, arguments)
        return _to_str(raw)


def _to_str(value: Any) -> str:
    """Normalise any MCP return value to a plain string."""
    if value is None:
        return "null"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    if isinstance(value, list):
        parts = []
        for item in value:
            parts.append(item.text if hasattr(item, "text") else str(item))
        return "\n".join(parts) or "null"
    if hasattr(value, "text"):
        return value.text
    return str(value)
