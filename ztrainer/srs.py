"""Spaced repetition (simplified SM-2) for weak combos.

An entry lives in stats['weak_combos'][key] and carries:
    ease      difficulty multiplier (1.3 .. 3.0)
    interval  review units until next due
    due       review-counter value at which it becomes due again
    streak    consecutive clean-and-fast reps since the last lapse
plus bookkeeping: seen / wrong / slow / last / op.
"""

from __future__ import annotations

import math
from datetime import datetime


def srs_init(op: str) -> dict:
    return {
        "op": op, "seen": 0, "wrong": 0, "slow": 0,
        "ease": 2.3, "interval": 1, "due": 0, "streak": 0, "last": "",
    }


def srs_update(ent: dict, outcome: str, counter: int) -> None:
    """outcome in {'good', 'slow', 'wrong'}; counter is the review-unit clock."""
    ease = ent.get("ease", 2.3)
    interval = ent.get("interval", 1)
    if outcome == "good":
        ent["streak"] = ent.get("streak", 0) + 1
        ease = min(3.0, ease + 0.10)
        interval = max(1, math.ceil(interval * ease))
    elif outcome == "slow":
        ent["streak"] = 0
        ease = max(1.3, ease - 0.05)
        interval = max(1, round(interval * 0.6))
    else:  # wrong
        ent["streak"] = 0
        ease = max(1.3, ease - 0.20)
        interval = 1
    ent["ease"] = round(ease, 2)
    ent["interval"] = interval
    ent["due"] = counter + interval
    ent["last"] = datetime.now().isoformat(timespec="seconds")


def srs_due_pool(stats: dict, n: int) -> list:
    """Keys to review now: due first, then hardest, then soonest due."""
    combos = stats.get("weak_combos", {})
    counter = stats.get("review_counter", 0)
    items = sorted(
        combos.items(),
        key=lambda kv: (kv[1].get("due", 0) > counter,
                        -(kv[1].get("wrong", 0)),
                        kv[1].get("due", 0)),
    )
    return [k for k, _ in items[:n]]
