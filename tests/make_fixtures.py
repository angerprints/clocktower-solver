"""Boards with their answers, for checking a second implementation.

The solver is about to be written a second time, in JavaScript, so that a
phone can run it without a laptop in the room. A port that is ninety-eight
percent right is worse than no port at all: it would look like it worked
and quietly mislead somebody mid-game.

So this writes out a corpus — boards paired with the answers the Python
solver gives — and both implementations are held to it. Python stays the
reference. JavaScript has to agree.

    python tests/make_fixtures.py          # rewrite the corpus
    python run_tests.py conformance        # check Python still matches it

Every board is generated from a fixed seed, so the corpus is reproducible
and a change to it shows up as a diff rather than as noise.
"""

import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import app                                                   # noqa: E402
from botc import scripts                                     # noqa: E402
from botc.catalogue import CHARACTERS                        # noqa: E402

CORPUS = HERE / "fixtures" / "conformance.json"

# Rounded, because two languages adding the same few thousand floats in
# the same order still differ in the last places. Four figures is far
# finer than anything shown on screen and far coarser than that noise.
PLACES = 4


def ids(script):
    return [CHARACTERS[k].id for k in script.keys]


def seat(claim="", **kw):
    return {"name": "", "claim": claim, "events": [], "certainty": "",
            "read": 0, "wake": "", **kw}


_KIND = {"NobleInfo": "Noble", "BecameInfo": "Became",
         "AlsaahirGuess": "Alsaahir", "AcrobatChoice": "Acrobat",
         "BalloonistInfo": "Balloonist"}


def mixed(name, seed, nights=4):
    """A game on a script drawn for that seed, as `messung/tor.py` plays
    them: the script first, then the game, from one run of the dice.

    Seven at the table, which is what a seed divisible by five gives
    there — so a seed found by that sweep is the same game here.
    """
    sys.path.insert(0, str(HERE.parent / "tools"))
    import play_games
    rng = random.Random(seed)
    script = play_games.an_awkward_script(rng, name=f"Mixed {seed}",
                                          as_named=True)
    return played(name, script, seed, [7, 8, 9, 10, 11][seed % 5], nights,
                  rng=rng)


def played(name, script, seed, n, nights, rng=None):
    """A simulator game, as the page would post it.

    The boards the simulator found hardest to explain are the ones worth
    holding both languages to: a Snake Charmer swapping with a Fang Gu
    that had just jumped, two swaps on one night, a Barber's swap, a
    Mastermind's extra day. Written from the played game rather than by
    hand, so the board is one that really happened.
    """
    import dataclasses
    sys.path.insert(0, str(HERE))
    import claims as claim_model
    import simulate
    rng = rng or random.Random(seed)
    deal, heard = simulate.play(n, rng, nights=nights, script=script)
    claims, wakes, _notes = claim_model.claims_for(deal, rng, script=script)
    players = []
    for seat in range(n):
        # Everything that happened to the seat, not only a death: it can
        # walk away from the gallows, drop dead nominating, or come back.
        events = deal.events(seat)
        # Votes and nominations go on the seat, day by day, which is
        # where the page and both readers look. Written at the top of the
        # payload they were silently dropped, and a Flowergirl who saw
        # the Demon vote read as lying (29.09.2026).
        players.append({"claim": claims.get(seat, ""), "events": events,
                        "wake": wakes.get(seat, ""),
                        "voted": sorted(day for day, who in deal.votes.items()
                                        if seat in who),
                        "nominated": sorted(
                            day for day, who in deal.nominations.items()
                            if seat in who)})
    infos = []
    for row in heard:
        got = {"type": _KIND.get(type(row).__name__, type(row).__name__),
               "night": row.night, "player": row.player}
        for field in dataclasses.fields(row):
            if field.name in ("night", "player", "trust", "confirmed"):
                continue
            value = getattr(row, field.name)
            if isinstance(value, (tuple, frozenset, set)):
                value = list(value)
            got[field.name] = value
        infos.append(got)
    # And what did not happen: the nights without a body and the days the
    # town got through, which is what somebody keeping the board at the
    # table ticks off as the game goes (04.10.2026).
    told = deal.record()
    return board(name, script, players, infos=infos,
                 quiet_nights=sorted(told["quiet_nights"]),
                 days_done=sorted(told["days_done"]),
                 game_over=told["game_over"])


def board(name, script, claims, **payload):
    return {
        "name": name,
        "payload": {
            "n_players": len(claims),
            "players": [seat(c) if isinstance(c, str) else seat(**c)
                        for c in claims],
            "infos": [],
            "script": {"name": script.name, "characters": ids(script)},
            **payload,
        },
    }


TB = scripts.TROUBLE_BREWING
BMR = scripts.BAD_MOON_RISING
SV = scripts.SECTS_AND_VIOLETS

TB9 = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
       "FortuneTeller", "Undertaker", "Recluse", "Saint"]
TB12 = TB9[:7] + ["Monk", "Ravenkeeper", "Slayer", "Recluse", "Saint"]
BMR9 = ["Grandmother", "Sailor", "Chambermaid", "Exorcist", "Innkeeper",
        "Gambler", "Gossip", "Tinker", "Moonchild"]
SV9 = ["Clockmaker", "Dreamer", "SnakeCharmer", "Mathematician",
       "Flowergirl", "TownCrier", "Oracle", "Mutant", "Sweetheart"]


