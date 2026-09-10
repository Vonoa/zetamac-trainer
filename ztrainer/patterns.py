"""Number-pattern tagging - the bottleneck analytics.

A tag is a structural label for one problem, e.g. 'mul:x7' or 'sub:cross-100'.
Reports aggregate accuracy and time per tag so you can see *which shape of
problem* is costing you, not just which operation.
"""

from __future__ import annotations

from statistics import median

_OP_PREFIX = {
    "add": "addition",
    "sub": "subtraction",
    "mul": "multiplication",
    "div": "division",
}

_STATIC_LABELS = {
    "add:carry": "addition with a carry",
    "add:no-carry": "addition, no carry",
    "add:near-100": "addition near 100",
    "add:2d+2d": "two-digit + two-digit",
    "sub:borrow": "subtraction with a borrow",
    "sub:no-borrow": "subtraction, no borrow",
    "sub:cross-100": "subtraction crossing 100",
    "mul:2d*2d": "two-digit x two-digit",
    "mul:xteens": "multiply by a number in the teens",
    "div:big-dividend": "division, dividend >= 500",
    "ans:3d+": "answer has 3+ digits",
}


def pattern_tags(op: str, operands: tuple, answer: int) -> list:
    """Structural labels for one problem, e.g. ['mul:x7', 'ans:3d+']."""
    a, b = operands
    tags: list = []

    if op == "addition":
        tags.append("add:carry" if (a % 10) + (b % 10) >= 10 else "add:no-carry")
        if a >= 90 or b >= 90:
            tags.append("add:near-100")
        if a >= 10 and b >= 10:
            tags.append("add:2d+2d")

    elif op == "subtraction":
        tags.append("sub:borrow" if (a % 10) < (b % 10) else "sub:no-borrow")
        if a > 100 and answer < 100:
            tags.append("sub:cross-100")

    elif op == "multiplication":
        small = min(a, b)
        if small <= 12:
            tags.append(f"mul:x{small}")
        elif small <= 19:
            tags.append("mul:xteens")
        if a >= 10 and b >= 10:
            tags.append("mul:2d*2d")

    elif op == "division":
        tags.append(f"div:/{min(a, b)}")
        if max(a, b) >= 500:
            tags.append("div:big-dividend")

    if answer >= 100:
        tags.append("ans:3d+")
    return tags


def tag_op(tag: str):
    """The operation a tag belongs to, or None for op-agnostic tags (ans:3d+)."""
    return _OP_PREFIX.get(tag.split(":")[0])


def pattern_label(tag: str) -> str:
    if tag.startswith("mul:x") and tag[5:].isdigit():
        return f"multiplication by {tag[5:]}"
    if tag.startswith("div:/") and tag[5:].isdigit():
        return f"division by {tag[5:]}"
    return _STATIC_LABELS.get(tag, tag)


def pattern_breakdown(attempts) -> dict:
    """tag -> {n, acc, median} over attempts carrying that tag (min 3 samples)."""
    agg: dict = {}
    for a in attempts:
        for tag in a.tags:
            d = agg.setdefault(tag, {"n": 0, "correct": 0, "times": []})
            d["n"] += 1
            d["correct"] += int(a.correct)
            if a.correct:
                d["times"].append(a.total)
    out = {}
    for tag, d in agg.items():
        if d["n"] < 3:
            continue
        out[tag] = {
            "n": d["n"],
            "acc": round(100 * d["correct"] / d["n"], 1),
            "median": round(median(d["times"]), 2) if d["times"] else 0.0,
        }
    return out
