#!/usr/bin/env python3
"""
Entrypoint CLI de CareerSignal.

Usage:
  python main.py --source "2301.07041" --type arxiv
  python main.py --source "anthropics/claude-code" --type github_repo
  python main.py --source "J'ai trouvé une technique pour réduire les hallucinations de 40%" --type raw_idea
  python main.py --source "./mon_article.pdf" --type pdf --mode live
"""

from __future__ import annotations

import argparse
import logging
import sys

from core.config import settings
from core.memory import SourceType
from orchestrator import ContentOrchestrator


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CareerSignal — contenu, reseau, veille et publication pour la recherche d'emploi",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--source", required=True, help="Contenu source : URL, chemin, ID arXiv ou texte"
    )
    parser.add_argument(
        "--type",
        choices=[t.value for t in SourceType],
        default="raw_idea",
        help="Type de source (défaut: raw_idea)",
    )
    parser.add_argument(
        "--mode",
        choices=["dry_run", "live"],
        default="dry_run",
        help="Mode publication (défaut: dry_run — aucun appel API réel)",
    )
    parser.add_argument("--max-revisions", type=int, default=2, help="Nombre max de révisions QA")
    parser.add_argument("--log-level", default=settings.log_level, help="Niveau de log")

    args = parser.parse_args()
    setup_logging(args.log_level)

    if args.mode == "live":
        print("⚠️  Mode LIVE activé — les posts seront publiés réellement !")
        confirm = input("Confirme avec 'yes' pour continuer : ")
        if confirm.strip().lower() != "yes":
            print("Annulé.")
            return 0

    orchestrator = ContentOrchestrator(publish_mode=args.mode)
    state = orchestrator.run(
        source_content=args.source,
        source_type=SourceType(args.type),
        max_revisions=args.max_revisions,
    )

    return 0 if state.linkedin_post_url or state.medium_post_url else 1


if __name__ == "__main__":
    sys.exit(main())