def handmade():
    """Boards chosen to hit one thing each, so a failure names itself."""
    yield board("tb-9-bare", TB, TB9)
    yield board("tb-12-bare", TB, TB12)
    yield board("tb-5-bare", TB, TB9[:5])

    yield board("tb-9-washerwoman", TB, TB9, infos=[
        {"type": "Washerwoman", "night": 1, "player": 0, "a": 1, "b": 5,
         "role": "Librarian"}])
    yield board("tb-9-librarian-nobody", TB, TB9, infos=[
        {"type": "Librarian", "night": 1, "player": 1, "a": "", "b": 0,
         "role": "Saint"}])
    yield board("tb-9-investigator", TB, TB9, infos=[
        {"type": "Investigator", "night": 1, "player": 2, "a": 3, "b": 8,
         "role": "Poisoner"}])
    yield board("tb-9-chef", TB, TB9, infos=[
        {"type": "Chef", "night": 1, "player": 3, "count": 1}])
    yield board("tb-9-empath", TB, TB9, infos=[
        {"type": "Empath", "night": 1, "player": 4, "count": 1}])
    yield board("tb-9-fortune-teller", TB, TB9, infos=[
        {"type": "FortuneTeller", "night": 1, "player": 5, "a": 0, "b": 8,
         "yes": True}])
    yield board("tb-9-slayer-landed", TB, TB12, infos=[
        {"type": "SlayerShot", "night": 2, "player": 9, "target": 11,
         "died": True}], players_override={11: ["D2"]})
    yield board("tb-9-virgin", TB, TB12, infos=[
        {"type": "VirginNomination", "night": 1, "player": 7,
         "nominator": 2, "triggered": False}])

    yield board("tb-9-night-kill", TB, TB9, players_override={2: ["N2"]})
    yield board("tb-9-execution", TB, TB9, players_override={7: ["X1"]})
    yield board("tb-9-quiet-night", TB, TB12, quiet_nights=[2])
    yield board("tb-9-undertaker", TB, TB9,
                players_override={7: ["X1"]},
                infos=[{"type": "Undertaker", "night": 2, "player": 6,
                        "target": 7, "role": "Spy"}])
    yield board("tb-9-ravenkeeper", TB, TB9,
                players_override={8: ["N2"]},
                infos=[{"type": "Ravenkeeper", "night": 2, "player": 8,
                        "target": 4, "role": "Empath"}])

    yield board("tb-9-certainties", TB,
                [{"claim": c, "certainty": k} for c, k in zip(
                    TB9, ["self", "confirmed", "hiding", "unsure", "", "",
                          "", "", ""])])
    yield board("tb-9-reads", TB,
                [{"claim": c, "read": r} for c, r in zip(
                    TB9, [3, -3, 1, 0, 0, 0, -1, 2, 0])])
    yield board("tb-9-wakes", TB,
                [{"claim": "", "wake": w} if i < 3 else {"claim": c}
                 for i, (c, w) in enumerate(zip(
                     TB9, ["every", "first", "never", "", "", "", "", "",
                           ""]))])
    yield board("tb-9-trust", TB, TB9, infos=[
        {"type": "Empath", "night": 1, "player": 4, "count": 2, "trust": 3},
        {"type": "Chef", "night": 1, "player": 3, "count": 0, "trust": -2}])

    yield board("bmr-9-bare", BMR, BMR9)
    yield board("bmr-9-grandmother", BMR, BMR9, infos=[
        {"type": "GrandmotherInfo", "night": 1, "player": 0, "target": 2,
         "role": "Chambermaid"}])
    yield board("bmr-9-grief", BMR, BMR9,
                players_override={2: ["N2"], 0: ["N2"]},
                infos=[{"type": "GrandmotherInfo", "night": 1, "player": 0,
                        "target": 2, "role": "Chambermaid"}])
    yield board("bmr-9-sailor-survives", BMR, BMR9,
                players_override={1: ["S1"]})
    yield board("bmr-9-two-bodies", BMR, BMR9,
                players_override={2: ["N2"], 4: ["N2"]})
    yield board("bmr-9-chambermaid", BMR, BMR9, infos=[
        {"type": "ChambermaidInfo", "night": 2, "player": 2, "a": 4, "b": 6,
         "count": 1}])
    yield board("bmr-9-gambler", BMR, BMR9,
                players_override={5: ["N2"]},
                infos=[{"type": "GamblerGuess", "night": 2, "player": 5,
                        "target": 2, "role": "Exorcist"}])
    yield board("bmr-9-courtier", BMR, BMR9, infos=[
        {"type": "CourtierChoice", "night": 1, "player": 7,
         "role": "Chambermaid"}])
    yield board("bmr-9-raised", BMR,
                BMR9[:3] + ["Professor"] + BMR9[4:],
                players_override={2: ["N2", "R4"]})
    yield board("bmr-9-mastermind-day", BMR, BMR9,
                players_override={2: ["X2"]}, quiet_nights=[3])

    # Sects & Violets, where nothing is reasoned about yet. Worth having
    # in the corpus from the start: it pins the shape of a script the
    # solver can deal but not yet read, and every rule added later has to
    # move these numbers deliberately rather than by accident.
    yield board("sv-9-bare", SV, SV9)
    yield board("sv-9-night-kill", SV, SV9, players_override={2: ["N2"]})
    yield board("sv-9-execution", SV, SV9, players_override={7: ["X1"]})
    yield board("sv-12-bare", SV,
                SV9 + ["Savant", "Seamstress", "Philosopher"])
    # The Fang Gu is its only setup changer, so this is the board where
    # the extra Outsider matters.
    yield board("sv-9-clockmaker", SV, SV9, infos=[
        {"type": "ClockmakerInfo", "night": 1, "player": 0, "count": 1}])
    yield board("sv-9-dreamer", SV, SV9, infos=[
        {"type": "DreamerInfo", "night": 1, "player": 1, "target": 2,
         "good_role": "Oracle", "evil_role": "Witch"}])
    yield board("sv-9-both", SV, SV9, infos=[
        {"type": "ClockmakerInfo", "night": 1, "player": 0, "count": 1},
        {"type": "DreamerInfo", "night": 1, "player": 1, "target": 2,
         "good_role": "Oracle", "evil_role": "Witch"}])
    # The Mathematician on a script that *can* be fully accounted for,
    # which is where it actually constrains anything.
    counted = scripts.from_ids(
        "Trouble Brewing and a Mathematician",
        [k.lower() for k in TB.keys] + ["mathematician"])
    maths = ["Washerwoman", "Librarian", "Investigator", "Mathematician",
             "Empath", "FortuneTeller", "Undertaker", "Recluse", "Saint"]
    for count in (0, 1, 4):
        yield board(f"maths-{count}", counted, maths, infos=[
            {"type": "MathematicianInfo", "night": 2, "player": 3,
             "count": count}])
    # And on one it cannot, where it deliberately says nothing.
    yield board("sv-9-mathematician", SV, SV9, infos=[
        {"type": "MathematicianInfo", "night": 2, "player": 3, "count": 1}])

    # The two that ask about the day. Both need votes or nominations
    # recorded, so these are the first boards in the corpus carrying any.
    voters = [{"claim": c, "voted": [2]} if i < 3 else c
              for i, c in enumerate(SV9)]
    for said in (True, False):
        yield board(f"sv-9-flowergirl-{'yes' if said else 'no'}", SV, voters,
                    days_done=[2], infos=[
                        {"type": "FlowergirlInfo", "night": 3, "player": 4,
                         "voted": said}])
    nominator = [{"claim": c, "nominated": [2]} if i == 2 else c
                 for i, c in enumerate(SV9)]
    yield board("sv-9-towncrier", SV, nominator, days_done=[2], infos=[
        {"type": "TownCrierInfo", "night": 3, "player": 5,
         "nominated": True}])

    # The second batch, on a lineup that fills the bag without pinning
    # anything being tested.
    SV9B = ["Clockmaker", "Dreamer", "Oracle", "Seamstress", "Juggler",
            "Savant", "Artist", "Mutant", "Sweetheart"]
    dead = [{"claim": c, "events": ["N2"]} if i == 2 else c
            for i, c in enumerate(SV9B)]
    yield board("sv-9-oracle", SV, dead, days_done=[2], infos=[
        {"type": "OracleInfo", "night": 3, "player": 2, "count": 1}])
    for same in (True, False):
        yield board(f"sv-9-seamstress-{'same' if same else 'apart'}", SV,
                    SV9B, infos=[{"type": "SeamstressInfo", "night": 2,
                                  "player": 3, "a": 0, "b": 1,
                                  "same": same}])
    yield board("sv-9-juggler", SV, SV9B, days_done=[2], infos=[
        {"type": "JugglerInfo", "night": 3, "player": 4, "count": 2,
         "guesses": [{"player": 0, "role": "Clockmaker"},
                     {"player": 1, "role": "Dreamer"}]}])
    yield board("sv-9-savant-artist", SV, SV9B, infos=[
        {"type": "SavantInfo", "night": 2, "player": 5,
         "first": "the demon sits beside an outsider",
         "second": "nobody has been mad"},
        {"type": "ArtistInfo", "night": 2, "player": 6,
         "question": "is seat 3 evil", "answer": True}])
    # A Savant pair in shapes the solver checks: exactly one is true, or
    # both false under a Vortox. Registration can make one either way.
    yield board("sv-9-savant-weighed", SV, SV9B, infos=[
        {"type": "SavantInfo", "night": 1, "player": 5,
         "first": "seat 3 is evil", "second": "the Witch is in play",
         "first_says": {"kind": "evil", "seat": 2},
         "second_says": {"kind": "in_play", "role": "Witch"}},
        {"type": "SavantInfo", "night": 2, "player": 5,
         "first": "", "second": "",
         "first_says": {"kind": "demon_among", "seats": [0, 1, 2]},
         "second_says": {"kind": "outsiders", "count": 2}}])
    yield board("sv-9-savant-shapes", SV, SV9B, infos=[
        {"type": "SavantInfo", "night": 1, "player": 5,
         "first_says": {"kind": "same", "a": 0, "b": 1},
         "second_says": {"kind": "is", "seat": 3, "role": "Oracle"}},
        {"type": "SavantInfo", "night": 2, "player": 5,
         "first_says": {"kind": "different", "a": 2, "b": 4},
         "second_says": {"kind": "not_in_play", "role": "Vortox"}},
        {"type": "SavantInfo", "night": 3, "player": 5,
         "first_says": {"kind": "good", "seat": 6},
         "second_says": {"kind": "bogus"}}])

    # The third batch. Sage and Klutz act on the night they die, the
    # Sweetheart starts impairing from its death, and the Barber lets the
    # Demon swap two characters.
    SV9C = ["Clockmaker", "Dreamer", "Oracle", "Sage", "Juggler", "Klutz",
            "Barber", "Mutant", "Sweetheart"]
    died = lambda who, phase: [
        {"claim": c, "events": [phase]} if i == who else c
        for i, c in enumerate(SV9C)]
    yield board("sv-9-sage", SV, died(3, "N2"), infos=[
        {"type": "SageInfo", "night": 2, "player": 3, "a": 0, "b": 8}])
    yield board("sv-9-klutz", SV, died(5, "N2"), infos=[
        {"type": "KlutzChoice", "night": 2, "player": 5, "target": 0}])
    yield board("sv-9-sweetheart", SV, died(8, "N2"))
    barber = [{"claim": c, "events": ["D2"]} if i == 6
              else {"claim": c, "events": ["N3"]} if i == 0 else c
              for i, c in enumerate(SV9C)]
    yield board("sv-9-barber", SV, barber, days_done=[3])

    # The fourth batch. The Witch and the Cerenovus are reached through
    # what the table saw rather than through the choice they made.
    SV9D = ["Philosopher", "Dreamer", "Oracle", "Sage", "Juggler", "Klutz",
            "Barber", "Mutant", "Sweetheart"]
    marked = lambda who, code: [
        {"claim": c, "events": [code]} if i == who else c
        for i, c in enumerate(SV9D)]
    yield board("sv-9-witch", SV, marked(2, "W2"))
    yield board("sv-9-cerenovus", SV, marked(2, "M2"))
    yield board("sv-9-eviltwin", SV, SV9D, infos=[
        {"type": "EvilTwinPair", "night": 1, "player": 1, "a": 1, "b": 6}])
    yield board("sv-9-philosopher", SV, SV9D, days_done=[3], infos=[
        {"type": "PhilosopherChoice", "night": 3, "player": 0,
         "role": "Juggler"}])
    yield board("sv-9-philosopher-juggles", SV, SV9D, days_done=[3], infos=[
        {"type": "PhilosopherChoice", "night": 3, "player": 0,
         "role": "Juggler"},
        {"type": "JugglerInfo", "night": 4, "player": 0, "count": 2,
         "guesses": [{"player": 1, "role": "Dreamer"},
                     {"player": 2, "role": "Oracle"}]}])

    # The Snake Charmer: the only handover where the star moves
    # sideways, and a choice that did nothing is worth recording too.
    SV9E = ["Clockmaker", "SnakeCharmer", "Oracle", "Sage", "Juggler",
            "Klutz", "Barber", "Mutant", "Sweetheart"]
    yield board("sv-9-snakecharmer-swapped", SV, SV9E, days_done=[2],
                infos=[{"type": "SnakeCharmerChoice", "night": 2,
                        "player": 1, "target": 4, "swapped": True}])
    yield board("sv-9-snakecharmer-nothing", SV, SV9E, infos=[
        {"type": "SnakeCharmerChoice", "night": 2, "player": 1,
         "target": 4, "swapped": False}])
    # And the Vortox, whose win condition is the other half of it.
    yield board("sv-9-vortox-quiet-day", SV, SV9E, days_done=[2])

    # The Pit-Hag, and the Mathematician now that it finally bites.
    SV9F = ["Clockmaker", "Dreamer", "SnakeCharmer", "Mathematician",
            "Flowergirl", "TownCrier", "Oracle", "Mutant", "Sweetheart"]
    yield board("sv-9-pithag-made", SV, SV9F, days_done=[3], infos=[
        {"type": "PitHagChoice", "night": 3, "player": 0, "target": 0,
         "role": "Philosopher"}])
    yield board("sv-9-pithag-already-in-play", SV, SV9F, days_done=[3],
                infos=[{"type": "PitHagChoice", "night": 3, "player": 0,
                        "target": 0, "role": "Dreamer"}])
    for count in (0, 2):
        yield board(f"sv-9-mathematician-{count}", SV, SV9F, infos=[
            {"type": "MathematicianInfo", "night": 2, "player": 3,
             "count": count}])

    yield board("sv-9-outsider-claims", SV,
                SV9[:5] + ["Mutant", "Sweetheart", "Barber", "Klutz"])

    # Bad Moon Rising's four declared choices, which used to be
    # unrecordable — the deduction each one carries is drawn by the death
    # and impairment rules, and they cannot know where a choice landed
    # unless somebody writes it down.
    sailed = [{"claim": c, "events": ["S3"]} if i == 1 else c
              for i, c in enumerate(BMR9)]
    yield board("bmr-9-sailor-choice", BMR, sailed, infos=[
        {"type": "SailorChoice", "night": 2, "player": 1, "target": 6}])
    yield board("bmr-9-exorcist-choice", BMR, BMR9, quiet_nights=[3],
                infos=[{"type": "ExorcistChoice", "night": 3, "player": 3,
                        "target": 6}])
    yield board("bmr-9-innkeeper-choice", BMR, BMR9, infos=[
        {"type": "InnkeeperChoice", "night": 2, "player": 4, "a": 0,
         "b": 2}])
    moon = [{"claim": c, "events": ["N2"]} if i == 8 else c
            for i, c in enumerate(BMR9)]
    yield board("bmr-9-moonchild-choice", BMR, moon, infos=[
        {"type": "MoonchildChoice", "night": 3, "player": 8, "target": 0}])

    # The rulebook read against the code, character by character
    # (02.10.2026). One board for each rule that was missing or loose, so
    # both languages are held to the reading that was settled.
    TEA = BMR9[:6] + ["TeaLady"] + BMR9[7:]
    # "Cannot die" covers the gallows: her good neighbour walks away.
    yield board("bmr-9-tea-lady-gallows", BMR, TEA,
                players_override={5: ["S1"]})
    # A Shabaloth takes her first and her neighbour second: both die.
    yield board("bmr-9-tea-lady-falls", BMR, TEA,
                players_override={6: ["N2"], 5: ["N2"]})
    # Somebody back from the dead with no Professor claimed: a Shabaloth
    # regurgitates, and may do it twice.
    yield board("bmr-9-regurgitated", BMR, BMR9,
                players_override={2: ["N2", "R3"], 4: ["N2"]})
    yield board("bmr-9-regurgitated-twice", BMR, BMR9,
                players_override={2: ["N2", "R3"], 4: ["N2"],
                                  5: ["N3", "R4"]})
    # A Courtier's drunkenness rests when it dies: the Sailor it named
    # walks away from the gallows the day after.
    COURT = BMR9[:6] + ["Courtier"] + BMR9[7:]
    yield board("bmr-9-courtier-died", BMR, COURT,
                players_override={6: ["N2"], 1: ["S2"]},
                infos=[{"type": "CourtierChoice", "night": 1, "player": 6,
                        "role": "Sailor"}])
    yield board("bmr-9-courtier-lives", BMR, COURT,
                players_override={2: ["N2"], 1: ["S2"]},
                infos=[{"type": "CourtierChoice", "night": 1, "player": 6,
                        "role": "Sailor"}])
    # A Minstrel silences the table when a Minion *dies* on the gallows,
    # not when one walks away from it.
    MINSTREL = BMR9[:6] + ["Minstrel"] + BMR9[7:]
    yield board("bmr-9-minstrel-survivor", BMR, MINSTREL,
                players_override={7: ["S1"], 1: ["S2"], 2: ["N2"]})
    # And the ordinary case beside it: the one hanged did die, so in the
    # worlds where that was a Minion the Minstrel sings.
    yield board("bmr-9-minstrel-sings", BMR, MINSTREL,
                players_override={7: ["X1"], 2: ["N2"]})
    # A Po takes one on the second night, never three.
    yield board("bmr-9-po-night-two", BMR, BMR9,
                players_override={2: ["N2"], 4: ["N2"], 5: ["N2"]})
    # Written down, a choice binds: one of the Innkeeper's pair dead, and
    # a death on the night the Exorcist named somebody.
    yield board("bmr-9-innkeeper-broken", BMR, BMR9,
                players_override={0: ["N2"]},
                infos=[{"type": "InnkeeperChoice", "night": 2, "player": 4,
                        "a": 0, "b": 2}])
    yield board("bmr-9-exorcist-named-and-killed", BMR, BMR9,
                players_override={2: ["N2"]},
                infos=[{"type": "ExorcistChoice", "night": 2, "player": 3,
                        "target": 6}])
    # A good player the Moonchild named who is still standing.
    hanged_child = [{"claim": c, "events": ["X1"]} if i == 8 else c
                    for i, c in enumerate(BMR9)]
    yield board("bmr-9-moonchild-spared", BMR, hanged_child,
                quiet_nights=[2],
                infos=[{"type": "MoonchildChoice", "night": 2, "player": 8,
                        "target": 0}])
    # And the same reading of Sects & Violets against the wiki.
    #
    # A Vigormortis takes an Outsider out of the bag: one Outsider claim
    # at nine players, where every other Demon needs two.
    yield board("sv-9-one-outsider", SV,
                SV9[:7] + ["Savant", "Sweetheart"])
    # Its own Minions keep their ability: a Witch dead since night two,
    # and somebody dropping dead as they nominate on day three.
    dead_witch = [{"claim": c, "events": ["N2"]} if i == 2
                  else {"claim": c, "events": ["W3"]} if i == 4
                  else {"claim": c, "events": ["N3"]} if i == 5 else c
                  for i, c in enumerate(SV9)]
    yield board("sv-9-dead-witch-still-curses", SV, dead_witch,
                days_done=[1, 2])
    # A Witch at a table of three has no ability left.
    three = [{"claim": c, "events": [e]} for c, e in
             zip(SV9[:5], ["X1", "N2", "W2", "", ""])]
    yield board("sv-5-witch-at-three", SV,
                [x if x["events"] != [""] else x["claim"] for x in three])
    # The good twin hanged and the game went on.
    yield board("sv-9-twin-hanged", SV, marked(1, "X1"), days_done=[1],
                infos=[{"type": "EvilTwinPair", "night": 1, "player": 1,
                        "a": 1, "b": 6}])
    # Under a Vortox even a drunk Townsfolk is told nothing true: an
    # Oracle whose ability a Philosopher took, giving the right number.
    drunk_oracle = [{"claim": "Philosopher"}] + [
        {"claim": c, "events": ["X1"]} if i == 7
        else {"claim": c, "events": ["N2"]} if i == 4 else c
        for i, c in enumerate(SV9) if i > 0]
    yield board("sv-9-drunk-under-a-vortox", SV, drunk_oracle,
                days_done=[1],
                infos=[{"type": "PhilosopherChoice", "night": 1, "player": 0,
                        "role": "Oracle"},
                       {"type": "OracleInfo", "night": 2, "player": 6,
                        "count": 0}])

    # A Gambler that guessed right, dead by morning all the same.
    yield board("bmr-9-gambler-right-and-dead", BMR, BMR9,
                players_override={5: ["N2"]},
                infos=[{"type": "GamblerGuess", "night": 2, "player": 5,
                        "target": 2, "role": "Chambermaid"}])

    # A reading the table confirmed. Evidence that its source is who
    # they claim, and it accumulates — so one board with a single tick
    # and one with three, to hold both languages to the same curve.
    executed = [{"claim": c, "events": ["X1"]} if i == 7
                else {"claim": c, "events": ["X2"]} if i == 3 else c
                for i, c in enumerate(TB9)]
    yield board("tb-9-confirmed-one", TB, executed, infos=[
        {"type": "Undertaker", "night": 2, "player": 6, "target": 7,
         "role": "Recluse", "confirmed": True}])
    yield board("tb-9-confirmed-none", TB, executed, infos=[
        {"type": "Undertaker", "night": 2, "player": 6, "target": 7,
         "role": "Recluse"}])
    yield board("tb-9-confirmed-two", TB, executed, infos=[
        {"type": "Undertaker", "night": 2, "player": 6, "target": 7,
         "role": "Recluse", "confirmed": True},
        {"type": "Undertaker", "night": 3, "player": 6, "target": 3,
         "role": "Chef", "confirmed": True}])

    # The Farmer: dies at night and hands the character on. Chosen by
    # registration, so a Spy may inherit and stays evil; chains, because
    # the new Farmer is a new instance; does nothing on an execution.
    farm = scripts.from_ids(
        "Trouble Brewing and a Farmer",
        [k.lower() for k in TB.keys] + ["farmer"])
    tb_farm = ["Farmer"] + list(TB9[1:])
    yield board("tb-9-farmer-night", farm,
                [{"claim": c, "events": ["X2"]} if i == 0 else c
                 for i, c in enumerate(tb_farm)])
    yield board("tb-9-farmer-executed", farm,
                [{"claim": c, "events": ["E2"]} if i == 0 else c
                 for i, c in enumerate(tb_farm)])
    yield board("tb-9-farmer-chain", farm,
                [{"claim": c, "events": ["X2"]} if i == 0
                 else {"claim": c, "events": ["X3"]} if i == 1 else c
                 for i, c in enumerate(tb_farm)])

    sentinel = scripts.from_ids("Trouble Brewing and a Sentinel",
                                ids(TB) + ["sentinel"])
    yield board("tb-9-sentinel", sentinel, TB9, fabled=["Sentinel"])

    small = scripts.from_ids("A narrow script", [
        "washerwoman", "librarian", "investigator", "chef", "empath",
        "recluse", "saint", "poisoner", "spy", "imp"])
    yield board("custom-7-narrow", small, TB9[:5] + ["Recluse", "Saint"])

    # The Mastermind: the Demon executed and the game going on for one
    # more day. Only with a working Mastermind alive, and only when no
    # Scarlet Woman could have taken over — or she was not working. And a
    # Zombuul executed for the first time, which is not a death at all.
    BMR9M = ["Grandmother", "Sailor", "Chambermaid", "Exorcist",
             "Innkeeper", "Gambler", "Gossip", "Courtier", "Professor"]
    hanged = [{"claim": c, "events": ["X2"]} if i == 6 else c
              for i, c in enumerate(BMR9M)]
    yield board("bmr-9-mastermind-quiet-after", BMR, hanged,
                quiet_nights=[3], days_done=[1, 2])
    yield board("bmr-9-zombuul-hanged", BMR,
                [{"claim": c, "events": ["X1"]} if i == 6 else c
                 for i, c in enumerate(BMR9M)],
                quiet_nights=[2], days_done=[1, 2])

    # Played games the solver once got wrong, kept so both languages are
    # held to them (29.09.2026): a charmer swapping with a Fang Gu that had
    # just jumped (1), a Barber's swap that keeps sides (61), a Philosopher
    # working the Snake Charmer (981 until the Philosopher chose first on
    # the first night, 13.10.2026; 1143 since, where it swaps with the
    # Demon), and at seven seats — the eleven-seat
    # originals took minutes a board — two swaps in a row (1063) and a
    # swap and a Barber on the same night (672); on Bad Moon Rising a
    # Mastermind's extra day and a Zombuul surviving its execution.
    for seed, n, nights in ((1, 8, 4), (61, 8, 4), (1143, 8, 4),
                            (1063, 7, 4), (672, 7, 4)):
        yield played(f"sv-played-{seed}", SV, seed, n, nights)
    yield played("bmr-played-mastermind", BMR, 5, 7, 4)
    yield played("bmr-played-zombuul", BMR, 34, 7, 4)

    # Games with the four things the simulator learned on 03.10.2026, one
    # of each kind: somebody walking away from the gallows for each of
    # the five reasons there are, the dead coming back by both hands, a
    # Moonchild taken at night that names somebody in the morning, a
    # Pukka whose kill came a night late because it was drunk, and a
    # nominator a Witch had cursed. The seeds are whichever came first.
    #
    # A seed names a game only until the simulator learns something new:
    # one more character acting moves every draw after it. These were
    # picked again when it learned the Goon and the three other kills,
    # later the same day. And "regurgitated" once more when the game
    # learned to stop with two left alive (04.10.2026): seed 1 brought
    # its dead back on a fourth night that is no longer played. Not the
    # first seed to do it now: in 50 two good players claim a character
    # they are not and the board has no worlds, and 94 has more of them
    # (60) than 86 or 93.
    for what, seed in (("walked-advocate", 42), ("walked-pacifist", 16),
                       ("walked-sailor", 21), ("walked-tea-lady", 19),
                       ("fool-and-back", 12), ("regurgitated", 94),
                       ("professor", 30), ("moonchild-at-night", 82),
                       ("pukka-a-night-late", 228)):
        yield played(f"bmr-played-{what}", BMR, seed, 7, 4)

    # And with what it learned next: a Demon that chose the Goon first
    # and killed nobody, with a Tea Lady sitting beside the Goon it had
    # just turned; a Sailor made drunk by the Goon it pointed at; the
    # Assassin striking, and striking to no effect; the Godfather
    # answering an executed Outsider; a Gossip coming true; a Courtier
    # and a Grandmother back from the dead, each a new one (table
    # ruling); and an Innkeeper choosing with a Pukka's token still on
    # it, kept alive, and healthy by morning.
    for what, seed in (("goon-and-a-quiet-night", 32), ("goon-sailor", 336),
                       ("assassin", 29), ("assassin-nothing", 76),
                       ("godfather", 55), ("gossip", 49),
                       ("courtier-again", 71), ("grandmother-again", 68),
                       ("under-the-token", 79)):
        yield played(f"bmr-played-{what}", BMR, seed, 7, 4)
    yield played("sv-played-witch", SV, 8, 7, 4)

    # Two on the board and the game going on: one of the dead is a
    # Zombuul that died once, and no living player is the Demon
    # (04.10.2026). Two played games, stopped on the morning the table
    # had that board; and the same thing by hand — five days, five
    # executions — once as it stands and once marked as a board from
    # after the end, where nothing of the kind follows.
    yield played("bmr-played-zombuul-two-left", BMR, 44, 7, 6)
    yield played("bmr-played-zombuul-two-left-2", BMR, 124, 7, 6)
    two_left = [{"claim": claim, "events": [code] if code else []}
                for claim, code in (
                    ("Gambler", "X2"), ("Gossip", "X3"),
                    ("Chambermaid", "X4"), ("Professor", "X5"),
                    ("Grandmother", ""), ("Courtier", ""),
                    ("Minstrel", "X1"))]
    yield board("bmr-7-two-left", BMR, two_left)
    yield board("bmr-7-two-left-game-over", BMR, two_left, game_over=True)

    # Easter Trouble, the script with the Ogre and the Marionette. The
    # Ogre turns evil from day one, so an Empath beside it can read 0 on
    # the first night and 1 on the second without anybody poisoned; the
    # Marionette believes it is good and sits beside the Demon.
    easter = scripts.from_ids("Easter Trouble", [
        "noble", "washerwoman", "librarian", "clockmaker", "grandmother",
        "slayer", "artist", "empath", "fortuneteller", "monk", "undertaker",
        "ravenkeeper", "virgin", "mayor", "ogre", "saint", "recluse",
        "drunk", "poisoner", "spy", "scarletwoman", "marionette", "baron",
        "imp"])
    EASTER9 = ["Noble", "Washerwoman", "Clockmaker", "Grandmother",
               "Empath", "Ogre", "Monk", "Undertaker", "Saint"]
    yield board("easter-9-plain", easter, EASTER9)
    yield board("easter-9-ogre-turns", easter, EASTER9, infos=[
        {"type": "Empath", "night": 1, "player": 4, "count": 0},
        {"type": "Empath", "night": 2, "player": 4, "count": 1}],
        quiet_nights=[2], days_done=[1])
    yield board("easter-9-ogre-chose", easter, EASTER9, infos=[
        {"type": "OgreChoice", "night": 1, "player": 5, "target": 6},
        {"type": "Empath", "night": 2, "player": 4, "count": 1}],
        quiet_nights=[2], days_done=[1])
    yield board("easter-9-noble", easter, EASTER9, infos=[
        {"type": "Noble", "night": 1, "player": 0, "a": 4, "b": 5,
         "c": 6}])

    # The experimental characters added singly, from 05.10.2026. They have
    # no script, so two are made for them (tests/test_experimental.py):
    # one with a Spy, a Recluse and a Zombuul, one with a Vortox. One
    # board for each row and each table decision, then games that were
    # played: a Nightwatchman's choice and the player it woke, a King
    # that learned a character and one that learned nothing beside a
    # Zombuul under its shroud, a Steward shown a Spy, and all of it
    # turned round by a Vortox.
    from test_experimental import SPY as XSPY, VORTOX as XVORTOX
    X7 = ["Steward", "Knight", "Shugenja", "Nightwatchman", "King",
          "Empath", "Chef"]
    X8 = X7 + ["Recluse"]
    V7 = ["Steward", "Knight", "Shugenja", "Nightwatchman", "King",
          "Oracle", "Dreamer"]
    yield board("x-spy-7-bare", XSPY, X7)
    yield board("x-spy-7-steward", XSPY, X7, infos=[
        {"type": "StewardInfo", "night": 1, "player": 0, "target": 3}])
    yield board("x-spy-7-knight", XSPY, X7, infos=[
        {"type": "KnightInfo", "night": 1, "player": 1, "a": 0, "b": 5}])
    yield board("x-spy-8-shugenja-clockwise", XSPY, X8, infos=[
        {"type": "ShugenjaInfo", "night": 1, "player": 2,
         "clockwise": True}])
    yield board("x-spy-8-shugenja-anticlockwise", XSPY, X8, infos=[
        {"type": "ShugenjaInfo", "night": 1, "player": 2,
         "clockwise": False}])
    yield board("x-spy-7-nightwatchman-seen", XSPY, X7, infos=[
        {"type": "NightwatchmanChoice", "night": 2, "player": 3,
         "target": 5},
        {"type": "NightwatchmanSeen", "night": 2, "player": 5, "shown": 3}],
        days_done=[1])
    yield board("x-spy-7-nightwatchman-seen-wrong", XSPY, X7, infos=[
        {"type": "NightwatchmanSeen", "night": 1, "player": 5, "shown": 1}])
    yield board("x-spy-7-nightwatchman-chose-night-one", XSPY, X7, infos=[
        {"type": "NightwatchmanChoice", "night": 1, "player": 3,
         "target": 6}], quiet_nights=[2], days_done=[1])
    yield board("x-spy-7-king", XSPY, X7,
                players_override={6: ["X1"], 0: ["N2"], 1: ["X2"],
                                  2: ["N3"]},
                infos=[{"type": "KingInfo", "night": 3, "player": 4,
                        "role": "Nightwatchman"}])
    yield board("x-spy-7-king-too-early", XSPY, X7,
                players_override={6: ["X1"], 0: ["N2"]},
                infos=[{"type": "KingInfo", "night": 2, "player": 4,
                        "role": "Nightwatchman"}])
    # As many crossed off as not, and the King says it learned nothing:
    # one of the dead is a Zombuul.
    yield board("x-spy-7-king-nothing-zombuul", XSPY, X7,
                players_override={0: ["X1"], 1: ["X2"], 6: ["X3"],
                                  2: ["X4"]},
                quiet_nights=[2, 3, 4, 5],
                infos=[{"type": "KingInfo", "night": 5, "player": 4,
                        "role": "", "learned": False}])
    yield board("x-spy-8-all-five", XSPY, X8, infos=[
        {"type": "StewardInfo", "night": 1, "player": 0, "target": 3},
        {"type": "KnightInfo", "night": 1, "player": 1, "a": 0, "b": 5},
        {"type": "ShugenjaInfo", "night": 1, "player": 2, "clockwise": True},
        {"type": "NightwatchmanSeen", "night": 1, "player": 6, "shown": 3},
        {"type": "Empath", "night": 1, "player": 5, "count": 1}])
    yield board("x-vortox-7-bare", XVORTOX, V7)
    yield board("x-vortox-7-all-five", XVORTOX, V7, infos=[
        {"type": "StewardInfo", "night": 1, "player": 0, "target": 3},
        {"type": "KnightInfo", "night": 1, "player": 1, "a": 0, "b": 5},
        {"type": "ShugenjaInfo", "night": 1, "player": 2,
         "clockwise": False},
        {"type": "NightwatchmanSeen", "night": 1, "player": 6, "shown": 3}])
    for what, seed, nights in (("nightwatchman-and-king-nothing", 63, 5),
                               ("king-learned", 158, 5),
                               ("steward-shown-a-spy", 272, 5),
                               ("king-beside-a-zombuul", 70, 5)):
        yield played(f"x-spy-played-{what}", XSPY, seed, 7, nights)
    for what, seed in (("nightwatchman-and-king", 4), ("all-turned-round", 85)):
        yield played(f"x-vortox-played-{what}", XVORTOX, seed, 7, 4)

    # Mixed scripts, from 07.10.2026: characters that have never shared a
    # script, each board a game the solver used to throw out or one the
    # simulator used to play wrongly. Found with `messung/tor.py`, which
    # draws the script from the seed — so each has a script of its own.
    # What is so, not what could have been said (table ruling,
    # 07.10.2026): a Recluse beside a Vortox makes untrue answers legal,
    # and they are still untrue. The Noble among them, which had been
    # the one character read the other way.
    from test_mixed_scripts import REGISTERING
    R8 = ["Chef", "Empath", "Recluse", "Clockmaker", "Seamstress", "Noble",
          "FortuneTeller", "Dreamer"]
    yield board("mixed-vortox-recluse-chef-one", REGISTERING, R8, infos=[
        {"type": "Chef", "night": 1, "player": 0, "count": 1}])
    yield board("mixed-vortox-recluse-empath-one", REGISTERING, R8, infos=[
        {"type": "Empath", "night": 1, "player": 1, "count": 1}])
    yield board("mixed-vortox-recluse-seamstress", REGISTERING, R8, infos=[
        {"type": "SeamstressInfo", "night": 1, "player": 4, "a": 2, "b": 0,
         "same": False}])
    yield board("mixed-vortox-recluse-noble", REGISTERING, R8, infos=[
        {"type": "Noble", "night": 1, "player": 5, "a": 0, "b": 1, "c": 2}])
    yield board("mixed-vortox-recluse-fortune-teller", REGISTERING, R8,
                infos=[{"type": "FortuneTeller", "night": 1, "player": 6,
                        "a": 2, "b": 0, "yes": True}])

    for what, seed in (
            ("gambler-right-before-a-swap", 1250),
            ("philosopher-gambler-dies", 735),
            ("exorcist-names-the-heir", 1725),
            ("drunk-becomes-the-fang-gu", 3375),
            ("fortune-teller-herring-vortox", 450),
            ("ravenkeeper-vortox", 6420),
            ("undertaker-vortox", 1345),
            ("chambermaid-beside-a-philosopher", 790),
            # An Acrobat dead of its own pick: the page refused the row,
            # and the JavaScript rule for it called a name that did not
            # exist, so no board with one had ever been solved there.
            ("acrobat-fell", 195)):
        yield mixed(f"mixed-{what}", seed)


    # The second five experimental characters (07.10.2026), on the two
    # scripts made for them in tests/test_experimental_2.py: what a
    # Banshee's announcement pins down, a Zealot that did not vote, a
    # claim to be the Goblin the town called, and games that were played.
    from test_experimental_2 import OJO as XOJO, OJO_BMR as XOJOB
    O7 = ["Banshee", "Chef", "Empath", "Zealot", "Undertaker", "Monk",
          "Soldier"]
    announced = {"type": "BansheeAnnounced", "night": 2, "player": 1}
    yield board("x-ojo-7-bare", XOJO, O7)
    yield board("x-ojo-7-banshee-announced", XOJO, O7, infos=[announced],
                players_override={0: ["N2"]})
    yield board("x-ojo-7-banshee-announced-somebody-else-died", XOJO, O7,
                infos=[announced], players_override={1: ["N2"]})
    # Two bodies and one announcement: which of them was the Banshee is
    # the world's to say. On the other script, where two can die.
    B7 = ["Banshee", "Sailor", "Chambermaid", "Zealot", "Gambler", "Gossip",
          "Banshee"]
    yield board("x-ojo-bmr-7-banshee-announced-two-died", XOJOB, B7,
                infos=[announced], players_override={0: ["N2"], 6: ["N2"]})
    said = {"type": "GoblinClaim", "night": 1, "player": 4}
    yield board("x-ojo-7-goblin-claim-only", XOJO, O7, infos=[said])
    yield board("x-ojo-7-goblin-claim-hanged-and-on", XOJO, O7, infos=[said],
                players_override={4: ["X1"]}, days_done=[1])
    yield board("x-ojo-7-goblin-claim-hanged-that-evening", XOJO, O7,
                infos=[said], players_override={4: ["X1"]})
    voting = [{"claim": c, "voted": [1] if i in (0, 1, 4) else [],
               "nominated": [1] if i == 1 else []}
              for i, c in enumerate(O7)]
    yield board("x-ojo-7-zealot-kept-its-hand-down", XOJO, voting)
    voting = [{"claim": c, "voted": [1] if i in (0, 3, 4) else [],
               "nominated": [1] if i == 1 else []}
              for i, c in enumerate(O7)]
    yield board("x-ojo-7-zealot-voted", XOJO, voting)
    for what, seed in (("banshee-and-a-goblin-wins", 19),
                       ("banshee-killed-by-the-ojo", 40),
                       ("banshee-and-a-claim", 108)):
        yield played(f"x-ojo-played-{what}", XOJO, seed, 7, 4)
    for what, seed in (("banshee-and-a-claim", 103),
                       ("zealot-and-a-claim-by-another", 294),
                       ("a-goblin-wins", 119)):
        yield played(f"x-ojo-bmr-played-{what}", XOJOB, seed, 7, 4)

    # The third five (08.10.2026), on the scripts of
    # tests/test_experimental_3.py. Only the Wraith shows on a board, and
    # only to a Chambermaid: a count of one beside two players whose
    # claims never wake says one of them is evil and woke.
    from test_experimental_3 import WRAITH as XW, WRAITH_BMR as XWB
    W7 = ["Chambermaid", "Grandmother", "Gambler", "Gossip", "Professor",
          "Magician", "PoppyGrower"]
    yield board("x-wraith-bmr-7-bare", XWB, W7)
    for night in (1, 2):
        for count in (0, 1):
            yield board(f"x-wraith-bmr-7-chambermaid-n{night}-counts-{count}",
                        XWB, W7, infos=[{
                            "type": "ChambermaidInfo", "night": night,
                            "player": 0, "a": 3, "b": 5, "count": count}])
    # A Courtier that named the Wraith, which then sleeps (table ruling,
    # 08.10.2026): a count of nought says nothing against anybody.
    C7 = ["Chambermaid", "Courtier", "Gambler", "Gossip", "Professor",
          "Magician", "Sailor"]
    for count in (0, 1):
        yield board(f"x-wraith-bmr-7-courtier-named-it-counts-{count}", XWB,
                    C7, infos=[
                        {"type": "CourtierChoice", "night": 1, "player": 1,
                         "role": "Wraith"},
                        {"type": "ChambermaidInfo", "night": 2, "player": 0,
                         "a": 3, "b": 5, "count": count}])
    yield board("x-wraith-9-snitch-politician", XW,
                ["Magician", "PoppyGrower", "Chef", "Empath", "Undertaker",
                 "Politician", "Snitch", "Monk", "Soldier"])
    for what, seed in (("chambermaid-asks-the-wraith-n1", 15),
                       ("chambermaid-asks-the-wraith-n2", 128),
                       ("poppy-grower-died", 6)):
        yield played(f"x-wraith-bmr-played-{what}", XWB, seed, 7, 4)
    yield played("x-wraith-played-magician-and-wraith", XW, 14, 7, 4)

    # The fourth four (10.10.2026), on the scripts of
    # tests/test_experimental_4.py: a Damsel guess the game went on after,
    # the Fearmonger's announcement, the Vizier's, a day voted blind and
    # one with votes, and games that were played.
    from test_experimental_4 import FOUR as XF, FOUR_BMR as XFB
    F7 = ["Chef", "Empath", "Undertaker", "Damsel", "Soldier", "Monk",
          "Mayor"]
    guessed = {"type": "DamselGuess", "night": 1, "player": 5, "target": 3}
    yield board("x-four-7-bare", XF, F7)
    yield board("x-four-7-damsel-guessed-that-evening", XF, F7,
                infos=[guessed])
    yield board("x-four-7-damsel-guessed-and-on", XF, F7, infos=[guessed],
                days_done=[1])
    yield board("x-four-7-fearmonger-chose", XF, F7, infos=[
        {"type": "FearmongerChose", "night": 1, "player": 0}])
    yield board("x-four-7-vizier-announced", XF, F7, infos=[
        {"type": "VizierAnnounced", "night": 1, "player": 4}])
    yield board("x-four-7-vizier-announced-and-walked", XF, F7, infos=[
        {"type": "VizierAnnounced", "night": 1, "player": 4}],
        players_override={4: ["S1"]})
    yield board("x-four-7-blind-vote", XF, F7, infos=[
        {"type": "BlindVote", "night": 1, "player": 0}])
    voting = [{"claim": c, "voted": [1] if i in (0, 1, 4) else [],
               "nominated": [1] if i == 1 else []}
              for i, c in enumerate(F7)]
    yield board("x-four-7-votes-on-the-board", XF, voting)
    B7 = ["Flowergirl", "Grandmother", "Gambler", "Gossip", "Professor",
          "Sailor", "Courtier"]
    for blind in (False, True):
        rows = [{"type": "FlowergirlInfo", "night": 2, "player": 0,
                 "voted": True}]
        if blind:
            rows.append({"type": "BlindVote", "night": 1, "player": 1})
        yield board("x-four-bmr-7-flowergirl" + ("-blind" if blind else ""),
                    XFB, B7, infos=rows)
    for what, seed in (("damsel-guess", 0), ("vizier-walked", 3),
                       ("blind-votes", 5), ("fearmonger-wins", 32)):
        yield played(f"x-four-played-{what}", XF, seed, 7, 4)
    for what, seed in (("vizier-forced", 1), ("flowergirl-blind", 7),
                       ("fearmonger-wins", 10)):
        yield played(f"x-four-bmr-played-{what}", XFB, seed, 7, 4)

    # The fifth five (10.10.2026), on the scripts of
    # tests/test_experimental_5.py: a Choirboy shown the Demon, a Princess
    # whose nominee hanged, a Golem's nomination either way, a Psychopath's
    # kill and its roshambo, a player told of a Widow — and games played.
    from test_experimental_5 import FIVE as XV, FIVE_BMR as XVB
    V7 = ["Chef", "Empath", "King", "Choirboy", "Washerwoman", "Mayor",
          "Undertaker"]
    yield board("x-five-7-bare", XV, V7)
    yield board("x-five-7-choirboy-shown", XV, V7, infos=[
        {"type": "ChoirboyInfo", "night": 2, "player": 3, "target": 6}],
        players_override={2: ["N2"]})
    yield board("x-five-7-choirboy-no-king-fell", XV, V7, infos=[
        {"type": "ChoirboyInfo", "night": 2, "player": 3, "target": 6}],
        players_override={0: ["N2"]})
    P7 = ["Chef", "Empath", "Princess", "Undertaker", "Washerwoman",
          "Mayor", "Monk"]
    nominated = {"type": "PrincessNominated", "night": 1, "player": 2,
                 "target": 0}
    yield board("x-five-7-princess-quiet-night", XV, P7, infos=[nominated],
                players_override={0: ["X1"]}, quiet_nights=[2])
    yield board("x-five-7-princess-and-a-body", XV, P7, infos=[nominated],
                players_override={0: ["X1"], 1: ["N2"]})
    G8 = ["Chef", "Empath", "Golem", "Undertaker", "Washerwoman", "Mayor",
          "Monk", "Recluse"]
    for target, died in ((0, True), (0, False), (7, False)):
        yield board(f"x-five-8-golem-{target}-{'died' if died else 'lived'}",
                    XV, G8, infos=[{"type": "GolemNomination", "night": 1,
                                    "player": 2, "target": target,
                                    "died": died}],
                    players_override={0: ["D1"]} if died else {})
    for died in (True, False):
        yield board(f"x-five-7-psychopath-{'killed' if died else 'missed'}",
                    XV, P7, infos=[{"type": "PsychopathKill", "night": 1,
                                    "player": 4, "target": 0,
                                    "died": died}],
                    players_override={0: ["D1"]} if died else {})
    yield board("x-five-7-roshambo-won", XV, P7, infos=[
        {"type": "PsychopathRoshambo", "night": 1, "player": 4}],
        players_override={4: ["S1"]})
    yield board("x-five-7-widow-known", XV, P7, infos=[
        {"type": "WidowKnown", "night": 1, "player": 0}])
    for what, seed in (("princess-stop", 0), ("widow", 1),
                       ("psychopath-kill-and-roshambo", 6),
                       ("choirboy", 12), ("roshambo-lost", 31)):
        yield played(f"x-five-played-{what}", XV, seed, 7, 4)
    for what, seed in (("choirboy", 8), ("princess-stop", 11),
                       ("psychopath-roshambo-lost", 19)):
        yield played(f"x-five-bmr-played-{what}", XVB, seed, 7, 4)

    # The sixth five (10.10.2026), on the scripts of
    # tests/test_experimental_6.py: a Preacher's sermon, a Huntsman finding
    # the Damsel, a Puzzlemaster's guess, a Xaan's night, a Boomdandy
    # going off — and games that were played.
    from test_experimental_6 import SIX as XS, SIX_BMR as XSB
    S7 = ["Chef", "Empath", "Preacher", "Undertaker", "Washerwoman",
          "Mayor", "Monk"]
    yield board("x-six-7-bare", XS, S7)
    yield board("x-six-7-preacher-chose", XS, S7, infos=[
        {"type": "PreacherChoice", "night": 1, "player": 2, "target": 5}])
    yield board("x-six-7-preacher-and-a-wrong-empath", XS, S7, infos=[
        {"type": "PreacherChoice", "night": 1, "player": 2, "target": 5},
        {"type": "Empath", "night": 2, "player": 1, "count": 2}])
    H7 = ["Chef", "Empath", "Huntsman", "Undertaker", "Damsel", "Mayor",
          "Monk"]
    yield board("x-six-7-huntsman-damsel", XS, H7)
    yield board("x-six-7-huntsman-chose-her", XS, H7, infos=[
        {"type": "HuntsmanChoice", "night": 2, "player": 2, "target": 4},
        {"type": "Became", "night": 2, "player": 4, "role": "Ravenkeeper",
         "was": "Damsel"}])
    P7 = ["Chef", "Empath", "Puzzlemaster", "Undertaker", "Washerwoman",
          "Mayor", "Monk", "Soldier"]
    for shown in (5, 6):
        yield board(f"x-six-8-puzzlemaster-shown-{shown}", XS, P7, infos=[
            {"type": "PuzzlemasterGuess", "night": 1, "player": 2,
             "guess": 0, "shown": shown}])
    X7 = ["Chef", "Empath", "Saint", "Undertaker", "Washerwoman", "Mayor",
          "Monk"]
    yield board("x-six-7-xaan-night-one", XS, X7, infos=[
        {"type": "Empath", "night": 1, "player": 1, "count": 2}])
    B7 = ["Chef", "Empath", "Mayor", "Undertaker", "Washerwoman", "Monk",
          "Soldier"]
    yield board("x-six-7-boomdandy", XS, B7, infos=[
        {"type": "BoomdandyExploded", "night": 1, "player": 5,
         "pointed": 0}],
        players_override={5: ["X1"], 1: ["D1"], 2: ["D1"], 0: ["D1"]},
        game_over=True)
    # A Preacher killed in the night chose before the Demon swung, so its
    # row stands; an Empath killed the same night heard nothing, and the
    # board is refused.
    yield board("x-six-7-preacher-killed-that-night", XS, S7, infos=[
        {"type": "PreacherChoice", "night": 2, "player": 2, "target": 5}],
        players_override={2: ["N2"]})
    yield board("x-six-7-empath-killed-that-night", XS, S7, infos=[
        {"type": "Empath", "night": 2, "player": 1, "count": 0}],
        players_override={1: ["N2"]})
    for what, seed in (("preached", 1), ("xaan-night", 2),
                       ("damsel-found", 8), ("boomdandy", 15),
                       ("puzzle-demon", 42)):
        yield played(f"x-six-played-{what}", XS, seed, 7, 4)
    for what, seed in (("preached", 5), ("boomdandy", 20),
                       ("damsel-found", 8)):
        yield played(f"x-six-bmr-played-{what}", XSB, seed, 7, 4)

    # The seventh five (11.10.2026), on the scripts of
    # tests/test_experimental_7.py: a mad Pixie that gained its Empath, three
    # Village Idiots, a Lycanthrope's kill and its faux paw, a Harpy's mad
    # player, a Lleech walking away and going with its host.
    from test_experimental_7 import SEVEN as XV, SEVEN_BMR as XVB7
    P7 = ["Chef", "Empath", "Monk", "Soldier", "Undertaker", "Empath",
          "Mayor"]
    yield board("x-seven-7-bare", XV, P7)
    yield board("x-seven-7-pixie-gained", XV, P7, infos=[
        {"type": "PixieLearned", "night": 1, "player": 5, "role": "Empath"},
        {"type": "Empath", "night": 3, "player": 5, "count": 1}],
        players_override={1: ["N2"]})
    yield board("x-seven-7-pixie-refused", XV, P7, infos=[
        {"type": "PixieLearned", "night": 1, "player": 5, "role": "Empath"},
        {"type": "Empath", "night": 3, "player": 5, "count": 2}],
        players_override={1: ["N2"]})
    V7 = ["VillageIdiot", "VillageIdiot", "VillageIdiot", "Empath", "Monk",
          "Chef", "Soldier"]
    yield board("x-seven-7-three-idiots", XV, V7, infos=[
        {"type": "VillageIdiotInfo", "night": 1, "player": 0, "target": 4,
         "evil": False},
        {"type": "VillageIdiotInfo", "night": 1, "player": 1, "target": 4,
         "evil": True},
        {"type": "VillageIdiotInfo", "night": 1, "player": 2, "target": 4,
         "evil": False}])
    L7 = ["Chef", "Empath", "Monk", "Soldier", "Lycanthrope", "Washerwoman",
          "Mayor"]
    yield board("x-seven-7-lycanthrope-kill", XV, L7, infos=[
        {"type": "LycanthropeChose", "night": 2, "player": 4, "target": 2}],
        players_override={2: ["N2"]})
    yield board("x-seven-7-lycanthrope-missed", XV, L7, infos=[
        {"type": "LycanthropeChose", "night": 2, "player": 4, "target": 1}],
        players_override={3: ["N2"]})
    yield board("x-seven-7-faux-paw", XV, L7, infos=[
        {"type": "Empath", "night": 1, "player": 1, "count": 1},
        {"type": "Chef", "night": 1, "player": 0, "count": 0}])
    yield board("x-seven-7-harpy", XV, L7, infos=[
        {"type": "HarpyMadness", "night": 1, "player": 2, "second": 3}])
    E8 = ["Chef", "Empath", "Monk", "Soldier", "Undertaker", "Washerwoman",
          "Mayor", "Slayer"]
    yield board("x-seven-8-lleech-walks-away", XV, E8,
                players_override={2: ["S1"], 3: ["N2"]})
    yield board("x-seven-8-host-hanged", XV, E8,
                players_override={2: ["X1"], 5: ["D1"], 3: ["N2"]})
    yield board("x-seven-8-slayer-hits-the-host", XV, E8, infos=[
        {"type": "SlayerShot", "night": 1, "player": 7, "target": 0,
         "died": True}],
        players_override={0: ["D1"], 4: ["D1"], 1: ["N2"]})
    for what, seed in (("harpy-kill", 0), ("lycanthrope-kill", 2),
                       ("lleech-walked", 4), ("lleech-scarlet-woman", 5),
                       ("pixie-gained", 10)):
        yield played(f"x-seven-played-{what}", XV, seed, 7, 4)
    for what, seed in (("idiot-drunk", 0), ("lycanthrope-kill", 3),
                       ("lleech-walked", 15), ("lleech-end", 19)):
        yield played(f"x-seven-bmr-played-{what}", XVB7, seed, 7, 4)

    yield from the_eighth_five()
    yield from the_ninth_three()
    yield from the_philosopher_takes()
    yield from the_philosopher_takes_group_1()
    yield from the_philosopher_takes_group_2()
    yield from the_philosopher_takes_group_3()
    yield from the_philosopher_takes_group_4()
    yield from the_farmers_heir()
    yield from the_philosopher_takes_group_5()
    yield from the_slayer_and_the_virgin()
    yield from the_philosopher_takes_group_6()
    yield from stelle_60()
    yield from the_lord_of_typhon()
    yield from the_kazali()
    yield from the_al_hadikhia()
    yield from the_lil_monsta()
    yield from the_summoner()
    yield from stellen_62_63()
    yield from the_hatter()
    yield from the_engineer()
    yield from the_boffin()
    yield from the_boffin_2()
    yield from the_plague_doctor()


