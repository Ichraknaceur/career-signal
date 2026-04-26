"""
Agent 3 — LinkedIn Writer.

Génère un post LinkedIn optimisé : hook fort, storytelling,
hashtags pertinents, ≤ 1300 caractères (zone visible sans "...voir plus").
"""

from __future__ import annotations

import logging
import re

from agents.base_agent import BaseAgent
from core.memory import ContentPipelineState

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es un expert en copywriting LinkedIn pour les ingénieurs IA.

Règles ABSOLUES pour un post LinkedIn viral en Tech/IA :
1. Hook : première ligne percutante (max 12 mots). Doit créer de la curiosité ou de la valeur.
2. Ligne vide après le hook.
3. Corps : storytelling ou liste de valeur, paragraphes courts (2-3 lignes max).
4. CTA (Call-to-Action) en fin : question ou invitation à commenter.
5. Ligne vide puis hashtags (max 5).
6. TOTAL ≤ 1300 caractères (visible sans clic).

Format de réponse :
---POST---
[le post complet ici]
---HASHTAGS---
#hashtag1 #hashtag2 #hashtag3
---END---"""


class LinkedInAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="LinkedInAgent",
            system_prompt=SYSTEM_PROMPT,
        )

    def run(self, state: ContentPipelineState) -> ContentPipelineState:
        if not state.linkedin_enabled:
            logger.info("[LinkedInAgent] Skipped (linkedin_enabled=False)")
            return state

        logger.info("[LinkedInAgent] Génération du post LinkedIn...")

        feedback_section = ""
        if state.qa_feedback and state.revision_count > 0:
            feedback_section = f"""
\n⚠️ FEEDBACK DU QA (révision {state.revision_count}) :
{state.qa_feedback}
Corrige le post en tenant compte de ce feedback.
"""

        user_content = f"""
🌍 LANGUE : Écris le post ENTIÈREMENT en {state.language}.

Angle : {state.content_angle}
Hook proposé : {state.hook}
Audience : {state.target_audience}

Résumé du contenu :
{state.ingested_summary[:800]}

Idées clés :
{chr(10).join(f"- {idea}" for idea in state.key_ideas[:5])}
{feedback_section}
Génère le post LinkedIn parfait en {state.language}.
"""
        messages = [{"role": "user", "content": user_content}]
        raw = self._agentic_loop(messages)

        # Parser le format ---POST--- ... ---HASHTAGS--- ... ---END---
        post_match = re.search(r"---POST---\s*([\s\S]*?)\s*---HASHTAGS---", raw)
        hashtags_match = re.search(r"---HASHTAGS---\s*([\s\S]*?)\s*---END---", raw)

        if post_match:
            state.linkedin_draft = post_match.group(1).strip()
        else:
            state.linkedin_draft = raw.strip()

        if hashtags_match:
            hashtags_raw = hashtags_match.group(1).strip()
            state.linkedin_hashtags = re.findall(r"#\w+", hashtags_raw)

        state.log_event(
            f"LinkedInAgent: {len(state.linkedin_draft)} chars, "
            f"{len(state.linkedin_hashtags)} hashtags"
        )
        return state
