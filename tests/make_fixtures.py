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


def played(name, script, seed, n, nights):
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
    rng = random.Random(seed)
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
    return board(name, script, players, infos=infos)


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
    # working the Snake Charmer (981), and at seven seats — the eleven-seat
    # originals took minutes a board — two swaps in a row (1063) and a
    # swap and a Barber on the same night (672); on Bad Moon Rising a
    # Mastermind's extra day and a Zombuul surviving its execution.
    for seed, n, nights in ((1, 8, 4), (61, 8, 4), (981, 8, 4),
                            (1063, 7, 4), (672, 7, 4)):
        yield played(f"sv-played-{seed}", SV, seed, n, nights)
    yield played("bmr-played-mastermind", BMR, 5, 7, 4)
    yield played("bmr-played-zombuul", BMR, 30, 7, 4)

    # Games with the four things the simulator learned on 03.10.2026, one
    # of each kind: somebody walking away from the gallows for each of
    # the five reasons there are, the dead coming back by both hands, a
    # Moonchild taken at night that names somebody in the morning, a
    # Pukka whose kill came a night late because it was drunk, and a
    # nominator a Witch had cursed. The seeds are whichever came first.
    for what, seed in (("walked-advocate", 41), ("walked-pacifist", 16),
                       ("walked-sailor", 9), ("walked-tea-lady", 19),
                       ("fool-and-back", 12), ("regurgitated", 1),
                       ("professor", 6), ("moonchild-at-night", 82),
                       ("pukka-a-night-late", 104)):
        yield played(f"bmr-played-{what}", BMR, seed, 7, 4)
    yield played("sv-played-witch", SV, 8, 7, 4)

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
