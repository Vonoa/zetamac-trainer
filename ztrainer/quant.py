"""Quant-interview prep: probability/EV problem generators + a Fermi-question bank.

Two grading styles, because the two skills are graded differently in real
interviews:
  - Probability & EV: answers are numeric (fraction/decimal/percent) and are
    graded against an exact computed answer within a tolerance.
  - Fermi/estimation: there is no "exact" answer, only order of magnitude.
    Graded by log10 distance from a reference value, same idea Tradermath
    and similar quant-prep sites use.
"""

from __future__ import annotations

import math
import random
from fractions import Fraction
from itertools import product
from math import comb

# --------------------------------------------------------------------------- #
#  Answer parsing
# --------------------------------------------------------------------------- #


def parse_numeric(s: str):
    """Accepts '1/6', '0.1667', '16.67%', '-3', ... -> float, or None."""
    s = (s or "").strip()
    if not s:
        return None
    pct = s.endswith("%")
    if pct:
        s = s[:-1]
    if not s:
        return None
    try:
        val = float(Fraction(s))
    except Exception:
        try:
            val = float(s)
        except Exception:
            return None
    return val / 100 if pct else val


def parse_magnitude(s: str):
    """Accepts '45000', '45k', '1.2m', '3b' (case-insensitive) -> float, or None."""
    s = (s or "").strip().lower().replace(",", "").replace(" ", "")
    if not s:
        return None
    mult = 1.0
    if s.endswith("k"):
        mult, s = 1e3, s[:-1]
    elif s.endswith("m"):
        mult, s = 1e6, s[:-1]
    elif s.endswith("b"):
        mult, s = 1e9, s[:-1]
    try:
        return float(s) * mult
    except Exception:
        return None


def check_answer(given, answer: float, exact: bool = False) -> bool:
    if given is None:
        return False
    if exact:
        return abs(given - round(answer)) < 0.5
    return abs(given - answer) <= max(0.002, 0.03 * abs(answer))


def fmt_answer(answer: float, exact: bool = False) -> str:
    if exact:
        return str(round(answer))
    if abs(answer) < 1:
        return f"{answer:.4f}  ({answer * 100:.2f}%)"
    return f"{answer:.4f}"


# --------------------------------------------------------------------------- #
#  Probability & EV generators
#  each returns (question_text, answer, tag, one_line_explanation, exact)
# --------------------------------------------------------------------------- #


def gen_dice_sum(rng: random.Random):
    n = rng.choice([2, 2, 3])
    target = rng.randint(n, 6 * n)
    total = 6 ** n
    ways = sum(1 for combo in product(range(1, 7), repeat=n) if sum(combo) == target)
    ans = ways / total
    text = f"Roll {n} fair dice. P(sum = {target})?"
    explain = f"{ways} of {total} equally likely outcomes sum to {target}."
    return text, ans, "prob:dice-sum", explain, False


def gen_binomial(rng: random.Random):
    n = rng.randint(3, 8)
    k = rng.randint(0, n)
    p_num, p_den = rng.choice([(1, 2), (1, 3), (1, 4), (1, 6)])
    p = p_num / p_den
    ans = comb(n, k) * p ** k * (1 - p) ** (n - k)
    text = (f"Success probability is {p_num}/{p_den} each independent trial, "
            f"{n} trials. P(exactly {k} successes)?")
    explain = f"C({n},{k}) x ({p_num}/{p_den})^{k} x (1-{p_num}/{p_den})^{n - k}"
    return text, ans, "prob:binomial", explain, False


def gen_card_pair(rng: random.Random):
    variant = rng.choice(["aces", "same-suit", "no-king"])
    if variant == "aces":
        ans = (4 / 52) * (3 / 51)
        text = "Draw 2 cards without replacement from a 52-card deck. P(both Aces)?"
        explain = "(4/52) x (3/51)"
    elif variant == "same-suit":
        ans = 12 / 51
        text = "Draw 2 cards without replacement. P(both the same suit)?"
        explain = "First card sets the suit; 12 of the remaining 51 match it."
    else:
        ans = (48 / 52) * (47 / 51)
        text = "Draw 2 cards without replacement. P(neither card is a King)?"
        explain = "(48/52) x (47/51) - complement of 'at least one King'."
    return text, ans, "prob:cards", explain, False


def gen_dice_ev(rng: random.Random):
    mult = rng.choice([1, 2, 5, 10])
    ans = 3.5 * mult
    text = f"Roll a fair six-sided die; you're paid ${mult} per pip shown. Expected payout?"
    explain = f"E[die] = 3.5, so 3.5 x {mult} = {ans:g}"
    return text, ans, "ev:dice", explain, False


def gen_geometric_ev(rng: random.Random):
    p_num, p_den = rng.choice([(1, 2), (1, 3), (1, 4), (1, 6)])
    p = p_num / p_den
    ans = 1 / p
    text = (f"You repeat an independent trial with success probability {p_num}/{p_den} "
            f"until the first success. Expected number of trials?")
    explain = f"Geometric distribution: E = 1/p = {p_den}/{p_num}"
    return text, ans, "ev:geometric", explain, False


def gen_game_fair_price(rng: random.Random):
    payouts = [rng.randint(0, 20) for _ in range(6)]
    ans = sum(payouts) / 6
    text = ("A fair die is rolled once. Payout by face (1-6): "
            + ", ".join(f"${p}" for p in payouts) + ". Expected value of one play?")
    explain = f"({' + '.join(str(p) for p in payouts)}) / 6 = {ans:.4f}"
    return text, ans, "ev:game", explain, False


