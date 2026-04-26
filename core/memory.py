"""
Gestion de l'état partagé entre agents dans le pipeline.

Le ContentPipelineState est le "bus de données" qui circule
de l'Agent 1 jusqu'à l'Agent 6. Chaque agent enrichit l'état
sans écraser le travail des agents précédents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class SourceType(StrEnum):
    GITHUB_REPO = "github_repo"
    PDF = "pdf"
    ARXIV = "arxiv"
    RAW_IDEA = "raw_idea"
    URL = "url"


class QAVerdict(StrEnum):
    APPROVED = "approved"
    NEEDS_REVISION = "needs_revision"
    REJECTED = "rejected"


@dataclass
class ContentPipelineState:
    """
    État partagé qui circule à travers tous les agents du pipeline.
    Chaque agent enrichit l'état sans écraser le travail des précédents.
    """

    # --- Input (fourni par l'utilisateur) ---
    user_subject: str = ""  # Sujet explicite fourni par l'utilisateur
    source_type: SourceType = SourceType.RAW_IDEA
    source_content: str = ""  # URL, chemin fichier, arXiv ID ou texte brut
    language: str = "French"  # Langue de l'article et des posts générés

    # --- Agent 1 : Ingestion ---
    ingested_summary: str = ""
    key_ideas: list[str] = field(default_factory=list)
    technical_level: str = "intermediate"

    # --- Agent 2 : Strategist ---
    content_angle: str = ""
    hook: str = ""
    linkedin_enabled: bool = True
    medium_enabled: bool = True
    target_audience: str = ""

    # --- Agent 3 : LinkedIn Writer ---
    linkedin_draft: str = ""
    linkedin_hashtags: list[str] = field(default_factory=list)

    # --- Agent 4 : Medium Writer ---
    medium_title: str = ""
    medium_draft: str = ""
    medium_tags: list[str] = field(default_factory=list)

    # --- Agent 5 : QA Judge ---
    qa_verdict: QAVerdict | None = None
    qa_feedback: str = ""
    qa_score: float = 0.0
    revision_count: int = 0
    max_revisions: int = 2

    # --- Agent 6 : Publisher ---
    linkedin_post_url: str | None = None
    medium_post_url: str | None = None
    published_at: str | None = None
    publish_log: list[str] = field(default_factory=list)

    def needs_revision(self) -> bool:
        return (
            self.qa_verdict == QAVerdict.NEEDS_REVISION and self.revision_count < self.max_revisions
        )

    def is_ready_to_publish(self) -> bool:
        return self.qa_verdict == QAVerdict.APPROVED

    def log_event(self, message: str) -> None:
        from datetime import datetime

        ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        self.publish_log.append(f"[{ts}] {message}")
