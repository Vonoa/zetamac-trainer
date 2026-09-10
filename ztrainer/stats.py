"""stats.json persistence, session recording, and the expected-score model.

stats.json shape:
    sessions          list of per-session summaries
    weak_combos       key -> SRS entry (see srs.py)
    patterns          tag -> {seen, correct, t_sum, t_n}  (lifetime aggregates)
    review_counter    increments once per weak-spot review session
    graduated_total   how many combos have been retired as fixed
    typing_floor      {median, best, samples, digits, updated}
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from statistics import mean

from .config import GRAD_INTERVAL, enabled_ops
from .srs import srs_init, srs_update
from .terminal import STATS_PATH


def load_stats() -> dict:
    if os.path.exists(STATS_PATH):
        try:
            with open(STATS_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            print("(could not read stats.json - starting fresh)")
            data = {}
    else:
        data = {}
    data.setdefault("sessions", [])
    data.setdefault("weak_combos", {})
    data.setdefault("patterns", {})
    data.setdefault("review_counter", 0)
    data.setdefault("graduated_total", 0)
    return data


def save_stats(stats: dict) -> None:
    with open(STATS_PATH, "w", encoding="utf-8") as fh:
        json.dump(stats, fh, indent=2)


def _outcome(a) -> str:
    if not a.correct:
        return "wrong"
    return "slow" if a.reason == "slow" else "good"


def record_session(mode: str, summary: dict, attempts, sprint_scores=None) -> None:
    if not summary:
        return
    stats = load_stats()
    is_review = mode == "weak_review"
    counter = stats["review_counter"] + (1 if is_review else 0)
    if is_review:
        stats["review_counter"] = counter

    rec = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "score": summary["score"],
        "attempted": summary["attempted"],
        "accuracy": summary["accuracy"],
        "per_op": summary.get("per_op", {}),
    }
    if sprint_scores is not None:
        rec["sprint_scores"] = sprint_scores
    stats["sessions"].append(rec)

    # ---- spaced repetition update -------------------------------------- #
    combos = stats["weak_combos"]
    rank = {"good": 0, "slow": 1, "wrong": 2}
    worst: dict = {}
    for a in attempts:
        o = _outcome(a)
        if a.key not in worst or rank[o] > rank[worst[a.key][0]]:
            worst[a.key] = (o, a.op)

    graduated = []
    for key, (outcome, op) in worst.items():
        tracked = key in combos
        if not tracked and outcome in ("wrong", "slow"):
            combos[key] = srs_init(op)
            tracked = True
        if not tracked:
            continue
        ent = combos[key]
        ent["seen"] = ent.get("seen", 0) + 1
        if outcome == "wrong":
            ent["wrong"] = ent.get("wrong", 0) + 1
        elif outcome == "slow":
            ent["slow"] = ent.get("slow", 0) + 1
        srs_update(ent, outcome, counter)
        if ent["streak"] >= 3 and ent["interval"] >= GRAD_INTERVAL:
            graduated.append(key)
            del combos[key]

    stats["graduated_total"] += len(graduated)

    # ---- lifetime number-pattern aggregates -------------------------- #
    pats = stats["patterns"]
    for a in attempts:
        for tag in a.tags:
            p = pats.setdefault(tag, {"seen": 0, "correct": 0, "t_sum": 0.0, "t_n": 0})
            p["seen"] += 1
            p["correct"] += int(a.correct)
            if a.correct:
                p["t_sum"] += a.total
                p["t_n"] += 1

    save_stats(stats)
    print(f"  session saved -> {STATS_PATH}")
    if graduated:
        print(f"  retired {len(graduated)} weak combo(s) as fixed: "
              + ", ".join(graduated[:6]) + ("..." if len(graduated) > 6 else ""))


def expected_score(cfg: dict, stats: dict):
    """Blend recent per-op thinking time with the typing floor -> pace model."""
    runs = [s for s in stats.get("sessions", [])
            if s["mode"] in ("classic", "sprint")]
    if not runs:
        return None
    recent = runs[-5:]
    thinks = []
    for op in enabled_ops(cfg):
        vals = [s["per_op"][op]["avg_think"] for s in recent
                if op in s.get("per_op", {})
                and isinstance(s["per_op"][op].get("avg_think"), (int, float))
                and s["per_op"][op]["avg_think"] > 0]
        if vals:
            thinks.append(mean(vals))
    if not thinks:
        return None
    mean_think = mean(thinks)
    dur = cfg["classic_duration"]
    out = {"mean_think": round(mean_think, 2), "calc_ceiling": round(dur / mean_think)}
    tf = stats.get("typing_floor", {}).get("median")
    if tf:
        out["typing_floor"] = tf
        out["expected"] = round(dur / (mean_think + tf))
    actual = [s["score"] for s in recent if s["mode"] == "classic"]
    if actual:
        out["recent_actual"] = round(mean(actual), 1)
    return out


def print_expected(cfg: dict) -> None:
    es = expected_score(cfg, load_stats())
    if not es:
        return
    print()
    print("  Expected-score model (from your recent runs):")
    print(f"    calc-only ceiling   ~{es['calc_ceiling']}   "
          f"(mean thinking {es['mean_think']}s/problem, instant typing)")
    if "expected" in es:
        print(f"    realistic expected  ~{es['expected']}   "
              f"(+ typing floor {es['typing_floor']}s)")
    else:
        print("    run 'Typing floor' once to unlock a realistic expected score.")
    if "recent_actual" in es:
        gap = es["recent_actual"] - es.get("expected", es["calc_ceiling"])
        hint = ("pace/consistency is the gap" if gap < -2
                else "you're converting calc speed well")
        print(f"    recent actual avg    {es['recent_actual']}   {hint}")
