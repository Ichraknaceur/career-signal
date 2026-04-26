"""
Tools de récupération de contenu web : URL générique, arXiv, GitHub.
Formatés comme tool definitions Anthropic SDK.
"""

from __future__ import annotations

import re
import urllib.parse
import urllib.request

# ── Tool definitions ─────────────────────────────────────────────────────────

FETCH_URL_TOOL = {
    "name": "fetch_url",
    "description": "Récupère le contenu brut d'une URL (HTML ou texte).",
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL à récupérer."},
            "max_chars": {"type": "integer", "default": 15000},
        },
        "required": ["url"],
    },
}

FETCH_ARXIV_TOOL = {
    "name": "fetch_arxiv",
    "description": "Récupère le titre, le résumé et les auteurs d'un paper arXiv.",
    "input_schema": {
        "type": "object",
        "properties": {
            "arxiv_id": {
                "type": "string",
                "description": "ID arXiv (ex: '2301.07041' ou URL complète).",
            },
        },
        "required": ["arxiv_id"],
    },
}

FETCH_GITHUB_README_TOOL = {
    "name": "fetch_github_readme",
    "description": "Récupère le README d'un repo GitHub public.",
    "input_schema": {
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "description": "Format 'owner/repo' ou URL GitHub complète.",
            },
        },
        "required": ["repo"],
    },
}


# ── Implémentations ──────────────────────────────────────────────────────────


def fetch_url(url: str, max_chars: int = 15_000) -> str:
    """Récupère le contenu d'une URL et supprime les balises HTML basiques."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ContentAgent/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8", errors="replace")
        # Suppression HTML basique
        content = re.sub(r"<[^>]+>", " ", content)
        content = re.sub(r"\s{2,}", " ", content).strip()
        return content[:max_chars]
    except Exception as e:
        return f"Erreur fetch_url({url}): {e}"


def fetch_arxiv(arxiv_id: str) -> dict:
    """Interroge l'API arXiv pour récupérer les métadonnées d'un paper."""
    # Extraire l'ID si c'est une URL
    match = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", arxiv_id)
    if match:
        arxiv_id = match.group(1)

    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}&max_results=1"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = resp.read().decode("utf-8")

        title = re.search(r"<title>(.*?)</title>", data, re.DOTALL)
        summary = re.search(r"<summary>(.*?)</summary>", data, re.DOTALL)
        authors = re.findall(r"<name>(.*?)</name>", data)

        return {
            "arxiv_id": arxiv_id,
            "title": title.group(1).strip() if title else "Non trouvé",
            "summary": summary.group(1).strip() if summary else "Non trouvé",
            "authors": authors[:5],  # Top 5 auteurs
            "url": f"https://arxiv.org/abs/{arxiv_id}",
        }
    except Exception as e:
        return {"error": str(e), "arxiv_id": arxiv_id}


def fetch_github_readme(repo: str) -> str:
    """Récupère le README.md d'un repo GitHub via l'API raw."""
    # Normaliser : extraire owner/repo
    match = re.search(r"github\.com/([^/]+/[^/]+)", repo)
    if match:
        repo = match.group(1).rstrip("/")

    # Essayer README.md puis readme.md
    for filename in ("README.md", "readme.md", "README.rst"):
        url = f"https://raw.githubusercontent.com/{repo}/main/{filename}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ContentAgent/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.read().decode("utf-8", errors="replace")[:15_000]
        except Exception:
            continue

    return f"Erreur: README introuvable pour {repo}"
