"""The timed-session loop shared by classic / single / sprint / weak / targeted."""

from __future__ import annotations

import sys
import time

from .capture import CAPTURE
from .scoring import build_attempt, report
from .stats import print_expected, record_session
from .terminal import BAD, CLOCK, IS_WINDOWS, OK, clear_screen


def run_block(problems_source, deadline: float, pace_target: int = 0):
    """Inner problem loop. Returns (attempts, stopped_early)."""
    attempts: list = []
    stopped = False
    block_start = time.monotonic()
    solved = 0
    try:
        while time.monotonic() < deadline:
            prob = problems_source()
            now = time.monotonic()
            remaining = deadline - now
            elapsed = now - block_start
            pace = ""
            if elapsed > 3 and solved > 0:
                proj = solved / elapsed * (deadline - block_start)
                pace = f" pace {proj:2.0f}"
                if pace_target:
                    pace += f"/{pace_target}{'+' if proj >= pace_target else '-'}"
            sys.stdout.write(f"[{remaining:4.0f}s{pace}]  {prob.text} = ")
            sys.stdout.flush()
            t0 = time.monotonic()
            k = CAPTURE(prob.answer, deadline)

            if k.mode == "timeout":
                sys.stdout.write(f"   {CLOCK}\n")
                break
            if k.mode == "esc":
                sys.stdout.write("   (stopped)\n")
                stopped = True
                break

            a = build_attempt(prob, k, t0)
            attempts.append(a)
            if a.correct:
                solved += 1
                sys.stdout.write(f"   {OK}\n")
            else:
                sys.stdout.write(f"   {BAD} = {prob.answer}\n")
            sys.stdout.flush()
    except KeyboardInterrupt:
        print("\n(interrupted)")
        stopped = True
    return attempts, stopped


def run_timed(problems_source, duration: int, label: str, cfg: dict,
              mode_tag: str, target: int = 0):
    """problems_source: a zero-arg callable returning the next Problem."""
    print()
    print(f"{label}  -  {duration}s")
    print("Type the answer; a correct answer submits itself. "
          "Enter = commit/skip, Esc = stop early.")
    if target:
        print(f"Live pace target: {target}")
    if not IS_WINDOWS:
        print("(this platform: press Enter to submit, 'q' to stop)")
    input("Press Enter to start... ")
    clear_screen()

    deadline = time.monotonic() + duration
    attempts, _ = run_block(problems_source, deadline, target)

    summary = report(attempts, cfg, label)
    record_session(mode_tag, summary, attempts)
    if mode_tag == "classic":
        print_expected(cfg)
    return attempts
