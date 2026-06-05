"""Command-line interface — what cron runs, and how you inspect the feed.

    beacon --db beacon.db poll --repo owner/name
    beacon --db beacon.db recent --limit 20
    beacon --db beacon.db since 2026-06-01T00:00:00Z
"""

from __future__ import annotations

import argparse

from beacon.poller import poll
from beacon.sources.github import GitHubSource
from beacon.store import Store


def _cmd_poll(args: argparse.Namespace) -> None:
    with Store(args.db) as store:
        n = poll(GitHubSource(args.repo, base=args.base), store)
        print(f"ingested {n} new event(s)")


def _cmd_recent(args: argparse.Namespace) -> None:
    with Store(args.db) as store:
        for e in store.recent(args.limit):
            print(f"{e.timestamp}  {e.ref}  {e.title}")


def _cmd_since(args: argparse.Namespace) -> None:
    with Store(args.db) as store:
        for e in store.changes_since(args.timestamp):
            print(f"{e.timestamp}  {e.ref}  {e.title}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="beacon", description="A change feed for agents.")
    parser.add_argument("--db", default="beacon.db", help="path to the SQLite store")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_poll = sub.add_parser("poll", help="fetch new changes from a source into the store")
    p_poll.add_argument("--repo", required=True, help="GitHub repo, owner/name")
    p_poll.add_argument("--base", default="main", help="base branch to watch")
    p_poll.set_defaults(func=_cmd_poll)

    p_recent = sub.add_parser("recent", help="show recent events, newest first")
    p_recent.add_argument("--limit", type=int, default=20)
    p_recent.set_defaults(func=_cmd_recent)

    p_since = sub.add_parser("since", help="show events newer than a timestamp")
    p_since.add_argument("timestamp", help="ISO-8601 UTC, e.g. 2026-06-01T00:00:00Z")
    p_since.set_defaults(func=_cmd_since)

    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
