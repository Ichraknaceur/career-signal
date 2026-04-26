# DevOps, Docker Et CI/CD

## Docker

Le repo est containerise autour d'une image unique Python + Playwright.

Services principaux dans `docker-compose.yml` :

- `app`
  UI Streamlit
- `api`
  API FastAPI + Swagger
- `autopublish-worker`
  worker de publication automatique LinkedIn

Les services partagent :

- `./data:/app/data`
- `./data/logs:/app/logs`

## Base SQLite

La base par defaut est :

- `/app/data/app.db` dans Docker
- `data/app.db` en local

Initialisation :

```bash
make db-init
docker compose run --rm app uv run python -m storage.init_db
```

## API FastAPI

Lancement local :

```bash
make api
```

Puis ouvrir :

- [http://localhost:8000/docs](http://localhost:8000/docs)
- [http://localhost:8000/health](http://localhost:8000/health)

## Makefile

Le Makefile sert de facade unique pour :

- l'installation
- la base SQLite
- l'UI
- les workers
- les tests
- Docker
- la CI locale

## CI

Le workflow `ci.yml` verifie :

- format
- lint
- typage
- tests
- compilation Python
- build Docker

## CD

Le workflow `cd.yml` prepare une publication d'image GHCR sur `main` et sur les tags.
Il peut etre active avec les droits standards GitHub Packages.
