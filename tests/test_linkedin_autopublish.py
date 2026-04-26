from __future__ import annotations

from datetime import date, datetime

from pipelines.linkedin_autopublish_pipeline import LinkedInAutoPublishPipeline
from tools.scheduler_tools import (
    ScheduledPost,
    get_due_approved_posts,
    save_posts,
)


def make_post(
    post_id: str,
    scheduled_date: str,
    status: str = "approved",
) -> ScheduledPost:
    return ScheduledPost(
        id=post_id,
        pillar="expertise_ia",
        day_of_week="monday",
        week_number=1,
        scheduled_date=scheduled_date,
        content=f"Post {post_id}",
        hashtags=["#ai"],
        status=status,
    )


def test_get_due_approved_posts_filters_correctly(tmp_path, monkeypatch):
    import tools.scheduler_tools as st_mod

    monkeypatch.setattr(st_mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(st_mod, "SCHEDULE_FILE", tmp_path / "schedule.json")
    monkeypatch.setattr(st_mod, "MEDIUM_PUBLISHED_FILE", tmp_path / "medium_published.json")

    save_posts(
        [
            make_post("due-approved", "2026-04-24", "approved"),
            make_post("future-approved", "2026-04-30", "approved"),
            make_post("due-draft", "2026-04-24", "draft"),
        ]
    )

    due_posts = get_due_approved_posts(as_of=date(2026, 4, 24))

    assert [post.id for post in due_posts] == ["due-approved"]


def test_get_due_approved_posts_respects_scheduled_time(tmp_path, monkeypatch):
    import tools.scheduler_tools as st_mod

    monkeypatch.setattr(st_mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(st_mod, "SCHEDULE_FILE", tmp_path / "schedule.json")
    monkeypatch.setattr(st_mod, "MEDIUM_PUBLISHED_FILE", tmp_path / "medium_published.json")

    morning_post = make_post("morning-post", "2026-04-24", "approved")
    evening_post = make_post("evening-post", "2026-04-24", "approved")
    morning_post.scheduled_time = "09:00"
    evening_post.scheduled_time = "18:00"
    save_posts([morning_post, evening_post])

    due_posts = get_due_approved_posts(as_of=datetime(2026, 4, 24, 10, 30))

    assert [post.id for post in due_posts] == ["morning-post"]


def test_autopublish_marks_successful_posts_as_published(tmp_path, monkeypatch):
    import tools.scheduler_tools as st_mod

    monkeypatch.setattr(st_mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(st_mod, "SCHEDULE_FILE", tmp_path / "schedule.json")
    monkeypatch.setattr(st_mod, "MEDIUM_PUBLISHED_FILE", tmp_path / "medium_published.json")

    save_posts(
        [
            make_post("post-1", "2026-04-24", "approved"),
            make_post("post-2", "2026-04-23", "approved"),
        ]
    )

    def fake_batch_publisher(**kwargs):
        posts = kwargs["posts"]
        return [{"id": post["id"], "success": True} for post in posts]

    pipeline = LinkedInAutoPublishPipeline(batch_publisher=fake_batch_publisher)
    result = pipeline.run_once(
        email="user@example.com",
        password="secret",
        as_of=date(2026, 4, 24),
    )

    published = st_mod.load_posts()

    assert result.published_posts == 2
    assert all(post.status == "published" for post in published)
    assert all(post.published_at is not None for post in published)


def test_autopublish_keeps_failed_posts_approved(tmp_path, monkeypatch):
    import tools.scheduler_tools as st_mod

    monkeypatch.setattr(st_mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(st_mod, "SCHEDULE_FILE", tmp_path / "schedule.json")
    monkeypatch.setattr(st_mod, "MEDIUM_PUBLISHED_FILE", tmp_path / "medium_published.json")

    save_posts([make_post("post-fail", "2026-04-24", "approved")])

    def fake_batch_publisher(**kwargs):
        return [{"id": "post-fail", "success": False, "error": "boom"}]

    pipeline = LinkedInAutoPublishPipeline(batch_publisher=fake_batch_publisher)
    result = pipeline.run_once(
        email="user@example.com",
        password="secret",
        as_of=date(2026, 4, 24),
    )

    posts = st_mod.load_posts()

    assert result.failed_posts == 1
    assert result.errors == ["boom"]
    assert posts[0].status == "approved"
    assert posts[0].published_at is None
