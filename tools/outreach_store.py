"""
Outreach Store — Phase 3.

Modèle de données OutreachRecord + CRUD JSON local.
Fichier de stockage : data/outreach.json

Statuts : pending → approved | rejected → sent → accepted | ignored
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import asdict, dataclass, field
from datetime import datetime

DATA_DIR = pathlib.Path("./data")
OUTREACH_FILE = DATA_DIR / "outreach.json"
COOKIES_FILE = DATA_DIR / "linkedin_cookies.json"
DAILY_LOG_FILE = DATA_DIR / "outreach_daily.json"


# ── Modèle ───────────────────────────────────────────────────────────────────
@dataclass
class OutreachRecord:
    """Un profil LinkedIn ciblé dans une campagne d'outreach."""

    id: str
    campaign_id: str  # ID de la campagne (keyword + date)
    profile_url: str
    name: str
    title: str  # Poste actuel
    company: str
    location: str = ""
    about: str = ""  # Extrait du "À propos" (500 chars max)

    # Note générée par l'agent
    note: str = ""  # ≤ 300 chars
    note_language: str = "English"

    # Workflow
    status: str = "pending"  # pending | approved | rejected | sent | accepted | skipped | ignored
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    sent_at: str | None = None
    accepted_at: str | None = None
    user_feedback: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> OutreachRecord:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── Helpers ──────────────────────────────────────────────────────────────────
def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_raw() -> list[dict]:
    if not OUTREACH_FILE.exists():
        return []
    try:
        return json.loads(OUTREACH_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_raw(records: list[dict]) -> None:
    _ensure_data_dir()
    OUTREACH_FILE.write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ── CRUD ─────────────────────────────────────────────────────────────────────
def load_records() -> list[OutreachRecord]:
    return [OutreachRecord.from_dict(d) for d in _load_raw() if _is_valid(d)]


def _is_valid(d: dict) -> bool:
    try:
        OutreachRecord.from_dict(d)
        return True
    except Exception:
        return False


def add_records(records: list[OutreachRecord]) -> int:
    existing = load_records()
    # Dédupliquer par profile_url
    existing_urls = {r.profile_url for r in existing}
    new = [r for r in records if r.profile_url not in existing_urls]
    _save_raw([r.to_dict() for r in existing + new])
    return len(new)


def update_record_status(
    record_id: str,
    status: str,
    feedback: str | None = None,
) -> bool:
    records = load_records()
    for r in records:
        if r.id == record_id:
            r.status = status
            if feedback:
                r.user_feedback = feedback
            if status == "sent":
                r.sent_at = datetime.utcnow().isoformat() + "Z"
            elif status == "accepted":
                r.accepted_at = datetime.utcnow().isoformat() + "Z"
            _save_raw([r.to_dict() for r in records])
            return True
    return False


def update_record_note(record_id: str, note: str) -> bool:
    records = load_records()
    for r in records:
        if r.id == record_id:
            r.note = note[:300]  # LinkedIn 300 chars max
            _save_raw([r.to_dict() for r in records])
            return True
    return False


def get_approved_records() -> list[OutreachRecord]:
    return [r for r in load_records() if r.status == "approved"]


def get_records_by_campaign(campaign_id: str) -> list[OutreachRecord]:
    return [r for r in load_records() if r.campaign_id == campaign_id]


def get_records_by_status(status: str) -> list[OutreachRecord]:
    return [r for r in load_records() if r.status == status]


# ── Rate limiting ─────────────────────────────────────────────────────────────
def get_sent_today() -> int:
    """Nombre de connexions envoyées aujourd'hui."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    records = load_records()
    return sum(
        1
        for r in records
        if r.status in ("sent", "accepted") and r.sent_at and r.sent_at.startswith(today)
    )


def can_send_today(daily_limit: int = 15) -> bool:
    return get_sent_today() < daily_limit


def remaining_today(daily_limit: int = 15) -> int:
    return max(0, daily_limit - get_sent_today())


# ── Cookies LinkedIn (session persistante) ────────────────────────────────────
def save_cookies(cookies: list[dict]) -> None:
    _ensure_data_dir()
    COOKIES_FILE.write_text(
        json.dumps(cookies, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_cookies() -> list[dict]:
    if not COOKIES_FILE.exists():
        return []
    try:
        return json.loads(COOKIES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def has_saved_session() -> bool:
    return COOKIES_FILE.exists() and len(load_cookies()) > 0


# ── Stats campagne ────────────────────────────────────────────────────────────
def get_campaign_stats() -> dict:
    records = load_records()
    return {
        "total": len(records),
        "pending": sum(1 for r in records if r.status == "pending"),
        "approved": sum(1 for r in records if r.status == "approved"),
        "rejected": sum(1 for r in records if r.status == "rejected"),
        "sent": sum(1 for r in records if r.status == "sent"),
        "accepted": sum(1 for r in records if r.status == "accepted"),
        "sent_today": get_sent_today(),
    }
