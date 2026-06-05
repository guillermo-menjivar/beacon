"""Tests for the SQLite event store. Stdlib only — runs with plain python3."""

import os
import tempfile
import unittest

from beacon.models import Event
from beacon.store import Store


def _evt(ref: str, ts: str, **kw) -> Event:
    return Event(ref=ref, source="github", title=kw.pop("title", ref), timestamp=ts, **kw)


class StoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.mkdtemp()
        self.store = Store(os.path.join(self._dir, "beacon.db"))

    def tearDown(self) -> None:
        self.store.close()

    def test_upsert_is_idempotent_by_ref(self) -> None:
        n1 = self.store.upsert([
            _evt("a", "2026-06-01T00:00:00Z"),
            _evt("b", "2026-06-02T00:00:00Z"),
        ])
        self.assertEqual(n1, 2)
        # re-ingesting "a" plus a new "c" → only "c" counts as new.
        n2 = self.store.upsert([
            _evt("a", "2026-06-01T00:00:00Z"),
            _evt("c", "2026-06-03T00:00:00Z"),
        ])
        self.assertEqual(n2, 1)
        self.assertEqual(len(self.store.all()), 3)

    def test_upsert_empty_is_noop(self) -> None:
        self.assertEqual(self.store.upsert([]), 0)

    def test_changes_since_is_exclusive_and_oldest_first(self) -> None:
        self.store.upsert([
            _evt("a", "2026-06-01T00:00:00Z"),
            _evt("b", "2026-06-02T00:00:00Z"),
            _evt("c", "2026-06-03T00:00:00Z"),
        ])
        out = self.store.changes_since("2026-06-01T00:00:00Z")
        self.assertEqual([e.ref for e in out], ["b", "c"])

    def test_recent_is_newest_first_with_limit(self) -> None:
        self.store.upsert([_evt(f"e{i}", f"2026-06-0{i}T00:00:00Z") for i in range(1, 5)])
        out = self.store.recent(limit=2)
        self.assertEqual([e.ref for e in out], ["e4", "e3"])

    def test_high_water_mark(self) -> None:
        self.assertIsNone(self.store.high_water_mark())
        self.store.upsert([
            _evt("a", "2026-06-01T00:00:00Z"),
            _evt("b", "2026-06-05T00:00:00Z"),
        ])
        self.assertEqual(self.store.high_water_mark(), "2026-06-05T00:00:00Z")

    def test_roundtrip_preserves_all_fields(self) -> None:
        self.store.upsert([
            _evt(
                "a", "2026-06-01T00:00:00Z",
                title="t", url="http://x", body="b", author="me",
                changed_paths=["x/y"], topics=["canary"],
            )
        ])
        e = self.store.all()[0]
        self.assertEqual(e.title, "t")
        self.assertEqual(e.url, "http://x")
        self.assertEqual(e.author, "me")
        self.assertEqual(e.changed_paths, ["x/y"])
        self.assertEqual(e.topics, ["canary"])

    def test_persists_across_reopen(self) -> None:
        path = os.path.join(self._dir, "persist.db")
        with Store(path) as s:
            s.upsert([_evt("a", "2026-06-01T00:00:00Z")])
        with Store(path) as s:
            self.assertEqual([e.ref for e in s.all()], ["a"])


if __name__ == "__main__":
    unittest.main()
