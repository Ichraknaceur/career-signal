"""
Tests unitaires — LinkedIn Scheduling Pipeline (Phase 2)

Couvre :
  - LinkedInContentAgent : génération d'un post via mock LLM + tool_use
  - LinkedInSchedulingPipeline : génération multi-slots avec mocks
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from agents.linkedin_content_agent import LinkedInContentAgent
from tools.scheduler_tools import ScheduledPost


# ── Helpers ──────────────────────────────────────────────────────────────────
def _make_tool_use_block(tool_name: str, tool_input: dict) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.id = str(uuid.uuid4())
    block.input = tool_input
    return block


def _make_text_block(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    block.id = str(uuid.uuid4())
    return block


def _make_response(stop_reason: str, content: list) -> MagicMock:
    r = MagicMock()
    r.stop_reason = stop_reason
    r.content = content
    return r


# ── Tests LinkedInContentAgent ────────────────────────────────────────────────
class TestLinkedInContentAgent:
    def test_generate_post_with_tool_use(self, tmp_path, monkeypatch):
        """
        Le LLM appelle schedule_post → l'agent retourne un ScheduledPost.
        """
        import tools.scheduler_tools as st_mod

        monkeypatch.setattr(st_mod, "DATA_DIR", tmp_path)
        monkeypatch.setattr(st_mod, "SCHEDULE_FILE", tmp_path / "schedule.json")

        tool_input = {
            "pillar": "expertise_ia",
            "day_of_week": "monday",
            "week_number": 1,
            "scheduled_date": "2026-04-27",
            "scheduled_time": "08:30",
            "content": "Le RAG hybride change tout pour la précision des LLMs.\n\nVoici pourquoi...",
            "hashtags": ["#ai", "#rag", "#llm"],
            "medium_article_url": None,
            "medium_article_title": None,
        }

        def fake_agentic_loop(self, messages):
            self.handle_schedule_post(**tool_input)
            return "Post planifié avec succès."

        monkeypatch.setattr(LinkedInContentAgent, "_agentic_loop", fake_agentic_loop)

        agent = LinkedInContentAgent()
        post = agent.generate_post(
            pillar="expertise_ia",
            day_of_week="monday",
            week_number=1,
            scheduled_date="2026-04-27",
            niche="IA appliquée",
            audience="ingénieurs IA",
        )

        assert post is not None
        assert isinstance(post, ScheduledPost)
        assert post.pillar == "expertise_ia"
        assert post.day_of_week == "monday"
        assert post.week_number == 1
        assert post.scheduled_time == "08:30"
        assert post.status == "draft"
        assert len(post.content) > 0
        assert len(post.hashtags) <= 5

    def test_generate_post_no_tool_call_returns_none(self, monkeypatch):
        """Si le LLM ne call pas le tool, l'agent retourne None."""
        monkeypatch.setattr(
            LinkedInContentAgent,
            "_agentic_loop",
            lambda self, messages: (
                "Voici un post : ---POST--- Contenu ---HASHTAGS--- #ai ---END---"
            ),
        )

        agent = LinkedInContentAgent()
        post = agent.generate_post(
            pillar="projets",
            day_of_week="wednesday",
            week_number=1,
            scheduled_date="2026-04-29",
            niche="MLOps",
            audience="data engineers",
        )

        # Pas de tool call → _pending_post reste None
        assert post is None

    def test_handle_schedule_post_limits_hashtags(self):
        """Le handler doit limiter les hashtags à 5 max."""
        agent = LinkedInContentAgent()

        result = agent.handle_schedule_post(
            pillar="projets",
            day_of_week="wednesday",
            week_number=1,
            scheduled_date="2026-04-29",
            content="Contenu test",
            hashtags=["#a", "#b", "#c", "#d", "#e", "#f", "#g"],  # 7 hashtags
        )

        assert result["success"] is True
        assert agent._pending_post is not None
        assert len(agent._pending_post.hashtags) <= 5

    def test_generate_post_promo_medium_includes_url(self, tmp_path, monkeypatch):
        """Pour promo_medium, le tool_input peut inclure l'URL de l'article."""
        import tools.scheduler_tools as st_mod

        monkeypatch.setattr(st_mod, "DATA_DIR", tmp_path)
        monkeypatch.setattr(st_mod, "SCHEDULE_FILE", tmp_path / "schedule.json")

        tool_input = {
            "pillar": "promo_medium",
            "day_of_week": "friday",
            "week_number": 1,
            "scheduled_date": "2026-05-01",
            "scheduled_time": "17:45",
            "content": "Mon article sur le RAG hybride est sorti !",
            "hashtags": ["#ai", "#medium"],
            "medium_article_url": "https://medium.com/@test/rag-hybride",
            "medium_article_title": "RAG Hybride : 40% moins d'hallucinations",
        }

        def fake_agentic_loop(self, messages):
            self.handle_schedule_post(**tool_input)
            return "Post promo planifié."

        monkeypatch.setattr(LinkedInContentAgent, "_agentic_loop", fake_agentic_loop)

        medium_article = {
            "title": "RAG Hybride : 40% moins d'hallucinations",
            "url": "https://medium.com/@test/rag-hybride",
            "tags": ["ai", "rag"],
        }

        agent = LinkedInContentAgent()
        post = agent.generate_post(
            pillar="promo_medium",
            day_of_week="friday",
            week_number=1,
            scheduled_date="2026-05-01",
            niche="IA appliquée",
            audience="ingénieurs IA",
            medium_article=medium_article,
        )

        assert post is not None
        assert post.scheduled_time == "17:45"
        assert post.medium_article_url == "https://medium.com/@test/rag-hybride"
        assert post.medium_article_title is not None


