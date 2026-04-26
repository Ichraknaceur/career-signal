"""
Scheduler Tools — Phase 2.

Modèle de données ScheduledPost + CRUD JSON local.
Fichier de stockage : data/schedule.json

Statuts : draft → approved | rejected → published
Pilliers : expertise_ia | projets | promo_medium
Jours    : monday | wednesday | friday
"""

from __future__ import annotations

import json
import pathlib
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta

# ── Chemins ─────────────────────────────────────────────────────────────────
DATA_DIR = pathlib.Path("./data")
SCHEDULE_FILE = DATA_DIR / "schedule.json"
MEDIUM_PUBLISHED_FILE = DATA_DIR / "medium_published.json"

# Jours de publication (0=lundi, 2=mercredi, 4=vendredi)
PUBLISH_DAYS = [0, 2, 4]
DAY_NAMES = {0: "monday", 2: "wednesday", 4: "friday"}

# Rotation des pilliers par jour
PILLAR_BY_DAY = {
    "monday": "expertise_ia",
    "wednesday": "projets",
    "friday": "promo_medium",
}

PILLARS = ["expertise_ia", "projets", "promo_medium"]
PILLAR_LABELS = {
    "expertise_ia": "🧠 Expertise IA",
    "projets": "🛠️ Projets",
    "promo_medium": "📣 Promo Medium",
}


