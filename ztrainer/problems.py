"""Problem generation and the canonical weak-combo key format.

Key formats (ASCII, used as dict keys in stats.json):
    a+b   addition, a <= b
    axb   multiplication, a <= b
    T-s   subtraction shown as T - s
    D/d   division shown as D / d
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .terminal import DIV, MUL


@dataclass
class Problem:
    op: str
    text: str  # "47 + 8" (display, may use x / div glyphs)
    answer: int
    key: str  # canonical ASCII weak-combo key, e.g. "8x47"
    operands: tuple  # the two numbers shown, left then right of the sign


def rand_in(rng: random.Random, span) -> int:
    return rng.randint(int(span[0]), int(span[1]))


def make_problem(op: str, cfg: dict, rng: random.Random) -> Problem:
    spec = cfg["operations"][op]
    a = rand_in(rng, spec["a"])
    b = rand_in(rng, spec["b"])

    if op == "addition":
        lo, hi = min(a, b), max(a, b)
        return Problem(op, f"{a} + {b}", a + b, f"{lo}+{hi}", (a, b))

    if op == "subtraction":
        total = a + b
        sub = rng.choice([a, b])
        return Problem(op, f"{total} - {sub}", total - sub, f"{total}-{sub}",
                       (total, sub))

    if op == "multiplication":
        lo, hi = min(a, b), max(a, b)
        return Problem(op, f"{a} {MUL} {b}", a * b, f"{lo}x{hi}", (a, b))

    if op == "division":
        divisor = rand_in(rng, spec["a"])   # 2..12 by default
        quotient = rand_in(rng, spec["b"])  # 2..100 by default
        dividend = divisor * quotient
        return Problem(op, f"{dividend} {DIV} {divisor}", quotient,
                       f"{dividend}/{divisor}", (dividend, divisor))

    raise ValueError(op)


def parse_key(key: str):
    """Rebuild (op, display_text, answer, operands) from a weak-combo key."""
    if "+" in key:
        x, y = map(int, key.split("+"))
        return "addition", f"{x} + {y}", x + y, (x, y)
    if "x" in key:
        x, y = map(int, key.split("x"))
        return "multiplication", f"{x} {MUL} {y}", x * y, (x, y)
    if "/" in key:
        x, y = map(int, key.split("/"))
        return "division", f"{x} {DIV} {y}", x // y, (x, y)
    if "-" in key:
        x, y = map(int, key.split("-"))
        return "subtraction", f"{x} - {y}", x - y, (x, y)
    raise ValueError(key)


def problem_from_key(key: str) -> Problem:
    op, text, answer, operands = parse_key(key)
    return Problem(op, text, answer, key, operands)
