"""Targeted practice - drill the number patterns your own data says are weak.

analyse_weak_patterns() ranks the lifetime pattern aggregates in stats.json by a
"weakness score" that combines slowness (avg time vs your overall average) and
inaccuracy. make_targeted_source() then builds a problem generator restricted to
the chosen patterns (direct construction for mul:xN / div:/N, rejection sampling
for the structural ones like sub:cross-100).
"""

from __future__ import annotations

import random
from statistics import mean

from .config import enabled_ops
from .patterns import pattern_label, pattern_tags, tag_op
from .problems import Problem, make_problem, rand_in
from .terminal import DIV, MUL


def analyse_weak_patterns(stats: dict, min_samples: int = 8) -> list:
    """Return [{tag,label,n,acc,avg,score}, ...] worst first."""
    pats = stats.get("patterns", {})
    per_avg = [p["t_sum"] / p["t_n"] for p in pats.values() if p.get("t_n")]
    ref = mean(per_avg) if per_avg else 3.0

    rows = []
    for tag, p in pats.items():
        if p.get("seen", 0) < min_samples:
            continue
        acc = p["correct"] / p["seen"]
        avg = p["t_sum"] / p["t_n"] if p.get("t_n") else ref * 2
        slow_factor = avg / ref if ref else 1.0
        miss_factor = 1.0 - acc
        rows.append({
            "tag": tag,
            "label": pattern_label(tag),
            "n": p["seen"],
            "acc": round(100 * acc, 1),
            "avg": round(avg, 2),
            "score": round(slow_factor * (1 + 2.5 * miss_factor), 2),
        })
    rows.sort(key=lambda r: -r["score"])
    return rows


def _direct(tag: str, cfg: dict, rng: random.Random):
    """Cheap construction for the parametric tags; None for the rest."""
    if tag.startswith("mul:x") and tag[5:].isdigit():
        k = int(tag[5:])
        other = rand_in(rng, cfg["operations"]["multiplication"]["b"])
        a, b = (k, other) if rng.random() < 0.5 else (other, k)
        lo, hi = min(a, b), max(a, b)
        return Problem("multiplication", f"{a} {MUL} {b}", a * b, f"{lo}x{hi}", (a, b))
    if tag.startswith("div:/") and tag[5:].isdigit():
        d = int(tag[5:])
        q = rand_in(rng, cfg["operations"]["division"]["b"])
        return Problem("division", f"{d * q} {DIV} {d}", q, f"{d * q}/{d}", (d * q, d))
    return None


def make_targeted_source(tags, cfg: dict, rng: random.Random):
    """Zero-arg callable producing Problems that match one of `tags`."""
    tagset = set(tags)
    ops = enabled_ops(cfg)
    implied = {tag_op(t) for t in tags if tag_op(t)} or set(ops)
    pool_ops = [o for o in ops if o in implied] or ops

    def gen() -> Problem:
        if rng.random() < 0.55:
            p = _direct(rng.choice(tags), cfg, rng)
            if p and tagset & set(pattern_tags(p.op, p.operands, p.answer)):
                return p
        last = None
        for _ in range(400):
            p = make_problem(rng.choice(pool_ops), cfg, rng)
            last = p
            if tagset & set(pattern_tags(p.op, p.operands, p.answer)):
                return p
        return last  # give up gracefully rather than hang

    return gen
