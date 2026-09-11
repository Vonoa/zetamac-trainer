"""Menu actions for quant-interview prep: Probability & EV, Fermi/estimation."""

from __future__ import annotations

import random
import sys
import time
from statistics import mean

from .capture import CAPTURE_FREE, ask_int
from .quant import (
    FERMI_BANK, PROB_GENERATORS, check_answer, fermi_tier, fmt_answer,
    fmt_magnitude, parse_magnitude, parse_numeric,
)
from .stats import record_fermi_session, record_prob_session
from .terminal import BAD, OK, clear_screen

PROB_ALLOWED = ".+-/%"
FERMI_ALLOWED = "+-.kmbeKMBE"


def mode_quant_prob(cfg: dict) -> None:
    dur = ask_int("Duration in seconds", cfg["quant"]["prob_duration"])
    print("\nProbability & EV drill - mixed dice / cards / EV / combinatorics.")
    print("Answer as a decimal, fraction (1/6), or percent (16.67%). "
          "Enter to submit, Esc to stop.")
    input("Press Enter to start... ")
    clear_screen()

    rng = random.Random()
    deadline = time.monotonic() + dur
    results: list = []
    try:
        while time.monotonic() < deadline:
            gen = rng.choice(PROB_GENERATORS)
            text, ans, tag, explain, exact = gen(rng)
            remaining = deadline - time.monotonic()
            sys.stdout.write(f"\n[{remaining:4.0f}s]  {text}\n   answer = ")
            sys.stdout.flush()
            t0 = time.monotonic()
            k = CAPTURE_FREE(deadline, PROB_ALLOWED)
            dt = time.monotonic() - t0
            sys.stdout.write("\n")

            if k.mode == "timeout":
                print("   time!")
                break
            if k.mode == "esc":
                print("   (stopped)")
                break

            given = parse_numeric(k.value) if k.value else None
            ok = check_answer(given, ans, exact)
            results.append({"tag": tag, "ok": ok, "total": dt})
            if ok:
                print(f"   {OK}  ({dt:.1f}s)")
            else:
                print(f"   {BAD}  correct = {fmt_answer(ans, exact)}   ({explain})")
    except KeyboardInterrupt:
        print("\n(interrupted)")

    _report_prob(results)
    if results:
        record_prob_session(results)
        print("  session saved -> stats.json")


def _report_prob(results: list) -> None:
    print("\n" + "=" * 60)
    print("  Probability & EV drill")
    print("=" * 60)
    if not results:
        print("  no problems attempted.")
        return
    n = len(results)
    score = sum(r["ok"] for r in results)
    print(f"  SCORE {score}   ({score}/{n} correct, {100 * score / n:.1f}% accuracy)")

    by_tag: dict = {}
    for r in results:
        d = by_tag.setdefault(r["tag"], {"n": 0, "ok": 0, "t": []})
        d["n"] += 1
        d["ok"] += int(r["ok"])
        d["t"].append(r["total"])

    print()
    print(f"  {'category':<16}{'att':>4}{'corr':>6}{'acc%':>7}{'avg s':>7}")
    print("  " + "-" * 40)
    for tag, d in sorted(by_tag.items()):
        print(f"  {tag:<16}{d['n']:>4}{d['ok']:>6}{100 * d['ok'] / d['n']:>7.1f}"
              f"{mean(d['t']):>7.1f}")
    print("=" * 60)


def mode_fermi(cfg: dict) -> None:
    n = ask_int("How many questions", cfg["quant"]["fermi_count"])
    timer = cfg["quant"]["fermi_timer"] or 600
    print("\nFermi / estimation - guesstimate, no lookup allowed.")
    print("Answer as a number: '45000', '45k', '1.2m', '3b'. "
          "Graded by order of magnitude, not exact value. Esc to stop.")
    input("Press Enter to start... ")
    rng = random.Random()
    bank = rng.sample(FERMI_BANK, min(n, len(FERMI_BANK)))

    results: list = []
    for i, item in enumerate(bank, 1):
        print(f"\n[{i}/{len(bank)}]  {item['q']}")
        sys.stdout.write("   estimate = ")
        sys.stdout.flush()
        t0 = time.monotonic()
        try:
            k = CAPTURE_FREE(t0 + timer, FERMI_ALLOWED)
        except KeyboardInterrupt:
            print("\n(interrupted)")
            break
        dt = time.monotonic() - t0
        sys.stdout.write("\n")
        if k.mode == "esc":
            print("   (stopped)")
            break

        guess = parse_magnitude(k.value) if k.value else None
        tier, diff = fermi_tier(guess, item["ref"])
        results.append({"tag": item["tag"], "tier": tier, "diff": diff, "total": dt})
        shown = fmt_magnitude(guess) if guess else "(no answer)"
        off = f"  ({diff:.2f} log10 off)" if diff is not None else ""
        print(f"   you said {shown}  ->  {tier}{off}")
        print(f"   reference ~{fmt_magnitude(item['ref'])}")
        print(f"   approach: {item['approach']}")

    _report_fermi(results)
    if results:
        record_fermi_session(results)
        print("  session saved -> stats.json")


def _report_fermi(results: list) -> None:
    print("\n" + "=" * 60)
    print("  Fermi / estimation")
    print("=" * 60)
    if not results:
        print("  no questions attempted.")
        return
    n = len(results)
    tiers: dict = {}
    for r in results:
        tiers[r["tier"]] = tiers.get(r["tier"], 0) + 1
    diffs = [r["diff"] for r in results if r["diff"] is not None]
    print(f"  {n} questions")
    for tier in ("excellent", "good", "order of magnitude", "off"):
        if tiers.get(tier):
            print(f"    {tier:<20} {tiers[tier]}")
    if diffs:
        print(f"  avg log10 distance from reference: {mean(diffs):.2f}"
              f"  (0 = exact, 1 = 10x off)")
    print("=" * 60)
