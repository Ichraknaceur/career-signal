"""
Agent 4 — Medium Writer.

Génère un article Medium complet en Markdown :
titre accrocheur, sections structurées, SEO-friendly,
blocs de code si pertinents.
"""

from __future__ import annotations

import logging
import re

from agents.base_agent import BaseAgent
from core.memory import ContentPipelineState

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es un auteur expert en articles techniques sur Medium (AI/ML/Engineering).

Structure d'un bon article Medium technique :
1. Titre : accrocheur, SEO (60-70 chars), contient un bénéfice ou une promesse
2. Introduction (100-150 mots) : contexte + pourquoi ça compte
3. 3-5 sections avec ## headers
4. Code blocks si pertinents (```python ... ```)
5. Conclusion avec takeaways
6. Tags SEO (5 max)

Longueur cible : 800-1500 mots.
Ton : professionnel mais accessible, premier personne ('j'ai', 'j'ai découvert').

Format de réponse :
---TITLE---
[titre ici]
---TAGS---
tag1, tag2, tag3
---CONTENT---
[article markdown complet ici, sans le titre (il sera ajouté séparément)]
---END---"""


class MediumAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="MediumAgent",
            system_prompt=SYSTEM_PROMPT,
        )

    def run(self, state: ContentPipelineState) -> ContentPipelineState:
        if not state.medium_enabled:
            logger.info("[MediumAgent] Skipped (medium_enabled=False)")
            return state

        logger.info("[MediumAgent] Génération de l'article Medium...")

        feedback_section = ""
        if state.qa_feedback and state.revision_count > 0:
            feedback_section = f"""
\n⚠️ FEEDBACK DU QA (révision {state.revision_count}) :
{state.qa_feedback}
Intègre ce feedback dans la révision de l'article.
"""

        user_content = f"""
⚠️ SUJET IMPOSÉ PAR L'UTILISATEUR (priorité absolue) :
« {state.user_subject} »
L'article DOIT traiter ce sujet exact. C'est non négociable.

🌍 LANGUE : Rédige l'article ENTIÈREMENT en {state.language}. Titre, sections, conclusion — tout en {state.language}.

Angle éditorial : {state.content_angle}
Audience cible : {state.target_audience}
Niveau technique : {state.technical_level}

Contexte et matière première :
{state.ingested_summary}

Idées clés à développer :
{chr(10).join(f"- {idea}" for idea in state.key_ideas)}
{feedback_section}
Génère l'article Medium complet sur ce sujet.
"""
        messages = [{"role": "user", "content": user_content}]
        raw = self._agentic_loop(messages)

        # Parser les sections
        title_match = re.search(r"---TITLE---\s*([\s\S]*?)\s*---TAGS---", raw)
        tags_match = re.search(r"---TAGS---\s*([\s\S]*?)\s*---CONTENT---", raw)
        content_match = re.search(r"---CONTENT---\s*([\s\S]*?)\s*---END---", raw)

        if title_match:
            state.medium_title = title_match.group(1).strip()
        if tags_match:
            state.medium_tags = [t.strip() for t in tags_match.group(1).split(",") if t.strip()][:5]
        if content_match:
            state.medium_draft = content_match.group(1).strip()
        else:
            state.medium_draft = raw.strip()

        state.log_event(
            f"MediumAgent: titre='{state.medium_title[:50]}', "
            f"{len(state.medium_draft.split())} mots"
        )
        return state
