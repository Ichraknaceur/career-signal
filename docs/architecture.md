# Architecture Cible

## Vision

Le projet devient un "job search operating system" pour un profil IA / Data.

## Couches

1. `app/`
   Adapters runtime : UI Streamlit, workers, CLI.
2. `domain/`
   Regles metier pures, statuts, entites, use cases.
3. `services/`
   Adaptateurs externes : LinkedIn, Medium, RSS, LLM.
4. `storage/`
   SQLite, migrations, repositories.
5. `observability/`
   Logs structures, workflow runs, events.

## Domaines metier

- `content`
- `publishing`
- `networking`
- `jobs`
- `watch`

## Principes

- la logique ne vit plus dans Streamlit
- les workers sont idempotents
- tous les traitements ont un `run_id`
- toute action sensible laisse une trace persistante
- SQLite est la source de verite, JSON devient transitoire ou legacy
