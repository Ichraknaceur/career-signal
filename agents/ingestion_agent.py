"""
Agent 1 — Ingestion & Understanding.

Reçoit une source (GitHub, PDF, arXiv, texte brut),
lit/récupère le contenu et produit un résumé structuré + idées clés.
"""

from __future__ import annotations

import json
import logging

from agents.base_agent import BaseAgent
from core.memory import ContentPipelineState, SourceType
from tools.file_tools import READ_FILE_TOOL, READ_PDF_TOOL, read_file, read_pdf
from tools.web_tools import (
    FETCH_ARXIV_TOOL,
    FETCH_GITHUB_README_TOOL,
    FETCH_URL_TOOL,
    fetch_arxiv,
    fetch_github_readme,
    fetch_url,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es un expert en analyse et compréhension de contenu technique.
Ta mission : lire le contenu source fourni, le comprendre en profondeur, et produire :
1. Un résumé structuré (250-400 mots)
2. Une liste des 5-8 idées clés les plus importantes
3. Le niveau technique estimé (beginner / intermediate / expert)

Utilise les tools disponibles pour accéder au contenu si nécessaire.
Réponds TOUJOURS en JSON avec ce format exact :
{
  "summary": "...",
  "key_ideas": ["...", "..."],
  "technical_level": "intermediate"
}"""


class IngestionAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="IngestionAgent",
            system_prompt=SYSTEM_PROMPT,
        )
        self._tools = [
            READ_FILE_TOOL,
            READ_PDF_TOOL,
            FETCH_URL_TOOL,
            FETCH_ARXIV_TOOL,
            FETCH_GITHUB_README_TOOL,
        ]

    # ── Tool handlers ────────────────────────────────────────────────────────
    def handle_read_file(self, path: str, max_chars: int = 20000) -> str:
        return read_file(path, max_chars)

    def handle_read_pdf(self, path: str) -> str:
        return read_pdf(path)

    def handle_fetch_url(self, url: str, max_chars: int = 15000) -> str:
        return fetch_url(url, max_chars)

    def handle_fetch_arxiv(self, arxiv_id: str) -> dict:
        return fetch_arxiv(arxiv_id)

    def handle_fetch_github_readme(self, repo: str) -> str:
        return fetch_github_readme(repo)

    # ── Main ─────────────────────────────────────────────────────────────────
    def run(self, state: ContentPipelineState) -> ContentPipelineState:
        logger.info(
            f"[IngestionAgent] Source: {state.source_type} | {state.source_content[:80]}..."
        )

        user_msg = self._build_user_message(state)
        messages = [{"role": "user", "content": user_msg}]

        raw = self._agentic_loop(messages)

        # Parser le JSON retourné par le LLM
        try:
            # Extraire le JSON si emballé dans du texte
            import re

            json_match = re.search(r"\{[\s\S]*\}", raw)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(raw)

            state.ingested_summary = data.get("summary", "")
            state.key_ideas = data.get("key_ideas", [])
            state.technical_level = data.get("technical_level", "intermediate")
        except Exception as e:
            logger.error(f"[IngestionAgent] Erreur parsing JSON: {e}\nRaw: {raw[:200]}")
            state.ingested_summary = raw
            state.key_ideas = []

        state.log_event(f"IngestionAgent terminé. {len(state.key_ideas)} idées extraites.")
        return state

    def _build_user_message(self, state: ContentPipelineState) -> str:
        msgs = {
            SourceType.GITHUB_REPO: f"Analyse ce repo GitHub et extrais les idées clés: {state.source_content}",
            SourceType.ARXIV: f"Analyse ce paper arXiv: {state.source_content}",
            SourceType.PDF: f"Lis et analyse ce PDF: {state.source_content}",
            SourceType.URL: f"Analyse le contenu de cette URL: {state.source_content}",
            SourceType.RAW_IDEA: f"Analyse et structure cette idée:\n\n{state.source_content}",
        }
        return msgs.get(state.source_type, f"Analyse: {state.source_content}")
