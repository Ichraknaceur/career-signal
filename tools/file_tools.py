"""
Tools de lecture de fichiers locaux : texte, PDF, code.
Formatés comme tool definitions Anthropic SDK.
"""

from __future__ import annotations

import pathlib

# ── Tool definitions (format Anthropic) ──────────────────────────────────────

READ_FILE_TOOL = {
    "name": "read_file",
    "description": (
        "Lit le contenu d'un fichier local. "
        "Supporte .txt, .md, .py, .json, .yaml, .csv et tout fichier texte."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Chemin absolu ou relatif vers le fichier.",
            },
            "max_chars": {
                "type": "integer",
                "description": "Nombre maximum de caractères à retourner (défaut: 20000).",
                "default": 20000,
            },
        },
        "required": ["path"],
    },
}

READ_PDF_TOOL = {
    "name": "read_pdf",
    "description": "Extrait le texte d'un fichier PDF.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Chemin vers le fichier PDF.",
            },
        },
        "required": ["path"],
    },
}


# ── Implémentations ──────────────────────────────────────────────────────────


def read_file(path: str, max_chars: int = 20_000) -> str:
    """Lit un fichier texte et retourne son contenu tronqué si nécessaire."""
    p = pathlib.Path(path)
    if not p.exists():
        return f"Erreur: fichier introuvable → {path}"
    if not p.is_file():
        return f"Erreur: le chemin n'est pas un fichier → {path}"
    content = p.read_text(encoding="utf-8", errors="replace")
    if len(content) > max_chars:
        content = content[:max_chars] + f"\n\n[... tronqué à {max_chars} chars]"
    return content


def read_pdf(path: str) -> str:
    """Extrait le texte d'un PDF via pypdf (à installer si besoin)."""
    try:
        import pypdf

        reader = pypdf.PdfReader(path)
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        return text.strip() or "Aucun texte extractible dans ce PDF."
    except ImportError:
        return "Erreur: pypdf non installé. Lance: pip install pypdf"
    except Exception as e:
        return f"Erreur lecture PDF: {e}"
