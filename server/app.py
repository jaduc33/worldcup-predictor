"""FastMCP server for the 2026 World Cup 1X2 predictor.

Run from the project root:
    python -m server.app                 # Streamable HTTP on 127.0.0.1:8000
or for stdio (e.g. a local MCP client):
    fastmcp run server/app.py
"""

import sys
from pathlib import Path

# Make `server` importable whether launched via `python -m server.app`,
# `fastmcp run server/app.py`, or `uv run fastmcp run server/app.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from server.core.config import MCP_HOST, MCP_PORT
from server.tools import admin, evaluate, fixtures, football, knockout, predict, ratings

mcp = FastMCP("worldcup-predictor")

for module in (ratings, fixtures, predict, evaluate, admin, football, knockout):
    module.register(mcp)


if __name__ == "__main__":
    mcp.run(transport="http", host=MCP_HOST, port=MCP_PORT)