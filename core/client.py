"""
Factory de providers LLM.

Usage :
    from core.client import get_provider

    provider = get_provider()           # Lit LLM_PROVIDER dans l'env (défaut: anthropic)
    provider = get_provider("openai")   # Force OpenAI

Providers disponibles : "anthropic" | "openai"
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache

from core.providers.base import LLMProvider

logger = logging.getLogger(__name__)

SUPPORTED_PROVIDERS = ("anthropic", "openai")


@lru_cache(maxsize=4)
def get_provider(provider_name: str | None = None) -> LLMProvider:
    """
    Retourne une instance mise en cache du provider LLM demandé.

    Le provider est déterminé dans l'ordre suivant :
      1. Argument `provider_name` explicite
      2. Variable d'environnement `LLM_PROVIDER`
      3. Défaut : "anthropic"

    Raises:
        EnvironmentError : si la clé API du provider est absente
        ValueError       : si le provider n'est pas supporté
    """
    raw_name = (
        provider_name if provider_name is not None else os.getenv("LLM_PROVIDER") or "anthropic"
    )
    name = raw_name.lower().strip()

    if name not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Provider '{name}' non supporté. Choix : {SUPPORTED_PROVIDERS}")

    logger.info(f"[LLM] Provider actif : {name}")

    if name == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise OSError("ANTHROPIC_API_KEY manquante. Renseigne-la dans .env")
        from core.providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider(api_key=api_key)

    if name == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise OSError("OPENAI_API_KEY manquante. Renseigne-la dans .env")
        from core.providers.openai_provider import OpenAIProvider

        return OpenAIProvider(api_key=api_key)

    raise ValueError(f"Provider inconnu : {name}")  # unreachable


def clear_provider_cache() -> None:
    """Vide le cache des providers (utile quand on change de provider dans l'UI)."""
    get_provider.cache_clear()
    logger.debug("[LLM] Cache providers vidé")
