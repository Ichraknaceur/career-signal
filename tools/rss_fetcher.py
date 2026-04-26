"""
RSS Fetcher — Phase 4.

Récupère les articles depuis des flux RSS (xml stdlib) et
des pages web directes (requests + BeautifulSoup).

Pas de dépendance à feedparser — utilise uniquement xml.etree + requests + bs4.
"""

from __future__ import annotations

import logging
import re
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

import requests  # type: ignore[import-untyped]
from bs4 import BeautifulSoup

from tools.veille_store import VeilleArticle, VeilleSource

logger = logging.getLogger(__name__)

# ── HTTP Session ──────────────────────────────────────────────────────────────
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/atom+xml, text/xml, */*",
}
_TIMEOUT = 15


# ── Namespaces RSS / Atom ─────────────────────────────────────────────────────
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "media": "http://search.yahoo.com/mrss/",
}


def _text(el: ET.Element | None) -> str:
    if el is None:
        return ""
    return (el.text or "").strip()


def _clean_html(raw: str) -> str:
    """Supprime les balises HTML et nettoie le texte."""
    if not raw:
        return ""
    soup = BeautifulSoup(raw, "html.parser")
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:3000]


def _parse_date(date_str: str) -> str:
    """Convertit une date RSS/Atom en ISO format."""
    if not date_str:
        return datetime.utcnow().isoformat() + "Z"
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.isoformat()
    except Exception:
        pass
    try:
        # Atom format: 2024-01-15T10:30:00Z
        return date_str[:19] + "Z"
    except Exception:
        return datetime.utcnow().isoformat() + "Z"


# ── Parseur RSS 2.0 ───────────────────────────────────────────────────────────
def _parse_rss2(root: ET.Element, source: VeilleSource, max_items: int) -> list[VeilleArticle]:
    articles = []
    channel = root.find("channel")
    if channel is None:
        return []

    for item in channel.findall("item")[:max_items]:
        title = _text(item.find("title"))
        link = _text(item.find("link"))
        if not link:
            # Parfois le lien est dans guid
            guid = item.find("guid")
            if guid is not None and guid.get("isPermaLink", "true") == "true":
                link = _text(guid)

        if not link or not title:
            continue

        # Contenu : content:encoded > description
        content_el = item.find("content:encoded", _NS)
        desc_el = item.find("description")
        raw_content = _text(content_el) if content_el is not None else _text(desc_el)
        content = _clean_html(raw_content)

        pub_date = _text(item.find("pubDate"))

        articles.append(
            VeilleArticle(
                id=str(uuid.uuid4()),
                source_id=source.id,
                source_name=source.name,
                url=link,
                title=title,
                content=content,
                published_at=_parse_date(pub_date),
                category=source.category,
            )
        )

    return articles


# ── Parseur Atom ──────────────────────────────────────────────────────────────
def _parse_atom(root: ET.Element, source: VeilleSource, max_items: int) -> list[VeilleArticle]:
    articles = []
    ns = "http://www.w3.org/2005/Atom"

    for entry in root.findall(f"{{{ns}}}entry")[:max_items]:
        title_el = entry.find(f"{{{ns}}}title")
        title = _text(title_el)

        # Lien : prefer type=html ou rel=alternate
        link = ""
        for link_el in entry.findall(f"{{{ns}}}link"):
            rel = link_el.get("rel", "alternate")
            if rel in ("alternate", ""):
                link = link_el.get("href", "")
                break
        if not link:
            fallback_link_el = entry.find(f"{{{ns}}}link")
            if fallback_link_el is not None:
                link = fallback_link_el.get("href", "")

        if not link or not title:
            continue

        # Contenu
        content_el = entry.find(f"{{{ns}}}content")
        summary_el = entry.find(f"{{{ns}}}summary")
        raw = _text(content_el) if content_el is not None else _text(summary_el)
        content = _clean_html(raw)

        pub_el = entry.find(f"{{{ns}}}published")
        if pub_el is None:
            pub_el = entry.find(f"{{{ns}}}updated")
        pub_date = _text(pub_el)

        articles.append(
            VeilleArticle(
                id=str(uuid.uuid4()),
                source_id=source.id,
                source_name=source.name,
                url=link,
                title=title,
                content=content,
                published_at=_parse_date(pub_date),
                category=source.category,
            )
        )

    return articles


# ── Fetch RSS ─────────────────────────────────────────────────────────────────
def fetch_rss(source: VeilleSource, max_items: int = 10) -> list[VeilleArticle]:
    """
    Récupère les articles d'un flux RSS/Atom.
    Retourne une liste de VeilleArticle (sans summary/post — à générer ensuite).
    """
    try:
        resp = requests.get(source.url, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        content = resp.content

        # Supprimer le BOM éventuel
        if content.startswith(b"\xef\xbb\xbf"):
            content = content[3:]

        root = ET.fromstring(content)
        tag = root.tag.lower()

        if "rss" in tag or root.tag == "rss":
            return _parse_rss2(root, source, max_items)
        elif "feed" in tag or "atom" in tag.lower():
            return _parse_atom(root, source, max_items)
        else:
            # Tenter RSS2 en fallback
            result = _parse_rss2(root, source, max_items)
            if not result:
                result = _parse_atom(root, source, max_items)
            return result

    except ET.ParseError as e:
        logger.error(f"[RSSFetcher] XML parse error ({source.url}): {e}")
        return []
    except requests.RequestException as e:
        logger.error(f"[RSSFetcher] HTTP error ({source.url}): {e}")
        return []
    except Exception as e:
        logger.error(f"[RSSFetcher] Erreur inattendue ({source.url}): {e}")
        return []


# ── Scraping direct (non-RSS) ─────────────────────────────────────────────────
def fetch_direct(source: VeilleSource, max_items: int = 5) -> list[VeilleArticle]:
    """
    Scrape une page web directement (fallback pour les sources sans RSS).
    Extrait les liens et titres d'articles depuis la page d'accueil.
    """
    try:
        resp = requests.get(source.url, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        articles = []
        seen_urls: set[str] = set()

        # Chercher les liens d'articles (heuristic : article / h2 / h3 avec lien)
        candidates = []
        for tag in ["article", "h2", "h3", "h1"]:
            for el in soup.find_all(tag):
                a = el.find("a", href=True)
                if a:
                    candidates.append(a)

        for a in candidates[: max_items * 3]:
            href_attr = a.get("href", "")
            if isinstance(href_attr, list):
                href = href_attr[0].strip() if href_attr else ""
            elif isinstance(href_attr, str):
                href = href_attr.strip()
            else:
                href = ""
            if not href or href.startswith("#") or href.startswith("javascript"):
                continue
            # Rendre l'URL absolue
            if href.startswith("/"):
                from urllib.parse import urlparse

                base = urlparse(source.url)
                href = f"{base.scheme}://{base.netloc}{href}"
            if href in seen_urls:
                continue
            seen_urls.add(href)

            title = a.get_text(strip=True) or href
            if len(title) < 10:
                continue

            # Scraper le contenu de l'article
            content = _scrape_article_content(href)

            articles.append(
                VeilleArticle(
                    id=str(uuid.uuid4()),
                    source_id=source.id,
                    source_name=source.name,
                    url=href,
                    title=title,
                    content=content,
                    published_at=datetime.utcnow().isoformat() + "Z",
                    category=source.category,
                )
            )

            if len(articles) >= max_items:
                break

        return articles

    except Exception as e:
        logger.error(f"[RSSFetcher] Direct scrape error ({source.url}): {e}")
        return []


def _scrape_article_content(url: str) -> str:
    """Extrait le texte principal d'un article web."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Supprimer nav, footer, ads
        for tag in ["nav", "footer", "aside", "script", "style", "header"]:
            for el in soup.find_all(tag):
                el.decompose()

        # Chercher le contenu principal
        main = (
            soup.find("article")
            or soup.find("main")
            or soup.find(class_=re.compile(r"article|content|post|entry", re.I))
            or soup.find("body")
        )

        if main:
            text = main.get_text(separator=" ")
            text = re.sub(r"\s+", " ", text).strip()
            return text[:3000]
        return ""
    except Exception:
        return ""


# ── Point d'entrée unifié ─────────────────────────────────────────────────────
def fetch_source(source: VeilleSource, max_items: int = 10) -> list[VeilleArticle]:
    """Dispatch RSS ou scraping direct selon source.rss."""
    if source.rss:
        return fetch_rss(source, max_items)
    else:
        return fetch_direct(source, max_items)
