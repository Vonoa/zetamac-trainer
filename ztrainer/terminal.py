"""Terminal quirks: UTF-8 output, glyph fallbacks, screen clear, file paths."""

from __future__ import annotations

import os
import sys

try:  # print UTF-8 where the terminal allows it
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass


def _supports_unicode() -> bool:
    enc = (sys.stdout.encoding or "ascii").lower()
    try:
        "×÷✓✗∙".encode(enc)
        return True
    except Exception:
        return False


UNI = _supports_unicode()
MUL = "×" if UNI else "x"
DIV = "÷" if UNI else "/"
OK = "✓" if UNI else "+"
BAD = "✗" if UNI else "x"
CLOCK = "⏱" if UNI else "!"

IS_WINDOWS = os.name == "nt"

msvcrt = None
if IS_WINDOWS:
    import msvcrt as _msvcrt  # noqa: E402

    msvcrt = _msvcrt


def clear_screen() -> None:
    os.system("cls" if IS_WINDOWS else "clear")


# Data files live next to the project root (parent of this package).
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATS_PATH = os.path.join(BASE_DIR, "stats.json")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