def the_eighth_five():
    """The eighth five (11.10.2026), on the scripts of
    tests/test_experimental_8.py: the Bounty Hunter's evil Townsfolk, a
    Cult Leader between its neighbours, a player a Mezepheles turned, the
    Leviathan's announcement and its jinxes, a Yaggababble's bodies."""
    from test_experimental_8 import EIGHT as X8, EIGHT_BMR as X8B
    B7 = ["Chef", "Empath", "Monk", "Soldier", "Undertaker", "BountyHunter",
          "CultLeader"]
    yield board("x-eight-7-bare", X8, B7)
    yield board("x-eight-7-bounty-hunter-shown", X8, B7, infos=[
        {"type": "BountyHunterInfo", "night": 1, "player": 5, "target": 2}])
    yield board("x-eight-7-bounty-hunter-shown-another", X8, B7, infos=[
        {"type": "BountyHunterInfo", "night": 1, "player": 5, "target": 2},
        {"type": "BountyHunterInfo", "night": 2, "player": 5, "target": 3}],
        players_override={2: ["X1"]}, quiet_nights=[2])
    yield board("x-eight-7-bounty-hunter-too-early", X8, B7, infos=[
        {"type": "BountyHunterInfo", "night": 1, "player": 5, "target": 2},
        {"type": "BountyHunterInfo", "night": 2, "player": 5, "target": 3}],
        quiet_nights=[2], days_done=[1])
    yield board("x-eight-7-bounty-hunter-and-the-chef", X8, B7, infos=[
        {"type": "BountyHunterInfo", "night": 1, "player": 5, "target": 1},
        {"type": "Chef", "night": 1, "player": 0, "count": 1}])
    yield board("x-eight-7-cult-leader-and-the-empath", X8, B7, infos=[
        {"type": "Empath", "night": 2, "player": 1, "count": 1}],
        players_override={0: ["N2"]}, days_done=[1])
    yield board("x-eight-7-cult-called", X8, B7, infos=[
        {"type": "CultCalled", "night": 2, "player": 6,
         "joined": [0, 1, 2, 3]}],
        quiet_nights=[2], days_done=[1, 2])
    yield board("x-eight-7-cult-called-by-all", X8, B7, infos=[
        {"type": "CultCalled", "night": 2, "player": 6,
         "joined": [0, 1, 2, 3, 4, 5]}],
        quiet_nights=[2], days_done=[1, 2])
    # Open item 55 (12.10.2026): a Cult Leader that is the Lycanthrope's
    # faux paw, shown as evil to a Village Idiot.
    faux = scripts.from_ids("Faux paw", [
        "villageidiot", "cultleader", "lycanthrope", "chef", "empath",
        "monk", "soldier", "saint", "recluse", "scarletwoman", "spy", "imp"])
    for target in (1, 3):
        yield board(f"x-eight-7-cult-leader-faux-paw-{target}", faux,
                    ["VillageIdiot", "CultLeader", "Lycanthrope", "Chef",
                     "Empath", "Saint", "Monk"],
                    infos=[{"type": "VillageIdiotInfo", "night": 1,
                            "player": 0, "target": target, "evil": True}])
    # Open item 57 (12.10.2026): a Noble that saw the faux paw on the
    # Xaan's night, when the Lycanthrope was poisoned too.
    xaan = scripts.from_ids("Faux paw and Xaan", [
        "noble", "lycanthrope", "chef", "empath", "monk", "soldier", "saint",
        "recluse", "xaan", "spy", "imp"])
    for seen in ((2, 3, 4), (3, 4, 5)):
        yield board(f"x-seven-7-faux-paw-xaan-night-{seen[0]}", xaan,
                    ["Noble", "Lycanthrope", "Chef", "Saint", "Empath",
                     "Monk", "Soldier"],
                    infos=[{"type": "Noble", "night": 1, "player": 0,
                            "a": seen[0], "b": seen[1], "c": seen[2]},
                           {"type": "LycanthropeChose", "night": 2,
                            "player": 1, "target": 2}],
                    players_override={4: ["N2"]}, days_done=[1])
    M7 = ["Chef", "Empath", "Monk", "Soldier", "King", "Slayer",
          "Undertaker"]
    yield board("x-eight-7-mezepheles-turned-a-neighbour", X8, M7, infos=[
        {"type": "Empath", "night": 1, "player": 1, "count": 0},
        {"type": "Empath", "night": 2, "player": 1, "count": 0},
        {"type": "Empath", "night": 3, "player": 1, "count": 1}],
        quiet_nights=[2, 3], days_done=[1, 2])
    yield board("x-eight-7-leviathan-announced", X8, M7, infos=[
        {"type": "LeviathanAnnounced", "night": 1, "player": 0}],
        quiet_nights=[2, 3], days_done=[1, 2])
    yield board("x-eight-7-leviathan-two-executed", X8, M7, infos=[
        {"type": "LeviathanAnnounced", "night": 1, "player": 0}],
        players_override={0: ["X1"], 1: ["X2"]}, quiet_nights=[2, 3])
    yield board("x-eight-7-leviathan-not-announced", X8, M7,
                quiet_nights=[2, 3], days_done=[1, 2])
    yield board("x-eight-7-leviathan-hangs-the-soldier", X8, M7, infos=[
        {"type": "LeviathanAnnounced", "night": 1, "player": 0},
        {"type": "ExecutionNomination", "night": 1, "player": 5}],
        players_override={3: ["X1"]}, quiet_nights=[2])
    yield board("x-eight-7-yaggababble-two-bodies", X8, M7,
                players_override={0: ["N2"], 2: ["N2"]}, days_done=[1])
    yield board("x-eight-7-yaggababble-three-bodies", X8, M7,
                players_override={0: ["N2"], 2: ["N2"], 4: ["N2"]},
                days_done=[1])
    yield board("x-eight-7-yaggababble-by-day", X8, M7,
                players_override={0: ["W1"]})
    G7 = ["Grandmother", "Exorcist", "Chambermaid", "Innkeeper", "Gossip",
          "Oracle", "TeaLady"]
    yield board("x-eight-bmr-7-leviathan-grandchild", X8B, G7, infos=[
        {"type": "GrandmotherInfo", "night": 1, "player": 0, "target": 4,
         "role": "Gossip"},
        {"type": "LeviathanAnnounced", "night": 1, "player": 0}],
        players_override={4: ["X1"]}, quiet_nights=[2])
    yield board("x-eight-bmr-7-yaggababble-and-the-exorcist", X8B, G7,
                infos=[{"type": "ExorcistChoice", "night": 2, "player": 1,
                        "target": 5}],
                players_override={0: ["N2"]}, days_done=[1])
    yield board("x-eight-bmr-7-chambermaid-and-the-cult-leader", X8B,
                ["Grandmother", "Exorcist", "Chambermaid", "Innkeeper",
                 "Gossip", "CultLeader", "TeaLady"],
                infos=[{"type": "ChambermaidInfo", "night": 2, "player": 2,
                        "a": 5, "b": 6, "count": 1}],
                quiet_nights=[2], days_done=[1])
    # Played, each chosen for one thing that happens in it (seeds found
    # at seven players, as `messung/find5.py` finds them).
    for what, seed in (("bounty-hunter-itself-evil", 19),
                       ("bounty-hunter-shown-twice", 26),
                       ("cult-called", 16), ("cult-turned", 6),
                       ("leviathan-banshee", 21), ("leviathan-ends", 205),
                       ("leviathan-farmer", 20),
                       ("leviathan-unannounced", 57),
                       ("mezepheles-turned", 38),
                       ("yaggababble-by-day", 110),
                       ("yaggababble-two", 30)):
        yield played(f"x-eight-played-{what}", X8, seed, 7, 4)
    for what, seed in (("evil-townsfolk", 12),
                       ("bounty-hunter-itself-evil", 49),
                       ("cult-called", 9), ("leviathan-ends", 72),
                       ("leviathan-nominator", 3),
                       ("leviathan-unannounced", 82),
                       ("mezepheles-turned", 5),
                       ("yaggababble-by-day", 43)):
        yield played(f"x-eight-bmr-played-{what}", X8B, seed, 7, 4)


