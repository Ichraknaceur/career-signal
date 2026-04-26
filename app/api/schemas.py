from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str
    database_path: str
    database_exists: bool


class InitDbRequest(BaseModel):
    db_path: str | None = Field(
        default=None,
        description="Chemin optionnel de la base SQLite a initialiser.",
    )


class InitDbResponse(BaseModel):
    status: str
    database_path: str


class AutoPublishRunRequest(BaseModel):
    email: str | None = Field(default=None, description="Override LinkedIn email.")
    password: str | None = Field(default=None, description="Override LinkedIn password.")
    as_of: date | datetime | None = Field(default=None, description="Date/heure de reference ISO.")
    headless: bool = Field(default=True, description="Execution Playwright headless.")
    max_posts: int | None = Field(default=None, ge=1, description="Nombre max de posts.")


class AutoPublishRunResponse(BaseModel):
    checked_at: str
    eligible_posts: int
    published_posts: int
    failed_posts: int
    skipped_posts: int
    errors: list[str]
    published_ids: list[str]
    success: bool


class ScheduledPostResponse(BaseModel):
    id: str
    pillar: str
    day_of_week: str
    week_number: int
    scheduled_date: str
    scheduled_time: str
    content: str
    hashtags: list[str]
    status: str
    medium_article_url: str | None = None
    medium_article_title: str | None = None
    created_at: str
    published_at: str | None = None
    user_feedback: str | None = None
