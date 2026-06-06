"""SQLite-backed event store.

The store is an idempotent event log keyed by ``Event.ref`` — re-ingesting the
same event never duplicates it. Consumers read from here (never from a source
directly), which is what lets ingestion and querying run independently.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable

from beacon.models import Event

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    ref           TEXT PRIMARY KEY,
    source        TEXT NOT NULL,
    title         TEXT NOT NULL,
    timestamp     TEXT NOT NULL,
    url           TEXT NOT NULL DEFAULT '',
    body          TEXT NOT NULL DEFAULT '',
    author        TEXT NOT NULL DEFAULT '',
    changed_paths TEXT NOT NULL DEFAULT '[]',
    topics        TEXT NOT NULL DEFAULT '[]',
    ingested_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_source ON events(source);
"""


class Store:
    """An append-mostly event log on SQLite. Idempotent by ``ref``."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        # WAL lets a poller write while consumers read concurrently.
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def upsert(self, events: Iterable[Event]) -> int:
        """Insert new events; rows whose ``ref`` already exists are left
        untouched. Returns the count of NEW rows actually inserted."""
        rows = [
            (
                e.ref, e.source, e.title, e.timestamp, e.url, e.body, e.author,
                json.dumps(e.changed_paths), json.dumps(e.topics),
            )
            for e in events
        ]
        if not rows:
            return 0
        with self._conn:
            before = self._conn.total_changes
            self._conn.executemany(
                "INSERT OR IGNORE INTO events "
                "(ref, source, title, timestamp, url, body, author, changed_paths, topics) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
            return self._conn.total_changes - before

    def changes_since(self, timestamp: str) -> list[Event]:
        """Events strictly newer than ``timestamp``, oldest first."""
        cur = self._conn.execute(
            "SELECT * FROM events WHERE timestamp > ? ORDER BY timestamp ASC",
            (timestamp,),
        )
        return [self._row_to_event(r) for r in cur.fetchall()]

    def recent(self, limit: int = 20) -> list[Event]:
        """The most recent events, newest first."""
        cur = self._conn.execute(
            "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        return [self._row_to_event(r) for r in cur.fetchall()]

    def all(self) -> list[Event]:
        """Full history, oldest first."""
        cur = self._conn.execute("SELECT * FROM events ORDER BY timestamp ASC")
        return [self._row_to_event(r) for r in cur.fetchall()]

    def search(self, query: str, since: str | None = None, limit: int = 20) -> list[Event]:
        """Keyword search — the *pull* side of the feed ("anything new about X?").

        Splits ``query`` into whitespace-separated terms and returns events where
        EVERY term appears (case-insensitive substring) in any of the text
        fields — title, body, source, changed_paths, topics — newest first. An
        empty query matches everything (acts like ``recent``). ``since`` is an
        optional ISO-8601 lower bound (strict ``>``).

        This is deliberately keyword, not semantic: topic classification is a
        deferred seam, so for v1 "about X" means "the word X shows up". The
        match spans changed_paths/topics too, so a path or topic fragment hits.
        """
        clauses: list[str] = []
        params: list[object] = []
        for term in query.split():
            like = f"%{term}%"
            clauses.append(
                "(title LIKE ? OR body LIKE ? OR source LIKE ? "
                "OR changed_paths LIKE ? OR topics LIKE ?)"
            )
            params.extend([like, like, like, like, like])
        if since:
            clauses.append("timestamp > ?")
            params.append(since)
        where = " AND ".join(clauses) if clauses else "1=1"
        params.append(limit)
        cur = self._conn.execute(
            f"SELECT * FROM events WHERE {where} ORDER BY timestamp DESC LIMIT ?",
            params,
        )
        return [self._row_to_event(r) for r in cur.fetchall()]

    def high_water_mark(self) -> str | None:
        """The latest event timestamp in the store, or ``None`` if empty.

        This is the poll cursor: a source asks for changes after this.
        """
        row = self._conn.execute("SELECT MAX(timestamp) AS hwm FROM events").fetchone()
        return row["hwm"] if row and row["hwm"] is not None else None

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> Event:
        return Event(
            ref=row["ref"],
            source=row["source"],
            title=row["title"],
            timestamp=row["timestamp"],
            url=row["url"],
            body=row["body"],
            author=row["author"],
            changed_paths=json.loads(row["changed_paths"]),
            topics=json.loads(row["topics"]),
        )