def the_ninth_three():
    """The ninth three (12.10.2026), on the scripts of
    tests/test_experimental_9.py: the High Priestess, the General and the
    Fisherman, kept and not weighed — beside a Vortox, a Mathematiker and
    a Kammerzofe that counts the two who wake every night."""
    from test_experimental_9 import NINE as X9, NINE_BMR as X9B
    N8 = ["Chef", "HighPriestess", "General", "Fisherman", "Empath",
          "Mathematician", "Saint", "Undertaker"]
    rows = [{"type": "HighPriestessInfo", "night": 1, "player": 1,
             "target": 4},
            {"type": "HighPriestessInfo", "night": 2, "player": 1,
             "target": 0},
            {"type": "GeneralInfo", "night": 1, "player": 2, "says": "evil"},
            {"type": "GeneralInfo", "night": 2, "player": 2,
             "says": "neither"},
            {"type": "FishermanAdvice", "night": 1, "player": 3,
             "advice": "Execute today."}]
    yield board("x-nine-8-bare", X9, N8)
    yield board("x-nine-8-kept-not-weighed", X9, N8, infos=rows,
                days_done=[1], quiet_nights=[2])
    yield board("x-nine-8-kept-beside-the-empath", X9, N8, infos=rows + [
        {"type": "Empath", "night": 1, "player": 4, "count": 1},
        {"type": "MathematicianInfo", "night": 1, "player": 5,
         "count": 1}])
    yield board("x-nine-8-fisherman-asked-twice", X9, N8, infos=[
        {"type": "FishermanAdvice", "night": 1, "player": 3, "advice": "a"},
        {"type": "FishermanAdvice", "night": 2, "player": 3, "advice": "b"}],
        days_done=[1, 2], quiet_nights=[2])
    yield board("x-nine-8-fisherman-killed-the-night-after", X9, N8, infos=[
        {"type": "FishermanAdvice", "night": 2, "player": 3, "advice": "a"}],
        players_override={3: ["N3"]}, days_done=[1, 2], quiet_nights=[2])
    B7 = ["Chambermaid", "HighPriestess", "General", "Fisherman", "Gossip",
          "Exorcist", "Tinker"]
    for count in (2, 1, 0):
        yield board(f"x-nine-bmr-7-chambermaid-counts-{count}", X9B, B7,
                    infos=[{"type": "ChambermaidInfo", "night": 1,
                            "player": 0, "a": 1, "b": 2, "count": count}])
    yield board("x-nine-bmr-7-chambermaid-and-the-fisherman", X9B, B7,
                infos=[{"type": "ChambermaidInfo", "night": 1, "player": 0,
                        "a": 3, "b": 4, "count": 0}])
    # Played (seeds at seven players): all three told something, beside
    # a Vortox, a Mathematiker, a Kammerzofe and a Philosoph.
    for what, seed in (("all-three", 2), ("all-three-vortox", 12),
                       ("mathematician-vortox", 16), ("drunk", 8)):
        yield played(f"x-nine-played-{what}", X9, seed, 7, 4)
    for what, seed in (("all-three", 12), ("chambermaid", 10),
                       ("philosopher", 16), ("philosopher-all-three", 36)):
        yield played(f"x-nine-bmr-played-{what}", X9B, seed, 7, 4)