def gen_combinatorics(rng: random.Random):
    n = rng.randint(5, 12)
    k = rng.randint(2, n - 1)
    ans = float(comb(n, k))
    text = f"How many ways to choose {k} items from {n} (order doesn't matter)?"
    explain = f"C({n},{k}) = {n}! / ({k}! x {n - k}!) = {int(ans)}"
    return text, ans, "combo:nCr", explain, True


PROB_GENERATORS = [
    gen_dice_sum, gen_binomial, gen_card_pair,
    gen_dice_ev, gen_geometric_ev, gen_game_fair_price,
    gen_combinatorics,
]


# --------------------------------------------------------------------------- #
#  Fermi / estimation bank
# --------------------------------------------------------------------------- #

FERMI_BANK = [
    {"q": "How many piano tuners are there in Chicago?", "ref": 100, "tag": "fermi:market",
     "approach": "Chicago ~2.7M people -> ~1M households -> ~1 in 10 own a regularly-"
                 "tuned piano -> ~100k tunings/yr. One tuner does ~4/day x 250 "
                 "workdays = 1,000/yr -> ~100 tuners."},
    {"q": "How many ping-pong balls fit inside a school bus?", "ref": 500000, "tag": "fermi:physical",
     "approach": "Usable interior volume ~35 m^3. A ping-pong ball is ~4cm across "
                 "(~3.3e-5 m^3 boxed); random packing ~60% efficient -> "
                 "35 / (3.3e-5/0.6) =~ 500,000-600,000 balls."},
    {"q": "How many gas stations are there in the United States?", "ref": 150000, "tag": "fermi:market",
     "approach": "~330M people, roughly one station per ~2,000-2,500 people "
                 "(covers rural + urban density) -> ~140k-160k stations."},
    {"q": "How many windows are there in New York City?", "ref": 20000000, "tag": "fermi:physical",
     "approach": "~3.5M housing units x ~5 windows each ~17.5M residential, plus "
                 "offices/commercial -> round to ~20M."},
    {"q": "How many golf balls fit inside a Boeing 747?", "ref": 600000, "tag": "fermi:physical",
     "approach": "Cabin usable volume ~40 m^3. Golf ball ~4.3cm (~4.6e-5 m^3 boxed); "
                 "~60% packing -> 40 / (4.6e-5/0.6) =~ 500,000-700,000 balls."},
    {"q": "How many Google searches happen worldwide per day?", "ref": 8500000000, "tag": "fermi:rate",
     "approach": "~5B internet users x ~2-4 searches/day average -> 10-20B; "
                 "reported figure is ~8.5B/day."},
    {"q": "How many taxis operate in Manhattan?", "ref": 13000, "tag": "fermi:market",
     "approach": "NYC yellow-cab medallions are capped; commonly cited figure "
                 "is ~13,000."},
    {"q": "What is the combined weight of all humans on Earth, in kg?", "ref": 4e11, "tag": "fermi:physical",
     "approach": "~8B people x ~50kg average (weighted for children) -> "
                 "~4x10^11 kg (~400M metric tons)."},
    {"q": "How many times does a human heart beat in an 75-year lifetime?", "ref": 3e9, "tag": "fermi:rate",
     "approach": "~70 beats/min x 60 x 24 x 365 x 75 yrs =~ 2.8 billion beats."},
    {"q": "How many registered cars are there in the United States?", "ref": 2.8e8, "tag": "fermi:population",
     "approach": "~330M people, roughly 0.85 vehicles per person on average "
                 "-> ~280M vehicles."},
    {"q": "What is the annual revenue of a single typical Starbucks store, in dollars?",
     "ref": 1300000, "tag": "fermi:market",
     "approach": "~500 customers/day x ~$6 avg ticket x 365 days =~ $1.1M-1.3M."},
    {"q": "How many hairdressers/barbers work in the United States?", "ref": 700000, "tag": "fermi:market",
     "approach": "~330M people, a haircut every ~6 weeks on average, a stylist "
                 "does ~8/day x 250 days = 2,000/yr -> 330M x (8.5 cuts/yr) / "
                 "2,000 =~ 700,000."},
    {"q": "How many liters of water does a typical person in the US use per day?",
     "ref": 300, "tag": "fermi:rate",
     "approach": "Shower ~65L + toilet ~70L + laundry/dishes ~80L + misc/outdoor "
                 "~85L =~ 300L/day (~80 gallons)."},
    {"q": "How many Uber/Lyft drivers are actively driving in NYC at a given moment?",
     "ref": 15000, "tag": "fermi:market",
     "approach": "NYC has ~100k+ registered rideshare drivers; at any instant "
                 "maybe 10-20% are on the road -> ~15,000."},
    {"q": "How many trees are there on Earth?", "ref": 3e12, "tag": "fermi:physical",
     "approach": "Forested land ~4x10^7 km^2, average density order ~10^4-10^5 "
                 "trees/km^2 depending on forest type -> commonly cited estimate "
                 "~3 trillion trees."},
    {"q": "How many pizzas are sold in the United States per year?", "ref": 3e9, "tag": "fermi:rate",
     "approach": "~330M people, average ~9 pizzas/person/year (varies widely) "
                 "-> roughly 3 billion pizzas/year."},
]


def fermi_tier(guess, ref: float):
    """Return (tier_label, log10_distance) or (tier_label, None) if invalid."""
    if guess is None or guess <= 0 or ref <= 0:
        return "off", None
    diff = abs(math.log10(guess) - math.log10(ref))
    if diff <= 0.3:
        return "excellent", diff
    if diff <= 0.7:
        return "good", diff
    if diff <= 1.3:
        return "order of magnitude", diff
    return "off", diff


def fmt_magnitude(x: float) -> str:
    if x >= 1e9:
        return f"{x / 1e9:g}B"
    if x >= 1e6:
        return f"{x / 1e6:g}M"
    if x >= 1e3:
        return f"{x / 1e3:g}k"
    return f"{x:g}"
