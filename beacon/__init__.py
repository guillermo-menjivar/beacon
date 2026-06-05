"""beacon — a standalone, agent-agnostic change feed.

Ingests change events from pluggable sources, stores them durably, and serves
them to consumers (an agent harness briefing, an on-demand query). See README.md.
"""

from beacon.models import Event
from beacon.store import Store

__all__ = ["Event", "Store"]
