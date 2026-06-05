"""GitHub source: merges to a base branch, via the REST API (stdlib only).

Lists closed PRs against ``base`` (default ``main``), newest-updated first, and
emits an Event per *merged* PR newer than the cursor. One list call per page; we
stop paging once we cross the cursor. Changed-file paths are intentionally not
fetched in v1 (that needs a per-PR call and is only useful once topic
classification lands).

Auth: a token via the constructor or ``GITHUB_TOKEN`` /
``GITHUB_PERSONAL_ACCESS_TOKEN``. Public repos work unauthenticated but are
rate-limited.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from beacon.models import Event

_API = "https://api.github.com"


class GitHubSource:
    name = "github"

    def __init__(
        self,
        repo: str,
        base: str = "main",
        token: str | None = None,
        per_page: int = 50,
        max_pages: int = 10,
    ) -> None:
        self.repo = repo  # "owner/name"
        self.base = base
        self.token = (
            token
            or os.environ.get("GITHUB_TOKEN")
            or os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "")
        )
        self.per_page = per_page
        self.max_pages = max_pages

    def fetch_since(self, cursor: str | None) -> list[Event]:
        events: list[Event] = []
        for page in range(1, self.max_pages + 1):
            prs = self._fetch_page(page)
            if not prs:
                break
            stop = False
            for pr in prs:
                # Sorted by updated desc, and merged_at <= updated_at always, so
                # once updated_at <= cursor everything remaining is older.
                if cursor and (pr.get("updated_at") or "") <= cursor:
                    stop = True
                    break
                merged = pr.get("merged_at")
                if merged and (cursor is None or merged > cursor):
                    events.append(self._to_event(pr))
            if stop or len(prs) < self.per_page:
                break
        return events

    @staticmethod
    def _to_event(pr: dict) -> Event:
        return Event(
            ref=f"github:pr:{pr['number']}",
            source="github",
            title=pr.get("title", ""),
            timestamp=pr.get("merged_at", ""),
            url=pr.get("html_url", ""),
            body=(pr.get("body") or "")[:4000],
            author=(pr.get("user") or {}).get("login", ""),
        )

    def _fetch_page(self, page: int) -> list[dict]:
        query = urllib.parse.urlencode(
            {
                "state": "closed",
                "base": self.base,
                "sort": "updated",
                "direction": "desc",
                "per_page": self.per_page,
                "page": page,
            }
        )
        url = f"{_API}/repos/{self.repo}/pulls?{query}"
        req = urllib.request.Request(url, headers=self._headers())
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - fixed https API host
            return json.loads(resp.read().decode())

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "beacon"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
