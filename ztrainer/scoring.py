"""Attempt records, weak-spot flagging, and the end-of-session report."""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean, median

from .config import OP_ORDER
from .patterns import pattern_breakdown, pattern_tags
from .terminal import IS_WINDOWS


@dataclass
class Attempt:
    op: str
    text: str
    answer: int
    given: str
    correct: bool
    total: float
    think: float
    type_: float
    key: str
    tags: list = field(default_factory=list)
    reason: str = ""  # set by flag_weak: 'wrong' | 'slow' | ''

    def has_split(self) -> bool:
        """True when a real think/type split was measured (Windows capture)."""
        return not (self.think == self.total and self.type_ == 0.0)


def _split(k, start: float):
    total = k.submit - start
    if k.first is None:
        return total, total, 0.0
    return total, max(k.first - start, 0.0), max(k.submit - k.first, 0.0)


def build_attempt(prob, k, start: float) -> Attempt:
    total, think, typ = _split(k, start)
    correct = True if k.mode == "auto" else (k.value == str(prob.answer))
    return Attempt(
        op=prob.op,
        text=prob.text,
        answer=prob.answer,
        given=k.value or "(skip)",
        correct=correct,
        total=total,
        think=think,
        type_=typ,
        key=prob.key,
        tags=pattern_tags(prob.op, prob.operands, prob.answer),
    )


def flag_weak(attempts, cfg: dict) -> list:
    """Mark each attempt's .reason and return the weak ones, worst first."""
    by_op: dict = {}
    for a in attempts:
        if a.correct:
            by_op.setdefault(a.op, []).append(a.total)

    thresholds = {}
    for op, times in by_op.items():
        floor = cfg["slow_floor"].get(op, 4.0)
        thresholds[op] = max(floor, 2 * median(times)) if len(times) >= 4 else floor

    weak = []
    for a in attempts:
        if not a.correct:
            a.reason = "wrong"
            weak.append(a)
        elif a.total > thresholds.get(a.op, cfg["slow_floor"].get(a.op, 4.0)):
            a.reason = "slow"
            weak.append(a)
        else:
            a.reason = ""
    weak.sort(key=lambda x: (x.reason != "wrong", -x.total))
    return weak


def _fmt(x: float) -> str:
    return f"{x:>7.1f}"


def report(attempts, cfg: dict, label: str) -> dict:
    print()
    print("=" * 60)
    print(f"  {label}")
    print("=" * 60)

    if not attempts:
        print("  no problems attempted.")
        return {}

    score = sum(a.correct for a in attempts)
    n = len(attempts)
    acc = 100 * score / n
    print(f"  SCORE {score}   ({score}/{n} correct, {acc:.1f}% accuracy)")
    print()

    header = (f"  {'operation':<15}{'att':>4}{'corr':>6}{'acc%':>7}"
              f"{'avg':>7}{'med':>7}{'think':>7}{'type':>7}")
    print(header)
    print("  " + "-" * (len(header) - 2))

    per_op = {}
    for op in OP_ORDER:
        rows = [a for a in attempts if a.op == op]
        if not rows:
            continue
        c = sum(a.correct for a in rows)
        tot = [a.total for a in rows]
        good = [a for a in rows if a.correct]
        think = mean(a.think for a in good) if good else 0.0
        typ = mean(a.type_ for a in good) if good else 0.0
        print(f"  {op:<15}{len(rows):>4}{c:>6}{100 * c / len(rows):>7.1f}"
              f"{_fmt(mean(tot))}{_fmt(median(tot))}{_fmt(think)}{_fmt(typ)}")
        per_op[op] = {
            "attempted": len(rows),
            "correct": c,
            "accuracy": round(100 * c / len(rows), 1),
            "avg_total": round(mean(tot), 2),
            "median_total": round(median(tot), 2),
            "avg_think": round(think, 2),
            "avg_type": round(typ, 2),
        }

    weak = flag_weak(attempts, cfg)
    if weak:
        print()
        print(f"  Weak spots ({len(weak)}) - missed or slow:")
        for a in weak[:25]:
            tag = "wrong" if a.reason == "wrong" else "slow "
            extra = (f"  (think {a.think:.1f} / type {a.type_:.1f})"
                     if a.has_split() else "")
            print(f"    [{tag}] {a.text} = {a.answer:<6} you: {a.given:<7}"
                  f"{a.total:5.1f}s{extra}")
        if len(weak) > 25:
            print(f"    ... and {len(weak) - 25} more")
    else:
        print("\n  No weak spots flagged - clean run.")

    patterns = pattern_breakdown(attempts)
    if patterns:
        overall_med = median([a.total for a in attempts if a.correct]) or 0.0
        ranked = sorted(patterns.items(), key=lambda kv: -kv[1]["median"])
        shown = set()
        print()
        print("  Number patterns (slowest first, min 3 samples):")
        for tag, d in ranked[:6]:
            shown.add(tag)
            delta = d["median"] - overall_med
            mark = f"  {delta:+.1f}s vs your median" if abs(delta) >= 0.4 else ""
            print(f"    {tag:<16} n={d['n']:<3} acc {d['acc']:>3.0f}%"
                  f"  median {d['median']:>4.1f}s{mark}")
        for tag, d in sorted(patterns.items(), key=lambda kv: kv[1]["acc"]):
            if d["acc"] < 75 and tag not in shown:
                print(f"    {tag:<16} n={d['n']:<3} acc {d['acc']:>3.0f}%"
                      f"  <- accuracy leak")

    print()
    if not IS_WINDOWS:
        print("  (line-input mode: think/type split unavailable on this platform)")

    return {
        "score": score,
        "attempted": n,
        "accuracy": round(acc, 1),
        "per_op": per_op,
        "weak_keys": [{"key": a.key, "reason": a.reason} for a in weak],
        "patterns": {t: {"n": d["n"], "acc": d["acc"], "median": d["median"]}
                     for t, d in patterns.items()},
    }
