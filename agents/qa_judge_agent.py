"""
Agent 5 — QA Judge (LLM-as-a-Judge).

Évalue la qualité du contenu généré par les agents 3 et 4.
Si le contenu ne passe pas, retourne un feedback pour révision
(feedback loop vers les agents writers).
"""

from __future__ import annotations

import json
import logging
import re

from agents.base_agent import BaseAgent
from core.memory import ContentPipelineState, QAVerdict

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es un expert en Quality Assurance de contenu pour les réseaux sociaux tech.

Ton rôle : évaluer le contenu généré et décider s'il est publiable.

Critères d'évaluation :
1. Exactitude technique (pas de claims incorrects ou flous)
2. Clarté et lisibilité (adapté à l'audience cible)
3. Engagement (hook, CTA, structure)
4. Conformité plateforme (longueur, format, hashtags)
5. Valeur ajoutée (apporte quelque chose d'utile ou d'original)

Score de 0 à 10. Seuil de validation : 7.5/10.

Réponds TOUJOURS en JSON :
{
  "verdict": "approved" | "needs_revision" | "rejected",
  "score": 8.5,
  "linkedin_issues": ["..."],
  "medium_issues": ["..."],
  "feedback": "Instructions précises pour améliorer le contenu.",
  "strengths": ["..."]
}"""


class QAJudgeAgent(BaseAgent):
    APPROVAL_THRESHOLD = 7.5

    def __init__(self) -> None:
        super().__init__(
            name="QAJudgeAgent",
            system_prompt=SYSTEM_PROMPT,
        )

    def run(self, state: ContentPipelineState) -> ContentPipelineState:
        logger.info(f"[QAJudgeAgent] Évaluation (révision #{state.revision_count})...")

        evaluation_input = self._build_evaluation_input(state)
        messages = [{"role": "user", "content": evaluation_input}]
        raw = self._agentic_loop(messages)

        try:
            json_match = re.search(r"\{[\s\S]*\}", raw)
            data = json.loads(json_match.group() if json_match else raw)

            state.qa_score = float(data.get("score", 0))
            state.qa_feedback = data.get("feedback", "")
            raw_verdict = data.get("verdict", "needs_revision")

            if raw_verdict == "approved" or state.qa_score >= self.APPROVAL_THRESHOLD:
                state.qa_verdict = QAVerdict.APPROVED
            elif raw_verdict == "rejected":
                state.qa_verdict = QAVerdict.REJECTED
            else:
                state.qa_verdict = QAVerdict.NEEDS_REVISION

        except Exception as e:
            logger.error(f"[QAJudgeAgent] Erreur parsing: {e}\nRaw: {raw[:200]}")
            state.qa_verdict = QAVerdict.NEEDS_REVISION
            state.qa_feedback = "Erreur d'évaluation. Révision nécessaire."

        state.log_event(f"QAJudgeAgent: score={state.qa_score}/10, verdict={state.qa_verdict}")
        return state

    def _build_evaluation_input(self, state: ContentPipelineState) -> str:
        sections = [
            f"Audience cible : {state.target_audience}",
            f"Niveau technique : {state.technical_level}",
        ]

        if state.linkedin_draft:
            sections.append(
                f"\n--- POST LINKEDIN ({len(state.linkedin_draft)} chars) ---\n"
                f"{state.linkedin_draft}\n"
                f"Hashtags: {' '.join(state.linkedin_hashtags)}"
            )

        if state.medium_draft:
            sections.append(
                f"\n--- ARTICLE MEDIUM ({len(state.medium_draft.split())} mots) ---\n"
                f"Titre: {state.medium_title}\n"
                f"Tags: {', '.join(state.medium_tags)}\n\n"
                f"{state.medium_draft[:2000]}..."
            )

        return "\n".join(sections)
