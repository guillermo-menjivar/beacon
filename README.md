# beacon

> Keep your agents current. A standalone change feed that briefs an agent on
> what changed in the systems it operates on.

**Status: early — v1 in progress.** This README is the intent; the
implementation is being built up from it.

## The problem

Agents that operate on evolving systems — codebases, infrastructure, fleets —
**drift out of sync with reality.** An agent builds a confident mental model and
then keeps acting on it long after the system has changed underneath it. The
failure mode is the dangerous kind: *silent and confident.* The agent doesn't
know to doubt itself, so it never asks.

> Real example that started this: an SRE agent kept making decisions assuming a
> deployment feature didn't exist — days after it had shipped — until a human
> forced it to re-read the code. It wasn't missing a tool; it was certain about a
> stale world.

The instinct is to let the agent *ask* "has anything changed?" — but a
confidently-wrong agent doesn't think to ask. **Pull doesn't fix certainty.**
The fix is **push**: catch the agent up at the start of every session, whether
it asks or not.

## What beacon is

A small, standalone, **source-agnostic** change feed that:

1. **ingests** change events from pluggable sources — v1: **GitHub merges to
   `main`**;
2. **stores** them durably (SQLite — history, queryable, zero infrastructure);
3. **serves** them to any consumer, two ways:
   - **push** — a "what changed since you last ran" briefing at session start;
   - **pull** — an on-demand query ("anything new about X?").

beacon knows **nothing about any specific agent.** It's a feed; agents and their
harnesses are just consumers. The first consumer is a Claude agent harness, but
the design stays agnostic so others can plug in.

## Design principles

- **Standalone & agent-agnostic** — any harness can consume it.
- **Pluggable sources (adapter model)** — GitHub now; more sources later.
- **Stateful by design** — history matters; it enables replay, topic
  re-classification, and multiple consumers. ("It's just a SQLite db you can
  open.")
- **Minimal dependencies** — stdlib-first (`sqlite3`, `urllib`).
- **Boring and legible** — easy to read, easy to fork, easy to extend.

## Architecture (and the seams it grows along)

```
 sources (adapters) ──▶ event store (SQLite) ──▶ query API ──▶ consumers
   GitHub merges                 history                       push: session briefing
   (more later)              idempotent by ref                 pull: "what's new?"
```

- **Sources** are adapters; each normalizes into a common event shape.
- **Store** is an idempotent event log (keyed by a stable `ref`), so re-ingesting
  never duplicates.
- **Consumers** read the store — never the source directly.
- **Deliberately deferred seams** (where it grows): **topic classification**
  (operational topics, *not* code-folder layout — the two diverge), additional
  sources, and real-time / mid-session notification.

## v1 scope

SQLite event store · GitHub merges-to-`main` source · a `poll` command (run on
cron) · a query API (`since` / `recent` / `all`). Topics, more sources, and
real-time push are **out of scope for v1** — on purpose.

## Why "beacon"

A beacon signals: it tells you something changed, and where to look.
