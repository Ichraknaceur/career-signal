"""
Pipeline Phase 1 — Medium Article Generation.

Flow :
  Toi (subject + source optionnelle)
    → Agent 1 : Ingestion      (lit la source si fournie)
    → Agent 2 : Strategist     (structure + angle basé sur TON sujet)
    → Agent 3 : Medium Writer  (rédige l'article)
    → Agent 4 : QA Judge       (évalue la qualité)
    → [Validation utilisateur dans l'UI]
    → Agent 5 : Medium Publisher

Le sujet est TOUJOURS celui fourni par l'utilisateur.
Les agents ne l'inventent pas — ils le servent.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from agents.ingestion_agent import IngestionAgent
from agents.medium_agent import MediumAgent
from agents.qa_judge_agent import QAJudgeAgent
from agents.strategist_agent import StrategistAgent
from core.memory import ContentPipelineState, QAVerdict, SourceType
from tools.medium_tools import post_to_medium

logger = logging.getLogger(__name__)

# Callback type : (step_name, message, state) -> None
StepCallback = Callable[[str, str, ContentPipelineState], None]


@dataclass
class MediumPipelineResult:
    """Résultat final du pipeline Medium."""

    state: ContentPipelineState
    success: bool
    error: str | None = None

    @property
    def article_title(self) -> str:
        return self.state.medium_title

    @property
    def article_content(self) -> str:
        return self.state.medium_draft

    @property
    def article_tags(self) -> list[str]:
        return self.state.medium_tags

    @property
    def qa_score(self) -> float:
        return self.state.qa_score

    @property
    def qa_feedback(self) -> str:
        return self.state.qa_feedback

    @property
    def published_url(self) -> str | None:
        return self.state.medium_post_url


class MediumPipeline:
    """
    Pipeline dédié à la génération et publication d'articles Medium.

    Usage :
        pipeline = MediumPipeline()

        # Génération (sans publier)
        result = pipeline.generate(
            subject="Comment j'ai réduit les hallucinations LLM de 40%",
            source_type=SourceType.GITHUB_REPO,
            source_content="anthropics/claude-code",
            callback=my_callback,
        )

        # Publication (après validation utilisateur)
        result = pipeline.publish(result.state, publish_mode="live")
    """

    def __init__(self) -> None:
        self.ingestion_agent = IngestionAgent()
        self.strategist_agent = StrategistAgent()
        self.medium_agent = MediumAgent()
        self.qa_judge = QAJudgeAgent()

    def generate(
        self,
        subject: str,
        source_type: SourceType = SourceType.RAW_IDEA,
        source_content: str = "",
        technical_level: str = "intermediate",
        max_revisions: int = 2,
        language: str = "English",
        callback: StepCallback | None = None,
    ) -> MediumPipelineResult:
        """
        Génère l'article Medium sans le publier.
        Retourne le résultat pour validation utilisateur.

        Args:
            subject         : Sujet fourni par l'utilisateur (obligatoire).
            source_type     : Type de source complémentaire.
            source_content  : Contenu source (URL, chemin, ID arXiv...).
            technical_level : Niveau technique visé (beginner/intermediate/expert).
            max_revisions   : Nombre max de tours QA.
            callback        : Fonction appelée à chaque étape pour mise à jour UI.
        """

        def _cb(step: str, msg: str, state: ContentPipelineState) -> None:
            logger.info(f"[{step}] {msg}")
            if callback:
                callback(step, msg, state)

        state = ContentPipelineState(
            user_subject=subject,
            source_type=source_type,
            source_content=source_content or subject,
            technical_level=technical_level,
            max_revisions=max_revisions,
            language=language,
            linkedin_enabled=False,  # Phase 1 : Medium seulement
            medium_enabled=True,
        )

        try:
            # ── Step 1 : Ingestion ──────────────────────────────────────────
            _cb("ingestion", f"Lecture de la source ({source_type.value})...", state)
            state = self.ingestion_agent.run(state)
            _cb("ingestion", f"✓ {len(state.key_ideas)} idées extraites", state)

            # ── Step 2 : Strategy ───────────────────────────────────────────
            _cb("strategy", f"Définition de la stratégie pour : « {subject} »...", state)
            state = self.strategist_agent.run(state)
            _cb("strategy", f"✓ Angle : {state.content_angle[:60]}...", state)

            # ── Step 3 : Rédaction + QA loop ───────────────────────────────
            while True:
                _cb(
                    "writing",
                    f"Rédaction de l'article (révision #{state.revision_count})...",
                    state,
                )
                state = self.medium_agent.run(state)
                word_count = len(state.medium_draft.split())
                _cb("writing", f"✓ Article rédigé : {word_count} mots", state)

                _cb("qa", "Évaluation QA de l'article...", state)
                state = self.qa_judge.run(state)
                qa_verdict_label = (
                    state.qa_verdict.value if state.qa_verdict is not None else "unknown"
                )
                _cb(
                    "qa",
                    f"Score QA : {state.qa_score:.1f}/10 — {qa_verdict_label}",
                    state,
                )

                if state.is_ready_to_publish():
                    break
                elif state.qa_verdict == QAVerdict.REJECTED:
                    _cb("qa", "❌ Article rejeté définitivement par le QA.", state)
                    break
                elif state.needs_revision():
                    state.revision_count += 1
                    _cb(
                        "qa",
                        f"Révision {state.revision_count}/{max_revisions} demandée...",
                        state,
                    )
                else:
                    _cb("qa", "⚠️ Max révisions atteint. Arrêt du pipeline.", state)
                    break

            return MediumPipelineResult(state=state, success=True)

        except Exception as e:
            logger.error(f"[MediumPipeline] Erreur: {e}", exc_info=True)
            return MediumPipelineResult(state=state, success=False, error=str(e))

    def publish(
        self,
        state: ContentPipelineState,
        publish_mode: str = "dry_run",
        # Permet à l'utilisateur de modifier le titre/contenu avant de publier
        override_title: str | None = None,
        override_content: str | None = None,
        override_tags: list[str] | None = None,
    ) -> MediumPipelineResult:
        """
        Publie l'article après validation utilisateur.

        Args:
            state           : État issu de generate().
            publish_mode    : "dry_run" (simulation) ou "live" (publication réelle).
            override_title  : Titre modifié par l'utilisateur dans l'UI.
            override_content: Contenu modifié par l'utilisateur dans l'UI.
            override_tags   : Tags modifiés par l'utilisateur dans l'UI.
        """
        title = override_title or state.medium_title
        content = override_content or state.medium_draft
        tags = override_tags or state.medium_tags
        dry_run = publish_mode != "live"

        result = post_to_medium(
            title=title,
            content=content,
            tags=tags,
            publish_status="public" if not dry_run else "draft",
            dry_run=dry_run,
        )

        if result.get("success"):
            state.medium_post_url = result.get("url", "dry_run://medium/article")
            state.medium_title = title
            state.medium_draft = content
            state.medium_tags = tags
            from datetime import datetime

            state.published_at = datetime.utcnow().isoformat() + "Z"
            state.log_event(f"Medium publié ({publish_mode}): {state.medium_post_url}")
            return MediumPipelineResult(state=state, success=True)
        else:
            error = result.get("error", "Erreur inconnue")
            state.log_event(f"Erreur publication Medium: {error}")
            return MediumPipelineResult(state=state, success=False, error=error)
