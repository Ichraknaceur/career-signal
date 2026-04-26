"""
LinkedIn AutoPublish Pipeline.

Scanne les posts approuvés arrivés à échéance, les publie via Playwright,
et les marque comme publiés en cas de succès.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime

from tools.linkedin_poster import publish_posts_with_session
from tools.scheduler_tools import get_due_approved_posts, update_post_status

logger = logging.getLogger(__name__)


@dataclass
class LinkedInAutoPublishResult:
    checked_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    eligible_posts: int = 0
    published_posts: int = 0
    failed_posts: int = 0
    skipped_posts: int = 0
    errors: list[str] = field(default_factory=list)
    published_ids: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.failed_posts == 0


class LinkedInAutoPublishPipeline:
    """
    Publie automatiquement les posts LinkedIn approuvés et échus.
    """

    def __init__(
        self,
        batch_publisher: Callable[..., list[dict]] | None = None,
    ) -> None:
        self._batch_publisher = batch_publisher or self._publish_batch

    def run_once(
        self,
        email: str,
        password: str,
        as_of: date | None = None,
        headless: bool = True,
        callback: Callable[[str], None] | None = None,
        max_posts: int | None = None,
    ) -> LinkedInAutoPublishResult:
        cb = callback or (lambda _: None)
        result = LinkedInAutoPublishResult()

        due_posts = get_due_approved_posts(as_of=as_of)
        if max_posts is not None:
            due_posts = due_posts[:max_posts]

        result.eligible_posts = len(due_posts)
        cb(f"🗓️ {len(due_posts)} post(s) approuvé(s) à publier automatiquement.")

        if not due_posts:
            return result

        if not email or not password:
            error = "Credentials LinkedIn manquants pour l'autopublication."
            logger.error("[AutoPublish] %s", error)
            result.failed_posts = len(due_posts)
            result.errors.append(error)
            return result

        payload = [
            {
                "id": post.id,
                "content": post.content,
                "hashtags": post.hashtags,
            }
            for post in due_posts
        ]

        publish_results = self._batch_publisher(
            email=email,
            password=password,
            posts=payload,
            headless=headless,
            callback=cb,
        )

        for item in publish_results:
            post_id = item.get("id", "unknown")
            if item.get("success"):
                update_post_status(post_id, "published")
                result.published_posts += 1
                result.published_ids.append(post_id)
                cb(f"✅ Post publié automatiquement: {post_id}")
            else:
                result.failed_posts += 1
                error = item.get("error", f"Échec de publication pour {post_id}")
                result.errors.append(error)
                cb(f"❌ {error}")

        return result

    @staticmethod
    def _publish_batch(
        email: str,
        password: str,
        posts: list[dict],
        headless: bool = True,
        callback: Callable[[str], None] | None = None,
    ) -> list[dict]:
        return asyncio.run(
            publish_posts_with_session(
                email=email,
                password=password,
                posts=posts,
                headless=headless,
                callback=callback,
            )
        )
