# Arborescence Cible Du Repo

```text
career-signal/
├── app/
│   ├── __init__.py
│   ├── ui/
│   │   └── __init__.py
│   └── workers/
│       └── __init__.py
├── domain/
│   ├── __init__.py
│   ├── content/
│   │   └── __init__.py
│   ├── publishing/
│   │   └── __init__.py
│   ├── networking/
│   │   └── __init__.py
│   ├── jobs/
│   │   └── __init__.py
│   └── watch/
│       └── __init__.py
├── services/
│   ├── __init__.py
│   ├── llm/
│   │   └── __init__.py
│   ├── linkedin/
│   │   └── __init__.py
│   ├── medium/
│   │   └── __init__.py
│   └── rss/
│       └── __init__.py
├── storage/
│   ├── __init__.py
│   ├── db.py
│   ├── init_db.py
│   ├── repositories/
│   │   └── __init__.py
│   └── migrations/
│       └── 0001_initial_schema.sql
├── observability/
│   ├── __init__.py
│   └── logging.py
├── docs/
│   ├── README.md
│   ├── architecture.md
│   ├── database.md
│   ├── devops.md
│   └── repo-structure.md
├── docker/
│   └── entrypoints/
│       ├── app.sh
│       └── worker.sh
├── tests/
│   └── storage/
│       └── test_init_db.py
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── cd.yml
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── README.md
└── pyproject.toml
```

## Raison du decoupage

- `domain` pour les decisions metier
- `services` pour les APIs et automations externes
- `storage` pour les acces aux donnees
- `app` pour les points d'entree
- `observability` pour rendre le systeme operable