def the_philosopher_takes():
    """Open item 56, step 1 (13.10.2026): a Philosopher that took the
    Sweetheart, the Barber or the Klutz has it on dying, and the real one
    it drunk does not."""
    P7 = ["Philosopher", "Oracle", "Clockmaker", "Dreamer", "Savant",
          "Artist", "Juggler"]
    def took(role):
        return {"type": "PhilosopherChoice", "night": 1, "player": 0,
                "role": role}
    for role in ("Sweetheart", "Dreamer"):
        yield board(f"sv-7-philosopher-{role.lower()}-dies", SV, P7,
                    infos=[took(role), {"type": "OracleInfo", "night": 3,
                                        "player": 1, "count": 1}],
                    players_override={0: ["N2"]}, days_done=[1, 2])
    R7 = ["Philosopher", "Oracle", "Sweetheart", "Dreamer", "Savant",
          "Artist", "Juggler"]
    yield board("sv-7-sweetheart-drunk-by-the-philosopher", SV, R7,
                infos=[took("Sweetheart"), {"type": "OracleInfo",
                                            "night": 3, "player": 1,
                                            "count": 1}],
                players_override={2: ["N2"]}, days_done=[1, 2])
    for role in ("Barber", "Dreamer"):
        yield board(f"sv-7-philosopher-{role.lower()}-executed", SV, P7,
                    infos=[took(role)], players_override={0: ["X1"]},
                    days_done=[1, 2])
    B7 = ["Philosopher", "Oracle", "Barber", "Dreamer", "Savant", "Artist",
          "Juggler"]
    yield board("sv-7-barber-drunk-by-the-philosopher", SV, B7,
                infos=[took("Barber")], players_override={2: ["X1"]},
                days_done=[1, 2])
    yield board("sv-7-philosopher-klutz-points", SV, P7,
                infos=[took("Klutz"), {"type": "KlutzChoice", "night": 2,
                                       "player": 0, "target": 3}],
                players_override={0: ["N2"]}, days_done=[1, 2])
    for what, seed in (("sweetheart", 21), ("barber", 66), ("klutz", 237)):
        yield played(f"sv-played-philosopher-{what}", SV, seed, 7, 4)


