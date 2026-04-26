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
from datetime import UTC, date, datetime, time, timedelta

# ── Chemins ─────────────────────────────────────────────────────────────────
DATA_DIR = pathlib.Path("./data")
SCHEDULE_FILE = DATA_DIR / "schedule.json"
MEDIUM_PUBLISHED_FILE = DATA_DIR / "medium_published.json"
LINKEDIN_PROMPT_CONFIG_FILE = DATA_DIR / "linkedin_prompt_config.json"

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
DEFAULT_PUBLISH_TIMES = {
    "monday": "09:00",
    "wednesday": "12:30",
    "friday": "17:30",
}
DEFAULT_PROMPT_PROFILE = {
    "global_prompt": (
        "Write posts that sound credible, concrete, and grounded in real engineering work. "
        "Avoid generic AI hype and prefer practical insights."
    ),
    "voice_and_tone": (
        "Professional, warm, concise, and confident. Sound like an AI/Data candidate "
        "sharing real work and lessons learned."
    ),
    "cta_style": "End with a question or invitation that encourages thoughtful engagement.",
    "pillar_prompts": {
        "expertise_ia": (
            "Teach one concrete technical idea, framework, tradeoff, or engineering lesson. "
            "Favor clarity and usefulness over trend-chasing."
        ),
        "projets": (
            "Highlight real project execution: problem, constraint, implementation choice, "
            "result, and lesson learned."
        ),
        "promo_medium": (
            "Make the article feel worth reading by teasing 2-3 insights without repeating "
            "the full article."
        ),
    },
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
    scheduled_time: str = "09:00"  # HH:MM (heure locale)
    hashtags: list[str] = field(default_factory=list)
    status: str = "draft"  # draft | approved | rejected | published
    medium_article_url: str | None = None  # Si pillar == promo_medium
    medium_article_title: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
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


def _week_start(ref_date: date) -> date:
    return ref_date - timedelta(days=ref_date.weekday())


def _normalize_time_string(value: str | None, fallback_day: str | None = None) -> str:
    raw = (value or "").strip()
    if not raw:
        return DEFAULT_PUBLISH_TIMES.get(fallback_day or "", "09:00")
    try:
        parsed = time.fromisoformat(raw)
    except ValueError:
        return DEFAULT_PUBLISH_TIMES.get(fallback_day or "", "09:00")
    return parsed.strftime("%H:%M")


def _combine_local_datetime(post: ScheduledPost) -> datetime:
    post_date = date.fromisoformat(post.scheduled_date)
    post_time = time.fromisoformat(_normalize_time_string(post.scheduled_time, post.day_of_week))
    return datetime.combine(post_date, post_time)


def _normalize_posts_calendar(posts: list[ScheduledPost]) -> list[ScheduledPost]:
    if not posts:
        return posts

    week_starts = sorted({_week_start(date.fromisoformat(post.scheduled_date)) for post in posts})
    week_map = {week_start: index for index, week_start in enumerate(week_starts, start=1)}

    for post in posts:
        scheduled = date.fromisoformat(post.scheduled_date)
        post.day_of_week = scheduled.strftime("%A").lower()
        post.week_number = week_map[_week_start(scheduled)]
        post.scheduled_time = _normalize_time_string(post.scheduled_time, post.day_of_week)

    posts.sort(key=lambda post: (_combine_local_datetime(post), post.created_at))
    return posts


def get_default_prompt_profile() -> dict:
    return json.loads(json.dumps(DEFAULT_PROMPT_PROFILE))


def load_prompt_profile() -> dict:
    if not LINKEDIN_PROMPT_CONFIG_FILE.exists():
        return get_default_prompt_profile()
    try:
        raw = json.loads(LINKEDIN_PROMPT_CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return get_default_prompt_profile()

    merged = get_default_prompt_profile()
    merged["global_prompt"] = str(raw.get("global_prompt", merged["global_prompt"])).strip()
    merged["voice_and_tone"] = str(raw.get("voice_and_tone", merged["voice_and_tone"])).strip()
    merged["cta_style"] = str(raw.get("cta_style", merged["cta_style"])).strip()
    pillar_prompts = raw.get("pillar_prompts", {})
    if isinstance(pillar_prompts, dict):
        for pillar in PILLARS:
            if pillar in pillar_prompts:
                merged["pillar_prompts"][pillar] = str(pillar_prompts[pillar]).strip()
    return merged


def save_prompt_profile(profile: dict) -> dict:
    _ensure_data_dir()
    normalized = get_default_prompt_profile()
    normalized["global_prompt"] = str(
        profile.get("global_prompt", normalized["global_prompt"])
    ).strip()
    normalized["voice_and_tone"] = str(
        profile.get("voice_and_tone", normalized["voice_and_tone"])
    ).strip()
    normalized["cta_style"] = str(profile.get("cta_style", normalized["cta_style"])).strip()
    pillar_prompts = profile.get("pillar_prompts", {})
    if isinstance(pillar_prompts, dict):
        for pillar in PILLARS:
            normalized["pillar_prompts"][pillar] = str(
                pillar_prompts.get(pillar, normalized["pillar_prompts"][pillar])
            ).strip()

    LINKEDIN_PROMPT_CONFIG_FILE.write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return normalized


def build_background_prompt(pillar: str, prompt_profile: dict | None = None) -> str:
    profile = prompt_profile or load_prompt_profile()
    pillar_prompts = profile.get("pillar_prompts", {})
    pillar_instruction = ""
    if isinstance(pillar_prompts, dict):
        pillar_instruction = str(pillar_prompts.get(pillar, "")).strip()

    sections = [
        "Background prompt instructions:",
        f"- Global guidance: {str(profile.get('global_prompt', '')).strip()}",
        f"- Voice and tone: {str(profile.get('voice_and_tone', '')).strip()}",
        f"- CTA style: {str(profile.get('cta_style', '')).strip()}",
    ]
    if pillar_instruction:
        sections.append(f"- Pillar-specific guidance ({pillar}): {pillar_instruction}")
    return "\n".join(sections)


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
    normalized_posts = _normalize_posts_calendar(posts)
    _save_raw([p.to_dict() for p in normalized_posts])


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


def get_due_approved_posts(as_of: date | datetime | None = None) -> list[ScheduledPost]:
    """
    Retourne les posts approuvés dont la date planifiée est échue.

    Args:
        as_of: Date de référence (défaut = aujourd'hui).
    """
    if as_of is None:
        reference_dt = datetime.now()
    elif isinstance(as_of, datetime):
        reference_dt = as_of
    else:
        reference_dt = datetime.combine(as_of, time.max)
    due_posts: list[ScheduledPost] = []

    for post in load_posts():
        if post.status != "approved":
            continue
        try:
            scheduled = _combine_local_datetime(post)
        except ValueError:
            continue
        if scheduled <= reference_dt:
            due_posts.append(post)

    due_posts.sort(key=lambda p: (_combine_local_datetime(p), p.created_at))
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
                p.published_at = datetime.now(UTC).isoformat()
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


def update_post_schedule(
    post_id: str,
    scheduled_date: str,
    scheduled_time: str | None = None,
) -> bool:
    """
    Met à jour la date/heure d'un post et renormalise l'organisation du calendrier.
    Retourne True si trouvé.
    """
    posts = load_posts()
    for post in posts:
        if post.id == post_id:
            post.scheduled_date = scheduled_date
            post.scheduled_time = _normalize_time_string(scheduled_time, post.day_of_week)
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
            "published_at": datetime.now(UTC).isoformat(),
        }
    )
    MEDIUM_PUBLISHED_FILE.write_text(
        json.dumps(articles, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ── Calcul des dates de publication ─────────────────────────────────────────
def compute_scheduled_dates(
    nb_weeks: int,
    start_date: date | None = None,
    publish_times: dict[str, str] | None = None,
) -> list[dict]:
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
    else:
        days_until_monday = (7 - start_date.weekday()) % 7
        start_date = start_date + timedelta(days=days_until_monday)

    publish_times_map = {**DEFAULT_PUBLISH_TIMES, **(publish_times or {})}

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
                    "time": _normalize_time_string(publish_times_map.get(day_name), day_name),
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
            "scheduled_time": {
                "type": "string",
                "description": "Heure locale HH:MM de publication.",
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
    scheduled_day = tool_input["day_of_week"]
    return ScheduledPost(
        id=str(uuid.uuid4()),
        pillar=tool_input["pillar"],
        day_of_week=scheduled_day,
        week_number=tool_input["week_number"],
        scheduled_date=tool_input["scheduled_date"],
        scheduled_time=_normalize_time_string(tool_input.get("scheduled_time"), scheduled_day),
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

    publish_at_value = (publish_at or date.today().isoformat()).strip()
    try:
        publish_dt = datetime.fromisoformat(publish_at_value)
        scheduled_date = publish_dt.date().isoformat()
        scheduled_time = publish_dt.time().strftime("%H:%M")
    except ValueError:
        scheduled_date = publish_at_value
        scheduled_time = DEFAULT_PUBLISH_TIMES["monday"]
    post = ScheduledPost(
        id=str(uuid.uuid4()),
        pillar="projets",
        day_of_week=date.fromisoformat(scheduled_date).strftime("%A").lower(),
        week_number=1,
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        content=content,
        status="draft",
    )
    add_posts([post])
    return {
        "success": True,
        "post_id": post.id,
        "scheduled_date": scheduled_date,
        "scheduled_time": scheduled_time,
    }
