"""
Provider Anthropic — implémentation de LLMProvider.

Format natif Anthropic SDK :
  - tools : {"name", "description", "input_schema"}
  - stop_reason : "end_turn" | "tool_use"
  - tool_use blocks dans response.content
  - tool_result blocks dans le message user suivant
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

import anthropic

from core.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """Provider basé sur le SDK Anthropic."""

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "anthropic"

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
        """Boucle agentic Anthropic native (tool_use → tool_result)."""
        # Copier les messages pour ne pas muter l'original
        msgs: list[dict] = [{"role": m["role"], "content": m["content"]} for m in messages]

        for iteration in range(max_iterations):
            logger.debug(f"[{agent_name}][anthropic] iteration {iteration + 1}")

            kwargs: dict[str, Any] = dict(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=msgs,
            )
            if tools:
                kwargs["tools"] = tools  # Format Anthropic natif

            response = self._client.messages.create(**kwargs)

            # Ajouter la réponse assistant dans l'historique
            msgs.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        return block.text
                return ""

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        logger.debug(f"[{agent_name}][anthropic] tool_use: {block.name}")
                        result = tool_executor(block.name, block.input)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": (
                                    json.dumps(result) if not isinstance(result, str) else result
                                ),
                            }
                        )
                msgs.append({"role": "user", "content": tool_results})
            else:
                logger.warning(
                    f"[{agent_name}][anthropic] stop_reason inattendu: {response.stop_reason}"
                )
                break

        raise RuntimeError(
            f"[{agent_name}][anthropic] max_iterations ({max_iterations}) atteint sans end_turn"
        )
