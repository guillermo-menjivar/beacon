"""The Source adapter interface.

A Source ingests change events from some external system. Adding a new kind of
source (GitLab, a deploy log, an incident feed) means implementing this one
method — that's the pluggable seam.
"""

from __future__ import annotations

from typing import Protocol

from beacon.models import Event


class Source(Protocol):
    name: str

    def fetch_since(self, cursor: str | None) -> list[Event]:
        """Return change events newer than ``cursor`` (an ISO-8601 timestamp),
        or all available if ``cursor`` is None.

        Ordering is not guaranteed — the store sorts. Implementations must be
        safe to call repeatedly (the store dedupes by ``Event.ref``).
        """
        ...
