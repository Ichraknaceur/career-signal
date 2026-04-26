"""
VeilleAgent — Phase 4.

Deux outils LLM :
  1. write_summary(summary)       → résumé concis d'un article (~100-150 mots)
  2. write_linkedin_post(post)    → post LinkedIn prêt à publier (200-1500 chars)

Usage :
    agent = VeilleAgent()
    summary = agent.summarize(article)
    post    = agent.suggest_post(article, summary)
"""

from __future__ import annotations

import logging

from agents.base_agent import BaseAgent
from core.memory import ContentPipelineState
from tools.veille_store import VeilleArticle

logger = logging.getLogger(__name__)

# ── Tool definitions ──────────────────────────────────────────────────────────
WRITE_SUMMARY_TOOL = {
    "name": "write_summary",
    "description": (
        "Sauvegarde le résumé de l'article. "
        "Doit être concis (100-150 mots), factuel, en français. "
        "Mettre en avant les points clés et l'angle IA/LLM/RAG si pertinent."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Résumé de l'article en 100-150 mots.",
            }
        },
        "required": ["summary"],
    },
}

WRITE_POST_TOOL = {
    "name": "write_linkedin_post",
    "description": (
        "Sauvegarde le post LinkedIn suggéré basé sur l'article. "
        "Le post doit être engageant, professionnel, avec un angle personnel ou analytique. "
        "Inclure 3-5 hashtags pertinents en fin de post. "
        "Longueur idéale : 300-800 caractères (hors hashtags)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "post": {
                "type": "string",
                "description": "Post LinkedIn complet avec hashtags.",
            },
            "hook": {
                "type": "string",
                "description": "Première phrase accrocheuse du post (max 120 chars).",
            },
        },
        "required": ["post"],
    },
}

SYSTEM_SUMMARY = """Tu es un expert en intelligence artificielle et veille technologique.

Ta mission : résumer des articles techniques de manière claire, concise et accessible.

Règles :
- Résumé en FRANÇAIS, 100-150 mots maximum
- Factuel, pas d'opinion personnelle dans le résumé
- Mettre en avant : l'innovation principale, les implications pratiques, les acteurs clés
- Si l'article parle de LLM, RAG, agents IA, GenAI : le mentionner explicitement
- Pas de jargon inutile — accessible à un professionnel IA non-expert du sujet précis

Appelle `write_summary` avec le résumé final."""

SYSTEM_POST = """Tu es un expert en personal branding LinkedIn pour les professionnels de l'IA.

Ta mission : créer un post LinkedIn engageant à partir d'un article et son résumé.

Règles :
- Langue : FRANÇAIS (sauf si le sujet est très anglophone — alors mélange possible)
- Ton : professionnel mais accessible, avec une touche analytique ou personnelle
- Structure :
    1. Hook fort (première ligne = ce qui accroche, fait poser une question ou surprend)
    2. Contexte / problème (2-3 phrases)
    3. Ce que l'article apporte / enseignements clés (bullet points ou paragraphe)
    4. Ton avis / question pour engager la communauté (1-2 phrases)
    5. 3-5 hashtags pertinents (#IA #LLM #RAG #GenAI #MachineLearning etc.)
- Longueur corps : 300-800 chars
- NE PAS copier le résumé — créer quelque chose de plus engageant et personnel

Appelle `write_linkedin_post` avec le post final."""


