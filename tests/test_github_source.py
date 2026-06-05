"""Tests for the GitHub source — parsing/filtering only, no network.

We inject canned PR pages by overriding ``_fetch_page``, so the HTTP layer is
never exercised here (that's validated live by ``poll``).
"""

import unittest

from beacon.sources.github import GitHubSource

# Newest-updated first, as the GitHub list endpoint returns them.
_PAGE = [
    {"number": 3, "title": "c", "merged_at": "2026-06-03T00:00:00Z",
     "updated_at": "2026-06-03T00:00:00Z", "html_url": "u3", "body": "b3",
     "user": {"login": "me"}},
    {"number": 2, "title": "b", "merged_at": None,  # closed but not merged
     "updated_at": "2026-06-02T12:00:00Z", "html_url": "u2", "body": None,
     "user": {"login": "me"}},
    {"number": 1, "title": "a", "merged_at": "2026-06-01T00:00:00Z",
     "updated_at": "2026-06-01T00:00:00Z", "html_url": "u1", "body": "b1",
     "user": {"login": "me"}},
]


class _FakeGitHub(GitHubSource):
    def __init__(self, pages, **kw):
        super().__init__("o/r", per_page=50, **kw)
        self._pages = pages

    def _fetch_page(self, page: int):
        return self._pages[page - 1] if page - 1 < len(self._pages) else []


class GitHubSourceTest(unittest.TestCase):
    def test_no_cursor_returns_all_merged_skipping_unmerged(self) -> None:
        out = _FakeGitHub([_PAGE]).fetch_since(None)
        self.assertEqual([e.ref for e in out], ["github:pr:3", "github:pr:1"])

    def test_cursor_is_exclusive_and_stops_paging(self) -> None:
        out = _FakeGitHub([_PAGE]).fetch_since("2026-06-01T00:00:00Z")
        # #1 == cursor (not strictly greater) → excluded; #2 unmerged → skipped.
        self.assertEqual([e.ref for e in out], ["github:pr:3"])

    def test_event_field_mapping(self) -> None:
        e = _FakeGitHub([_PAGE]).fetch_since(None)[0]
        self.assertEqual(e.source, "github")
        self.assertEqual(e.ref, "github:pr:3")
        self.assertEqual(e.timestamp, "2026-06-03T00:00:00Z")
        self.assertEqual(e.url, "u3")
        self.assertEqual(e.author, "me")

    def test_none_body_becomes_empty_string(self) -> None:
        page = [dict(_PAGE[0], body=None)]
        self.assertEqual(_FakeGitHub([page]).fetch_since(None)[0].body, "")

    def test_paginates_until_short_page(self) -> None:
        # per_page=50 but page has 3 → treated as the last page (no page 2 call).
        out = _FakeGitHub([_PAGE]).fetch_since(None)
        self.assertEqual(len(out), 2)


if __name__ == "__main__":
    unittest.main()
