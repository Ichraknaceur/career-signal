"""
Configuration centralisée du système multi-agent.
Chargée depuis les variables d'environnement via python-dotenv.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class ModelConfig:
    """
    Modèles par provider et par rôle.
    Le provider actif est déterminé par LLM_PROVIDER dans .env ou l'UI.
    """

    # Anthropic
    anthropic_orchestrator: str = "claude-opus-4-6"
    anthropic_agent: str = "claude-sonnet-4-6"

    # OpenAI
    openai_orchestrator: str = "gpt-4o"
    openai_agent: str = "gpt-4o-mini"

    max_tokens: int = 4096

    def orchestrator(self, provider: str = "anthropic") -> str:
        return self.openai_orchestrator if provider == "openai" else self.anthropic_orchestrator

    def agent(self, provider: str = "anthropic") -> str:
        return self.openai_agent if provider == "openai" else self.anthropic_agent


@dataclass(frozen=True)
class AgentConfig:
    """Limites et comportements des agents."""

    max_iterations: int = 10  # Nombre max de tours dans l'agentic loop
    max_subagent_calls: int = 5  # Nombre max d'appels à des sous-agents
    timeout_seconds: int = 120  # Timeout par appel LLM


@dataclass
class Settings:
    """Point d'entrée unique pour toute la configuration."""

    # Clés API — validées uniquement dans get_provider() au moment de l'appel réel
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))

    # Provider actif — peut être surchargé par l'UI (os.environ["LLM_PROVIDER"])
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "anthropic"))

    model: ModelConfig = field(default_factory=ModelConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


def _require_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise OSError(
            f"Variable d'environnement requise manquante : '{key}'. "
            f"Copie .env.example vers .env et remplis les valeurs."
        )
    return value


# Singleton — importé partout dans le projet
settings = Settings()
