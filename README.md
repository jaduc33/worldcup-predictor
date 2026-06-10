# worldcup-predictor

Serveur **MCP** de prédictions 1N2 pour la Coupe du Monde 2026, construit sur
FastMCP (Streamable HTTP) — même philosophie que le Travel Planner.

L'idée n'est pas qu'un LLM « devine » les résultats (mal calibré), mais qu'un
**agent orchestre** : il interroge un cœur statistique via des outils MCP, puis
contextualise et explique. Le modèle est volontairement simple et **remplaçable**.

## Architecture

```
server/
  core/
    elo.py        # cœur de prédiction : Elo -> probas 1N2 (paramètres réglables)
    data.py       # chargement groupes + ratings
  tools/          # outils MCP, séparés par fonctionnalité
    ratings.py    # list_teams, get_team_rating
    fixtures.py   # get_group, get_group_fixtures
    predict.py    # predict_match, predict_group
    evaluate.py   # record_prediction, record_result, get_accuracy
  app.py          # instancie FastMCP et monte les outils
data/
  groups.json     # les 12 groupes définitifs (tirage + barrages résolus)
  elo_ratings.json# ratings SEED -> à remplacer par du live (eloratings.net)
```

## Lancer

```bash
uv sync
uv run python -m server.app        # Streamable HTTP sur 127.0.0.1:8000
# ou, en stdio pour un client MCP local :
uv run fastmcp run server/app.py
```

## Évaluation

Chaque prédiction est loggée puis soldée contre le vrai résultat. `get_accuracy`
calcule le **RPS** (métrique standard du foot, respecte l'ordre V > N > D), le
Brier, la log-loss et le hit-rate. C'est ce qui permet de **calibrer** `DRAW_BASE`
sur les vrais matchs de poule au fil du tournoi.

## Étapes suivantes

1. Brancher les ratings live (outil qui fetch eloratings.net via httpx).
2. Ajouter la couche agent (client MCP + Claude) qui orchestre + explique.
3. Enrichir le qualitatif (blessures, compos) via un outil `get_news`.
4. Mettre à jour les ratings après chaque match (K-factor Elo).
