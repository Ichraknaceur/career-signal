"""
Agent 6 — Publisher.

Publie le contenu approuvé par le QA Judge sur LinkedIn et Medium.
Gère le scheduling, la confirmation et le logging.
"""

from __future__ import annotations

import logging

from agents.base_agent import BaseAgent
from core.memory import ContentPipelineState, QAVerdict
from tools.linkedin_tools import LINKEDIN_POST_TOOL, post_to_linkedin
from tools.medium_tools import MEDIUM_POST_TOOL, post_to_medium
from tools.scheduler_tools import SCHEDULE_POST_TOOL, schedule_post

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es le Publisher Agent. Ta mission : publier le contenu approuvé.

Utilise les tools disponibles pour :
1. Poster sur LinkedIn si linkedin_enabled
2. Poster sur Medium si medium_enabled
3. Logger les URLs de publication

Par défaut, publie en dry_run=true SAUF si l'utilisateur a explicitement
demandé une publication réelle (publish_mode="live").

Retourne un résumé de ce qui a été publié.
"""


class PublisherAgent(BaseAgent):
    def __init__(self, publish_mode: str = "dry_run") -> None:
        """
        Args:
            publish_mode: "dry_run" (défaut, simulation) ou "live" (publication réelle)
        """
        super().__init__(
            name="PublisherAgent",
            system_prompt=SYSTEM_PROMPT,
        )
        self.publish_mode = publish_mode
        self._tools = [LINKEDIN_POST_TOOL, MEDIUM_POST_TOOL, SCHEDULE_POST_TOOL]

    # ── Tool handlers ────────────────────────────────────────────────────────
    def handle_post_to_linkedin(self, text: str, dry_run: bool = True) -> dict:
        dry = self.publish_mode != "live" or dry_run
        return post_to_linkedin(text, dry_run=dry)

    def handle_post_to_medium(
        self, title: str, content: str, tags=None, publish_status="draft", dry_run=True
    ) -> dict:
        dry = self.publish_mode != "live" or dry_run
        return post_to_medium(title, content, tags, publish_status, dry_run=dry)

    def handle_schedule_post(self, platform: str, content: str, publish_at=None) -> dict:
        return schedule_post(platform, content, publish_at)

    # ── Main ─────────────────────────────────────────────────────────────────
    def run(self, state: ContentPipelineState) -> ContentPipelineState:
        if state.qa_verdict != QAVerdict.APPROVED:
            logger.warning(
                f"[PublisherAgent] Contenu non approuvé (verdict={state.qa_verdict}). Skip."
            )
            return state

        logger.info(f"[PublisherAgent] Publication en mode '{self.publish_mode}'...")

        # Publication LinkedIn
        if state.linkedin_enabled and state.linkedin_draft:
            full_post = state.linkedin_draft
            if state.linkedin_hashtags:
                full_post += "\n\n" + " ".join(state.linkedin_hashtags)

            result = post_to_linkedin(full_post, dry_run=(self.publish_mode != "live"))
            if result.get("success"):
                state.linkedin_post_url = result.get("url", "dry_run://linkedin")
                state.log_event(f"LinkedIn publié: {state.linkedin_post_url}")
            else:
                state.log_event(f"LinkedIn erreur: {result.get('error')}")

        # Publication Medium
        if state.medium_enabled and state.medium_draft:
            result = post_to_medium(
                title=state.medium_title,
                content=state.medium_draft,
                tags=state.medium_tags,
                publish_status="draft" if self.publish_mode != "live" else "public",
                dry_run=(self.publish_mode != "live"),
            )
            if result.get("success"):
                state.medium_post_url = result.get("url", "dry_run://medium")
                state.log_event(f"Medium publié: {state.medium_post_url}")
            else:
                state.log_event(f"Medium erreur: {result.get('error')}")

        from datetime import datetime

        state.published_at = datetime.utcnow().isoformat() + "Z"
        state.log_event(
            f"PublisherAgent terminé. mode={self.publish_mode}. "
            f"LinkedIn={state.linkedin_post_url} | Medium={state.medium_post_url}"
        )
        return state
