from __future__ import annotations

import sqlite3
from pathlib import Path


class SearchIndex:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def search_notes(self, query: str) -> list[tuple[str, str]]:
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute(
                "select canonical_event_uid, text_body from journal_events_fts where journal_events_fts match ? limit 20",
                (query,),
            ).fetchall()