def the_philosopher_takes_group_1():
    """Open item 56, step 2, group 1 (13.10.2026): a Philosopher keeps
    somebody alive with what it took, and the real one it took from is
    drunk. On the script of tests/test_philosopher_takes_2.py."""
    sys.path.insert(0, str(HERE))
    from test_philosopher_takes_2 import GROUP_1, SHIELDS
    R7 = ["Chef", "Empath", "Investigator", "Philosopher", "Washerwoman",
          "ScarletWoman", "Imp"]

    def took(role):
        return {"type": "PhilosopherChoice", "night": 1, "player": 3,
                "role": role}
    for role in ("Monk", "Soldier", "Innkeeper", "Sailor", "TeaLady",
                 "Chef"):
        yield board(f"x-shields-7-philosopher-{role.lower()}-quiet",
                    SHIELDS, R7, infos=[took(role)], quiet_nights=[2],
                    days_done=[1, 2])
    for target in (6, 2):
        yield board(f"x-shields-7-philosopher-exorcist-names-{target}",
                    SHIELDS, R7,
                    infos=[took("Exorcist"),
                           {"type": "ExorcistChoice", "night": 2,
                            "player": 3, "target": target}],
                    quiet_nights=[2], days_done=[1, 2])
    for role, seat in (("Fool", 3), ("Pacifist", 2)):
        yield board(f"x-shields-7-philosopher-{role.lower()}-gallows",
                    SHIELDS, R7, infos=[took(role)],
                    players_override={seat: ["S1"]}, days_done=[1, 2])
    yield board("x-shields-7-philosopher-mayor-corpse", SHIELDS, R7,
                infos=[took("Mayor")], players_override={1: ["X1"]},
                quiet_nights=[2], days_done=[1, 2])
    yield board("x-shields-7-philosopher-princess", SHIELDS, R7,
                infos=[took("Princess"),
                       {"type": "PrincessNominated", "night": 1,
                        "player": 3, "target": 0}],
                players_override={0: ["X1"], 1: ["N2"]}, days_done=[1])
    S7 = list(R7)
    S7[2] = "Soldier"
    yield board("x-shields-7-soldier-drunk-by-the-philosopher", SHIELDS,
                S7, infos=[took("Soldier")], players_override={2: ["N2"]},
                days_done=[1, 2])
    T7 = list(R7)
    T7[2] = "Sailor"
    for name, real, mine in (("philosopher", 4, 1), ("real", 1, 4)):
        yield board(f"x-shields-7-two-sailors-{name}-hits", SHIELDS, T7,
                    infos=[took("Sailor"),
                           {"type": "SailorChoice", "night": 1, "player": 2,
                            "target": real},
                           {"type": "SailorChoice", "night": 1, "player": 3,
                            "target": mine},
                           {"type": "Empath", "night": 1, "player": 1,
                            "count": 2}],
                    days_done=[1])
    sys.path.insert(0, str(HERE.parent / "tools"))
    import play_games
    for seed in PLAYED_GROUP_1:
        rng = random.Random(seed)
        script = play_games.an_awkward_script(
            rng, must_have=("Philosopher",) + GROUP_1)
        yield played(f"x-shields-played-{seed}", script, seed,
                     [7, 8, 9, 10, 11][seed % 5], 4, rng=rng)


def the_philosopher_takes_group_2():
    """Open item 56, step 2, group 2 (13.10.2026): a Philosopher kills
    with what it took. On the script of tests/test_philosopher_takes_2.py:
    the boards its tests solve in both languages, and four games."""
    sys.path.insert(0, str(HERE))
    from test_philosopher_takes_2 import GROUP_2, KILLERS, P7
    R7 = ["Chef", "Empath", "Investigator", "Philosopher", "Washerwoman",
          "ScarletWoman", "Imp"]

    def took(role):
        return {"type": "PhilosopherChoice", "night": 1, "player": 3,
                "role": role}
    for role in GROUP_2 + ("Chef",):
        low = role.lower()
        yield board(f"x-killers-7-philosopher-{low}-two-bodies", KILLERS, R7,
                    infos=[took(role)],
                    players_override={3: ["N2"], 0: ["N2"]},
                    days_done=[1, 2])
    for role in ("Moonchild", "Chef"):
        yield board(f"x-killers-7-philosopher-{role.lower()}-picks",
                    KILLERS, R7,
                    infos=[took(role), {"type": "MoonchildChoice", "night": 2,
                                        "player": 3, "target": 0}],
                    players_override={3: ["X1"], 0: ["N2"], 1: ["N2"]},
                    days_done=[1, 2])
    for role in ("Lycanthrope", "Chef"):
        yield board(f"x-killers-7-philosopher-{role.lower()}-faux-paw",
                    KILLERS, R7,
                    infos=[took(role), {"type": "Empath", "night": 1,
                                        "player": 1, "count": 1}],
                    days_done=[1])
    for role in ("Acrobat", "Chef"):
        yield board(f"x-killers-7-philosopher-{role.lower()}-falls",
                    KILLERS, P7,
                    infos=[took(role), {"type": "Acrobat", "night": 2,
                                        "player": 3, "target": 1}],
                    players_override={3: ["N2"], 0: ["N2"]},
                    days_done=[1, 2])
    sys.path.insert(0, str(HERE.parent / "tools"))
    import play_games
    for seed in PLAYED_GROUP_2:
        rng = random.Random(seed)
        script = play_games.an_awkward_script(
            rng, must_have=("Philosopher",) + GROUP_2)
        yield played(f"x-killers-played-{seed}", script, seed, 7, 4,
                     rng=rng)


def the_philosopher_takes_group_3():
    """Open item 56, step 2, group 3 (13.10.2026): a Philosopher disturbs
    with what it took. The boards of tests/test_philosopher_takes_2.py,
    and four games."""
    sys.path.insert(0, str(HERE))
    from test_philosopher_takes_2 import GROUP_3, DISTURBERS, P7, G7, R
    def took(role, seat=3):
        return {"type": "PhilosopherChoice", "night": 1, "player": seat,
                "role": role}

    def empath(night, count):
        return {"type": "Empath", "night": night, "player": 1,
                "count": count}
    for role in GROUP_3 + ("Chef",):
        low = role.lower()
        yield board(f"x-disturbers-7-philosopher-{low}-minion-hanged",
                    DISTURBERS, R, infos=[took(role), empath(2, 2)],
                    players_override={5: ["X1"]}, days_done=[1, 2])
        yield board(f"x-disturbers-7-philosopher-{low}-preaches",
                    DISTURBERS, P7,
                    infos=[took(role), {"type": "PreacherChoice", "night": 1,
                                        "player": 3, "target": 5},
                           empath(2, 2)], days_done=[1, 2])
        yield board(f"x-disturbers-7-philosopher-{low}-beside-the-empath",
                    DISTURBERS, G7, infos=[took(role, 2), empath(2, 1)],
                    days_done=[1, 2])
        yield board(f"x-disturbers-7-philosopher-{low}-first-night",
                    DISTURBERS, R, infos=[took(role), empath(1, 2)],
                    days_done=[1])
    sys.path.insert(0, str(HERE.parent / "tools"))
    import play_games
    for seed in PLAYED_GROUP_3:
        rng = random.Random(seed)
        script = play_games.an_awkward_script(
            rng, must_have=("Philosopher",) + GROUP_3)
        yield played(f"x-disturbers-played-{seed}", script, seed, 7, 4,
                     rng=rng)


