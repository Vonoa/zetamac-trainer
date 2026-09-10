#!/usr/bin/env python3
"""Zetamac Trainer - entry point.

The implementation lives in the ``ztrainer`` package (see ztrainer/__init__.py
for the module map). Run this file, or ``python -m ztrainer``.

    python zetamac_trainer.py            # interactive menu
    python zetamac_trainer.py --classic  # straight into a 120s classic run
    python zetamac_trainer.py --targeted # drill your weak number patterns
    python zetamac_trainer.py --help
"""

import sys

from ztrainer.cli import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
