"""
Database bootstrap for the SQLite schema.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from storage.db import connect, get_database_path

SCHEMA_FILE = Path(__file__).parent / "migrations" / "0001_initial_schema.sql"


def init_db(db_path: str | None = None) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))
        conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialise la base SQLite du projet.")
    parser.add_argument("--db-path", default=str(get_database_path()), help="Chemin de la base.")
    args = parser.parse_args()
    init_db(args.db_path)
    print(f"SQLite initialisee: {args.db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
