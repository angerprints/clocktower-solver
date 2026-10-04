"""Play games out, and write down what happened and what the solver made
of it.

    python tools/play_games.py --games 5 --players 9

Two things come out of each game, and they answer different questions.

**A protocol** you can read: the true assignment, then phase by phase
what the Storyteller did, what each seat learned, who claimed what and
why, and where the solver stood at that moment. That is for checking the
*simulator* — if it resolves a Poisoner wrongly, everything downstream is
confidently wrong in the same direction, and no assertion I write will
notice. Your eyes on a played-out game are the only check on that.

**A save file** in the app's own format, so the same game can be opened
in the grimoire and stepped through by hand.

What it does *not* claim is that a low reading for the truth is a
failure. If the truth sits at 12% after night one that is often correct:
the evidence genuinely does not distinguish it yet, and a solver that
always put the truth top would be cheating. The measures worth having
are whether the truth is ever *ruled out* — always a bug — and whether
confidence grows as information arrives.
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
from botc.catalogue import CHARACTERS                         # noqa: E402
from botc.info import GameState, phase_index                  # noqa: E402
from botc.roles import TEAM                                   # noqa: E402
from botc.worlds import World                                 # noqa: E402

OUT = HERE.parent / "games"

# Above this many worlds, sample. Below the second, the board will be
# repaired — which costs far more than enumerating — so sample there too.
# Tied to the solver's own cornered threshold, which is the number that
# actually decides whether repair fires.
ENUMERATE_UP_TO = 20_000
REPAIR_LIKELY = S._CORNERED * 20


def show(key):
    return CHARACTERS[key].name if key in CHARACTERS else key


def phases_of(deal, nights):
    """Every phase the game reached, in order."""
    # Reached, not asked for: a game evil won, or one a Mastermind's
    # extra day finished, has no phases after its last (04.10.2026).
    last = min(nights, deal.game_ends_after or nights)
    out = []
    for night in range(1, last + 1):
        out.append(f"N{night}")
        if deal.ended_at == f"N{night}":
            break                         # over at dawn: no day follows
        out.append(f"D{night}")
    return out


def board_at(deal, heard, claims, wakes, phase, script=None):
    """What a player would have written down by this point.

    Only what the table has seen: deaths that have happened, readings
    that have been given. The true assignment is not in here — that is
    the whole point.
    """
    limit = phase_index(phase)
    record = deal.record(upto=phase)
    infos = [row for row in heard if phase_index(f"N{row.night}") <= limit]
    from botc import scripts
    return GameState(n_players=deal.n, script=script or scripts.TROUBLE_BREWING,
                     claims=dict(claims), wakes=dict(wakes),
                     infos=infos, **record)


def reading(state, deal, reachable=True):
    """Where the solver stands, and where the truth sits in its answer.

    `reachable` is false when the game contains a lie the search cannot
    represent at all — a Townsfolk claiming to be a *different*
    Townsfolk. The solver prices that (TOWNSFOLK_LIE_PENALTY, 0.02) but
    has never generated it, so the world simply is not among the
    candidates and "the truth was thrown away" would be the wrong
    reading of what happened.
    """
    # Sample rather than enumerate on the boards where enumerating is
    # ruinous, exactly as `calibrate.py` does.
    #
    # Two kinds are ruinous and they look opposite. A *wide* board — four
    # seats softclaiming "never" on Sects & Violets — reaches a quarter
    # of a million worlds. And a board that fits almost *nothing* is
    # worse still, because `solve_or_repair` then opens each of nine
    # claims in turn with good lies allowed; three such boards took 40,
    # 147 and 296 seconds while the estimate said 0, 0 and 195.
    #
    # Without this, generating six Sects & Violets games for somebody to
    # read simply did not finish.
    est = S.pilot_size(state, walks=400)
    thin = est < REPAIR_LIKELY
    if est > ENUMERATE_UP_TO or thin:
        rows = S.sampled_rows(state, dives=9000, allow_good_lies=thin)
        if not rows:
            return {"worlds": 0, "truth_kept": False, "truth_pct": 0.0,
                    "rows": [], "sampled": True}
        truth = World(tuple(deal.roles), tuple(deal.believes))
        demon = deal.demon_at(state.final_phase())
        order = sorted(range(deal.n), key=lambda i: -rows[i]["demon_pct"])
        return {
            "worlds": int(est), "sampled": True,
            "repaired_seat": None,
            "truth_reachable": True, "truth_kept": False, "truth_pct": 0.0,
            "demon_seat": demon + 1 if demon is not None else None,
            "demon_rank": order.index(demon) + 1 if demon is not None else None,
            "demon_pct": round(rows[demon]["demon_pct"], 2)
                         if demon is not None else 0.0,
            "demon_ruled_out": (demon is not None
                                and rows[demon]["demon_pct"] <= 0.0),
            "rows": rows,
        }

    _all, valid, liar = S.solve_or_repair(state)
    if not valid:
        return {"worlds": 0, "truth_kept": False, "truth_pct": 0.0,
                "rows": []}

    weights = [S.world_weight(w, state) for w in valid]
    total = sum(weights) or 1.0
    truth = World(tuple(deal.roles), tuple(deal.believes))
    kept = truth in valid
    share = sum(x for w, x in zip(valid, weights) if w == truth) / total

    rows = S.summarize(valid, state)
    # What the tool is actually for. Whether the exact world survives is
    # a stricter question than anybody needs answered: a good player
    # lying scrambles who holds what without changing who the Demon is,
    # and catching the Demon is the whole job.
    demon = deal.demon_at(state.final_phase())
    rows = S.summarize(valid, state)
    order = sorted(range(deal.n), key=lambda i: -rows[i]["demon_pct"])

    return {
        "worlds": len(valid),
        "repaired_seat": (liar + 1) if liar is not None else None,
        "truth_reachable": reachable,
        "truth_kept": kept,
        "truth_pct": round(100 * share, 2),
        "demon_seat": demon + 1,
        "demon_rank": order.index(demon) + 1,
        "demon_pct": round(rows[demon]["demon_pct"], 2),
        "demon_ruled_out": rows[demon]["demon_pct"] <= 0.0,
        "rows": [{"seat": i + 1,
                  "evil_pct": round(r["evil_pct"], 1),
                  "demon_pct": round(r["demon_pct"], 1),
                  "top": [[show(name), round(pct, 1)]
                          for name, pct in r["roles"][:3]]}
                 for i, r in enumerate(rows)],
    }


def one_game(n, nights, seed, script=None):
    """Play a game and write down everything about it."""
    from botc import scripts
    script = script or scripts.TROUBLE_BREWING
    rng = random.Random(seed)
    deal, heard = simulate.play(n, rng, nights=nights, script=script)
    claims, wakes, notes = claim_model.claims_for(deal, rng, script=script)

    # Can the search even represent this game? A Townsfolk claiming a
    # different Townsfolk is a world it never generates, in any mode, so
    # a game containing one is outside what the solver can be asked.
    reachable = not any(
        "no reason" in note
        and TEAM[deal.roles[seat]] == "townsfolk"
        and TEAM.get(claims.get(seat, ""), "") == "townsfolk"
        for seat, note in notes.items())

    seats = []
    for seat in range(deal.n):
        seats.append({
            "seat": seat + 1,
            "really": show(deal.roles[seat]),
            "believes": show(deal.believes[seat]) if deal.believes[seat]
                        else None,
            "team": TEAM[deal.roles[seat]],
            "claimed": show(claims[seat]) if seat in claims else None,
            "softclaim": wakes.get(seat),
            "why": notes[seat],
        })

    timeline = []
    for phase in phases_of(deal, nights):
        died = [s + 1 for s in sorted(deal.died_on(phase))]
        # An execution is recorded as "E2", not "D2", so matching the
        # phase exactly dropped every one: the transcript showed an
        # Undertaker reading a seat that had apparently never died. The
        # simulator was right and the write-up was lying about it.
        executed = [s + 1 for s in sorted(deal.died_on("E" + phase[1:]))
                    ] if phase.startswith("D") else []
        learned = [{"seat": row.player + 1, "type": type(row).__name__,
                    "said": describe(row),
                    "misled": misled_by(deal, row)}
                   for row in heard if f"N{row.night}" == phase]
        state = board_at(deal, heard, claims, wakes, phase, script)
        timeline.append({
            "phase": phase,
            "died": died,
            "executed": executed,
            "poisoned": [deal.poisoned[int(phase[1:])] + 1]
                        if phase.startswith("N")
                        and int(phase[1:]) in deal.poisoned else [],
            "learned": learned,
            "solver": reading(state, deal, reachable),
        })

    return {
        "seed": seed, "players": n, "nights": nights,
        "truth_reachable": reachable,
        "red_herring": (deal.red_herring + 1) if deal.red_herring is not None
                       else None,
        "seats": seats,
        "timeline": timeline,
        "script": script.name,
        "save": save_file(deal, heard, claims, wakes, script),
    }


def misled_by(deal, row):
    """Was this reading a legal lie, and who made it one?

    A Spy shown as a Townsfolk, a Recluse shown as a Minion. The
    Storyteller is allowed to mislead, and the whole point of reviewing a
    played game is being able to see when it did — so this says so rather
    than leaving a reading that looks simply wrong.
    """
    kind = type(row).__name__
    if kind in ("Washerwoman", "Librarian", "Investigator"):
        if getattr(row, "a", None) is None:
            return None
        pair = (row.a, row.b)
        if any(deal.roles[p] == row.role for p in pair):
            return None
        for p in pair:
            if deal.roles[p] in ("Spy", "Recluse"):
                return f"seat {p + 1} is really the {show(deal.roles[p])}"
        return "nobody in the pair is that character"
    if kind == "FortuneTeller" and getattr(row, "yes", False):
        demon = deal.demon_at(f"N{row.night}")
        if demon in (row.a, row.b) or deal.red_herring in (row.a, row.b):
            return None
        for p in (row.a, row.b):
            if deal.roles[p] == "Recluse":
                return f"seat {p + 1} is really the Recluse"
    return None


def describe(row):
    """A reading in the words the table heard it in."""
    bits = []
    for field in ("a", "b", "target", "nominator"):
        got = getattr(row, field, None)
        if isinstance(got, int):
            bits.append(f"{field}=seat {got + 1}")
    # `swapped` and `voted` and `nominated` were missing, so a Snake
    # Charmer row read the same whether it had swapped with the Demon or
    # touched an ordinary player — which is the one thing a reviewer
    # needs to see about it.
    for field in ("role", "count", "yes", "died", "triggered", "swapped",
                  "voted", "nominated", "same", "answer"):
        got = getattr(row, field, None)
        if got is not None and got != "":
            bits.append(f"{field}={show(got) if isinstance(got, str) else got}")
    return ", ".join(bits)


def save_file(deal, heard, claims, wakes, script=None):
    from botc import scripts as _s
    script = script or _s.TROUBLE_BREWING
    """The same game in the app's own save format.

    One game per file, and the whole document is what the page reads —
    the first version nested this inside a larger report, so the app saw
    a file it did not recognise and refused it. The `script` block is
    required too: without it the page has nothing to deal from.
    """
    players = []
    for seat in range(deal.n):
        events = deal.events(seat)
        players.append({
            "name": f"Seat {seat + 1}",
            "claim": claims.get(seat, ""),
            "events": events,
            "certainty": "", "read": 0,
            "wake": wakes.get(seat, ""),
            "suspect": False, "voted": [], "nominated": [],
        })
    return {
        "format": "clocktower-solver-game", "version": 1,
        "saved": "played by tools/play_games.py",
        "script": {"name": script.name, "author": script.author,
                   "characters": [CHARACTERS[k].id for k in script.keys],
                   "fabled": []},
        "game": {
            "n": deal.n, "players": players,
            "infos": [dict(type=type(r).__name__, night=r.night,
                           player=r.player,
                           **{f: getattr(r, f) for f in
                              ("a", "b", "target", "role", "count", "yes",
                               "died", "triggered", "nominator")
                              if getattr(r, f, None) is not None})
                      for r in heard],
            "quiet": sorted(deal.record()["quiet_nights"]),
            "done": sorted(deal.record()["days_done"]),
            "history": [], "fabled": [],
            "notes": {}, "open": ["ledger"],
        },
    }


def transcript(got):
    """The game as prose, for reading rather than parsing.

    The JSON is what a machine checks; this is what a person checks. The
    question being asked of it is about the *simulator* — did the right
    people wake, is what each was told actually true, did the Poisoner
    land where it says — and that is far easier to see in sentences than
    in nested objects.
    """
    out = []
    seats = got["seats"]
    name = lambda i: f"seat {i}"

    out.append(f"GAME  seed {got['seed']}  —  {got['players']} players, "
               f"{got['nights']} nights")
    out.append("")
    out.append("Who was who")
    for s in seats:
        was = s["really"]
        if s["believes"]:
            was += f" (thinks it is the {s['believes']})"
        said = s["claimed"] or f"softclaim: {s['softclaim']}"
        out.append(f"  {name(s['seat']):<8} {was:<28} says {said:<16} "
                   f"— {s['why']}")
    if got.get("red_herring"):
        out.append(f"  the red herring is {name(got['red_herring'])}")
    out.append("")

    for phase in got["timeline"]:
        kind = "Night" if phase["phase"].startswith("N") else "Day"
        out.append(f"{kind} {phase['phase'][1:]}")
        for seat in phase["poisoned"]:
            out.append(f"  the Poisoner chose {name(seat)}")
        for row in phase["learned"]:
            line = f"  {name(row['seat'])} learned {row['type']}: {row['said']}"
            if row.get("misled"):
                line += f"   [MISREGISTERED — {row['misled']}]"
            out.append(line)
        for seat in phase.get("executed", []):
            out.append(f"  the town executed {name(seat)}, and they died")
        for seat in phase["died"]:
            out.append(f"  {name(seat)} was found dead")
        if not (phase["poisoned"] or phase["learned"] or phase["died"]
                or phase.get("executed")):
            out.append("  nothing happened")
        solver = phase["solver"]
        line = (f"  -> the solver puts the real Demon ({name(solver['demon_seat'])}) "
                f"at {solver['demon_pct']:.0f}%, "
                f"ranked {solver['demon_rank']} of {got['players']}")
        if solver.get("repaired_seat"):
            line += f" (after positing {name(solver['repaired_seat'])} lied)"
        out.append(line)
        out.append("")
    return "\n".join(out)


def an_awkward_script(rng, name="Mixed", must_have=()):
    """A script chosen to make characters meet who never have.

    The published three are three selections out of an enormous number,
    and each exercises its own characters against its own neighbours. A
    Tea Lady has never sat beside a Recluse; a Vortox has never had to
    falsify a Chambermaid; two droison sources have rarely been in play
    at once.

    Every bug that has cost real time here lived in a *combination* — a
    Vigormortis reaching two seats and poisoning one, a Vortox
    falsifying a choice, a lineage following a star that had moved. None
    of them showed until something forced the pair to meet.

    So this does not sample uniformly. It deliberately takes several
    droison sources, more than one character that changes who holds what,
    and a Demon from a different script than the Townsfolk, because those
    are the pairings nobody has ever played.
    """
    from botc.catalogue import CHARACTERS, IMPAIRS
    from botc import scripts as _s
    every = {k: c for k, c in CHARACTERS.items() if c.modelled}
    by = lambda team: [k for k, c in every.items() if c.team == team]

    # At least two droison sources, and at least one character that moves
    # characters around. Those are the awkward halves.
    movers = [k for k in every if k in ("PitHag", "SnakeCharmer",
                                        "Philosopher", "Barber")]
    sources = [k for k in every if k in IMPAIRS]

    # Characters the caller insists on. A new character has no home
    # script to put it beside anything, so this is how it gets made to
    # meet the rest.
    keys = [k for k in must_have if k in every]
    keys += rng.sample([k for k in sources if CHARACTERS[k].team == "minion"]
                       or by("minion"), 1)
    keys += rng.sample([k for k in movers
                        if CHARACTERS[k].team == "townsfolk"] or by("townsfolk"),
                       min(2, len(movers)))
    for team, want in (("townsfolk", 13), ("outsider", 4),
                       ("minion", 4), ("demon", 4)):
        spare = [k for k in by(team) if k not in keys]
        keys += rng.sample(spare, min(want - sum(
            1 for k in keys if CHARACTERS[k].team == team), len(spare)))
    return _s.Script(name=name, keys=tuple(keys))


def build_these(seeds, players, nights, script=None):
    """Play a named handful rather than a run.

    The games worth reading are found by seed — a Pit-Hag creation, a
    Snake Charmer swap, a board the solver got confidently wrong — not by
    playing the next hundred and hoping.
    """
    OUT.mkdir(exist_ok=True)
    played = [one_game(players, nights, seed, script) for seed in seeds]
    tag = f"{players}p-picked"
    (OUT / f"games-{tag}.json").write_text(
        json.dumps({"games": played}, indent=1))
    for got in played:
        (OUT / f"open-me-{players}p-seed{got['seed']}.json").write_text(
            json.dumps(got["save"], indent=1))
    (OUT / f"transcript-{tag}.txt").write_text(
        "\n\n".join(transcript(g) for g in played))
    print(f"{len(played)} games written to games/transcript-{tag}.txt")
    return 0


def build(games, players, nights, first_seed, script=None):
    OUT.mkdir(exist_ok=True)
    # Measured by the Demon rather than by the exact world. A good player
    # lying scrambles who holds what without changing who the Demon is,
    # and catching the Demon is the whole job — a solver that named it
    # while getting three Townsfolk wrong has done what it is for.
    played, shares, ranks = [], [], []
    caught = ruled_out = repaired = 0
    for i in range(games):
        got = one_game(players, nights, first_seed + i, script)
        played.append(got)
        last = got["timeline"][-1]["solver"]
        ranks.append(last["demon_rank"])
        shares.append(last["demon_pct"])
        caught += last["demon_rank"] == 1
        ruled_out += bool(last["demon_ruled_out"])
        repaired += any(t["solver"].get("repaired_seat") is not None
                        for t in got["timeline"])

    path = OUT / f"games-{players}p-{first_seed}.json"
    path.write_text(json.dumps({"games": played}, indent=1))

    # And each game on its own, in the shape the app opens. A save has to
    # *be* the document, not sit inside a report of one.
    for got in played:
        one = OUT / f"open-me-{players}p-seed{got['seed']}.json"
        one.write_text(json.dumps(got["save"], indent=1))

    # And the same games as prose, which is what a person reads.
    told = OUT / f"transcript-{players}p-{first_seed}.txt"
    told.write_text("\n\n".join(transcript(g) for g in played))

    print(f"{games} games of {players} players, {nights} nights each")
    print(f"  the Demon was the top suspect in {caught} of {games}")
    ranks.sort()
    print(f"  where it ranked: best {ranks[0]}, "
          f"middle {ranks[len(ranks) // 2]}, worst {ranks[-1]} of {players}")
    shares.sort()
    print(f"  what it was given: lowest {shares[0]:.1f}%, "
          f"middle {shares[len(shares) // 2]:.1f}%, "
          f"highest {shares[-1]:.1f}%")
    if repaired:
        print(f"  {repaired} board(s) needed a lie posited to make sense")
    if ruled_out:
        print(f"  RULED OUT ENTIRELY in {ruled_out} — a bug, not a reading")
    print(f"  written to {path.relative_to(HERE.parent)}")
    return 1 if ruled_out else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--games", type=int, default=5)
    ap.add_argument("--players", type=int, default=9)
    ap.add_argument("--nights", type=int, default=3)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--script", default="Trouble Brewing")
    ap.add_argument("--seeds", default="",
                    help="specific seeds, comma separated")
    args = ap.parse_args()
    from botc import scripts as _s
    chosen = _s.BUILT_IN[args.script]
    if args.seeds:
        raise SystemExit(build_these(
            [int(x) for x in args.seeds.split(",")],
            args.players, args.nights, chosen))
    raise SystemExit(build(args.games, args.players, args.nights, args.seed,
                           chosen))

# Still open, and worth writing down rather than leaving in a head:
#
#   * A handful of games still lose the truth for reasons not yet traced.
#     Every one so far has been the harness asking the wrong question
#     rather than the solver being wrong, but "so far" is doing work in
#     that sentence and the remainder needs looking at one game at a time.
#   * `allow_good_lies` is slow enough on nine seats that a dozen games
#     is a long wait. The sampler exists; this should probably use it.
#   * Calibration is the real prize and is not measured yet: across many
#     games, do the things the solver calls 30% happen about 30% of the
#     time? That is what would let the judgement-call constants be tuned
#     against evidence instead of instinct.
