"""Keystroke capture with Zetamac-style auto-submit, plus small input helpers.

On Windows, read_answer() reads character by character: it records the time of
the first keystroke (thinking time ends there) and submits the instant the
buffer equals the correct answer. Elsewhere we fall back to line input and only
total time is meaningful.
"""

from __future__ import annotations

import sys
import time
from collections import namedtuple

from .terminal import IS_WINDOWS, msvcrt

Key = namedtuple("Key", "value first submit mode")
# mode: 'auto'    answer matched while typing (correct, Zetamac-style)
#       'enter'   Enter pressed with a non-empty buffer
#       'skip'    Enter pressed with an empty buffer
#       'esc'     Esc pressed -> end the session / drill
#       'timeout' the session clock ran out mid-answer


def read_answer(correct: int, deadline: float) -> Key:
    """Character capture with auto-submit. Windows only."""
    correct_str = str(correct)
    buf: list = []
    first = None

    while True:
        if time.monotonic() >= deadline:
            return Key("".join(buf), first, time.monotonic(), "timeout")

        if not msvcrt.kbhit():
            time.sleep(0.004)
            continue

        ch = msvcrt.getwch()
        now = time.monotonic()

        if ch in ("\x00", "\xe0"):  # function / arrow key - consume next, ignore
            msvcrt.getwch()
            continue
        if ch == "\x03":  # Ctrl-C
            raise KeyboardInterrupt
        if ch == "\x1b":  # Esc
            return Key("".join(buf), first, now, "esc")
        if ch in ("\r", "\n"):
            if not buf:
                return Key("", first, now, "skip")
            return Key("".join(buf), first, now, "enter")
        if ch in ("\x08", "\x7f"):  # backspace
            if buf:
                buf.pop()
                sys.stdout.write("\b \b")
                sys.stdout.flush()
            continue
        if ch == "-" and not buf:  # leading minus (reverse drills)
            buf.append(ch)
            sys.stdout.write(ch)
            sys.stdout.flush()
            continue
        if ch.isdigit():
            if first is None:
                first = now
            buf.append(ch)
            sys.stdout.write(ch)
            sys.stdout.flush()
            if "".join(buf) == correct_str:
                return Key("".join(buf), first, time.monotonic(), "auto")
            continue
        # anything else: ignore


def read_answer_linemode(correct: int, deadline: float) -> Key:
    """Fallback for non-Windows terminals: line input, total time only."""
    if deadline - time.monotonic() <= 0:
        return Key("", None, time.monotonic(), "timeout")
    try:
        raw = input().strip()
    except EOFError:
        return Key("", None, time.monotonic(), "esc")
    now = time.monotonic()
    if raw == "":
        return Key("", None, now, "skip")
    if raw.lower() in ("q", "quit", "esc"):
        return Key("", None, now, "esc")
    if now > deadline:
        return Key(raw, None, now, "timeout")
    mode = "auto" if raw == str(correct) else "enter"
    return Key(raw, None, now, mode)


CAPTURE = read_answer if IS_WINDOWS else read_answer_linemode


def prompt_int(label: str, correct: int, timeout: float = 90.0):
    """Ask a single value inline (guided drills). Returns (Key, elapsed_seconds)."""
    sys.stdout.write(label)
    sys.stdout.flush()
    start = time.monotonic()
    k = CAPTURE(correct, start + timeout)
    sys.stdout.write("\n")
    return k, time.monotonic() - start


def ask_int(label: str, default: int) -> int:
    raw = input(f"{label} [{default}]: ").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        print("  not a number - using default.")
        return default
