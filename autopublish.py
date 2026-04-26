#!/usr/bin/env python3
"""
Worker d'autopublication LinkedIn.

Publie automatiquement les posts approuvés dont la date planifiée est atteinte.
"""

from __future__ import annotations

import argparse
import logging
import os
import time

from pipelines.linkedin_autopublish_pipeline import LinkedInAutoPublishPipeline


def _setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Autopublie les posts LinkedIn approuvés arrivés à échéance.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Exécute un seul cycle puis s'arrête.",
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=int(os.getenv("LINKEDIN_AUTOPUBLISH_INTERVAL_SECONDS", "300")),
        help="Intervalle entre deux scans en mode daemon.",
    )
    parser.add_argument(
        "--max-posts",
        type=int,
        default=int(os.getenv("LINKEDIN_AUTOPUBLISH_MAX_POSTS", "0")),
        help="Nombre max de posts par cycle (0 = pas de limite).",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=_env_bool("LINKEDIN_AUTOPUBLISH_HEADLESS", True),
        help="Force l'exécution headless.",
    )
    parser.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Désactive le mode headless.",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        help="Niveau de log.",
    )
    return parser


def run_cycle(args: argparse.Namespace) -> int:
    email = os.getenv("LINKEDIN_EMAIL", "")
    password = os.getenv("LINKEDIN_PASSWORD", "")
    pipeline = LinkedInAutoPublishPipeline()

    result = pipeline.run_once(
        email=email,
        password=password,
        headless=args.headless,
        max_posts=(None if args.max_posts <= 0 else args.max_posts),
        callback=lambda msg: logging.getLogger("autopublish").info(msg),
    )

    logging.getLogger("autopublish").info(
        "Cycle terminé | eligible=%s | published=%s | failed=%s",
        result.eligible_posts,
        result.published_posts,
        result.failed_posts,
    )
    return 0 if result.success else 1


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    _setup_logging(args.log_level)

    if args.once:
        return run_cycle(args)

    while True:
        run_cycle(args)
        time.sleep(max(30, args.interval_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
