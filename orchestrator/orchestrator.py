"""
Orchestrateur principal de CareerSignal.

Coordonne les 6 agents selon l'architecture du diagramme :
  Agent1 (Ingestion) → Agent2 (Strategist) → Agent3 + Agent4 (Writers, parallèle logique)
  → Agent5 (QA Judge, avec feedback loop vers writers) → Agent6 (Publisher)

Le feedback loop du QA Judge re-route vers Agent3/4 si révision nécessaire.
"""

from __future__ import annotations

import copy
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from agents.ingestion_agent import IngestionAgent
from agents.linkedin_agent import LinkedInAgent
from agents.medium_agent import MediumAgent
from agents.publisher_agent import PublisherAgent
from agents.qa_judge_agent import QAJudgeAgent
from agents.strategist_agent import StrategistAgent
from core.memory import ContentPipelineState, QAVerdict, SourceType

logger = logging.getLogger(__name__)


class ContentOrchestrator:
    """
    Pipeline d'orchestration : source → ingestion → stratégie →
    rédaction → QA (+ retry) → publication.
    """

    def __init__(self, publish_mode: Literal["dry_run", "live"] = "dry_run") -> None:
        self.publish_mode = publish_mode

        # Instanciation des agents
        self.ingestion_agent = IngestionAgent()
        self.strategist_agent = StrategistAgent()
        self.linkedin_agent = LinkedInAgent()
        self.medium_agent = MediumAgent()
        self.qa_judge = QAJudgeAgent()
        self.publisher = PublisherAgent(publish_mode=publish_mode)

    def run(
        self,
        source_content: str,
        source_type: SourceType = SourceType.RAW_IDEA,
        max_revisions: int = 2,
    ) -> ContentPipelineState:
        """
        Lance le pipeline complet.

        Args:
            source_content: URL, chemin fichier, arXiv ID ou texte brut.
            source_type: Type de la source (github_repo, pdf, arxiv, url, raw_idea).
            max_revisions: Nombre max de tours de révision QA.

        Returns:
            ContentPipelineState avec tout le contenu généré et les URLs de publication.
        """
        # Initialisation de l'état
        state = ContentPipelineState(
            source_type=source_type,
            source_content=source_content,
            max_revisions=max_revisions,
        )
        state.log_event(f"Pipeline démarré. source_type={source_type}, mode={self.publish_mode}")

        # ── Step 1 : Ingestion ──────────────────────────────────────────────
        logger.info("=" * 60)
        logger.info("STEP 1 — Ingestion & Understanding")
        state = self.ingestion_agent.run(state)

        # ── Step 2 : Strategy ───────────────────────────────────────────────
        logger.info("=" * 60)
        logger.info("STEP 2 — Content Strategy")
        state = self.strategist_agent.run(state)

        # ── Steps 3+4 + QA feedback loop ────────────────────────────────────
        while True:
            # Steps 3+4 : LinkedIn & Medium en PARALLÈLE
            # Chaque writer reçoit une copie indépendante de l'état pour éviter
            # les race conditions, puis on fusionne uniquement leurs champs.
            state = self._run_writers_parallel(state)

            # Step 5 : QA Judge
            logger.info("=" * 60)
            logger.info(f"STEP 5 — QA Judge (révision #{state.revision_count})")
            state = self.qa_judge.run(state)

            if state.is_ready_to_publish():
                logger.info(f"✅ QA approuvé ! Score: {state.qa_score}/10")
                break
            elif state.qa_verdict == QAVerdict.REJECTED:
                logger.error(f"❌ QA rejeté définitivement. Score: {state.qa_score}/10")
                break
            elif state.needs_revision():
                logger.info(
                    f"⚠️  Révision nécessaire ({state.revision_count + 1}/{max_revisions}). "
                    f"Score: {state.qa_score}/10"
                )
                state.revision_count += 1
                state.log_event(f"Feedback loop → révision {state.revision_count}")
            else:
                # Max révisions atteint sans approbation — on arrête sans publier.
                # Ne jamais force-approuver du contenu sous le seuil QA.
                logger.error(
                    f"❌ Max révisions ({max_revisions}) atteint. "
                    f"Score final : {state.qa_score}/10. Pipeline arrêté."
                )
                state.log_event(
                    f"Pipeline arrêté : max_revisions={max_revisions} atteint, "
                    f"score={state.qa_score}/10 < seuil QA."
                )
                # qa_verdict reste NEEDS_REVISION → PublisherAgent ne publiera pas
                break

        # ── Step 6 : Publisher ───────────────────────────────────────────────
        logger.info("=" * 60)
        logger.info("STEP 6 — Publisher")
        state = self.publisher.run(state)

        logger.info("=" * 60)
        logger.info("Pipeline terminé !")
        self._print_summary(state)

        return state

    def _run_writers_parallel(self, state: ContentPipelineState) -> ContentPipelineState:
        """
        Exécute LinkedInAgent et MediumAgent en parallèle via ThreadPoolExecutor.

        Pattern copy-then-merge :
          1. Chaque writer reçoit une deepcopy de l'état → pas de race condition.
          2. On fusionne uniquement les champs que chaque writer est censé écrire.
          3. Les logs des deux copies sont consolidés dans l'état final.
        """
        rev = state.revision_count
        futures = {}

        with ThreadPoolExecutor(max_workers=2) as executor:
            if state.linkedin_enabled:
                logger.info("=" * 60)
                logger.info(f"STEP 3 — LinkedIn Writer (révision #{rev}) [parallèle]")
                li_state = copy.deepcopy(state)
                futures["linkedin"] = executor.submit(self.linkedin_agent.run, li_state)

            if state.medium_enabled:
                logger.info("=" * 60)
                logger.info(f"STEP 4 — Medium Writer (révision #{rev}) [parallèle]")
                md_state = copy.deepcopy(state)
                futures["medium"] = executor.submit(self.medium_agent.run, md_state)

        # Fusion des résultats dans l'état principal
        for platform, future in futures.items():
            try:
                result_state = future.result()
                if platform == "linkedin":
                    state.linkedin_draft = result_state.linkedin_draft
                    state.linkedin_hashtags = result_state.linkedin_hashtags
                    state.publish_log.extend(
                        e for e in result_state.publish_log if e not in state.publish_log
                    )
                elif platform == "medium":
                    state.medium_title = result_state.medium_title
                    state.medium_draft = result_state.medium_draft
                    state.medium_tags = result_state.medium_tags
                    state.publish_log.extend(
                        e for e in result_state.publish_log if e not in state.publish_log
                    )
            except Exception as e:
                logger.error(f"[Orchestrator] Erreur writer {platform}: {e}")
                state.log_event(f"Erreur {platform} writer: {e}")

        return state

    def _print_summary(self, state: ContentPipelineState) -> None:
        """Affiche un résumé lisible du résultat."""
        print("\n" + "=" * 60)
        print("RÉSUMÉ DU PIPELINE")
        print("=" * 60)
        print(f"  QA Score     : {state.qa_score:.1f}/10 ({state.qa_verdict})")
        print(f"  Révisions    : {state.revision_count}")
        print(f"  LinkedIn URL : {state.linkedin_post_url or 'N/A'}")
        print(f"  Medium URL   : {state.medium_post_url or 'N/A'}")
        print(f"  Publié à     : {state.published_at or 'Non publié'}")
        print("\nLog du pipeline:")
        for entry in state.publish_log[-10:]:
            print(f"  {entry}")
        print("=" * 60)
