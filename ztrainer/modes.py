"""Every menu action. Each mode_* takes the live config dict and runs to completion."""

from __future__ import annotations

import random
import sys
import time
from statistics import mean, median, pstdev

from .capture import CAPTURE, ask_int, prompt_int
from .config import OP_ORDER, OP_SIGN, enabled_ops, save_config, DEFAULT_CONFIG
from .engine import run_block, run_timed
from .patterns import pattern_label
from .problems import make_problem, parse_key, problem_from_key
from .scoring import report
from .srs import srs_due_pool
from .stats import expected_score, load_stats, record_session, save_stats
from .targeted import analyse_weak_patterns, make_targeted_source
from .terminal import BAD, MUL, OK, clear_screen
import json

# --------------------------------------------------------------------------- #
#  Timed modes
# --------------------------------------------------------------------------- #


def mode_classic(cfg: dict) -> None:
    ops = enabled_ops(cfg)
    if not ops:
        print("No operations enabled - check Settings.")
        return
    rng = random.Random()
    run_timed(lambda: make_problem(rng.choice(ops), cfg, rng),
              cfg["classic_duration"], "Classic (mixed)", cfg, "classic",
              cfg.get("target_score", 0))


def mode_single(cfg: dict) -> None:
    print("\nWhich operation?")
    for i, op in enumerate(OP_ORDER, 1):
        print(f"  {i}) {op}")
    try:
        op = OP_ORDER[int(input("> ").strip()) - 1]
    except (ValueError, IndexError):
        print("invalid choice.")
        return
    dur = ask_int("Duration in seconds", cfg["classic_duration"])
    rng = random.Random()
    run_timed(lambda: make_problem(op, cfg, rng),
              dur, f"Single operation - {op}", cfg, f"single:{op}",
              cfg.get("target_score", 0))


def mode_sprint(cfg: dict) -> None:
    """Several short bursts back to back - the report is about consistency."""
    ops = enabled_ops(cfg)
    if not ops:
        print("No operations enabled - check Settings.")
        return
    n = ask_int("Number of sprints", cfg["sprint"]["count"])
    length = ask_int("Seconds per sprint", cfg["sprint"]["length"])
    if n < 1 or length < 5:
        print("need at least 1 sprint of 5s+.")
        return
    print(f"\nSprint set - {n} x {length}s, short rest between each.")
    print("A correct answer submits itself. Esc ends the current sprint.")
    input("Press Enter for sprint 1... ")
    rng = random.Random()

    all_attempts: list = []
    sprint_scores: list = []
    for s in range(n):
        clear_screen()
        print(f"--- sprint {s + 1}/{n}  ({length}s) ---")
        deadline = time.monotonic() + length
        atts, stopped = run_block(
            lambda: make_problem(rng.choice(ops), cfg, rng), deadline)
        sc = sum(a.correct for a in atts)
        sprint_scores.append(sc)
        all_attempts += atts
        print(f"\n  sprint {s + 1}: {sc} solved  (~{round(sc * 120 / length)} at 120s)")
        if stopped:
            break
        if s < n - 1:
            try:
                input("  Enter for the next sprint... ")
            except (EOFError, KeyboardInterrupt):
                break

    print("\n" + "=" * 60)
    print("  SPRINT SET - consistency")
    print("=" * 60)
    if sprint_scores:
        equiv = [round(x * 120 / length) for x in sprint_scores]
        print(f"  raw scores  : {sprint_scores}")
        print(f"  120s-equiv  : {equiv}")
        print(f"  best {max(equiv)}   worst {min(equiv)}   mean {mean(equiv):.0f}")
        if len(equiv) > 1:
            sd = pstdev(equiv)
            cv = 100 * sd / mean(equiv) if mean(equiv) else 0
            print(f"  spread      : stdev {sd:.1f}  (CV {cv:.0f}%)  - lower is steadier")
            print(f"  best-worst gap: {max(equiv) - min(equiv)} points "
                  f"= what inconsistency costs you")

    summary = report(all_attempts, cfg, "Sprint set - all sprints combined")
    record_session("sprint", summary, all_attempts, sprint_scores=sprint_scores)


