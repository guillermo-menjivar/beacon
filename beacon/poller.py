"""The poller: ingest new events from a source into the store.

Deliberately tiny and idempotent — safe to run on a cron. The store's
high-water mark is the cursor, so each run only asks the source for what it
hasn't seen, and ``upsert`` dedupes anything that overlaps.
"""

from __future__ import annotations

from beacon.sources.base import Source
from beacon.store import Store


def poll(source: Source, store: Store) -> int:
    """Fetch changes since the store's high-water mark, upsert them, and return
    the number of new events."""
    cursor = store.high_water_mark()
    events = source.fetch_since(cursor)
    return store.upsert(events)
