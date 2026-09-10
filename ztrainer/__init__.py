"""Zetamac Trainer package - a terminal mental-arithmetic trainer.

Module map
  terminal   encoding / glyphs / screen / file paths
  config     DEFAULT_CONFIG, load/save, enabled_ops, constants
  problems   Problem, make_problem, parse_key  (problem generation)
  patterns   number-pattern tagging + labels (bottleneck analytics)
  srs        spaced-repetition scheduling for weak combos
  capture    keystroke capture, auto-submit, prompt/ask helpers
  scoring    Attempt, weak-spot flagging, the end-of-session report
  stats      stats.json persistence, record_session, expected-score model
  engine     run_block / run_timed - the timed-session loop
  targeted   read stats -> drill the patterns you personally struggle with
  modes      every menu action (mode_*)
  cli        menu text + main()
"""

__version__ = "0.2.0"
