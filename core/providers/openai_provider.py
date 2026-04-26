"""
Provider OpenAI — implémentation de LLMProvider.

Différences clés vs Anthropic :
  - Le system prompt est un message {"role": "system"} en tête de la liste
  - Les tools sont au format {"type": "function", "function": {...}}
    (input_schema → parameters)
  - finish_reason : "stop" | "tool_calls"
  - Les appels tools sont dans message.tool_calls (pas dans content)
  - Les tool results sont {"role": "tool", "tool_call_id": ..., "content": ...}
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from core.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """Provider basé sur le SDK OpenAI."""

    def __init__(self, api_key: str) -> None:
        try:
            from openai import OpenAI

            self._client = OpenAI(api_key=api_key)
        except ImportError as err:
            raise ImportError("openai n'est pas installé. Lance : uv add openai") from err

    @property
    def provider_name(self) -> str:
        return "openai"

    # ── Conversion des tool definitions ──────────────────────────────────────
    @staticmethod
    def _to_openai_tools(tools: list[dict]) -> list[dict]:
        """
        Convertit les tool definitions du format Anthropic vers OpenAI.

        Anthropic : {"name": ..., "description": ..., "input_schema": {...}}
        OpenAI    : {"type": "function", "function": {"name": ..., "description": ..., "parameters": {...}}}
        """
        result = []
        for tool in tools:
            result.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get(
                            "input_schema",
                            {
                                "type": "object",
                                "properties": {},
                            },
                        ),
                    },
                }
            )
        return result

    # ── Boucle agentic ────────────────────────────────────────────────────────
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
        """Boucle agentic OpenAI (function calling)."""

        # Construire la liste de messages OpenAI
        # Le system prompt est injecté en premier message
        msgs: list[dict] = [{"role": "system", "content": system}]
        for m in messages:
            msgs.append({"role": m["role"], "content": m["content"]})

        oai_tools = self._to_openai_tools(tools) if tools else []

        for iteration in range(max_iterations):
            logger.debug(f"[{agent_name}][openai] iteration {iteration + 1}")

            kwargs: dict[str, Any] = dict(
                model=model,
                max_tokens=max_tokens,
                messages=msgs,
            )
            if oai_tools:
                kwargs["tools"] = oai_tools
                # "required" force le modèle à appeler un tool au premier tour.
                # Dès le 2e tour (après un tool result), on repasse en "auto"
                # pour laisser le modèle conclure en texte si besoin.
                kwargs["tool_choice"] = "required" if iteration == 0 else "auto"

            response = self._client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            msg = choice.message

            if choice.finish_reason == "stop":
                return msg.content or ""

            if choice.finish_reason == "tool_calls" and msg.tool_calls:
                # Ajouter le message assistant avec les tool_calls
                # msg.content peut être None quand il y a des tool_calls (OpenAI SDK >= 1.30)
                # On garde None explicite car l'API OpenAI l'accepte et le SDK l'attend tel quel
                msgs.append(
                    {
                        "role": "assistant",
                        "content": msg.content,  # None OK — attendu par l'API quand tool_calls présents
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in msg.tool_calls
                        ],
                    }
                )

                # Exécuter chaque tool et ajouter les résultats
                for tc in msg.tool_calls:
                    logger.debug(f"[{agent_name}][openai] tool_call: {tc.function.name}")
                    try:
                        tool_input = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        tool_input = {}

                    result = tool_executor(tc.function.name, tool_input)
                    result_str = json.dumps(result) if not isinstance(result, str) else result

                    msgs.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result_str,
                        }
                    )
            else:
                logger.warning(
                    f"[{agent_name}][openai] finish_reason inattendu: {choice.finish_reason}"
                )
                break

        raise RuntimeError(
            f"[{agent_name}][openai] max_iterations ({max_iterations}) atteint sans réponse finale"
        )
