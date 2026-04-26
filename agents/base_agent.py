"""
BaseAgent — Agentic loop générique, multi-provider.

Pattern :
  1. L'agent construit ses messages initiaux
  2. Il délègue la boucle complète au provider actif (Anthropic ou OpenAI)
  3. Le provider gère tool_use / tool_calls dans son propre format
  4. L'agent reçoit le texte final

Pour changer de provider : définir LLM_PROVIDER=openai dans .env ou via l'UI.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import Any

from core.client import get_provider
from core.config import settings
from core.memory import ContentPipelineState
from core.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Agent de base avec agentic loop multi-provider.
    Tous les agents spécialisés héritent de cette classe.
    """

    def __init__(
        self,
        name: str,
        system_prompt: str,
        model: str | None = None,
    ) -> None:
        self.name = name
        self.system_prompt = system_prompt
        self._tools: list[dict] = []

        # Résoudre le provider au moment de la création de l'agent
        # Lit LLM_PROVIDER depuis l'env (peut être mis à jour par l'UI)
        provider_name = os.getenv("LLM_PROVIDER", "anthropic")
        self.provider: LLMProvider = get_provider(provider_name)

        # Résoudre le modèle selon le provider
        if model:
            self.model = model
        else:
            self.model = settings.model.agent(provider_name)

        logger.debug(f"[{self.name}] provider={provider_name}, model={self.model}")

    @property
    def tools(self) -> list[dict]:
        return self._tools

    @abstractmethod
    def run(self, state: ContentPipelineState) -> ContentPipelineState:
        """Point d'entrée principal. Reçoit l'état, le modifie, le retourne."""
        ...

    def _agentic_loop(
        self,
        messages: list[dict],
        extra_tools: list[dict] | None = None,
    ) -> str:
        """
        Délègue la boucle agentic complète au provider actif.

        Args:
            messages    : Messages initiaux [{"role": "user", "content": "..."}]
            extra_tools : Tools additionnels (en plus de self._tools)

        Returns:
            Texte de la réponse finale
        """
        tools = self._tools + (extra_tools or [])

        return self.provider.run_loop(
            system=self.system_prompt,
            messages=messages,
            tools=tools,
            model=self.model,
            max_tokens=settings.model.max_tokens,
            max_iterations=settings.agent.max_iterations,
            tool_executor=self._execute_tool,
            agent_name=self.name,
        )

    def _execute_tool(self, tool_name: str, tool_input: dict) -> Any:
        """
        Dispatch vers la méthode handle_<tool_name>.
        Override dans les sous-classes pour ajouter des tools.
        """
        handler = getattr(self, f"handle_{tool_name}", None)
        if handler is None:
            return {"error": f"Tool '{tool_name}' non implémenté dans {self.name}"}
        try:
            return handler(**tool_input)
        except Exception as e:
            logger.error(f"[{self.name}] Erreur tool {tool_name}: {e}")
            return {"error": str(e)}
