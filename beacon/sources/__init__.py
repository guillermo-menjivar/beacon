"""Source adapters — the pluggable ingest seam."""

from beacon.sources.base import Source
from beacon.sources.github import GitHubSource

__all__ = ["Source", "GitHubSource"]
