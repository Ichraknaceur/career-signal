# ─────────────────────────────────────────────────────────────────
# CareerSignal — Dockerfile
# ─────────────────────────────────────────────────────────────────

FROM python:3.11-slim AS base

LABEL maintainer="ichraknaceurr@gmail.com"
LABEL description="CareerSignal — personal branding, networking and job search platform"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_NO_CACHE=1 \
    DATABASE_PATH=/app/data/app.db \
    LOG_DIR=/app/logs \
    # Playwright stocke Chromium ici (chemin fixe dans le container)
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# ── Dépendances système + Playwright deps en UNE seule couche ───
# Tout dans le même RUN pour que rm -rf /var/cache/apt soit dans
# la même couche → la taille finale de l'image est beaucoup plus petite.
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Libs Chromium (Playwright)
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libxshmfence1 \
    # Libs supplémentaires requises par playwright install-deps
    libx11-6 libx11-xcb1 libxcb1 libxext6 libxfixes3 \
    libxi6 libxrender1 libxss1 libxtst6 \
    fonts-liberation fonts-noto-color-emoji \
    # Utilitaires
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# ── Installer uv ────────────────────────────────────────────────
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# ── Dépendances Python ──────────────────────────────────────────
COPY pyproject.toml uv.lock* ./
RUN uv sync --extra phase1 --no-dev

# ── Playwright : Chromium seulement, sans install-deps ──────────
# Les dépendances système sont déjà installées ci-dessus.
# On skippe install-deps (qui re-appelle apt et sature le cache)
# et on nettoie immédiatement après le download.
RUN uv run playwright install chromium \
    && find /ms-playwright -name "*.zip" -delete 2>/dev/null || true

# ── Code source ─────────────────────────────────────────────────
COPY . .

# ── Port Streamlit ──────────────────────────────────────────────
EXPOSE 8501

# ── Healthcheck ─────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# ── Entrypoints ─────────────────────────────────────────────────
COPY docker/entrypoints /entrypoints
RUN chmod +x /entrypoints/*.sh

ENTRYPOINT ["/entrypoints/app.sh"]
