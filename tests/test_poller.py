"""Tests for the poller — cursor handling + idempotency, with a fake source."""

import os
import tempfile
import unittest

from beacon.models import Event
from beacon.poller import poll
from beacon.store import Store


def _evt(ref: str, ts: str) -> Event:
    return Event(ref=ref, source="fake", title=ref, timestamp=ts)


class _FakeSource:
    name = "fake"

    def __init__(self, by_cursor: dict) -> None:
        self.by_cursor = by_cursor
        self.calls: list = []

    def fetch_since(self, cursor):
        self.calls.append(cursor)
        return self.by_cursor.get(cursor, [])


class PollerTest(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.mkdtemp()
        self.store = Store(os.path.join(self._dir, "beacon.db"))

    def tearDown(self) -> None:
        self.store.close()

    def test_first_poll_uses_none_cursor_and_ingests(self) -> None:
        src = _FakeSource({None: [
            _evt("a", "2026-06-01T00:00:00Z"),
            _evt("b", "2026-06-02T00:00:00Z"),
        ]})
        self.assertEqual(poll(src, self.store), 2)
        self.assertEqual(src.calls, [None])
        self.assertEqual(self.store.high_water_mark(), "2026-06-02T00:00:00Z")

    def test_second_poll_advances_cursor_to_high_water_mark(self) -> None:
        src = _FakeSource({
            None: [_evt("a", "2026-06-01T00:00:00Z")],
            "2026-06-01T00:00:00Z": [_evt("b", "2026-06-02T00:00:00Z")],
        })
        poll(src, self.store)
        self.assertEqual(poll(src, self.store), 1)
        self.assertEqual(src.calls, [None, "2026-06-01T00:00:00Z"])

    def test_idempotent_when_nothing_new(self) -> None:
        src = _FakeSource({
            None: [_evt("a", "2026-06-01T00:00:00Z")],
            "2026-06-01T00:00:00Z": [],
        })
        poll(src, self.store)
        self.assertEqual(poll(src, self.store), 0)


if __name__ == "__main__":
    unittest.main()