def the_philosopher_takes_group_4():
    """Open item 56, step 2, group 4 (13.10.2026): a Philosopher changes
    a character or a side with what it took. The boards of
    tests/test_philosopher_takes_2.py, five games, and the Bad Moon Rising
    game of the ninth three where a Philosopher-Professor raised an
    Exorcist after its turn."""
    sys.path.insert(0, str(HERE))
    from test_philosopher_takes_2 import GROUP_4, CHANGERS, CL, R
    from test_experimental_9 import NINE_BMR

    def took(role, seat=3):
        return {"type": "PhilosopherChoice", "night": 1, "player": seat,
                "role": role}
    prof = list(R)
    prof[2] = "Professor"
    damsel = list(R) + ["Damsel"]        # eight players: one Outsider
    for role in GROUP_4 + ("Chef",):
        low = role.lower()
        yield board(f"x-changers-7-philosopher-{low}-raised",
                    CHANGERS, R, infos=[took(role)],
                    players_override={0: ["N2", "R3"]}, days_done=[1, 2, 3])
        yield board(f"x-changers-7-philosopher-{low}-raised-itself",
                    CHANGERS, prof, infos=[took(role)],
                    players_override={3: ["N2", "R3"]}, days_done=[1, 2, 3])
        yield board(f"x-changers-7-philosopher-{low}-killed",
                    CHANGERS, R, infos=[took(role)],
                    players_override={3: ["N2"]}, days_done=[1, 2])
        yield board(f"x-changers-7-philosopher-{low}-hunts",
                    CHANGERS, damsel,
                    infos=[took(role), {"type": "HuntsmanChoice", "night": 2,
                                        "player": 3, "target": 7}],
                    days_done=[1, 2])
        yield board(f"x-changers-7-philosopher-{low}-learns",
                    CHANGERS, R,
                    infos=[took(role), {"type": "PixieLearned", "night": 1,
                                        "player": 3, "role": "Monk"}],
                    days_done=[1])
        yield board(f"x-changers-7-philosopher-{low}-picks-a-side",
                    CHANGERS, CL,
                    infos=[took(role, 2), {"type": "OgreChoice", "night": 1,
                                           "player": 2, "target": 3},
                           {"type": "Empath", "night": 2, "player": 1,
                            "count": 1}], days_done=[1, 2])
    sys.path.insert(0, str(HERE.parent / "tools"))
    import play_games
    for seed in PLAYED_GROUP_4:
        rng = random.Random(seed)
        script = play_games.an_awkward_script(
            rng, must_have=("Philosopher",) + GROUP_4)
        yield played(f"x-changers-played-{seed}", script, seed, 7, 4,
                     rng=rng)
    yield played("x-nine-bmr-played-philosopher-professor", NINE_BMR, 881,
                 8, 4)


def the_philosopher_takes_group_5():
    """Open item 56, step 2, group 5 (14.10.2026): a Philosopher acts by
    day with what it took. The boards of tests/test_philosopher_takes_2.py
    and games where it used the Golem or the Alsaahir."""
    sys.path.insert(0, str(HERE))
    from test_philosopher_takes_2 import GROUP_5, _payloads_5
    kinds = ("shot", "shot-at-a-po", "virgin", "golem")
    for i, payload in enumerate(_payloads_5()):
        role = (GROUP_5 + ("Chef",))[i // len(kinds)].lower()
        yield {"name": f"x-by-day-7-philosopher-{role}-{kinds[i % len(kinds)]}",
               "payload": payload}
    sys.path.insert(0, str(HERE.parent / "tools"))
    import play_games
    for seed in PLAYED_GROUP_5:
        rng = random.Random(seed)
        script = play_games.an_awkward_script(
            rng, must_have=("Philosopher",) + GROUP_5)
        yield played(f"x-by-day-played-{seed}", script, seed, 7, 4, rng=rng)


# Games where a Philosopher took one of group 5 and used it: the Golem
# (42, 120), the Alsaahir (106, 452).
PLAYED_GROUP_5 = (42, 120, 106, 452)


def the_philosopher_takes_group_6():
    """Open item 56, step 2, group 6 and I (14.10.2026): a Philosopher at
    the end of the game and registering, and one that took the Drunk or
    the Lunatic. The boards of tests/test_philosopher_takes_2.py and
    played games."""
    sys.path.insert(0, str(HERE))
    from test_philosopher_takes_2 import GROUP_6, TOKENS, _payloads_6
    kinds = ("hanged", "guessed", "grieves", "king-killed", "beside-empath",
             "librarian")
    for i, payload in enumerate(_payloads_6()):
        role = (GROUP_6 + TOKENS + ("Chef",))[i // len(kinds)].lower()
        yield {"name": f"x-at-the-end-7-philosopher-{role}-"
                       f"{kinds[i % len(kinds)]}", "payload": payload}
    sys.path.insert(0, str(HERE.parent / "tools"))
    import play_games
    for group, seeds, name in ((GROUP_6, PLAYED_GROUP_6, "at-the-end"),
                               (TOKENS, PLAYED_TOKENS, "tokens")):
        for seed in seeds:
            rng = random.Random(seed)
            script = play_games.an_awkward_script(
                rng, must_have=("Philosopher",) + group)
            yield played(f"x-{name}-played-{seed}", script, seed, 7, 4,
                         rng=rng)


# Games where a Philosopher took one and it showed: the Saint (0), the
# King (39), the Recluse (90), the Grandmother (95), the Choirboy (193),
# the Damsel (683); the Drunk (39, 86) and the Lunatic (9).
PLAYED_GROUP_6 = (0, 39, 90, 95, 193, 683)
PLAYED_TOKENS = (39, 86, 9)


def the_slayer_and_the_virgin():
    """Stelle 59 (14.10.2026): the simulator plays the Slayer and the
    Virgin. The boards of tests/test_slayer_virgin.py, under a Vortox, and
    played Trouble Brewing games: a shot that missed, one that landed, a
    Virgin that took its nominator, and mixed ones with a Philosopher."""
    sys.path.insert(0, str(HERE))
    from test_slayer_virgin import _payloads
    names = ("missed", "missed-the-vortox", "quiet", "triggered",
             "quiet-on-a-townsfolk")
    for name, payload in zip(names, _payloads()):
        yield {"name": f"x-in-the-open-{name}", "payload": payload}
    for seed in PLAYED_TB_OPEN:
        yield played(f"tb-played-in-the-open-{seed}", TB, seed, 7, 4)
    sys.path.insert(0, str(HERE.parent / "tools"))
    import play_games
    for seed in PLAYED_MIXED_OPEN:
        rng = random.Random(seed)
        script = play_games.an_awkward_script(
            rng, must_have=("Philosopher", "Slayer", "Virgin"))
        yield played(f"x-in-the-open-played-{seed}", script, seed, 7, 4,
                     rng=rng)


def the_lord_of_typhon():
    """The Lord of Typhon (19.10.2026): the boards of
    tests/test_lord_of_typhon.py and played games with one dealt."""
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(HERE.parent / "tools"))
    import play_games
    from test_lord_of_typhon import _payloads
    for name, payload in zip(("quiet", "a-night-death", "executed"),
                             _payloads()):
        yield {"name": f"x-typhon-{name}", "payload": payload}
    for seed, n in PLAYED_TYPHON:
        rng = random.Random(seed)
        script = play_games.an_awkward_script(
            rng, must_have=("LordOfTyphon",))
        yield played(f"x-typhon-played-{seed}", script, seed, n, 3, rng=rng)


PLAYED_TYPHON = ((0, 7), (12, 9))


def the_kazali():
    """The Kazali (20.10.2026): the boards of tests/test_kazali.py and
    played games with one dealt."""
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(HERE.parent / "tools"))
    import play_games
    from test_kazali import _payloads
    for name, payload in zip(("quiet", "a-night-death", "executed"),
                             _payloads()):
        yield {"name": f"x-kazali-{name}", "payload": payload}
    for seed, n in PLAYED_KAZALI:
        rng = random.Random(seed)
        script = play_games.an_awkward_script(rng, must_have=("Kazali",))
        yield played(f"x-kazali-played-{seed}", script, seed, n, 3, rng=rng)


PLAYED_KAZALI = ((0, 7), (31, 8))


def the_al_hadikhia():
    """The Al-Hadikhia (21.10.2026): the boards of
    tests/test_al_hadikhia.py and played games with one dealt."""
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(HERE.parent / "tools"))
    import play_games
    from test_al_hadikhia import _payloads
    names = ("one-dies", "all-three", "a-soldier", "twice", "one-back",
             "chambermaid")
    for name, payload in zip(names, _payloads()):
        yield {"name": f"x-al-hadikhia-{name}", "payload": payload}
    for seed, n in PLAYED_AL_HADIKHIA:
        rng = random.Random(seed)
        script = play_games.an_awkward_script(rng,
                                              must_have=("AlHadikhia",))
        yield played(f"x-al-hadikhia-played-{seed}-{n}", script, seed, n,
                     3, rng=rng)


# Two with a return (2 and 19), two without (0 and 12).
PLAYED_AL_HADIKHIA = ((0, 8), (2, 8), (12, 7), (19, 7))


def the_lil_monsta():
    """Lil' Monsta (21.10.2026): the boards of tests/test_lil_monsta.py
    and played games with it in the bag."""
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(HERE.parent / "tools"))
    import play_games
    from test_lil_monsta import _payloads
    names = ("one-dies", "fortune-teller", "babysat", "slayer",
             "scarlet-woman", "two-yeses")
    for name, payload in zip(names, _payloads(), strict=True):
        yield {"name": f"x-lil-monsta-{name}", "payload": payload}
    for seed, n in PLAYED_LIL_MONSTA:
        rng = random.Random(seed)
        script = play_games.an_awkward_script(rng, must_have=("LilMonsta",))
        yield played(f"x-lil-monsta-played-{seed}-{n}", script, seed, n, 3,
                     rng=rng)


# Small and quick to count, none of them sampled.
PLAYED_LIL_MONSTA = ((9, 7), (12, 7), (19, 7))


def the_summoner():
    """The Summoner (21.10.2026): the boards of tests/test_summoner.py and
    played games with it dealt."""
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(HERE.parent / "tools"))
    import play_games
    from test_summoner import _payloads
    names = ("third-night", "two-nights", "fortune-teller", "hanged",
             "clockmaker", "marionette", "marionette-ten")
    for name, payload in zip(names, _payloads(), strict=True):
        yield {"name": f"x-summoner-{name}", "payload": payload}
    for seed, n in PLAYED_SUMMONER:
        rng = random.Random(seed)
        script = play_games.an_awkward_script(rng, must_have=("Summoner",))
        yield played(f"x-summoner-played-{seed}-{n}", script, seed, n, 4,
                     rng=rng)


# An Imp on the third night (12), a Pukka on the second (25), a Zombuul
# (39), and a Summoner dead before its turn (34). None sampled.
PLAYED_SUMMONER = ((12, 7), (25, 8), (34, 8), (39, 7))


def the_hatter():
    """The Hatter (22.10.2026), its first stage: the boards of
    tests/test_hatter.py and played games with a tea party."""
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(HERE.parent / "tools"))
    import play_games
    from test_hatter import _payloads
    names = ("hanged", "gambler", "evil-twin", "at-night", "summoner",
             "two-days", "at-night-assassin", "summoner-third-night",
             "two-demons-deaths")
    for name, payload in zip(names, _payloads(), strict=True):
        yield {"name": f"x-hatter-{name}", "payload": payload}
    for seed, n in PLAYED_HATTER:
        rng = random.Random(seed)
        script = play_games.an_awkward_script(rng, must_have=("Hatter",))
        yield played(f"x-hatter-played-{seed}-{n}", script, seed, n, 4,
                     rng=rng)
    # A Summoner chosen at the party, and a second living Demon (stage 2,
    # 25.10.2026).
    for seed, n in PLAYED_TWO_DEMONS:
        rng = random.Random(seed)
        script = play_games.an_awkward_script(
            rng, must_have=("Hatter", "Summoner"))
        yield played(f"x-hatter-two-demons-{seed}-{n}", script, seed, n, 4,
                     rng=rng)


def the_engineer():
    """The Engineer (26.10.2026): the boards of tests/test_engineer.py and
    played games where it chose."""
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(HERE.parent / "tools"))
    import play_games
    from test_engineer import _payloads
    names = ("baron", "po", "two-minions", "summoner", "three-minions",
             "lil-monsta", "poisoner")
    for name, payload in zip(names, _payloads(), strict=True):
        yield {"name": f"x-engineer-{name}", "payload": payload}
    for seed, n in PLAYED_ENGINEER:
        rng = random.Random(seed)
        script = play_games.an_awkward_script(rng, must_have=("Engineer",))
        yield played(f"x-engineer-played-{seed}-{n}", script, seed, n, 4,
                     rng=rng)


def the_boffin():
    """The Boffin, stage 1 (26.10.2026): the boards of tests/test_boffin.py
    and played games where the Demon had an ability the town can see."""
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(HERE.parent / "tools"))
    import play_games
    from test_boffin import _payloads
    names = ("nothing", "imp-walks", "imp-walks-night", "row-fool",
             "starpass", "row-sailor")
    for name, payload in zip(names, _payloads(), strict=True):
        yield {"name": f"x-boffin-{name}", "payload": payload}
    for seed, n in PLAYED_BOFFIN:
        rng = random.Random(seed)
        script = play_games.an_awkward_script(rng, must_have=("Boffin",))
        yield played(f"x-boffin-played-{seed}-{n}", script, seed, n, 4,
                     rng=rng)


