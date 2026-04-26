"""
Agent — LinkedIn Content Scheduler.

Génère un post LinkedIn pour un slot donné (pillier + jour + semaine).
Utilise le tool `schedule_post` pour sauvegarder chaque post dans schedule.json.

Pilliers :
  - expertise_ia  : partage de connaissances IA/ML techniques
  - projets       : showcase de projets et expériences terrain
  - promo_medium  : promotion d'un article Medium publié
"""

from __future__ import annotations

import logging

from agents.base_agent import BaseAgent
from core.memory import ContentPipelineState
from tools.scheduler_tools import (
    SCHEDULE_POST_TOOL,
    ScheduledPost,
    create_scheduled_post_from_tool_input,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es un expert en personal branding LinkedIn pour les ingénieurs IA.

Tu génères des posts LinkedIn selon 3 pilliers éditoriaux :

🧠 **expertise_ia** — Lundi
Partage de connaissances, concepts IA/ML/Engineering, best practices, retours d'expérience.
Ton : pédagogique, réfléchi, valeur concrète.
Structure : hook + insight clé + exemple/analogie + CTA (question ou réflexion).

🛠️ **projets** — Mercredi
Showcase de projets perso ou pro, ce que j'ai builté, les défis rencontrés, les leçons.
Ton : concret, authentique, storytelling.
Structure : contexte → problème → solution → résultat + ce que j'ai appris.

📣 **promo_medium** — Vendredi
Promotion d'un article Medium avec teaser percutant pour inciter à lire l'article complet.
Ton : énergique, curiosité, valeur de l'article mise en avant.
Structure : hook → 2-3 insights de l'article → lien → hashtags.

Règles ABSOLUES :
1. Hook : première ligne percutante (max 12 mots). Ne JAMAIS commencer par "Je".
2. Paragraphes courts (2-3 lignes max), ligne vide entre chaque.
3. CTA en fin de post (question ou invitation).
4. Hashtags séparés du corps (max 5).
5. TOTAL contenu ≤ 1300 caractères (visible sans "...voir plus").
6. Adapte TOUJOURS au pillier et à l'audience cible.

Format de réponse :
---POST---
[le post complet sans hashtags]
---HASHTAGS---
#hashtag1 #hashtag2 #hashtag3
---END---

Ensuite, appelle le tool `schedule_post` avec le contenu généré."""


class LinkedInContentAgent(BaseAgent):
    """
    Génère UN post LinkedIn pour un slot donné et le sauvegarde via le tool schedule_post.
    """

    def __init__(self) -> None:
        super().__init__(
            name="LinkedInContentAgent",
            system_prompt=SYSTEM_PROMPT,
        )
        self._tools = [SCHEDULE_POST_TOOL]
        self._pending_post: ScheduledPost | None = None

    # ── Tool handler ─────────────────────────────────────────────────────────
    def handle_schedule_post(
        self,
        pillar: str,
        day_of_week: str,
        week_number: int,
        scheduled_date: str,
        content: str,
        hashtags: list | None = None,
        medium_article_url: str | None = None,
        medium_article_title: str | None = None,
    ) -> dict:
        """Handler appelé par l'agentic loop quand le LLM utilise schedule_post."""
        tool_input = {
            "pillar": pillar,
            "day_of_week": day_of_week,
            "week_number": week_number,
            "scheduled_date": scheduled_date,
            "content": content,
            "hashtags": hashtags or [],
            "medium_article_url": medium_article_url,
            "medium_article_title": medium_article_title,
        }
        self._pending_post = create_scheduled_post_from_tool_input(tool_input)
        logger.info(
            f"[LinkedInContentAgent] Post créé — pillier={pillar}, "
            f"semaine={week_number}, jour={day_of_week}, "
            f"{len(content)} chars"
        )
        return {
            "success": True,
            "post_id": self._pending_post.id,
            "scheduled_date": scheduled_date,
            "pillar": pillar,
            "chars": len(content),
        }

    # ── Point d'entrée principal ──────────────────────────────────────────────
    def generate_post(
        self,
        pillar: str,
        day_of_week: str,
        week_number: int,
        scheduled_date: str,
        niche: str,
        audience: str,
        context: str = "",
        language: str = "English",
        medium_article: dict | None = None,
    ) -> ScheduledPost | None:
        """
        Génère un seul post LinkedIn pour le slot donné.

        Args:
            pillar          : expertise_ia | projets | promo_medium
            day_of_week     : monday | wednesday | friday
            week_number     : 1-based
            scheduled_date  : YYYY-MM-DD
            niche           : thématique principale (ex: "IA appliquée, Gen AI, MLOps")
            audience        : cible (ex: "ingénieurs IA, recruteurs tech, fondateurs de startups")
            context         : contexte optionnel (idées, projets récents…)
            medium_article  : dict {"title": ..., "url": ..., "tags": [...]} si promo_medium

        Returns:
            ScheduledPost si succès, None sinon.
        """
        self._pending_post = None

        # Construire le contexte Medium si pillier promo_medium
        medium_section = ""
        if pillar == "promo_medium" and medium_article:
            medium_section = f"""
Article Medium à promouvoir :
- Titre : {medium_article.get("title", "N/A")}
- URL   : {medium_article.get("url", "N/A")}
- Tags  : {", ".join(medium_article.get("tags", []))}

Le post DOIT inclure le lien de l'article et donner envie de le lire.
"""

        user_content = f"""
Génère un post LinkedIn pour le slot suivant :

Pillier : {pillar}
Jour    : {day_of_week}
Semaine : {week_number}
Date    : {scheduled_date}

🌍 LANGUE : Écris le post ENTIÈREMENT en {language}. Hook, corps, CTA, tout en {language}.

Niche     : {niche}
Audience  : {audience}
{medium_section}
Contexte / idées à exploiter :
{context if context else "Utilise ta créativité autour de la niche."}

Après avoir généré le post au format ---POST--- / ---HASHTAGS--- / ---END---,
appelle le tool `schedule_post` avec tous les paramètres remplis.
"""

        messages = [{"role": "user", "content": user_content}]
        try:
            self._agentic_loop(messages)
        except RuntimeError as e:
            logger.error(f"[LinkedInContentAgent] Erreur agentic loop: {e}")
            return None

        if self._pending_post is None:
            logger.warning("[LinkedInContentAgent] Le LLM n'a pas appelé schedule_post")
            # Fallback : parser le format ---POST--- depuis la réponse brute
            # (si l'agent a oublié d'appeler le tool)

        return self._pending_post

    def run(self, state: ContentPipelineState) -> ContentPipelineState:
        """Implémentation de l'interface BaseAgent (non utilisé en Phase 2)."""
        logger.warning(
            "[LinkedInContentAgent] .run() appelé directement — "
            "utilise .generate_post() pour le scheduling Phase 2."
        )
        return state