class VeilleAgent(BaseAgent):
    """
    Agent de veille IA : résume des articles et suggère des posts LinkedIn.
    """

    def __init__(self) -> None:
        super().__init__(
            name="VeilleAgent",
            system_prompt=SYSTEM_SUMMARY,  # Remplacé selon la tâche
        )
        self._result: str = ""

    # ── Tool handlers ─────────────────────────────────────────────────────────
    def handle_write_summary(self, summary: str) -> dict:
        self._result = summary.strip()
        logger.info(f"[VeilleAgent] Résumé généré — {len(self._result)} chars")
        return {"success": True, "chars": len(self._result)}

    def handle_write_linkedin_post(self, post: str, hook: str = "") -> dict:
        self._result = post.strip()
        logger.info(f"[VeilleAgent] Post LinkedIn généré — {len(self._result)} chars")
        return {"success": True, "chars": len(self._result), "hook": hook}

    # ── Résumé ────────────────────────────────────────────────────────────────
    def summarize(self, article: VeilleArticle) -> str:
        """
        Génère un résumé de l'article en français (100-150 mots).

        Le LLM est censé appeler `write_summary` (tool call) → self._result est rempli.
        Si le LLM répond en texte direct (finish_reason=stop), on utilise ce texte.
        """
        self._result = ""
        self.system_prompt = SYSTEM_SUMMARY
        self._tools = [WRITE_SUMMARY_TOOL]

        content_excerpt = article.content[:2000] if article.content else "Contenu non disponible"

        user_content = f"""Résume cet article :

Titre   : {article.title}
Source  : {article.source_name}
Catégorie: {article.category}
Publié  : {article.published_at[:10] if article.published_at else "N/A"}

Contenu :
{content_excerpt}

Génère un résumé de 100-150 mots en français.
Appelle `write_summary` avec le résumé."""

        llm_text = ""
        try:
            llm_text = self._agentic_loop([{"role": "user", "content": user_content}]) or ""
        except Exception as e:
            logger.error(f"[VeilleAgent] Erreur résumé: {e}")

        # Priorité : tool call → réponse texte → fallback minimal
        if not self._result and llm_text and llm_text.strip():
            self._result = llm_text.strip()
            logger.info(f"[VeilleAgent] Résumé via réponse texte ({len(self._result)} chars)")
        elif not self._result:
            self._result = f"**{article.title}** ({article.source_name})\n\n" + (
                article.content[:300] + "…" if article.content else "Contenu non disponible."
            )
            logger.warning("[VeilleAgent] Fallback résumé utilisé (LLM n'a pas répondu)")

        return self._result

    # ── Suggestion de post LinkedIn ───────────────────────────────────────────
    def suggest_post(self, article: VeilleArticle, summary: str) -> str:
        """
        Génère un post LinkedIn engageant à partir de l'article et son résumé.

        Le LLM est censé appeler `write_linkedin_post` → self._result est rempli.
        Si le LLM répond en texte direct, on utilise ce texte.
        """
        self._result = ""
        self.system_prompt = SYSTEM_POST
        self._tools = [WRITE_POST_TOOL]

        user_content = f"""Crée un post LinkedIn à partir de cet article :

Titre   : {article.title}
Source  : {article.source_name}
URL     : {article.url}
Catégorie: {article.category}

Résumé de l'article :
{summary}

Génère un post LinkedIn engageant en français avec hashtags.
Appelle `write_linkedin_post` avec le post final."""

        llm_text = ""
        try:
            llm_text = self._agentic_loop([{"role": "user", "content": user_content}]) or ""
        except Exception as e:
            logger.error(f"[VeilleAgent] Erreur post: {e}")

        # Priorité : tool call → réponse texte → fallback minimal
        if not self._result and llm_text and llm_text.strip():
            self._result = llm_text.strip()
            logger.info(f"[VeilleAgent] Post via réponse texte ({len(self._result)} chars)")
        elif not self._result:
            self._result = (
                f"📖 Article intéressant : **{article.title}**\n\n"
                f"{summary[:300]}…\n\n"
                f"🔗 {article.url}\n\n"
                f"#IA #LLM #GenAI #MachineLearning"
            )
            logger.warning("[VeilleAgent] Fallback post utilisé (LLM n'a pas répondu)")

        return self._result

    def run(self, state: ContentPipelineState) -> ContentPipelineState:
        logger.warning(
            "[VeilleAgent] .run() non utilisé directement — utilise .summarize() / .suggest_post()"
        )
        return state
