"""Agentic loop: Claude + MCP tools for World Cup 2026 predictions."""

import os
from typing import Any

import anthropic

from agent.client import MCPClient
from agent.prompts import SYSTEM_PROMPT
from server.core.config import MCP_URL

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096
MAX_TOOL_ROUNDS = 10  # safety cap against infinite loops


class WorldCupAgent:
    """Orchestrates Claude + MCP tools to answer football prediction questions."""

    def __init__(self, mcp_url: str = MCP_URL):
        self._mcp_url = mcp_url
        self._anthropic = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )

    async def run(self, user_message: str) -> str:
        """Run one complete agentic turn and return Claude's final response."""
        async with MCPClient(self._mcp_url) as mcp:
            tools = await mcp.list_tools()
            messages: list[dict] = [{"role": "user", "content": user_message}]

            for _ in range(MAX_TOOL_ROUNDS):
                response = self._anthropic.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=SYSTEM_PROMPT,
                    tools=tools,
                    messages=messages,
                )

                if response.stop_reason == "end_turn":
                    return _extract_text(response.content)

                if response.stop_reason == "tool_use":
                    # Append Claude's turn (may include text + tool_use blocks)
                    messages.append({"role": "assistant", "content": response.content})

                    # Execute every tool call in sequence and collect results
                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            result = await mcp.call_tool(block.name, block.input)
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            })

                    messages.append({"role": "user", "content": tool_results})
                else:
                    # Unexpected stop reason — return whatever text is available
                    return _extract_text(response.content)

            return "Limite de tours atteinte sans réponse finale."


def _extract_text(content: list[Any]) -> str:
    parts = [block.text for block in content if hasattr(block, "text")]
    return "\n".join(parts).strip() or "(aucune réponse textuelle)"
