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
    elo.py               # cœur de prédiction : Elo + Poisson -> probas 1N2 / scores exacts
    config.py            # paramètres réglables (env-var overridable)
    data.py              # groupes, hôtes, ratings, historique des matchs
    form.py              # ajustement de forme récente (vs attendu Elo)
    ratings_effective.py # rating/avantage effectifs (Elo + forme + bonus hôte)
    h2h.py               # mélange des probas 1N2 avec l'historique des confrontations
    standings.py         # projection des classements de poule (valeurs attendues)
    simulation.py        # simulation Monte Carlo des poules (probas de qualif réelles)
    bracket.py           # résolution du tableau des 16es de finale
    football_api.py      # client API-Football (calendrier, scores live, H2H, blessures)
    cache.py             # cache JSON avec TTL pour API-Football
    fetch.py             # ratings live depuis eloratings.net
  tools/                  # outils MCP, séparés par fonctionnalité
    ratings.py            # list_teams, get_team_rating
    fixtures.py           # get_group, get_group_fixtures
    predict.py            # predict_match, predict_group
    knockout.py           # simulate_group_stage, simulate_all_groups,
                           # simulate_groups_monte_carlo, predict_knockout_match,
                           # simulate_round_of_32, simulate_tournament
    football.py           # get_match_schedule, get_live_scores, get_head_to_head, get_team_news
    admin.py              # refresh_ratings, update_match_result, get_tournament_status
    evaluate.py           # record_prediction, record_result, get_accuracy
  app.py                  # instancie FastMCP et monte les outils
data/
  groups.json           # les 12 groupes définitifs + hôtes (USA/Canada/Mexique)
  elo_ratings.json      # ratings SEED -> à remplacer par du live (eloratings.net)
  match_history.json    # historique des matchs joués (alimente form.py)
  predictions.json      # journal des prédictions (record_prediction / get_accuracy)
  cache/                # cache TTL des réponses API-Football
```

## Lancer

```bash
uv sync
uv run python -m server.app        # Streamable HTTP sur 127.0.0.1:8000
# ou, en stdio pour un client MCP local :
uv run fastmcp run server/app.py
```

## Modèle amélioré

En plus du cœur Elo + Poisson (`elo.py`), le modèle combine quatre ajustements,
actifs par défaut et réglables via variables d'environnement
(voir `server/core/config.py`) :

1. **Forme récente** (`form.py`) — sur les `FORM_WINDOW` derniers matchs
   (défaut `4`) d'une équipe enregistrés via `update_match_result`, calcule un
   score de sur/sous-performance vs l'attendu Elo (points + différence de buts),
   le multiplie par `FORM_WEIGHT` (défaut `8.0`) et plafonne l'ajustement à
   `±FORM_MAX_ADJUSTMENT` (défaut `40.0`) points Elo. Vaut `0` tant qu'une
   équipe a moins de 2 matchs enregistrés (le cas de toutes les équipes avant
   le tournoi).
2. **Avantage pays hôte** (`ratings_effective.host_bonus`) — bonus Elo de
   `HOST_ADV` (défaut `60.0`) pour les USA, le Canada et le Mexique
   (`groups.json["hosts"]`), appliqué via `effective_advantage` quel que soit
   le label home/away du fixture, en phase de groupes comme en phase à
   élimination directe.
3. **Confrontations directes (H2H)** (`h2h.py`) — `predict_match(...,
   use_h2h=True)` et `predict_knockout_match(..., use_h2h=True)` mélangent les
   probas Elo avec les taux victoire/nul/défaite pondérés par récence
   (`H2H_DECAY`, défaut `0.85`) des `H2H_MAX_MATCHES` (défaut `10`) dernières
   confrontations, à hauteur de `H2H_WEIGHT` (défaut `0.15`), si au moins
   `H2H_MIN_MATCHES` (défaut `3`) confrontations exploitables existent. Repli
   silencieux sur l'Elo pur si `API_FOOTBALL_KEY` est absent ou en cas d'erreur
   API. `predict_group` n'utilise jamais le H2H (dépasserait le quota gratuit).
4. **Simulation Monte Carlo des poules** (`simulation.py`,
   `simulate_groups_monte_carlo`) — simule `MONTE_CARLO_ITERATIONS` (défaut
   `2000`) tirages des 6 matchs de chaque groupe (scores Poisson), classe selon
   les critères officiels (points, diff. de buts, buts marqués -- égalités
   totales départagées aléatoirement), et retourne par équipe `p_first`...
   `p_fourth`, `p_qualify_top2`, `p_qualify_best_third`, `p_qualify`. Complète
   (sans remplacer) `simulate_all_groups`, qui reste la projection rapide et
   déterministe par valeurs attendues.

`effective_rating` (Elo + forme) et `effective_advantage` (avantage hôte) sont
utilisés par tous les points de prédiction : `predict.py`, `standings.py`,
`knockout.py` et `evaluate.py`.

## Évaluation

Chaque prédiction est loggée puis soldée contre le vrai résultat. `get_accuracy`
calcule le **RPS** (métrique standard du foot, respecte l'ordre V > N > D), le
Brier, la log-loss et le hit-rate. C'est ce qui permet de **calibrer** `DRAW_BASE`,
`HOST_ADV`, `FORM_WEIGHT` et `H2H_WEIGHT` sur les vrais matchs au fil du
tournoi.

## Étapes suivantes

1. Calibrer `DRAW_BASE`, `HOST_ADV`, `FORM_WEIGHT` et `H2H_WEIGHT` sur les
   premiers résultats réels via `get_accuracy`.
2. Ajouter la couche agent (client MCP + Claude) qui orchestre + explique.
3. Tableau officiel complet d'attribution des meilleurs 3es de poule (la
   recherche par backtracking de `bracket.assign_third_placed` trouve une
   affectation valide mais pas forcément celle de la table FIFA, voir
   `bracket.ASSIGNMENT_NOTE`).
