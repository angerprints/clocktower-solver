"""Does a 30% actually happen 30% of the time?

    python tools/calibrate.py --games 300

Every other measurement so far has asked whether the solver is *right* —
whether the truth survives, whether the Demon is found. This asks
something different and harder to fake: when the solver says a seat is
30% likely to be evil, is it evil about 30% of the time?

That is worth having because it is the only thing that turns the
judgement-call constants into measurements. `POISON_HIT_PENALTY` is 0.35
because it felt about right; the sensitivity sweep says which constants
matter without saying what they should be. A calibration table says.

**What it cannot tell you.** It measures the solver against this
simulator, so a systematic error in the simulator becomes a systematic
correction in the priors. The protocol from `play_games.py` exists for
exactly that reason: somebody has to read a played game and check the
Storyteller resolved it properly.

**And a caveat about buckets.** Most seat-readings sit near the base
rate — two evil in nine is 22% — so the middle buckets fill up and the
extremes stay thin. A bucket with four readings in it says nothing; the
count is printed beside every line so a thin one can be ignored rather
than believed.
"""

import argparse
import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "tests"))

import claims as claim_model                                  # noqa: E402
import simulate                                               # noqa: E402
import botc.solver as S                                       # noqa: E402
from botc import scripts                                      # noqa: E402
from botc.info import GameState                               # noqa: E402
from botc.roles import TEAM, is_evil                          # noqa: E402

OUT = HERE.parent / "games"

# Ten points wide. Narrower buckets look more precise and are mostly
# noise at any sample size this can reach in a few minutes.
EDGES = list(range(0, 101, 10))