# ── Modèle de données ────────────────────────────────────────────────────────
@dataclass
class ScheduledPost:
    """Un post LinkedIn planifié dans le calendrier éditorial."""

    id: str
    pillar: str  # expertise_ia | projets | promo_medium
    day_of_week: str  # monday | wednesday | friday
    week_number: int  # 1-based (semaine 1, 2, ...)
    scheduled_date: str  # YYYY-MM-DD
    content: str  # Corps du post
    hashtags: list[str] = field(default_factory=list)
    status: str = "draft"  # draft | approved | rejected | published
    medium_article_url: str | None = None  # Si pillar == promo_medium
    medium_article_title: str | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    published_at: str | None = None
    user_feedback: str | None = None  # Feedback en cas de rejet ou demande d'édition

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> ScheduledPost:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── Helpers ──────────────────────────────────────────────────────────────────
def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_raw() -> list[dict]:
    if not SCHEDULE_FILE.exists():
        return []
    try:
        return json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_raw(posts: list[dict]) -> None:
    _ensure_data_dir()
    SCHEDULE_FILE.write_text(
        json.dumps(posts, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ── CRUD principal ───────────────────────────────────────────────────────────
def load_posts() -> list[ScheduledPost]:
    """Charge tous les posts depuis schedule.json."""
    raw = _load_raw()
    posts = []
    for d in raw:
        try:
            posts.append(ScheduledPost.from_dict(d))
        except Exception:
            pass  # Entrée corrompue — on ignore
    return posts


def save_posts(posts: list[ScheduledPost]) -> None:
    """Écrase schedule.json avec la liste fournie."""
    _save_raw([p.to_dict() for p in posts])


def add_posts(new_posts: list[ScheduledPost]) -> None:
    """Ajoute des posts à schedule.json sans écraser l'existant."""
    existing = load_posts()
    all_posts = existing + new_posts
    save_posts(all_posts)


def get_drafts() -> list[ScheduledPost]:
    """Retourne uniquement les posts en statut 'draft'."""
    return [p for p in load_posts() if p.status == "draft"]


def get_posts_by_status(status: str) -> list[ScheduledPost]:
    """Filtre les posts par statut."""
    return [p for p in load_posts() if p.status == status]


def get_due_approved_posts(as_of: date | None = None) -> list[ScheduledPost]:
    """
    Retourne les posts approuvés dont la date planifiée est échue.

    Args:
        as_of: Date de référence (défaut = aujourd'hui).
    """
    reference_date = as_of or date.today()
    due_posts: list[ScheduledPost] = []

    for post in load_posts():
        if post.status != "approved":
            continue
        try:
            scheduled = date.fromisoformat(post.scheduled_date)
        except ValueError:
            continue
        if scheduled <= reference_date:
            due_posts.append(post)

    due_posts.sort(key=lambda p: (p.scheduled_date, p.created_at))
    return due_posts


def get_posts_by_week(week_number: int) -> list[ScheduledPost]:
    """Retourne tous les posts d'une semaine donnée."""
    return [p for p in load_posts() if p.week_number == week_number]


def update_post_status(
    post_id: str,
    status: str,
    user_feedback: str | None = None,
) -> bool:
    """
    Met à jour le statut d'un post (approved | rejected | published).
    Retourne True si le post a été trouvé et mis à jour.
    """
    posts = load_posts()
    for p in posts:
        if p.id == post_id:
            p.status = status
            if user_feedback:
                p.user_feedback = user_feedback
            if status == "published":
                p.published_at = datetime.utcnow().isoformat() + "Z"
            save_posts(posts)
            return True
    return False


def update_post_content(
    post_id: str,
    content: str,
    hashtags: list[str] | None = None,
) -> bool:
    """
    Met à jour le contenu (et optionnellement les hashtags) d'un post.
    Retourne True si trouvé.
    """
    posts = load_posts()
    for p in posts:
        if p.id == post_id:
            p.content = content
            if hashtags is not None:
                p.hashtags = hashtags
            save_posts(posts)
            return True
    return False


def delete_post(post_id: str) -> bool:
    """Supprime un post de la liste. Retourne True si trouvé."""
    posts = load_posts()
    new_posts = [p for p in posts if p.id != post_id]
    if len(new_posts) < len(posts):
        save_posts(new_posts)
        return True
    return False


def get_weeks_summary() -> dict[int, dict]:
    """
    Retourne un résumé par semaine pour l'affichage UI.
    Format: {week_number: {"posts": [...], "approved": int, "draft": int, ...}}
    """
    posts = load_posts()
    summary: dict[int, dict] = {}
    for p in posts:
        if p.week_number not in summary:
            summary[p.week_number] = {
                "posts": [],
                "draft": 0,
                "approved": 0,
                "rejected": 0,
                "published": 0,
            }
        summary[p.week_number]["posts"].append(p)
        summary[p.week_number][p.status] = summary[p.week_number].get(p.status, 0) + 1
    return summary


# ── Medium articles publiés (pour le pillier promo_medium) ──────────────────
def get_published_medium_articles() -> list[dict]:
    """
    Retourne les articles Medium publiés (stockés dans data/medium_published.json).
    Format: [{"title": "...", "url": "...", "published_at": "...", "tags": [...]}]
    """
    if not MEDIUM_PUBLISHED_FILE.exists():
        return []
    try:
        return json.loads(MEDIUM_PUBLISHED_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def record_medium_publication(title: str, url: str, tags: list[str]) -> None:
    """
    Enregistre un article Medium publié pour usage futur par le pillier promo_medium.
    Appelé automatiquement par MediumPublisher après publication.
    """
    _ensure_data_dir()
    articles = get_published_medium_articles()
    articles.append(
        {
            "title": title,
            "url": url,
            "tags": tags,
            "published_at": datetime.utcnow().isoformat() + "Z",
        }
    )
    MEDIUM_PUBLISHED_FILE.write_text(
        json.dumps(articles, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ── Calcul des dates de publication ─────────────────────────────────────────
def compute_scheduled_dates(nb_weeks: int, start_date: date | None = None) -> list[dict]:
    """
    Calcule les dates Mon/Wed/Fri pour les nb_weeks prochaines semaines.
    start_date : date de début (défaut = lundi prochain ou aujourd'hui si lundi).

    Retourne une liste de dicts :
    [{"week": 1, "day": "monday", "date": "2026-04-27"}, ...]
    """
    if start_date is None:
        today = date.today()
        # Trouver le prochain lundi (ou aujourd'hui si c'est lundi)
        days_until_monday = (7 - today.weekday()) % 7
        start_date = today + timedelta(days=days_until_monday)

    slots = []
    for week in range(1, nb_weeks + 1):
        week_start = start_date + timedelta(weeks=week - 1)
        for offset, day_name in DAY_NAMES.items():
            slot_date = week_start + timedelta(days=offset)
            slots.append(
                {
                    "week": week,
                    "day": day_name,
                    "date": slot_date.isoformat(),
                    "pillar": PILLAR_BY_DAY[day_name],
                }
            )
    return slots


# ── Outil Anthropic (tool_use) ───────────────────────────────────────────────
SCHEDULE_POST_TOOL = {
    "name": "schedule_post",
    "description": "Programme un post LinkedIn dans le calendrier éditorial.",
    "input_schema": {
        "type": "object",
        "properties": {
            "pillar": {
                "type": "string",
                "enum": PILLARS,
                "description": "Pillier éditorial du post.",
            },
            "day_of_week": {
                "type": "string",
                "enum": ["monday", "wednesday", "friday"],
                "description": "Jour de publication.",
            },
            "week_number": {
                "type": "integer",
                "description": "Numéro de la semaine (1-based).",
            },
            "scheduled_date": {
                "type": "string",
                "description": "Date ISO (YYYY-MM-DD) de la publication.",
            },
            "content": {
                "type": "string",
                "description": "Corps du post LinkedIn (≤ 1300 chars).",
            },
            "hashtags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Hashtags (max 5, avec #).",
            },
            "medium_article_url": {
                "type": "string",
                "description": "URL de l'article Medium (pour pillar promo_medium uniquement).",
            },
            "medium_article_title": {
                "type": "string",
                "description": "Titre de l'article Medium promu (pour pillar promo_medium uniquement).",
            },
        },
        "required": ["pillar", "day_of_week", "week_number", "scheduled_date", "content"],
    },
}


def create_scheduled_post_from_tool_input(tool_input: dict) -> ScheduledPost:
    """Factory : crée un ScheduledPost depuis le tool_input de l'LLM."""
    return ScheduledPost(
        id=str(uuid.uuid4()),
        pillar=tool_input["pillar"],
        day_of_week=tool_input["day_of_week"],
        week_number=tool_input["week_number"],
        scheduled_date=tool_input["scheduled_date"],
        content=tool_input["content"],
        hashtags=tool_input.get("hashtags", [])[:5],
        status="draft",
        medium_article_url=tool_input.get("medium_article_url"),
        medium_article_title=tool_input.get("medium_article_title"),
    )


def schedule_post(platform: str, content: str, publish_at: str | None = None) -> dict:
    """
    Helper legacy utilisé par PublisherAgent.

    Programme un post minimal dans `schedule.json` pour conserver la compatibilité
    avec l'ancien flow orienté tools.
    """
    if platform.lower() != "linkedin":
        return {"success": False, "error": f"Platform non supportée: {platform}"}

    scheduled_date = publish_at or date.today().isoformat()
    post = ScheduledPost(
        id=str(uuid.uuid4()),
        pillar="projets",
        day_of_week=date.fromisoformat(scheduled_date).strftime("%A").lower(),
        week_number=1,
        scheduled_date=scheduled_date,
        content=content,
        status="draft",
    )
    add_posts([post])
    return {"success": True, "post_id": post.id, "scheduled_date": scheduled_date}
