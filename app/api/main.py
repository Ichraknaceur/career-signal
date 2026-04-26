from __future__ import annotations

import os

from fastapi import APIRouter, FastAPI, Query

from app.api.schemas import (
    AutoPublishRunRequest,
    AutoPublishRunResponse,
    HealthResponse,
    InitDbRequest,
    InitDbResponse,
    ScheduledPostResponse,
)
from pipelines.linkedin_autopublish_pipeline import LinkedInAutoPublishPipeline
from storage.db import get_database_path
from storage.init_db import init_db
from tools.scheduler_tools import get_due_approved_posts, load_posts

app = FastAPI(
    title="CareerSignal API",
    version="0.1.0",
    description=(
        "API de pilotage pour tester les features de CareerSignal "
        "sans passer par l'interface Streamlit."
    ),
)

router = APIRouter()


def _scheduled_post_to_response(post) -> ScheduledPostResponse:
    return ScheduledPostResponse(
        id=post.id,
        pillar=post.pillar,
        day_of_week=post.day_of_week,
        week_number=post.week_number,
        scheduled_date=post.scheduled_date,
        content=post.content,
        hashtags=post.hashtags,
        status=post.status,
        medium_article_url=post.medium_article_url,
        medium_article_title=post.medium_article_title,
        created_at=post.created_at,
        published_at=post.published_at,
        user_feedback=post.user_feedback,
    )


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    db_path = get_database_path()
    return HealthResponse(
        status="ok",
        service="career-signal-api",
        database_path=str(db_path),
        database_exists=db_path.exists(),
    )


@router.post("/db/init", response_model=InitDbResponse, tags=["system"])
def init_database(payload: InitDbRequest) -> InitDbResponse:
    init_db(payload.db_path)
    db_path = payload.db_path or str(get_database_path())
    return InitDbResponse(status="initialized", database_path=db_path)


@router.get(
    "/scheduled-posts",
    response_model=list[ScheduledPostResponse],
    tags=["publishing"],
)
def list_scheduled_posts(
    status: str | None = Query(default=None, description="Filtre optionnel par statut."),
    due_only: bool = Query(default=False, description="Retourne seulement les posts dus."),
) -> list[ScheduledPostResponse]:
    posts = get_due_approved_posts() if due_only else load_posts()
    if status:
        posts = [post for post in posts if post.status == status]
    return [_scheduled_post_to_response(post) for post in posts]


@router.post(
    "/publishing/linkedin/autopublish/run-once",
    response_model=AutoPublishRunResponse,
    tags=["publishing"],
)
def run_autopublish_once(payload: AutoPublishRunRequest) -> AutoPublishRunResponse:
    pipeline = LinkedInAutoPublishPipeline()
    email = payload.email if payload.email is not None else (os.getenv("LINKEDIN_EMAIL") or "")
    password = (
        payload.password if payload.password is not None else (os.getenv("LINKEDIN_PASSWORD") or "")
    )
    result = pipeline.run_once(
        email=email,
        password=password,
        as_of=payload.as_of,
        headless=payload.headless,
        max_posts=payload.max_posts,
    )
    return AutoPublishRunResponse(
        checked_at=result.checked_at,
        eligible_posts=result.eligible_posts,
        published_posts=result.published_posts,
        failed_posts=result.failed_posts,
        skipped_posts=result.skipped_posts,
        errors=result.errors,
        published_ids=result.published_ids,
        success=result.success,
    )


app.include_router(router)
