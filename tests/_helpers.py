"""Shared test helpers (not collected by pytest -- no test_*/​*_test name)."""

import asyncio

from fastmcp import Client


def call_tool(mcp_app, name: str, arguments: dict | None = None):
    """Call an MCP tool on an in-memory FastMCP app and return its parsed result."""

    async def _run():
        async with Client(mcp_app) as client:
            result = await client.call_tool(name, arguments or {})
            return result.data

    return asyncio.run(_run())
