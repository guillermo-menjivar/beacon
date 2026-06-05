"""Core data model: a single change event."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Event:
    """One change event from a source.

    `ref` is the stable idempotency key (e.g. "github:pr:123") — re-ingesting the
    same change must produce the same `ref` so the store can dedupe.

    `timestamp` is ISO-8601 UTC and is the ordering key for "since" queries, so
    it must be lexically sortable (zero-padded, e.g. "2026-06-04T19:28:00Z").
    """

    ref: str
    source: str
    title: str
    timestamp: str
    url: str = ""
    body: str = ""
    author: str = ""
    changed_paths: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