def mode_weak_review(cfg: dict) -> None:
    stats = load_stats()
    combos = stats.get("weak_combos", {})
    if not combos:
        print("\nNo weak combinations logged yet - run some sessions first.")
        return
    counter = stats.get("review_counter", 0)
    due_now = sum(1 for v in combos.values() if v.get("due", 0) <= counter)
    size = ask_int("How many combos this session", min(20, len(combos)))
    pool = srs_due_pool(stats, max(1, size))
    print(f"\n{len(combos)} combos tracked, {due_now} due now. "
          f"This session draws {len(pool)} (due first, hardest first).")
    dur = ask_int("Duration in seconds", 90)
    rng = random.Random()
    run_timed(lambda: problem_from_key(rng.choice(pool)),
              dur, "Weak-spot review (SRS)", cfg, "weak_review")


def mode_targeted(cfg: dict) -> None:
    """Drill the number patterns your lifetime data flags as slow / inaccurate."""
    stats = load_stats()
    ranked = analyse_weak_patterns(stats, min_samples=6)
    thin = False
    if len(ranked) < 3:
        ranked = analyse_weak_patterns(stats, min_samples=3)
        thin = True
    if not ranked:
        print("\nNot enough pattern data yet. Play a few Classic or Single "
              "runs first so the trainer can see which shapes are slow.")
        return

    if thin:
        print("\n(only light data so far - these will sharpen with more sessions)")
    print("\nYour weakest number patterns, from lifetime data:")
    shortlist = ranked[:8]
    for i, r in enumerate(shortlist, 1):
        print(f"  {i}) {r['label']:<28} n={r['n']:<4} "
              f"acc {r['acc']:>3.0f}%  avg {r['avg']:>4.1f}s")

    default_k = cfg.get("targeted_count", 3)
    print(f"\nPick patterns to drill: numbers separated by commas, "
          f"or Enter for the worst {default_k}.")
    raw = input("> ").strip()
    if not raw:
        chosen = [r["tag"] for r in shortlist[:default_k]]
    else:
        chosen = []
        for tok in raw.replace(" ", "").split(","):
            if tok.isdigit() and 1 <= int(tok) <= len(shortlist):
                chosen.append(shortlist[int(tok) - 1]["tag"])
        if not chosen:
            print("nothing valid picked.")
            return

    labels = ", ".join(pattern_label(t) for t in chosen)
    print(f"\nDrilling: {labels}")
    dur = ask_int("Duration in seconds", 90)
    rng = random.Random()
    src = make_targeted_source(chosen, cfg, rng)
    run_timed(src, dur, f"Targeted - {labels}", cfg, "targeted",
              cfg.get("target_score", 0))


# --------------------------------------------------------------------------- #
#  Guided drills
# --------------------------------------------------------------------------- #


