"""
Tool de publication sur LinkedIn via l'API officielle.
Nécessite un access token OAuth 2.0 avec scope: w_member_social.
"""

from __future__ import annotations

import json
import os
import urllib.request

LINKEDIN_POST_TOOL = {
    "name": "post_to_linkedin",
    "description": "Publie un post texte sur LinkedIn (compte personnel ou organisation).",
    "input_schema": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Texte du post LinkedIn (max 3000 chars).",
            },
            "dry_run": {
                "type": "boolean",
                "description": "Si true, simule la publication sans appel API réel.",
                "default": False,
            },
        },
        "required": ["text"],
    },
}


def post_to_linkedin(text: str, dry_run: bool = False) -> dict:
    """
    Publie sur LinkedIn via l'API Share.
    Variables d'environnement requises:
      - LINKEDIN_ACCESS_TOKEN
      - LINKEDIN_PERSON_URN  (format: urn:li:person:<id>)
    """
    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "preview": text[:200] + "..." if len(text) > 200 else text,
            "char_count": len(text),
        }

    token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    urn = os.getenv("LINKEDIN_PERSON_URN")

    if not token or not urn:
        return {
            "success": False,
            "error": "LINKEDIN_ACCESS_TOKEN ou LINKEDIN_PERSON_URN manquant dans .env",
        }

    payload = json.dumps(
        {
            "author": urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
    ).encode()

    req = urllib.request.Request(
        "https://api.linkedin.com/v2/ugcPosts",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            post_id = resp.headers.get("X-RestLi-Id", "unknown")
            return {
                "success": True,
                "post_id": post_id,
                "url": f"https://www.linkedin.com/feed/update/{post_id}/",
            }
    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.code}: {e.read().decode()}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