# ── Tests LinkedInSchedulingPipeline ─────────────────────────────────────────
class TestLinkedInSchedulingPipeline:
    @patch("pipelines.linkedin_scheduling_pipeline.LinkedInContentAgent")
    def test_generate_calls_agent_per_slot(self, MockAgent, tmp_path, monkeypatch):
        """Le pipeline doit appeler generate_post pour chaque slot."""
        import tools.scheduler_tools as st_mod

        monkeypatch.setattr(st_mod, "DATA_DIR", tmp_path)
        monkeypatch.setattr(st_mod, "SCHEDULE_FILE", tmp_path / "schedule.json")
        monkeypatch.setattr(st_mod, "MEDIUM_PUBLISHED_FILE", tmp_path / "medium_published.json")

        # Mock l'agent pour retourner un post fictif à chaque appel
        mock_agent_instance = MockAgent.return_value

        def make_mock_post(pillar, day_of_week, week_number, scheduled_date, **kwargs):
            return ScheduledPost(
                id=str(uuid.uuid4()),
                pillar=pillar,
                day_of_week=day_of_week,
                week_number=week_number,
                scheduled_date=scheduled_date,
                content=f"Post {pillar} {day_of_week} semaine {week_number}",
                hashtags=["#ai"],
                status="draft",
            )

        mock_agent_instance.generate_post.side_effect = make_mock_post

        from pipelines.linkedin_scheduling_pipeline import LinkedInSchedulingPipeline

        pipeline = LinkedInSchedulingPipeline()
        result = pipeline.generate(
            niche="IA appliquée",
            audience="ingénieurs IA",
            nb_weeks=1,
        )

        assert result.success is True
        assert result.total_posts == 3  # 1 semaine × 3 jours
        assert mock_agent_instance.generate_post.call_count == 3

    @patch("pipelines.linkedin_scheduling_pipeline.LinkedInContentAgent")
    def test_generate_saves_to_json(self, MockAgent, tmp_path, monkeypatch):
        """Les posts générés doivent être sauvegardés dans schedule.json."""
        import tools.scheduler_tools as st_mod

        monkeypatch.setattr(st_mod, "DATA_DIR", tmp_path)
        monkeypatch.setattr(st_mod, "SCHEDULE_FILE", tmp_path / "schedule.json")
        monkeypatch.setattr(st_mod, "MEDIUM_PUBLISHED_FILE", tmp_path / "medium_published.json")

        mock_agent_instance = MockAgent.return_value

        def make_mock_post(pillar, day_of_week, week_number, scheduled_date, **kwargs):
            return ScheduledPost(
                id=str(uuid.uuid4()),
                pillar=pillar,
                day_of_week=day_of_week,
                week_number=week_number,
                scheduled_date=scheduled_date,
                content="Contenu test",
                hashtags=["#ai"],
                status="draft",
            )

        mock_agent_instance.generate_post.side_effect = make_mock_post

        from pipelines.linkedin_scheduling_pipeline import LinkedInSchedulingPipeline

        pipeline = LinkedInSchedulingPipeline()
        pipeline.generate(niche="IA", audience="devs", nb_weeks=2)

        schedule_file = tmp_path / "schedule.json"
        assert schedule_file.exists()

        import json

        saved = json.loads(schedule_file.read_text())
        assert len(saved) == 6  # 2 semaines × 3 posts

    @patch("pipelines.linkedin_scheduling_pipeline.LinkedInContentAgent")
    def test_generate_handles_agent_failure(self, MockAgent, tmp_path, monkeypatch):
        """Si un slot échoue, le pipeline continue avec les autres."""
        import tools.scheduler_tools as st_mod

        monkeypatch.setattr(st_mod, "DATA_DIR", tmp_path)
        monkeypatch.setattr(st_mod, "SCHEDULE_FILE", tmp_path / "schedule.json")
        monkeypatch.setattr(st_mod, "MEDIUM_PUBLISHED_FILE", tmp_path / "medium_published.json")

        call_count = 0

        def sometimes_fail(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                return None  # Simule un échec (tool pas appelé)
            return ScheduledPost(
                id=str(uuid.uuid4()),
                pillar=kwargs["pillar"],
                day_of_week=kwargs["day_of_week"],
                week_number=kwargs["week_number"],
                scheduled_date=kwargs["scheduled_date"],
                content="Contenu ok",
                hashtags=["#ai"],
                status="draft",
            )

        MockAgent.return_value.generate_post.side_effect = sometimes_fail

        from pipelines.linkedin_scheduling_pipeline import LinkedInSchedulingPipeline

        pipeline = LinkedInSchedulingPipeline()
        result = pipeline.generate(niche="IA", audience="devs", nb_weeks=1)

        # 2 posts réussis sur 3, pas d'exception
        assert result.total_posts == 2
        assert len(result.errors) == 1  # 1 slot a échoué
