from __future__ import annotations

import sqlite3

from storage.init_db import init_db


def test_init_db_creates_core_tables(tmp_path):
    db_path = tmp_path / "app.db"

    init_db(str(db_path))

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()

    table_names = {row[0] for row in rows}
    assert "workflow_runs" in table_names
    assert "scheduled_posts" in table_names
    assert "contacts" in table_names
    assert "job_postings" in table_names
    assert "watch_articles" in table_names