def bucket_of(pct):
    return min(int(pct // 10), 9)


# Above this many worlds, sample rather than enumerate.
#
# The number matters more than it looks. Set at 50,000 this did nothing,
# because the boards that actually run away sit at a quarter of a million
# and everything else is under three thousand — there is almost nothing
# in between, so the threshold either catches the outliers or it catches
# none of them.
#
# One Sects & Violets game in twenty-two took 430 seconds against 12 for
# the next worst. Four seats had softclaimed "never", which on that
# script narrows twenty-five characters to ten apiece: ten thousand
# combinations before any other constraint applies. Nothing is wrong with
# the board, it genuinely has that many worlds.
ENUMERATE_UP_TO = 20_000

# Below this, the board is likely to be *repaired*, which costs far more
# than enumerating ever does — nine claims opened one at a time with good
# lies allowed. Sampling with good lies on answers the same question in
# one pass.
#
# Tied to the solver's own cornered threshold rather than picked
# separately, because that is the number that decides whether repair
# fires. Guessing at 40 left boards estimating 99 and 195 to take 158 and
# 294 seconds; those had 3 and 14 surviving worlds, both under the
# threshold, both repaired.
#
# The estimate is rough, so allow generous headroom above it.
REPAIR_LIKELY = S._CORNERED * 20


def readings(games, players, nights, script, first_seed, dives=12000):
    """Every seat-reading from a pile of played games, with the truth."""
    for i in range(games):
        seed = first_seed + i
        rng = random.Random(seed)
        deal, heard = simulate.play(players, rng, nights=nights,
                                    script=script)
        claims, wakes, _notes = claim_model.claims_for(deal, rng,
                                                       script=script)
        # What the table could honestly have established — true readings
        # whose named seats are settled by something else. Not every true
        # reading: that would hand the solver knowledge a real table
        # never had, and flatter the very thing being measured.
        claim_model.confirm_readings(deal, heard, rng)
        state = GameState(n_players=players, script=script, claims=claims,
                          wakes=wakes, deaths=dict(deal.deaths),
                          infos=list(heard), votes=dict(deal.votes),
                          nominations=dict(deal.nominations))
        # Sample when enumerating would take too long. Two measurements
        # hit that wall before this existed — a Sects & Violets
        # calibration and a fifteen player table — and neither board is
        # unusual, they are just wide.
        #
        # Which way round is decided by a quick estimate rather than by
        # trying and giving up: `pilot_size` walks the space a little and
        # says roughly how big it is.
        # A few hundred walks is enough to tell a five-hundred-world
        # board from a quarter-million one, and costs milliseconds.
        # A board that fits nothing is the *expensive* one, not the
        # cheap one. `pilot_size` measures the plain space, which on such
        # a board is zero or near it — and then `solve_or_repair` opens
        # each of nine claims in turn with good lies allowed, which is
        # where the minutes go. Three boards in eighty took 40, 147 and
        # 296 seconds while the pilot reported 0, 0 and 195.
        #
        # So a tiny estimate is as much a reason to sample as a huge one.
        est = S.pilot_size(state, walks=400)
        if est > ENUMERATE_UP_TO or est < REPAIR_LIKELY:
            rows = S.sampled_rows(state, dives=dives, rng=rng,
                                  allow_good_lies=est < REPAIR_LIKELY)
            if not rows:
                continue
        else:
            _all, valid, _liar = S.solve_or_repair(state)
            if not valid:
                continue
            rows = S.summarize(valid, state)
        phase = state.final_phase()
        for seat, row in enumerate(rows):
            yield {
                "seed": seed,
                "seat": seat,
                "evil_pct": row["evil_pct"],
                "demon_pct": row["demon_pct"],
                "really_evil": is_evil(deal.role_at(seat, phase)),
                "really_demon": TEAM[deal.role_at(seat, phase)] == "demon",
            }


def table(rows, said, was):
    """One calibration table: what was claimed against what happened."""
    buckets = [{"n": 0, "said": 0.0, "hit": 0} for _ in range(10)]
    for row in rows:
        b = buckets[bucket_of(row[said])]
        b["n"] += 1
        b["said"] += row[said]
        b["hit"] += bool(row[was])
    out = []
    for i, b in enumerate(buckets):
        if not b["n"]:
            continue
        out.append({
            "range": f"{EDGES[i]:>3}-{EDGES[i + 1]:<3}",
            "n": b["n"],
            "said": b["said"] / b["n"],
            "happened": 100.0 * b["hit"] / b["n"],
        })
    return out


def show(name, got):
    print(f"\n{name}")
    print("  bucket     said   happened   readings   gap")
    worst = 0.0
    for line in got:
        gap = line["happened"] - line["said"]
        # A thin bucket is noise; say so rather than let it be read.
        note = "  (thin)" if line["n"] < 30 else ""
        if line["n"] >= 30:
            worst = max(worst, abs(gap))
        print(f"  {line['range']}  {line['said']:6.1f}%   "
              f"{line['happened']:6.1f}%   {line['n']:>8}   "
              f"{gap:+6.1f}{note}")
    print(f"  worst gap in a bucket with 30 or more: {worst:.1f} points")
    return worst


def build(games, players, nights, script_name, first_seed):
    script = scripts.BUILT_IN[script_name]
    rows = list(readings(games, players, nights, script, first_seed))
    if not rows:
        print("no readings at all")
        return 1

    OUT.mkdir(exist_ok=True)
    evil = table(rows, "evil_pct", "really_evil")
    demon = table(rows, "demon_pct", "really_demon")

    print(f"{games} games of {players} players on {script_name}, "
          f"{nights} nights each")
    print(f"{len(rows)} seat-readings")
    worst = max(show("is this seat evil?", evil),
                show("is this seat the Demon?", demon))

    path = OUT / f"calibration-{players}p-{first_seed}.json"
    path.write_text(json.dumps({
        "games": games, "players": players, "nights": nights,
        "script": script_name, "seed": first_seed,
        "readings": len(rows), "evil": evil, "demon": demon,
    }, indent=1))
    print(f"\nwritten to {path.relative_to(HERE.parent)}")
    return 0 if worst < 25 else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--games", type=int, default=100)
    ap.add_argument("--players", type=int, default=9)
    ap.add_argument("--nights", type=int, default=3)
    ap.add_argument("--script", default="Trouble Brewing")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    raise SystemExit(build(args.games, args.players, args.nights,
                           args.script, args.seed))
