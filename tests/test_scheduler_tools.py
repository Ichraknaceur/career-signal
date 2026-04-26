"""
Tests unitaires — scheduler_tools.py (Phase 2)

Couvre :
  - ScheduledPost : création, sérialisation, désérialisation
  - CRUD : add, load, update_status, update_content, delete
  - compute_scheduled_dates : nombre de slots, pilliers, jours
  - get_published_medium_articles : lecture d'un fichier mock
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest

from tools.scheduler_tools import (
    DEFAULT_PUBLISH_TIMES,
    PILLAR_BY_DAY,
    ScheduledPost,
    add_posts,
    compute_scheduled_dates,
    create_scheduled_post_from_tool_input,
    delete_post,
    get_drafts,
    get_published_medium_articles,
    get_weeks_summary,
    load_posts,
    record_medium_publication,
    save_posts,
    update_post_content,
    update_post_schedule,
    update_post_status,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────
def make_post(
    pillar: str = "expertise_ia",
    day: str = "monday",
    week: int = 1,
    status: str = "draft",
    content: str = "Test post content",
) -> ScheduledPost:
    base_monday = date(2026, 4, 27)
    day_offsets = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    scheduled = base_monday + timedelta(weeks=week - 1, days=day_offsets.get(day, 0))
    return ScheduledPost(
        id=str(uuid.uuid4()),
        pillar=pillar,
        day_of_week=day,
        week_number=week,
        scheduled_date=scheduled.isoformat(),
        content=content,
        hashtags=["#ai", "#test"],
        status=status,
    )


@pytest.fixture()
def tmp_data_dir(tmp_path, monkeypatch):
    """Redirige DATA_DIR et SCHEDULE_FILE vers un répertoire temporaire."""
    import tools.scheduler_tools as st_mod

    monkeypatch.setattr(st_mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(st_mod, "SCHEDULE_FILE", tmp_path / "schedule.json")
    monkeypatch.setattr(st_mod, "MEDIUM_PUBLISHED_FILE", tmp_path / "medium_published.json")
    return tmp_path


# ── Tests ScheduledPost ──────────────────────────────────────────────────────
class TestScheduledPost:
    def test_to_dict_roundtrip(self):
        post = make_post()
        d = post.to_dict()
        restored = ScheduledPost.from_dict(d)
        assert restored.id == post.id
        assert restored.pillar == post.pillar
        assert restored.hashtags == post.hashtags
        assert restored.status == post.status

    def test_default_status_is_draft(self):
        post = make_post()
        assert post.status == "draft"

    def test_create_from_tool_input(self):
        tool_input = {
            "pillar": "projets",
            "day_of_week": "wednesday",
            "week_number": 1,
            "scheduled_date": "2026-04-29",
            "scheduled_time": "14:45",
            "content": "Contenu du post",
            "hashtags": ["#ai", "#build", "#genai", "#ml", "#extra", "#toomany"],
            "medium_article_url": None,
            "medium_article_title": None,
        }
        post = create_scheduled_post_from_tool_input(tool_input)
        assert post.pillar == "projets"
        assert post.scheduled_time == "14:45"
        assert len(post.hashtags) <= 5  # max 5 hashtags
        assert post.status == "draft"


# ── Tests CRUD ───────────────────────────────────────────────────────────────
class TestCRUD:
    def test_empty_load(self, tmp_data_dir):
        posts = load_posts()
        assert posts == []

    def test_save_and_load(self, tmp_data_dir):
        p1 = make_post(pillar="expertise_ia", week=1)
        p2 = make_post(pillar="projets", week=1, day="wednesday")
        save_posts([p1, p2])

        loaded = load_posts()
        assert len(loaded) == 2
        assert {p.pillar for p in loaded} == {"expertise_ia", "projets"}

    def test_add_posts_appends(self, tmp_data_dir):
        p1 = make_post(week=1)
        save_posts([p1])

        p2 = make_post(pillar="projets", week=2)
        add_posts([p2])

        all_posts = load_posts()
        assert len(all_posts) == 2

    def test_get_drafts(self, tmp_data_dir):
        posts = [
            make_post(status="draft"),
            make_post(status="approved"),
            make_post(status="published"),
        ]
        save_posts(posts)
        drafts = get_drafts()
        assert len(drafts) == 1
        assert drafts[0].status == "draft"

    def test_update_post_status_approved(self, tmp_data_dir):
        p = make_post(status="draft")
        save_posts([p])

        result = update_post_status(p.id, "approved")
        assert result is True

        loaded = load_posts()
        assert loaded[0].status == "approved"

    def test_update_post_status_published_sets_timestamp(self, tmp_data_dir):
        p = make_post(status="approved")
        save_posts([p])

        update_post_status(p.id, "published")
        loaded = load_posts()
        assert loaded[0].published_at is not None

    def test_update_post_status_not_found(self, tmp_data_dir):
        result = update_post_status("nonexistent-id", "approved")
        assert result is False

    def test_update_post_content(self, tmp_data_dir):
        p = make_post(content="Ancien contenu")
        save_posts([p])

        update_post_content(p.id, "Nouveau contenu", ["#new"])
        loaded = load_posts()
        assert loaded[0].content == "Nouveau contenu"
        assert loaded[0].hashtags == ["#new"]

    def test_update_post_schedule(self, tmp_data_dir):
        p = make_post(day="monday", week=1)
        save_posts([p])

        update_post_schedule(p.id, "2026-04-30", "16:15")
        loaded = load_posts()
        assert loaded[0].scheduled_date == "2026-04-30"
        assert loaded[0].scheduled_time == "16:15"
        assert loaded[0].day_of_week == "thursday"

    def test_delete_post(self, tmp_data_dir):
        p1 = make_post()
        p2 = make_post(pillar="projets")
        save_posts([p1, p2])

        deleted = delete_post(p1.id)
        assert deleted is True

        remaining = load_posts()
        assert len(remaining) == 1
        assert remaining[0].pillar == "projets"

    def test_delete_nonexistent_returns_false(self, tmp_data_dir):
        result = delete_post("not-a-real-id")
        assert result is False

    def test_get_weeks_summary(self, tmp_data_dir):
        posts = [
            make_post(week=1, pillar="expertise_ia", status="draft"),
            make_post(week=1, pillar="projets", day="wednesday", status="approved"),
            make_post(week=2, pillar="promo_medium", day="friday", status="draft"),
        ]
        save_posts(posts)
        summary = get_weeks_summary()

        assert 1 in summary
        assert 2 in summary
        assert summary[1]["draft"] == 1
        assert summary[1]["approved"] == 1
        assert len(summary[1]["posts"]) == 2
        assert len(summary[2]["posts"]) == 1


# ── Tests compute_scheduled_dates ────────────────────────────────────────────
class TestComputeScheduledDates:
    def test_nb_slots(self):
        slots = compute_scheduled_dates(2)
        assert len(slots) == 6  # 2 semaines × 3 jours

    def test_nb_slots_4_weeks(self):
        slots = compute_scheduled_dates(4)
        assert len(slots) == 12

    def test_days_are_monday_wednesday_friday(self):
        slots = compute_scheduled_dates(1)
        days = {s["day"] for s in slots}
        assert days == {"monday", "wednesday", "friday"}

    def test_pillars_match_days(self):
        slots = compute_scheduled_dates(2)
        for slot in slots:
            assert slot["pillar"] == PILLAR_BY_DAY[slot["day"]]

    def test_week_numbers(self):
        slots = compute_scheduled_dates(3)
        weeks = {s["week"] for s in slots}
        assert weeks == {1, 2, 3}

    def test_start_date_respected(self):
        start = date(2026, 4, 27)  # Lundi
        slots = compute_scheduled_dates(1, start_date=start)
        monday_slot = next(s for s in slots if s["day"] == "monday")
        assert monday_slot["date"] == "2026-04-27"

    def test_dates_are_iso_strings(self):
        slots = compute_scheduled_dates(1)
        for slot in slots:
            # Doit être parseable comme date ISO
            parsed = date.fromisoformat(slot["date"])
            assert parsed is not None

    def test_wednesday_is_plus_2_from_monday(self):
        start = date(2026, 4, 27)  # Lundi
        slots = compute_scheduled_dates(1, start_date=start)
        monday_date = date.fromisoformat(next(s["date"] for s in slots if s["day"] == "monday"))
        wednesday_date = date.fromisoformat(
            next(s["date"] for s in slots if s["day"] == "wednesday")
        )
        assert (wednesday_date - monday_date).days == 2

    def test_default_publish_times_are_included(self):
        slots = compute_scheduled_dates(1)
        assert (
            next(s for s in slots if s["day"] == "monday")["time"]
            == DEFAULT_PUBLISH_TIMES["monday"]
        )

    def test_custom_publish_times_are_respected(self):
        slots = compute_scheduled_dates(1, publish_times={"friday": "19:15"})
        friday_slot = next(s for s in slots if s["day"] == "friday")
        assert friday_slot["time"] == "19:15"


# ── Tests Medium Published Articles ─────────────────────────────────────────
class TestMediumPublishedArticles:
    def test_empty_when_no_file(self, tmp_data_dir):
        articles = get_published_medium_articles()
        assert articles == []

    def test_record_and_retrieve(self, tmp_data_dir):
        record_medium_publication(
            title="Mon super article",
            url="https://medium.com/@test/mon-super-article",
            tags=["ai", "genai"],
        )
        articles = get_published_medium_articles()
        assert len(articles) == 1
        assert articles[0]["title"] == "Mon super article"
        assert articles[0]["url"] == "https://medium.com/@test/mon-super-article"
        assert "published_at" in articles[0]

    def test_record_multiple(self, tmp_data_dir):
        record_medium_publication("Article 1", "https://medium.com/1", ["ai"])
        record_medium_publication("Article 2", "https://medium.com/2", ["ml"])
        articles = get_published_medium_articles()
        assert len(articles) == 2
