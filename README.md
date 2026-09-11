# Zetamac Trainer

A terminal mental-arithmetic trainer built around the [Zetamac](https://arithmetic.zetamac.com/)
speed-drill format, with extra modes for building the underlying calculation skills.

```
python zetamac_trainer.py            # menu
python -m ztrainer                   # same thing
python zetamac_trainer.py --classic  # straight into a 120s classic run
python zetamac_trainer.py --sprint   # straight into a sprint set
python zetamac_trainer.py --targeted # drill your weak number patterns
```

Stdlib only, Python 3.8+. On Windows you get character-by-character capture:
answers auto-submit the instant they're correct (like real Zetamac), and every
problem is split into **thinking time** (prompt shown -> first keystroke) and
**typing time** (first keystroke -> submit). Other platforms fall back to line
input (total time only).

## Modes

| # | Mode | What it trains |
|---|------|----------------|
| 1 | Classic | 120s mixed `+ - x div`, Zetamac default ranges, live pace readout |
| 2 | Sprint set | 6 x 20s bursts back to back; report is about **consistency**, not best |
| 3 | Single operation | Grind one operation, any duration |
| 4 | Decomposition | Guided place-value breakdown: `47 x 8 -> 40x8 + 7x8` |
| 5 | Reverse drill | Missing-operand recognition: `? x 7 = 91` |
| 6 | Complement subtraction | Round-to-anchor: `73 - 48 -> +2 to 50, +23 to 73` |
| 7 | Rapid recognition | Flash a number, retype from memory (adaptive length) |
| 8 | Typing floor | Pure numpad speed, no maths -> your raw entry-time floor |
| 9 | Weak-spot review | **Spaced repetition** over combos you miss/stall on; retires ones you've fixed |
| 10 | Targeted practice | Reads your `stats.json`, ranks your weakest **number patterns**, and generates problems in exactly those patterns |
| 11 | Probability & EV | Quant-interview drill: dice / cards / EV / combinatorics, answer as decimal, fraction or percent, tolerance-graded |
| 12 | Fermi / estimation | Guesstimate bank (market sizing, unit conversions, etc.), graded by order of magnitude |
| 13 | Progress report | Trends, expected score, lifetime worst number patterns |
| 14 | Settings | Duration, ranges, drill sizes, live pace target |

### Targeted practice (mode 10)

`analyse_weak_patterns()` scores every lifetime pattern by *slowness* (avg time
vs your overall average) and *inaccuracy*, then lists the worst. Pick some (or
take the default worst-3) and it drills only those: direct construction for
`mul:xN` / `div:/N`, rejection sampling for the structural ones (`sub:borrow`,
`sub:cross-100`, `add:carry`, ...). Results feed straight back into the same
pattern aggregates, so you watch the weakness score drop over sessions.

## What makes it a coach, not just a timer

**Spaced repetition (mode 9).** Every missed or slow combo gets a recall-strength
score. Weak-spot review serves what's *due* first, hardest first; nail a combo
several times fast and it's retired as fixed, so you stop re-drilling things you
already own.

**Pattern-level analytics.** Reports break each operation down by structure -
`mul:x7` vs `mul:x2`, `sub:cross-100`, `add:carry`, `div:/8` - with per-pattern
accuracy and median time, and tell you which pattern is costing you the most
seconds. The progress report keeps a lifetime view.

**Expected score.** Run the typing-floor drill once to record your entry speed.
The trainer then estimates a *calc-only ceiling* (score if typing were instant)
and a *realistic expected score* (calc speed + typing floor), so you can see
whether points are being lost to calculation, to fingers, or to inconsistency.

**Live pace + sprint consistency.** Classic shows `pace 44/50-` as you go. Sprint
mode runs several short bursts and reports the spread (stdev, best-worst gap) -
the score you're losing to the one slow patch rather than to your average.

## Default ranges (match Zetamac)

| Operation | Built as | Operands |
|-----------|----------|----------|
| Addition | `a + b` | a, b in 2-100 |
| Subtraction | addition reversed | answer 2-100 |
| Multiplication | `a x b` | 2-12 times 2-100 |
| Division | multiplication reversed | quotient 2-100, divisor 2-12 |

## End-of-session report

- **SCORE** = number correct, plus overall accuracy.
- Per operation: attempted, correct, accuracy %, avg + median total time,
  avg thinking time, avg typing time.
- **Weak spots**: every problem answered wrong, or correct but slower than
  `max(floor, 2x your median for that operation)`, worst first, with the
  think/type split.

## Project layout

```
zetamac_trainer.py     entry point (also: python -m ztrainer)
ztrainer/
  terminal.py   encoding / glyphs / screen / file paths
  config.py     DEFAULT_CONFIG, load/save, enabled_ops, constants
  problems.py   Problem, make_problem, parse_key
  patterns.py   number-pattern tagging + human labels
  srs.py        spaced-repetition scheduling
  capture.py    keystroke capture, auto-submit, prompt/ask helpers
  scoring.py    Attempt, weak-spot flagging, end-of-session report
  stats.py      stats.json persistence, record_session, expected-score model
  engine.py     run_block / run_timed - the timed-session loop
  targeted.py   weak-pattern analysis + targeted problem generator
  modes.py      every menu action (mode_*)
  cli.py        menu text + main()
```

## Files written (next to the entry point)

- `stats.json` - session history, weak-combo SRS state, lifetime pattern
  aggregates, review counter, and your recorded typing floor.
- `config.json` - only if you save changes from the Settings menu.