# Games with a Boffin whose Demon had an ability the town can see, each
# solved in seconds: the Saint (25) and the Gambler (31) with the Boffin's
# row, the Klutz (41), the Banshee with its row (78), the Acrobat (108).
PLAYED_BOFFIN = ((25, 7), (31, 8), (41, 8), (78, 10), (108, 10))


def the_boffin_2():
    """The Boffin, stage 2 (27.10.2026): the boards of
    tests/test_boffin_2.py and played games where the Demon had an ability
    stage 2 reckons."""
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(HERE.parent / "tools"))
    import play_games
    from test_boffin_2 import _payloads
    names = ("plain", "professor", "nightwatchman", "engineer",
             "row-philosopher", "philosopher-chose", "row-empath",
             "reading-empath", "balloonist")
    for name, payload in zip(names, _payloads(), strict=True):
        yield {"name": f"x-boffin2-{name}", "payload": payload}
    for line, seed, n in PLAYED_BOFFIN_2:
        must = BOFFIN_2_LINES[line]
        rng = random.Random(seed)
        script = play_games.an_awkward_script(rng, must_have=must)
        yield played(f"x-boffin2-played-{line}-{seed}-{n}", script, seed, n,
                     4, rng=rng)


# The two gate lines of stage 2 the played boards come from.
BOFFIN_2_LINES = {
    "a": ("Boffin", "Professor", "Engineer", "Nightwatchman", "Pixie",
          "Philosopher"),
    "e": ("Boffin", "Balloonist", "Huntsman", "Damsel", "Choirboy",
          "BountyHunter"),
}
# Each solved in seconds: a Pixie (a 5), an Engineer (a 65), a
# Nightwatchman (e 145), a Philosopher that took the Savant (e 156) and a
# Bounty Hunter (e 340).
PLAYED_BOFFIN_2 = (("a", 5, 7), ("a", 65, 7), ("e", 145, 7), ("e", 156, 8),
                   ("e", 340, 7))


def the_plague_doctor():
    """The Plague Doctor, stage 1 (28.10.2026): the boards of
    tests/test_plague_doctor.py and played games where the Storyteller
    gained an ability stage 1 reckons."""
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(HERE.parent / "tools"))
    import play_games
    from test_plague_doctor import _payloads
    names = ("plain", "godfather", "witch", "advocate", "row-poisoner",
             "scarlet-woman",
             # Stage 2 (29.10.2026).
             "stage-2", "pit-hag", "baron", "boomdandy", "evil-twin",
             "summoner", "spy", "mezepheles")
    for name, payload in zip(names, _payloads(), strict=True):
        yield {"name": f"x-plague-{name}", "payload": payload}
    for line, seed, n in PLAYED_PLAGUE:
        must = PLAGUE_LINES[line]
        rng = random.Random(seed)
        script = play_games.an_awkward_script(rng, must_have=must)
        yield played(f"x-plague-played-{line}-{seed}-{n}", script, seed, n,
                     4, rng=rng)


# The gate lines of the Plague Doctor the played boards come from.
PLAGUE_LINES = {
    "k": ("PlagueDoctor", "Poisoner", "Godfather", "Assassin"),
    "h": ("PlagueDoctor", "Witch", "DevilsAdvocate", "Mastermind"),
    "j": ("PlagueDoctor", "ScarletWoman", "Goblin", "Fearmonger"),
    "x": ("PlagueDoctor", "Widow", "Xaan", "Spy"),
    # Stage 2 (29.10.2026).
    "a": ("PlagueDoctor", "PitHag", "Mezepheles", "Summoner"),
    "b": ("PlagueDoctor", "Boffin", "Baron"),
    "c": ("PlagueDoctor", "EvilTwin", "Boomdandy", "Marionette"),
    "d": ("PlagueDoctor", "Spy", "Empath", "Investigator", "Undertaker"),
}
# Each solved in seconds, the Storyteller with: the Godfather (k 27), the
# Poisoner (k 72), the Assassin (k 86), the Witch (h 72), the Devil's
# Advocate (h 107), the Mastermind (h 207); a Minion with the Goblin's
# (j 32), the Scarlet Woman's (j 137), the Fearmonger's (j 47); the Xaan
# (x 1), the Widow (x 47).
# Stage 2 (29.10.2026): the Storyteller's Summoner (a 296), Mezepheles
# (a 312), Pit-Hag (a 317), Baron (b 56), Boffin (b 177); the Evil Twin
# (c 2), the Marionette (c 21), the Boomdandy (c 88); a Minion with the
# Spy's ability (d 131).
PLAYED_PLAGUE = (("k", 27, 9), ("k", 72, 9), ("k", 86, 8), ("h", 72, 9),
                 ("h", 107, 9), ("h", 207, 9), ("j", 32, 9), ("j", 137, 9),
                 ("j", 47, 9), ("x", 1, 8), ("x", 47, 9),
                 ("a", 296, 8), ("a", 312, 9), ("a", 317, 9), ("b", 56, 8),
                 ("b", 177, 9), ("c", 2, 9), ("c", 21, 8), ("c", 88, 10),
                 ("d", 131, 8))


# Games where the Engineer chose, each solved in seconds: a Widow on the
# first night (0), Goblin and Assassin on the second (6), the Pit-Hag (15)
# and a Lleech for the Demon (17).
PLAYED_ENGINEER = ((0, 7), (6, 8), (15, 8), (17, 9))


# Games with a tea party, each solved in seconds: a claimed Hatter
# executed (56, 82, 256) and a Hatter nobody claimed (1, 62, 120, 175);
# and a claimed Hatter dead at night, the party straight after the Demons'
# turn (176, 195; Hatter stage 3c, 23.10.2026).
PLAYED_HATTER = ((1, 8), (56, 8), (62, 9), (82, 9), (120, 7), (175, 7),
                 (256, 8), (176, 8), (195, 7))

# Games where a Minion chose the Summoner at a tea party and it summoned a
# second living Demon on the third night (Hatter stage 2, 25.10.2026).
PLAYED_TWO_DEMONS = ((7050, 7), (4500, 7))


def stellen_62_63():
    """Stellen 62 and 63 (20.10.2026): a Bounty Hunter shown the faux
    paw, and a Mathematician's number under a Vortox — played games the
    solver lost."""
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(HERE.parent / "tools"))
    import play_games
    from test_stelle_62_63 import PLAYED
    for name, seed, n, nights, must in PLAYED:
        # Too big to count, so sampled, and the corpus holds no sampled
        # board: its test keeps it.
        if name == "pixie-made-on-night-one":
            continue
        rng = random.Random(seed)
        script = play_games.an_awkward_script(rng, must_have=must)
        yield played(f"x-stelle-62-63-{name}-{seed}", script, seed, n,
                     nights, rng=rng)


def stelle_60():
    """Stelle 60 (19.10.2026): played games the solver lost. A Snake
    Charmer choosing the Scarlet Woman after she stepped up in daylight
    (a); a Savant asking on the day of a Slayer's hit, before it (b); a
    Savant told about a Cult Leader that had turned, or a Goon, with and
    without a Vortox."""
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(HERE.parent / "tools"))
    import play_games
    from test_stelle_60 import PLAYED
    for name, seed, n, nights, must in PLAYED:
        rng = random.Random(seed)
        script = play_games.an_awkward_script(rng, must_have=must)
        yield played(f"x-stelle-60-{name}-{seed}", script, seed, n, nights,
                     rng=rng)


# A shot that missed (1), a quiet nomination (5), a Virgin that took its
# nominator (7), a shot that landed and went to the Scarlet Woman (80), a
# shot that ended the game (105); mixed ones where a Philosopher shot or
# was nominated as the Virgin (26, 65).
PLAYED_TB_OPEN = (1, 5, 7, 80, 105)
PLAYED_MIXED_OPEN = (26, 65)


def the_farmers_heir():
    """Stelle 58 (14.10.2026): whoever is handed a character says so,
    and the search reads it. The boards of tests/test_farmer_heir.py and
    played games: heirs on the first script of batch 8, one killed the
    same night, and good players the Pit-Hag changed."""
    sys.path.insert(0, str(HERE))
    from test_farmer_heir import _payloads
    from test_experimental_8 import EIGHT
    names = ("row", "row-chef", "row-wrong-chef", "no-row", "two-heirs",
             "pit-hag-unwritten", "pit-hag-unwritten-chef")
    for name, payload in zip(names, _payloads()):
        yield {"name": f"x-farmer-heir-{name}", "payload": payload}
    for seed in PLAYED_HEIRS:
        yield played(f"x-eight-played-farmer-heir-{seed}", EIGHT, seed, 7, 4)
    sys.path.insert(0, str(HERE.parent / "tools"))
    import play_games
    for seed in PLAYED_PIT_HAG:
        rng = random.Random(seed)
        script = play_games.an_awkward_script(rng, must_have=("PitHag",))
        yield played(f"x-pit-hag-played-{seed}", script, seed, 7, 4,
                     rng=rng)


# Played games: heirs on batch 8, and good players the Pit-Hag changed
# saying so (mixed scripts with the Pit-Hag, seven players).
PLAYED_HEIRS = (18, 75, 312)       # one heir; one killed and handing on; a Spy saying so
PLAYED_PIT_HAG = (12, 39, 41)


# Games where a Philosopher took one of group 4 and used it: the Ogre
# (105), the Pixie (76), the Huntsman on the Damsel (345), the Farmer dying
# at night (826), raised by the real Professor it had drunk (99), raising
# somebody itself (143). Not 693: there the heir only says "Farmer", and
# the page, which takes a good player's claim as dealt, finds no world.
PLAYED_GROUP_4 = (105, 76, 345, 826, 99, 143)


# Gate games where a Philosopher took one of group 3 and used it: the
# Goon turned (120), a sermon (215), a Minion hanged beside the Minstrel
# (235), a Puzzlemaster's guess (1305).
PLAYED_GROUP_3 = (120, 215, 235, 1305)


# Gate games where a Philosopher took one of group 2 and used it: the
# Tinker (15), the Lycanthrope (65), the Acrobat (750), the Moonchild (1490).
PLAYED_GROUP_2 = (15, 65, 750, 1490)


# Gate games where a Philosopher took one of group 1 and used it.
PLAYED_GROUP_1 = (14, 805, 50)


def generated(how_many=60):
    """Random boards, so the corpus covers combinations nobody chose."""
    sys.path.insert(0, str(HERE))
    from test_random_scripts import a_script

    rng = random.Random(4602)
    for i in range(how_many):
        script = a_script(rng, name=f"Random {i}")
        n = rng.choice((5, 6, 7, 8, 9, 10, 12))
        wanted = max(2, min(4, n // 4))
        seats = rng.sample(range(n), wanted)
        claims = []
        for s in range(n):
            pool = script.outsiders if s in seats else script.townsfolk
            claims.append(rng.choice(pool))
        events = {}
        for s in rng.sample(range(n), rng.randint(0, 2)):
            events[s] = [rng.choice(("N2", "N3", "X1", "X2", "D2"))]
        payload = {}
        if rng.random() < 0.3:
            payload["quiet_nights"] = [rng.choice((2, 3))]
        yield board(f"random-{i:02d}", script, claims,
                    players_override=events, **payload)


def apply_overrides(case):
    """Events are easier to write beside the board than inside it."""
    over = case["payload"].pop("players_override", None) or {}
    for seat_no, events in over.items():
        case["payload"]["players"][int(seat_no)]["events"] = events
    return case


def answer(payload):
    """What the reference implementation says, trimmed to what matters."""
    got = app.run_solve(payload)
    if "error" in got:
        return {"error": got["error"]}
    out = {
        "valid": got["valid"],
        "sampled": got["sampled"],
        "rows": [{k: round(row[k], PLACES) for k in
                  ("evil_pct", "demon_pct", "drunk_pct", "lying_pct")}
                 for row in got["rows"]],
    }
    if got.get("blame"):
        out["blame"] = {night: {seat: {c: round(v, PLACES)
                                       for c, v in causes.items()}
                                for seat, causes in seats.items()}
                        for night, seats in got["blame"].items()}
    if got.get("diagnosis"):
        out["diagnosis"] = got["diagnosis"]
    # What the solver does not reckon yet (the Hatter, 22.10.2026).
    if got.get("unreckoned"):
        out["unreckoned"] = {why: round(v, PLACES)
                             for why, v in got["unreckoned"].items()}
    return out


def build():
    cases = [apply_overrides(c) for c in list(handmade()) + list(generated())]
    sampled = 0
    for case in cases:
        case["expect"] = answer(json.loads(json.dumps(case["payload"])))
        sampled += bool(case["expect"].get("sampled"))
    CORPUS.parent.mkdir(exist_ok=True)
    CORPUS.write_text(json.dumps(
        {"note": "Generated by tests/make_fixtures.py. Python is the "
                 "reference; any other implementation has to agree.",
         "places": PLACES,
         "cases": cases}, indent=1) + "\n")
    errors = sum(1 for c in cases if "error" in c["expect"])
    empty = sum(1 for c in cases
                if not c["expect"].get("error") and not c["expect"]["valid"])
    print(f"{len(cases)} boards written to {CORPUS.relative_to(HERE.parent)}")
    print(f"   {errors} refused, {empty} with no worlds, {sampled} sampled")
    print(f"   {CORPUS.stat().st_size / 1024:.0f} kB")


if __name__ == "__main__":
    build()
