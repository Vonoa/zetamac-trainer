"""Configuration: defaults, load/save, and small shared constants."""

from __future__ import annotations

import json
import os

from .terminal import CONFIG_PATH, DIV, MUL

DEFAULT_CONFIG = {
    "classic_duration": 120,
    "operations": {
        "addition": {"enabled": True, "a": [2, 100], "b": [2, 100]},
        "subtraction": {"enabled": True, "a": [2, 100], "b": [2, 100]},
        "multiplication": {"enabled": True, "a": [2, 12], "b": [2, 100]},
        "division": {"enabled": True, "a": [2, 12], "b": [2, 100]},
    },
    # A "correct but slow" answer is flagged when total time exceeds
    #   max(slow_floor[op], 2 x median time for that op this session).
    "slow_floor": {
        "addition": 3.5,
        "subtraction": 3.5,
        "multiplication": 4.5,
        "division": 4.5,
    },
    "decomp_count": 10,
    "reverse_count": 20,
    "complement_count": 12,
    "rapid": {"rounds": 15, "digits": 4, "flash_ms": 750, "adaptive": True},
    "typing": {"rounds": 20, "digits": 3},
    "sprint": {"count": 6, "length": 20},
    "targeted_count": 3,   # how many weak patterns the targeted drill picks by default
    "target_score": 0,     # 0 = no live pace target
}

# A tracked weak combo is retired once it has survived this many review units
# with a streak of >= 3 clean-and-fast reps.
GRAD_INTERVAL = 8

OP_ORDER = ["addition", "subtraction", "multiplication", "division"]
OP_SIGN = {
    "addition": "+",
    "subtraction": "-",
    "multiplication": MUL,
    "division": DIV,
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
                return _deep_merge(DEFAULT_CONFIG, json.load(fh))
        except Exception:
            print("(could not read config.json - using defaults)")
    return json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy


def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)
    print(f"saved -> {CONFIG_PATH}")


def enabled_ops(cfg: dict) -> list:
    return [op for op in OP_ORDER if cfg["operations"][op]["enabled"]]
