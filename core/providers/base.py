"""
Interface abstraite pour les providers LLM.

Tous les providers (Anthropic, OpenAI, ...) implémentent cette interface.
Les agents appellent uniquement `provider.run_loop()` — ils ne savent pas
quel provider est utilisé en dessous.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    """Représente un appel de tool retourné par le LLM."""

    id: str
    name: str
    input: dict


@dataclass
class LLMResponse:
    """Réponse normalisée d'un LLM, indépendante du provider."""

    stop_reason: str  # "end_turn" | "tool_use"
    text: str = ""  # Texte final (quand stop_reason == "end_turn")
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMProvider(ABC):
    """
    Interface commune pour tous les providers LLM.

    Chaque provider implémente la boucle agentic complète (tool_use → tool_result → ...)
    dans son propre format d'API, et expose une interface normalisée.
    """

    @abstractmethod
    def run_loop(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict],
        model: str,
        max_tokens: int,
        max_iterations: int,
        tool_executor: Callable[[str, dict], Any],
        agent_name: str = "Agent",
    ) -> str:
        """
        Exécute la boucle agentic complète et retourne le texte final.

        Args:
            system         : System prompt
            messages       : Messages initiaux [{"role": "user", "content": "..."}]
            tools          : Tool definitions au format Anthropic (le provider convertit)
            model          : Nom du modèle pour ce provider
            max_tokens     : Tokens max en output
            max_iterations : Nombre max d'itérations de la boucle
            tool_executor  : Callable(tool_name, tool_input) → résultat
            agent_name     : Nom de l'agent pour les logs

        Returns:
            Texte de la réponse finale
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nom du provider (ex: "anthropic", "openai")."""
        ...