def mode_decomposition(cfg: dict) -> None:
    """Guided place-value breakdown of a 2-digit x 1-digit product."""
    count = cfg["decomp_count"]
    print(f"\nDecomposition drill - {count} problems of the form NN {MUL} N.")
    print(f"Break the big number into tens and ones:  47 {MUL} 8  ->  "
          f"40 {MUL} 8  +  7 {MUL} 8.")
    input("Press Enter to start... ")
    rng = random.Random()

    step_hits = step_total = finished = 0
    times: list = []

    for i in range(count):
        big = rng.randint(12, 99)
        small = rng.randint(3, 9)
        tens, ones = (big // 10) * 10, big % 10
        print(f"\n[{i + 1}/{count}]   {big} {MUL} {small}")
        t_start = time.monotonic()

        steps = [(f"   {tens} {MUL} {small} = ", tens * small),
                 (f"   {ones} {MUL} {small} = ", ones * small),
                 (f"   {tens * small} + {ones * small} = ", big * small)]
        aborted = False
        for label, ans in steps:
            k, _ = prompt_int(label, ans)
            if k.mode == "esc":
                print("   (stopped)")
                aborted = True
                break
            step_total += 1
            step_hits += k.value == str(ans)
        if aborted:
            break

        times.append(time.monotonic() - t_start)
        finished += 1
        ok = k.value == str(big * small)
        print(f"   {OK if ok else BAD} {big} {MUL} {small} = {big * small}")

    print("\n" + "=" * 60)
    print(f"  Decomposition - {finished} completed")
    if step_total:
        print(f"  step accuracy: {step_hits}/{step_total} "
              f"({100 * step_hits / step_total:.0f}%)")
    if times:
        print(f"  avg time per problem: {mean(times):.1f}s   "
              f"(fastest {min(times):.1f}s)")
    print("=" * 60)


def mode_reverse(cfg: dict) -> None:
    """Missing-operand problems across all four operations."""
    count = cfg["reverse_count"]
    print(f"\nReverse drill - {count} problems. Find the missing number.")
    print("Recognising  ? + 34 = 81  as  81 - 34  is the whole skill.")
    input("Press Enter to start... ")
    rng = random.Random()
    ops = enabled_ops(cfg)

    hits = 0
    times: list = []
    misses: list = []

    for i in range(count):
        op = rng.choice(ops)
        prob = make_problem(op, cfg, rng)
        sign = OP_SIGN[op]
        left, _, right = prob.text.split(" ")
        left, right = int(left), int(right)
        if op in ("addition", "multiplication"):
            shown = left + right if op == "addition" else left * right
        else:
            shown = prob.answer

        if rng.random() < 0.5:
            missing, q = left, f"?  {sign} {right} = {shown}"
        else:
            missing, q = right, f"{left} {sign}  ? = {shown}"

        sys.stdout.write(f"\n[{i + 1}/{count}]   {q}\n   ? = ")
        sys.stdout.flush()
        t0 = time.monotonic()
        k = CAPTURE(missing, t0 + 60)
        dt = time.monotonic() - t0
        sys.stdout.write("\n")
        if k.mode == "esc":
            print("   (stopped)")
            break
        ok = k.value == str(missing)
        hits += ok
        times.append(dt)
        if ok:
            print(f"   {OK}  ({dt:.1f}s)")
        else:
            print(f"   {BAD}  ? = {missing}")
            misses.append(f"{q.replace('?', '_')}  -> {missing}")

    print("\n" + "=" * 60)
    print(f"  Reverse drill - {hits}/{len(times)} correct")
    if times:
        print(f"  avg {mean(times):.1f}s   median {median(times):.1f}s")
    if misses:
        print("  missed:")
        for m in misses:
            print(f"    {m}")
    print("=" * 60)


def mode_complement(cfg: dict) -> None:
    """Guided round-to-anchor subtraction: 73 - 48 -> +2 to 50, +23 to 73 -> 25."""
    count = cfg["complement_count"]
    print(f"\nComplement subtraction - {count} problems.")
    print("Step up from the small number to the next ten, then up to the big "
          "number, then add the two jumps.")
    input("Press Enter to start... ")
    rng = random.Random()

    step_hits = step_total = finished = 0
    times: list = []

    for i in range(count):
        big = rng.randint(41, 100)
        small = rng.randint(11, big - 5)
        anchor = ((small // 10) + 1) * 10
        jump1, jump2 = anchor - small, big - anchor
        answer = big - small

        print(f"\n[{i + 1}/{count}]   {big} - {small}")
        t0 = time.monotonic()
        steps = [(f"   {small} up to {anchor}:  + ", jump1),
                 (f"   {anchor} up to {big}:  + ", jump2),
                 (f"   {jump1} + {jump2} = ", answer)]
        aborted = False
        for label, ans in steps:
            k, _ = prompt_int(label, ans)
            if k.mode == "esc":
                print("   (stopped)")
                aborted = True
                break
            step_total += 1
            step_hits += k.value == str(ans)
        if aborted:
            break

        times.append(time.monotonic() - t0)
        finished += 1
        ok = k.value == str(answer)
        print(f"   {OK if ok else BAD} {big} - {small} = {answer}")

    print("\n" + "=" * 60)
    print(f"  Complement subtraction - {finished} completed")
    if step_total:
        print(f"  step accuracy: {step_hits}/{step_total} "
              f"({100 * step_hits / step_total:.0f}%)")
    if times:
        print(f"  avg time per problem: {mean(times):.1f}s")
    print("=" * 60)


def mode_rapid(cfg: dict) -> None:
    """Flash a number, blank the screen, retype it."""
    r = cfg["rapid"]
    rounds = ask_int("Rounds", r["rounds"])
    digits = ask_int("Starting digits", r["digits"])
    flash_ms = ask_int("Flash time (ms)", r["flash_ms"])
    adaptive = r.get("adaptive", True)
    print(f"\nRapid recognition - {rounds} rounds, {flash_ms}ms flash"
          f"{', adaptive length' if adaptive else ''}.")
    input("Press Enter to start... ")
    rng = random.Random()

    hits = 0
    times: list = []
    streak_ok = streak_bad = 0
    max_digits = digits

    for i in range(rounds):
        number = rng.randint(10 ** (digits - 1), 10 ** digits - 1)

        clear_screen()
        print("\n\n")
        print(f"        {number}")
        sys.stdout.flush()
        time.sleep(flash_ms / 1000.0)
        clear_screen()

        sys.stdout.write(f"[{i + 1}/{rounds}]  recall ({digits} digits): ")
        sys.stdout.flush()
        t0 = time.monotonic()
        k = CAPTURE(number, t0 + 30)
        dt = time.monotonic() - t0
        sys.stdout.write("\n")
        if k.mode == "esc":
            print("(stopped)")
            break

        ok = k.value == str(number)
        hits += ok
        times.append(dt)
        print(f"  {OK}  {number}   ({dt:.1f}s)" if ok
              else f"  {BAD}  was {number}, you typed {k.value or '(nothing)'}")

        if adaptive:
            if ok:
                streak_ok, streak_bad = streak_ok + 1, 0
                if streak_ok >= 3:
                    digits += 1
                    max_digits = max(max_digits, digits)
                    streak_ok = 0
                    print(f"  -> up to {digits} digits")
            else:
                streak_bad, streak_ok = streak_bad + 1, 0
                if streak_bad >= 2 and digits > 3:
                    digits -= 1
                    streak_bad = 0
                    print(f"  -> back to {digits} digits")

    print("\n" + "=" * 60)
    print(f"  Rapid recognition - {hits}/{len(times)} correct")
    if times:
        print(f"  avg recall {mean(times):.1f}s   longest length reached: "
              f"{max_digits} digits")
    print("=" * 60)


def mode_typing_floor(cfg: dict) -> None:
    """Pure numpad speed: a number appears, you type it. No arithmetic."""
    t = cfg["typing"]
    rounds = ask_int("Rounds", t["rounds"])
    digits = ask_int("Digits per number", t["digits"])
    print("\nTyping floor - measures raw answer-entry time, no maths involved.")
    print("A number appears; type it back. Correct answers submit themselves.")
    input("Press Enter to start... ")
    rng = random.Random()

    times: list = []
    hits = attempts = 0
    for i in range(rounds):
        n = rng.randint(10 ** (digits - 1), 10 ** digits - 1)
        sys.stdout.write(f"\n[{i + 1}/{rounds}]   {n}\n   > ")
        sys.stdout.flush()
        t0 = time.monotonic()
        k = CAPTURE(n, t0 + 20)
        dt = time.monotonic() - t0
        sys.stdout.write("\n")
        if k.mode == "esc":
            print("(stopped)")
            break
        attempts += 1
        if k.value == str(n):
            hits += 1
            times.append(dt)
        else:
            print(f"   {BAD} (miss - not counted)")

    print("\n" + "=" * 60)
    print(f"  Typing floor - {hits}/{attempts} clean entries")
    if len(times) >= 5:
        med, best = median(times), min(times)
        print(f"  median {med:.2f}s per answer   best {best:.2f}s")
        stats = load_stats()
        stats["typing_floor"] = {
            "median": round(med, 3),
            "best": round(best, 3),
            "samples": len(times),
            "digits": digits,
            "updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        save_stats(stats)
        print("  saved -> stats.json")
        es = expected_score(cfg, stats)
        if es:
            print()
            print(f"  calc-only ceiling ~{es['calc_ceiling']}   "
                  f"realistic expected ~{es.get('expected', '?')}")
    else:
        print("  need at least 5 clean entries to record a floor - try again.")
    print("=" * 60)


# --------------------------------------------------------------------------- #
#  Progress + settings
# --------------------------------------------------------------------------- #


def mode_progress(cfg: dict) -> None:
    stats = load_stats()
    sessions = stats.get("sessions", [])
    if not sessions:
        print("\nNo saved sessions yet.")
        return

    print("\n" + "=" * 72)
    print("  PROGRESS")
    print("=" * 72)
    print(f"  {'date':<20}{'mode':<16}{'score':>6}{'acc%':>7}"
          f"{'add':>6}{'sub':>6}{'mul':>6}{'div':>6}   (avg s/problem)")
    print("  " + "-" * 70)
    for s in sessions[-15:]:
        po = s.get("per_op", {})

        def cell(op):
            v = po.get(op, {}).get("avg_total")
            return f"{v:>6.1f}" if isinstance(v, (int, float)) else f"{'-':>6}"

        print(f"  {s['timestamp'][:19]:<20}{s['mode'][:15]:<16}"
              f"{s['score']:>6}{s['accuracy']:>7.1f}"
              f"{cell('addition')}{cell('subtraction')}"
              f"{cell('multiplication')}{cell('division')}")

    classic = [s for s in sessions if s["mode"] == "classic"]
    if classic:
        best = max(classic, key=lambda s: s["score"])
        recent = classic[-5:]
        print()
        print(f"  Classic best: {best['score']}  ({best['timestamp'][:10]})")
        print(f"  Classic last {len(recent)}: "
              f"{', '.join(str(s['score']) for s in recent)}")

    es = expected_score(cfg, stats)
    if es:
        tf = stats.get("typing_floor", {})
        print()
        print("  Expected score:")
        print(f"    calc-only ceiling   ~{es['calc_ceiling']}  "
              f"(thinking {es['mean_think']}s/problem)")
        if "expected" in es:
            print(f"    realistic expected  ~{es['expected']}  "
                  f"(typing floor {tf.get('median')}s, "
                  f"measured {tf.get('updated', '')[:10]})")
        else:
            print("    realistic expected  - run 'Typing floor' to unlock")
        if "recent_actual" in es:
            print(f"    recent actual avg    {es['recent_actual']}")

    combos = stats.get("weak_combos", {})
    if combos:
        counter = stats.get("review_counter", 0)
        due = sum(1 for v in combos.values() if v.get("due", 0) <= counter)
        print(f"\n  Weak-spot SRS: {len(combos)} tracked, {due} due, "
              f"{stats.get('graduated_total', 0)} retired as fixed.")
        ranked = sorted(combos.items(),
                        key=lambda kv: (kv[1].get("wrong", 0) * 2
                                        + kv[1].get("slow", 0)),
                        reverse=True)
        for key, e in ranked[:12]:
            _, text, ans, _ = parse_key(key)
            print(f"    {text} = {ans:<6}  wrong {e.get('wrong', 0)}, "
                  f"slow {e.get('slow', 0)}, next due @{e.get('due', 0)}")

    _print_lifetime_patterns(stats)
    print("=" * 72)


def _print_lifetime_patterns(stats: dict) -> None:
    ranked = analyse_weak_patterns(stats, min_samples=6)
    if not ranked:
        return
    print("\n  Lifetime number patterns (weakest first, min 6 samples):")
    for r in ranked[:10]:
        print(f"    {r['label']:<28} n={r['n']:<4} acc {r['acc']:>3.0f}%"
              f"   avg {r['avg']:>4.1f}s   weakness {r['score']}")
    print("  -> 'Targeted practice' drills these directly.")


def mode_settings(cfg: dict) -> None:
    while True:
        print("\n--- Settings ---")
        print(f"  1) Classic duration            {cfg['classic_duration']}s")
        for i, op in enumerate(OP_ORDER, start=2):
            s = cfg["operations"][op]
            state = "on " if s["enabled"] else "off"
            print(f"  {i}) {op:<15} [{state}]  a {s['a']}  b {s['b']}")
        print(f"  6) Decomposition count         {cfg['decomp_count']}")
        print(f"  7) Reverse drill count         {cfg['reverse_count']}")
        print(f"  8) Complement count            {cfg['complement_count']}")
        print(f"  9) Rapid recognition           {cfg['rapid']}")
        print(f"  t) Live pace target            "
              f"{cfg.get('target_score', 0) or 'off'}")
        print(f"  p) Sprint set                  "
              f"{cfg['sprint']['count']} x {cfg['sprint']['length']}s")
        print(f"  y) Typing-floor drill          "
              f"{cfg['typing']['rounds']} rounds, {cfg['typing']['digits']} digits")
        print(f"  g) Targeted patterns per run   {cfg.get('targeted_count', 3)}")
        print("  s) save    r) reset to defaults    b) back")
        c = input("> ").strip().lower()

        if c == "1":
            cfg["classic_duration"] = ask_int("Duration seconds",
                                              cfg["classic_duration"])
        elif c in {"2", "3", "4", "5"}:
            op = OP_ORDER[int(c) - 2]
            s = cfg["operations"][op]
            if input("toggle on/off? (y to toggle, Enter to keep) ").strip().lower() == "y":
                s["enabled"] = not s["enabled"]
            s["a"] = [ask_int(f"{op} a min", s["a"][0]),
                      ask_int(f"{op} a max", s["a"][1])]
            s["b"] = [ask_int(f"{op} b min", s["b"][0]),
                      ask_int(f"{op} b max", s["b"][1])]
        elif c == "6":
            cfg["decomp_count"] = ask_int("count", cfg["decomp_count"])
        elif c == "7":
            cfg["reverse_count"] = ask_int("count", cfg["reverse_count"])
        elif c == "8":
            cfg["complement_count"] = ask_int("count", cfg["complement_count"])
        elif c == "9":
            rp = cfg["rapid"]
            rp["rounds"] = ask_int("rounds", rp["rounds"])
            rp["digits"] = ask_int("starting digits", rp["digits"])
            rp["flash_ms"] = ask_int("flash ms", rp["flash_ms"])
            ad = input("adaptive length? y/n ").strip().lower()
            if ad in ("y", "n"):
                rp["adaptive"] = ad == "y"
        elif c == "t":
            cfg["target_score"] = ask_int("Live pace target (0 = off)",
                                          cfg.get("target_score", 0))
        elif c == "p":
            cfg["sprint"]["count"] = ask_int("sprints", cfg["sprint"]["count"])
            cfg["sprint"]["length"] = ask_int("seconds each", cfg["sprint"]["length"])
        elif c == "y":
            cfg["typing"]["rounds"] = ask_int("rounds", cfg["typing"]["rounds"])
            cfg["typing"]["digits"] = ask_int("digits", cfg["typing"]["digits"])
        elif c == "g":
            cfg["targeted_count"] = ask_int("patterns per targeted run",
                                            cfg.get("targeted_count", 3))
        elif c == "s":
            save_config(cfg)
        elif c == "r":
            cfg.clear()
            cfg.update(json.loads(json.dumps(DEFAULT_CONFIG)))
            print("  reset (not yet saved).")
        elif c == "b":
            return
