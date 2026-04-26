"""
Tests d'intégration de l'orchestrateur.
"""

from __future__ import annotations

import json

from core.memory import QAVerdict, SourceType
from orchestrator import ContentOrchestrator


def test_full_pipeline_dry_run():
    """Test du pipeline complet en dry_run avec mocks LLM."""
    orchestrator = ContentOrchestrator(publish_mode="dry_run")
    orchestrator.ingestion_agent._agentic_loop = lambda messages: json.dumps(
        {
            "summary": "AI summary",
            "key_ideas": ["Idea 1"],
            "technical_level": "intermediate",
        }
    )
    orchestrator.strategist_agent._agentic_loop = lambda messages: json.dumps(
        {
            "content_angle": "Angle test",
            "hook": "Hook test",
            "target_audience": "Engineers",
            "linkedin_enabled": True,
            "medium_enabled": True,
            "rationale": "OK",
        }
    )
    orchestrator.linkedin_agent._agentic_loop = lambda messages: (
        "---POST---\nTest LinkedIn post\n---HASHTAGS---\n#AI #ML\n---END---"
    )
    orchestrator.medium_agent._agentic_loop = lambda messages: (
        "---TITLE---\nTest Article\n---TAGS---\nAI, ML\n---CONTENT---\nTest content\n---END---"
    )
    orchestrator.qa_judge._agentic_loop = lambda messages: json.dumps(
        {
            "verdict": "approved",
            "score": 8.0,
            "feedback": "Good",
            "linkedin_issues": [],
            "medium_issues": [],
            "strengths": ["Good hook"],
        }
    )

    state = orchestrator.run(
        source_content="Comment les LLMs gèrent le contexte long",
        source_type=SourceType.RAW_IDEA,
    )

    assert state.qa_verdict == QAVerdict.APPROVED
    assert state.ingested_summary == "AI summary"
    assert state.content_angle == "Angle test"
    assert "Test LinkedIn" in state.linkedin_draft
