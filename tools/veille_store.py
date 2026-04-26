"""
Veille Store — Phase 4.

Persistance JSON pour les sources RSS et les articles scrappés.

Modèle :
  VeilleSource  → flux RSS ou URL à surveiller
  VeilleArticle → article extrait, résumé + post LinkedIn suggéré
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import asdict, dataclass, field
from datetime import datetime

DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

SOURCES_FILE = DATA_DIR / "veille_sources.json"
ARTICLES_FILE = DATA_DIR / "veille_articles.json"


# ── Modèles ───────────────────────────────────────────────────────────────────
@dataclass
class VeilleSource:
    id: str
    name: str  # ex: "Towards Data Science"
    url: str  # URL du flux RSS ou de la page
    category: str = "IA"  # IA / LLM / RAG / Data / Général
    active: bool = True
    rss: bool = True  # True = flux RSS, False = scraping direct
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    last_fetched: str | None = None
    article_count: int = 0


@dataclass
class VeilleArticle:
    id: str
    source_id: str
    source_name: str
    url: str
    title: str
    content: str = ""  # Contenu extrait (tronqué à 3000 chars)
    summary: str = ""  # Résumé LLM (~150 mots)
    suggested_post: str = ""  # Post LinkedIn prêt à publier
    published_at: str = ""  # Date de publication de l'article
    fetched_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    status: str = "new"  # new | read | used | ignored
    category: str = "IA"


# ── Sources CRUD ──────────────────────────────────────────────────────────────
def _load_sources() -> list[VeilleSource]:
    if not SOURCES_FILE.exists():
        return []
    try:
        data = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
        return [VeilleSource(**d) for d in data]
    except Exception:
        return []


def _save_sources(sources: list[VeilleSource]) -> None:
    SOURCES_FILE.write_text(
        json.dumps([asdict(s) for s in sources], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_sources(active_only: bool = False) -> list[VeilleSource]:
    sources = _load_sources()
    if active_only:
        sources = [s for s in sources if s.active]
    return sources


def add_source(source: VeilleSource) -> bool:
    """Ajoute une source si l'URL n'existe pas déjà. Retourne True si ajoutée."""
    sources = _load_sources()
    if any(s.url == source.url for s in sources):
        return False
    sources.append(source)
    _save_sources(sources)
    return True


def update_source(source_id: str, **kwargs) -> None:
    sources = _load_sources()
    for s in sources:
        if s.id == source_id:
            for k, v in kwargs.items():
                if hasattr(s, k):
                    setattr(s, k, v)
            break
    _save_sources(sources)


def delete_source(source_id: str) -> None:
    sources = [s for s in _load_sources() if s.id != source_id]
    _save_sources(sources)


def toggle_source(source_id: str) -> bool:
    """Active/désactive une source. Retourne le nouvel état."""
    sources = _load_sources()
    new_state = True
    for s in sources:
        if s.id == source_id:
            s.active = not s.active
            new_state = s.active
            break
    _save_sources(sources)
    return new_state


# ── Articles CRUD ─────────────────────────────────────────────────────────────
def _load_articles() -> list[VeilleArticle]:
    if not ARTICLES_FILE.exists():
        return []
    try:
        data = json.loads(ARTICLES_FILE.read_text(encoding="utf-8"))
        return [VeilleArticle(**d) for d in data]
    except Exception:
        return []


def _save_articles(articles: list[VeilleArticle]) -> None:
    ARTICLES_FILE.write_text(
        json.dumps([asdict(a) for a in articles], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_articles(
    status: str | None = None,
    source_id: str | None = None,
    limit: int = 100,
) -> list[VeilleArticle]:
    articles = _load_articles()
    if status:
        articles = [a for a in articles if a.status == status]
    if source_id:
        articles = [a for a in articles if a.source_id == source_id]
    # Plus récents en premier
    articles.sort(key=lambda a: a.fetched_at, reverse=True)
    return articles[:limit]


def url_already_fetched(url: str) -> bool:
    return any(a.url == url for a in _load_articles())


def add_articles(articles: list[VeilleArticle]) -> int:
    """Ajoute les articles dont l'URL n'existe pas encore. Retourne le nb ajoutés."""
    existing = _load_articles()
    existing_urls = {a.url for a in existing}
    new_ones = [a for a in articles if a.url not in existing_urls]
    if new_ones:
        _save_articles(existing + new_ones)
    return len(new_ones)


def update_article(article_id: str, **kwargs) -> None:
    articles = _load_articles()
    for a in articles:
        if a.id == article_id:
            for k, v in kwargs.items():
                if hasattr(a, k):
                    setattr(a, k, v)
            break
    _save_articles(articles)


def update_article_status(article_id: str, status: str) -> None:
    update_article(article_id, status=status)


def get_veille_stats() -> dict:
    articles = _load_articles()
    return {
        "total": len(articles),
        "new": sum(1 for a in articles if a.status == "new"),
        "read": sum(1 for a in articles if a.status == "read"),
        "used": sum(1 for a in articles if a.status == "used"),
        "ignored": sum(1 for a in articles if a.status == "ignored"),
        "with_summary": sum(1 for a in articles if a.summary),
        "with_post": sum(1 for a in articles if a.suggested_post),
        "sources": len(get_sources()),
    }


# ── Sources par défaut (IA / LLM / RAG) ──────────────────────────────────────
DEFAULT_SOURCES: list[dict] = [
    {
        "name": "Towards Data Science",
        "url": "https://towardsdatascience.com/feed",
        "category": "Data/IA",
        "rss": True,
    },
    {
        "name": "The Batch (DeepLearning.AI)",
        "url": "https://www.deeplearning.ai/the-batch/feed/",
        "category": "LLM",
        "rss": True,
    },
    {
        "name": "Hugging Face Blog",
        "url": "https://huggingface.co/blog/feed.xml",
        "category": "LLM",
        "rss": True,
    },
    {
        "name": "Google AI Blog",
        "url": "https://blog.research.google/feeds/posts/default",
        "category": "IA",
        "rss": True,
    },
    {
        "name": "OpenAI Blog",
        "url": "https://openai.com/blog/rss.xml",
        "category": "LLM",
        "rss": True,
    },
    {
        "name": "LangChain Blog",
        "url": "https://blog.langchain.dev/rss/",
        "category": "RAG",
        "rss": True,
    },
    {
        "name": "Sebastian Raschka (AI newsletter)",
        "url": "https://magazine.sebastianraschka.com/feed",
        "category": "LLM",
        "rss": True,
    },
]


def seed_default_sources() -> int:
    """Initialise les sources par défaut si aucune n'existe. Retourne le nb ajoutées."""
    import uuid

    if get_sources():
        return 0
    added = 0
    for s in DEFAULT_SOURCES:
        source = VeilleSource(
            id=str(uuid.uuid4()),
            name=s["name"],
            url=s["url"],
            category=s["category"],
            rss=s["rss"],
        )
        if add_source(source):
            added += 1
    return added
