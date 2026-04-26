"""
Tests unitaires pour les agents.
Utilise des mocks pour éviter les appels API réels.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from agents.ingestion_agent import IngestionAgent
from agents.qa_judge_agent import QAJudgeAgent
from core.memory import ContentPipelineState, QAVerdict, SourceType


class TestIngestionAgent:
    """Tests de l'IngestionAgent."""

    @patch("agents.base_agent.BaseAgent._agentic_loop")
    def test_run_raw_idea(self, mock_agentic_loop):
        """L'agent doit parser le JSON retourné par le LLM."""
        mock_agentic_loop.return_value = json.dumps(
            {
                "summary": "Test summary",
                "key_ideas": ["Idea 1", "Idea 2", "Idea 3"],
                "technical_level": "intermediate",
            }
        )

        agent = IngestionAgent()
        state = ContentPipelineState(
            source_type=SourceType.RAW_IDEA,
            source_content="Test idea",
        )
        result = agent.run(state)

        assert result.ingested_summary == "Test summary"
        assert len(result.key_ideas) == 3
        assert result.technical_level == "intermediate"

    def test_build_user_message_arxiv(self):
        """Le message user doit mentionner arXiv pour ce type de source."""
        agent = IngestionAgent()
        state = ContentPipelineState(
            source_type=SourceType.ARXIV,
            source_content="2301.07041",
        )
        msg = agent._build_user_message(state)
        assert "arXiv" in msg or "arxiv" in msg.lower()


class TestQAJudge:
    """Tests du QAJudgeAgent."""

    @patch("agents.base_agent.BaseAgent._agentic_loop")
    def test_approved_above_threshold(self, mock_agentic_loop):
        """Score >= 7.5 → verdict APPROVED."""
        mock_agentic_loop.return_value = json.dumps(
            {
                "verdict": "approved",
                "score": 8.5,
                "feedback": "Excellent contenu",
                "linkedin_issues": [],
                "medium_issues": [],
                "strengths": ["Hook fort"],
            }
        )

        agent = QAJudgeAgent()
        state = ContentPipelineState(
            linkedin_draft="Test post LinkedIn",
            medium_draft="Test article Medium",
            medium_title="Test Title",
        )
        result = agent.run(state)

        assert result.qa_verdict == QAVerdict.APPROVED
        assert result.qa_score == 8.5

    @patch("agents.base_agent.BaseAgent._agentic_loop")
    def test_needs_revision_below_threshold(self, mock_agentic_loop):
        """Score < 7.5 → verdict NEEDS_REVISION."""
        mock_agentic_loop.return_value = json.dumps(
            {
                "verdict": "needs_revision",
                "score": 6.0,
                "feedback": "Hook trop faible",
                "linkedin_issues": ["Hook peu engageant"],
                "medium_issues": [],
                "strengths": [],
            }
        )

        agent = QAJudgeAgent()
        state = ContentPipelineState(linkedin_draft="Weak post", medium_draft="")
        result = agent.run(state)

        assert result.qa_verdict == QAVerdict.NEEDS_REVISION
        assert result.qa_score == 6.0
