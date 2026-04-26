# ═══════════════════════════════════════════════════════════════════
# CareerSignal — Makefile
# Usage : make <commande>
# ═══════════════════════════════════════════════════════════════════

.DEFAULT_GOAL := help
.PHONY: help install dev-install sync lock ui api autopublish db-init docs tree build up up-auto down restart logs shell \
        test lint format typecheck clean prune env-check compile \
        precommit precommit-install ci

# ── Couleurs ────────────────────────────────────────────────────────
CYAN  := \033[36m
GREEN := \033[32m
YELLOW:= \033[33m
RESET := \033[0m

# ═══════════════════════════════════════════════════════════════════
# AIDE
# ═══════════════════════════════════════════════════════════════════
help:
	@echo ""
	@echo "$(CYAN)CareerSignal$(RESET)"
	@echo "─────────────────────────────────────────────"
	@echo "$(GREEN)Setup$(RESET)"
	@echo "  make install       Installe les dépendances Phase 1 (uv sync)"
	@echo "  make dev-install   Installe toutes les dépendances + outils dev"
	@echo "  make sync          Sync l'env avec uv.lock (après git pull)"
	@echo "  make lock          Regénère uv.lock"
	@echo "  make env-check     Vérifie que le .env est configuré"
	@echo ""
	@echo "$(GREEN)Développement local$(RESET)"
	@echo "  make ui            Lance l'UI Streamlit en local"
	@echo "  make api           Lance l'API FastAPI en local"
	@echo "  make autopublish   Lance le worker d'autopublication LinkedIn"
	@echo "  make db-init       Initialise la base SQLite"
	@echo "  make docs          Affiche l'index de documentation"
	@echo "  make tree          Affiche l'arborescence cible"
	@echo "  make test          Lance les tests unitaires"
	@echo "  make lint          Vérifie le style du code (ruff)"
	@echo "  make format        Formate le code (ruff)"
	@echo "  make typecheck     Vérifie les types (mypy)"
	@echo "  make compile       Vérifie la compilation Python"
	@echo ""
	@echo "$(GREEN)Docker$(RESET)"
	@echo "  make build         Build l'image Docker"
	@echo "  make up            Lance les containers (Streamlit)"
	@echo "  make up-auto       Lance l'UI + le worker d'autopublication"
	@echo "  make down          Arrête les containers"
	@echo "  make restart       Redémarre les containers"
	@echo "  make logs          Affiche les logs en temps réel"
	@echo "  make shell         Ouvre un shell dans le container app"
	@echo "  make prune         Supprime les images/volumes non utilisés"
	@echo ""
	@echo "$(GREEN)CI/CD$(RESET)"
	@echo "  make precommit        Lance tous les checks (format+lint+type+test)"
	@echo "  make precommit-install  Active les hooks git pre-commit"
	@echo "  make ci               Simule le pipeline CI complet (+ docker build)"
	@echo ""
	@echo "$(GREEN)Utilitaires$(RESET)"
	@echo "  make clean         Supprime les fichiers temporaires Python"
	@echo ""

# ═══════════════════════════════════════════════════════════════════
# SETUP
# ═══════════════════════════════════════════════════════════════════
install:
	@echo "$(CYAN)→ Installation des dépendances Phase 1 (uv)...$(RESET)"
	uv sync --extra phase1

dev-install:
	@echo "$(CYAN)→ Installation complète avec outils dev (uv)...$(RESET)"
	uv sync --all-extras
	uv run playwright install chromium

sync:
	@echo "$(CYAN)→ Synchronisation de l'environnement avec uv.lock...$(RESET)"
	uv sync
	@echo "$(GREEN)✓ Environnement à jour$(RESET)"

lock:
	@echo "$(CYAN)→ Regénération du lockfile uv.lock...$(RESET)"
	uv lock
	@echo "$(GREEN)✓ uv.lock mis à jour$(RESET)"

env-check:
	@echo "$(CYAN)→ Vérification du fichier .env...$(RESET)"
	@test -f .env || (echo "$(YELLOW)⚠️  .env absent — copie .env.example$(RESET)" && cp .env.example .env && echo "✓ .env créé, remplis ANTHROPIC_API_KEY")
	@grep -q "ANTHROPIC_API_KEY=sk-" .env && echo "$(GREEN)✓ ANTHROPIC_API_KEY configurée$(RESET)" || echo "$(YELLOW)⚠️  ANTHROPIC_API_KEY non configurée dans .env$(RESET)"

# ═══════════════════════════════════════════════════════════════════
# DÉVELOPPEMENT LOCAL
# ═══════════════════════════════════════════════════════════════════
ui: env-check
	@echo "$(CYAN)→ Lancement de l'UI Streamlit...$(RESET)"
	uv run streamlit run ui/app.py \
		--server.port=8501 \
		--server.address=localhost \
		--browser.gatherUsageStats=false

api: env-check
	@echo "$(CYAN)→ Lancement de l'API FastAPI...$(RESET)"
	uv run uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --reload

autopublish: env-check
	@echo "$(CYAN)→ Lancement du worker d'autopublication LinkedIn...$(RESET)"
	uv run python autopublish.py

db-init:
	@echo "$(CYAN)→ Initialisation de la base SQLite...$(RESET)"
	uv run python -m storage.init_db

docs:
	@echo "$(CYAN)→ Documentation disponible:$(RESET)"
	@echo "  - README.md"
	@echo "  - docs/README.md"
	@echo "  - docs/architecture.md"
	@echo "  - docs/repo-structure.md"
	@echo "  - docs/database.md"
	@echo "  - docs/devops.md"

tree:
	@sed -n '1,200p' docs/repo-structure.md

test:
	@echo "$(CYAN)→ Lancement des tests...$(RESET)"
	uv run pytest tests/ -v --tb=short

lint:
	@echo "$(CYAN)→ Vérification du code (ruff)...$(RESET)"
	uv run ruff check .

format:
	@echo "$(CYAN)→ Formatage du code (ruff)...$(RESET)"
	uv run ruff format .
	uv run ruff check . --fix

typecheck:
	@echo "$(CYAN)→ Vérification des types (mypy)...$(RESET)"
	uv run mypy agents/ app/ core/ domain/ observability/ pipelines/ services/ storage/ tools/ --ignore-missing-imports

compile:
	@echo "$(CYAN)→ Vérification compilation Python...$(RESET)"
	python3 -m compileall agents app core domain observability orchestrator pipelines services storage tools ui > /dev/null
	@echo "$(GREEN)✓ Compilation OK$(RESET)"

# ═══════════════════════════════════════════════════════════════════
# DOCKER
# ═══════════════════════════════════════════════════════════════════
build:
	@echo "$(CYAN)→ Build de l'image Docker...$(RESET)"
	docker compose build

up: env-check
	@echo "$(CYAN)→ Démarrage des containers (Phase 1+2)...$(RESET)"
	docker compose up -d
	@echo "$(GREEN)✓ UI disponible sur http://localhost:8501$(RESET)"
	@echo "$(GREEN)✓ API disponible sur http://localhost:8000/docs$(RESET)"

up-auto: env-check
	@echo "$(CYAN)→ Démarrage UI + autopublish worker...$(RESET)"
	docker compose --profile automation up -d
	@echo "$(GREEN)✓ UI disponible sur http://localhost:8501$(RESET)"
	@echo "$(GREEN)✓ API disponible sur http://localhost:8000/docs$(RESET)"

down:
	@echo "$(CYAN)→ Arrêt des containers...$(RESET)"
	docker compose down

restart:
	@echo "$(CYAN)→ Redémarrage des containers...$(RESET)"
	docker compose restart

logs:
	docker compose logs -f app api autopublish-worker

shell:
	@echo "$(CYAN)→ Ouverture d'un shell dans le container app...$(RESET)"
	docker compose exec app /bin/bash

prune:
	@echo "$(YELLOW)→ Nettoyage Docker (images + volumes non utilisés)...$(RESET)"
	docker system prune -f
	docker volume prune -f

# ═══════════════════════════════════════════════════════════════════
# CI/CD
# ═══════════════════════════════════════════════════════════════════

## Lance tous les checks dans l'ordre exact du pipeline CI
## Format → Lint → Types → Tests
## Bloque si une étape échoue (fail-fast)
precommit:
	@echo "$(CYAN)═══ Pre-commit checks ═══$(RESET)"
	@echo ""
	@echo "$(CYAN)[1/4] Format (ruff format)...$(RESET)"
	@uv run ruff format --check . || (echo "$(YELLOW)→ Lance 'make format' pour corriger$(RESET)" && exit 1)
	@echo "$(GREEN)✓ Format OK$(RESET)"
	@echo ""
	@echo "$(CYAN)[2/4] Lint (ruff check)...$(RESET)"
	@uv run ruff check . || (echo "$(YELLOW)→ Lance 'make lint' pour voir les détails$(RESET)" && exit 1)
	@echo "$(GREEN)✓ Lint OK$(RESET)"
	@echo ""
	@echo "$(CYAN)[3/4] Types (mypy)...$(RESET)"
	@uv run mypy agents/ app/ core/ domain/ observability/ pipelines/ services/ storage/ tools/ --ignore-missing-imports --no-error-summary \
		|| (echo "$(YELLOW)→ Corrige les erreurs de typage$(RESET)" && exit 1)
	@echo "$(GREEN)✓ Types OK$(RESET)"
	@echo ""
	@echo "$(CYAN)[4/4] Tests (pytest)...$(RESET)"
	@uv run pytest tests/ -v --tb=short -q || (echo "$(YELLOW)→ Des tests ont échoué$(RESET)" && exit 1)
	@python3 -m compileall agents app core domain observability orchestrator pipelines services storage tools ui > /dev/null \
		|| (echo "$(YELLOW)→ Erreur de compilation Python$(RESET)" && exit 1)
	@echo "$(GREEN)✓ Tests OK$(RESET)"
	@echo ""
	@echo "$(GREEN)═══ ✅ Tous les checks sont passés — prêt à commiter ═══$(RESET)"

## Active les hooks git pour lancer precommit automatiquement avant chaque commit
precommit-install:
	@echo "$(CYAN)→ Installation des hooks git pre-commit...$(RESET)"
	uv run pre-commit install
	@echo "$(GREEN)✓ Hooks activés — 'make precommit' sera lancé avant chaque git commit$(RESET)"

## Simule le pipeline CI complet (comme GitHub Actions)
## Inclut le docker build en plus des checks qualité
ci: precommit
	@echo ""
	@echo "$(CYAN)[5/5] Docker build check...$(RESET)"
	@docker build -t career-signal:ci-check . \
		&& echo "$(GREEN)✓ Docker build OK$(RESET)" \
		|| (echo "$(YELLOW)→ Le Dockerfile a un problème$(RESET)" && exit 1)
	@docker rmi career-signal:ci-check -f > /dev/null 2>&1
	@echo ""
	@echo "$(GREEN)═══ ✅ Pipeline CI complet validé ═══$(RESET)"

# ═══════════════════════════════════════════════════════════════════
# UTILITAIRES
# ═══════════════════════════════════════════════════════════════════
clean:
	@echo "$(CYAN)→ Nettoyage des fichiers temporaires...$(RESET)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✓ Nettoyage terminé$(RESET)"
