"""Interactive CLI for the World Cup 2026 prediction agent.

Usage:
    uv run python -m agent.cli
    # or with a custom MCP server URL:
    MCP_URL=http://127.0.0.1:8000 uv run python -m agent.cli
"""

import asyncio
import os
import sys

from agent.analyst import WorldCupAgent
from server.core.config import MCP_URL

BANNER = """
╔══════════════════════════════════════════════════════╗
║   PRONOSTIQUEUR IA  —  Coupe du Monde 2026          ║
║   Tapez votre question en français.                 ║
║   Commandes : 'exit' pour quitter, 'help' pour aide ║
╚══════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
Exemples de questions :
  → Qui va gagner le match Brésil vs Argentine ?
  → Donne-moi les pronostics du groupe A complet.
  → Quel est le rating Elo de la France ?
  → Enregistre un pronostic pour France vs Espagne.
  → Montre-moi la précision de mes prédictions.
  → Quelle équipe a le plus de chances de gagner le groupe C ?
"""


async def _run(agent: WorldCupAgent, question: str) -> None:
    print("\nAnalyse en cours...\n")
    try:
        answer = await agent.run(question)
        print(answer)
    except Exception as exc:
        print(f"[Erreur] {exc}", file=sys.stderr)
        if "ANTHROPIC_API_KEY" not in os.environ:
            print(
                "[Info] La variable ANTHROPIC_API_KEY n'est pas définie.",
                file=sys.stderr,
            )


def main() -> None:
    if "ANTHROPIC_API_KEY" not in os.environ:
        print(
            "ANTHROPIC_API_KEY non définie. Exportez-la avant de lancer le CLI.",
            file=sys.stderr,
        )
        sys.exit(1)

    agent = WorldCupAgent(mcp_url=MCP_URL)

    print(BANNER)

    while True:
        try:
            user_input = input("\n> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAu revoir !")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            print("Au revoir !")
            break
        if user_input.lower() == "help":
            print(HELP_TEXT)
            continue

        asyncio.run(_run(agent, user_input))


if __name__ == "__main__":
    main()
