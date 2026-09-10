"""Zetamac Trainer - a terminal mental-arithmetic trainer.

(This module is the menu and main loop; see ztrainer/__init__.py for the map.)

  1  Classic            120s mixed +/-/x/div, Zetamac default ranges, live pace
  2  Sprint set         short bursts back to back; measures consistency
  3  Single operation   one operation at a time
  4  Decomposition      guided NN x N place-value breakdown
  5  Reverse drill      missing-operand problems:  ? x 7 = 91
  6  Complement sub     guided round-to-anchor subtraction
  7  Rapid recognition  flash a number, retype from memory
  8  Typing floor       pure numpad speed -> unlocks the expected-score model
  9  Weak-spot review   spaced repetition over combos you miss / stall on
 10  Targeted practice  drill the number patterns your stats.json flags as weak
 11  Progress report    trends, expected score, worst number patterns
 12  Settings           duration, ranges, drill sizes, pace target

Stdlib only. Windows gets character capture (auto-submit + think/type split);
other platforms fall back to line input (total time only).
"""

from __future__ import annotations

from .config import load_config
from .modes import (
    mode_classic, mode_complement, mode_decomposition, mode_progress,
    mode_rapid, mode_reverse, mode_settings, mode_single, mode_sprint,
    mode_targeted, mode_typing_floor, mode_weak_review,
)
from .terminal import clear_screen

MENU = """
=========  ZETAMAC TRAINER  =========
   1) Classic            120s mixed, Zetamac default ranges + live pace
   2) Sprint set         short bursts back to back - consistency check
   3) Single operation   grind one of +  -  x  div
   4) Decomposition      guided NN x N breakdown
   5) Reverse drill      find the missing operand
   6) Complement sub     guided round-to-anchor subtraction
   7) Rapid recognition  flash-and-retype numbers
   8) Typing floor       pure entry speed -> unlocks expected score
   9) Weak-spot review   spaced repetition over what you miss / stall on
  10) Targeted practice  drill your data-flagged weak number patterns
  11) Progress report    trends, expected score, worst number patterns
  12) Settings
   0) Quit
"""

ACTIONS = {
    "1": mode_classic,
    "2": mode_sprint,
    "3": mode_single,
    "4": mode_decomposition,
    "5": mode_reverse,
    "6": mode_complement,
    "7": mode_rapid,
    "8": mode_typing_floor,
    "9": mode_weak_review,
    "10": mode_targeted,
    "11": mode_progress,
    "12": mode_settings,
}

_DIRECT = {
    "--classic": mode_classic,
    "--sprint": mode_sprint,
    "--targeted": mode_targeted,
    "--progress": mode_progress,
}


def main(argv) -> int:
    cfg = load_config()

    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    for flag, fn in _DIRECT.items():
        if flag in argv:
            fn(cfg)
            return 0

    while True:
        print(MENU)
        try:
            choice = input("select > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye.")
            return 0
        if choice in ("0", "q", "quit"):
            print("bye.")
            return 0
        action = ACTIONS.get(choice)
        if not action:
            print("  ? pick a number from the menu.")
            continue
        try:
            action(cfg)
        except KeyboardInterrupt:
            print("\n(back to menu)")
        input("\nPress Enter for the menu... ")
        clear_screen()
