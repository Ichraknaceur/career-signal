"""
Tool de publication sur Medium via l'API officielle.
Nécessite un Integration Token Medium.
"""

from __future__ import annotations

import json
import os
import urllib.request

MEDIUM_POST_TOOL = {
    "name": "post_to_medium",
    "description": "Publie un article sur Medium en Markdown.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Titre de l'article."},
            "content": {"type": "string", "description": "Corps de l'article en Markdown."},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags (max 5).",
                "default": [],
            },
            "publish_status": {
                "type": "string",
                "enum": ["public", "draft", "unlisted"],
                "default": "draft",
                "description": "Statut de publication.",
            },
            "dry_run": {
                "type": "boolean",
                "default": False,
                "description": "Si true, simule sans appel API réel.",
            },
        },
        "required": ["title", "content"],
    },
}


def post_to_medium(
    title: str,
    content: str,
    tags: list[str] | None = None,
    publish_status: str = "draft",
    dry_run: bool = False,
) -> dict:
    """
    Publie sur Medium via l'API Integration.
    Variables d'environnement requises:
      - MEDIUM_INTEGRATION_TOKEN
    """
    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "title": title,
            "char_count": len(content),
            "tags": tags or [],
        }

    token = os.getenv("MEDIUM_INTEGRATION_TOKEN")
    if not token:
        return {"success": False, "error": "MEDIUM_INTEGRATION_TOKEN manquant dans .env"}

    # Récupérer l'ID utilisateur
    try:
        req = urllib.request.Request(
            "https://api.medium.com/v1/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            user_data = json.loads(resp.read())
        user_id = user_data["data"]["id"]
    except Exception as e:
        return {"success": False, "error": f"Erreur auth Medium: {e}"}

    # Publier l'article
    payload = json.dumps(
        {
            "title": title,
            "contentFormat": "markdown",
            "content": f"# {title}\n\n{content}",
            "tags": (tags or [])[:5],
            "publishStatus": publish_status,
        }
    ).encode()

    req = urllib.request.Request(
        f"https://api.medium.com/v1/users/{user_id}/posts",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
        post = result["data"]
        return {
            "success": True,
            "post_id": post["id"],
            "url": post["url"],
            "title": post["title"],
        }
    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.code}: {e.read().decode()}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
