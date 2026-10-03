"""The JavaScript readings and board, held against the Python ones.

A reading is a function of (world, board), so checking it against one
world proves almost nothing: a wrong implementation agrees with a right
one most of the time. So each reading is run against *every* world of a
board and digested over the whole sequence of trues and falses. It only
matches if the two agree world by world.

Also checked: where a reading gets attributed when somebody relays it,
and every question a board can be asked about a moment — who was standing
when, what an execution means, how far the game has got.

Skipped when Node is not installed.
"""

import hashlib
import json
import pathlib
import shutil
import subprocess
import unittest

from helpers import SolverTest                    # sets up the import path
from botc import info as I, scripts               # noqa: E402
from botc.info import (GameState, _living_neighbours,  # noqa: E402
                       _possible_evil_counts)
from botc.waking import possible_counts, uncertain, woke, woke_as  # noqa: E402
from botc.worlds import iter_worlds                # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
NODE = shutil.which("node")

TB = scripts.TROUBLE_BREWING
BMR = scripts.BAD_MOON_RISING

TB9 = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
       "FortuneTeller", "Undertaker", "Recluse", "Saint"]
# A board where somebody claims the character being tested. Checking a
# Virgin trigger on a table with no Virgin claim makes it false in every
# world, which tells one implementation apart from nothing.
TB12 = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
        "FortuneTeller", "Undertaker", "Virgin", "Slayer", "Monk",
        "Recluse", "Saint"]
# Seven players, because that is the only table size whose bag wants
# *no* Outsiders — so "none in play" is a thing the Librarian can
# truthfully say. At nine it is impossible whatever anybody claims.
#
# Two Outsider claims, because otherwise it is true in *every* world: a
# Baron's bag wants two Outsiders and seven Townsfolk claims cannot fill
# it, so only the plain bag survives and the answer never varies.
TB7 = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
       "Recluse", "Saint"]
BMR9 = ["Grandmother", "Sailor", "Chambermaid", "Exorcist", "Innkeeper",
        "Gambler", "Gossip", "Tinker", "Moonchild"]

KINDS = {
    "Washerwoman": I.Washerwoman, "Librarian": I.Librarian,
    "Investigator": I.Investigator, "Chef": I.Chef, "Empath": I.Empath,
    "FortuneTeller": I.FortuneTeller, "Undertaker": I.Undertaker,
    "Ravenkeeper": I.Ravenkeeper, "GrandmotherInfo": I.GrandmotherInfo,
    "GamblerGuess": I.GamblerGuess, "CourtierChoice": I.CourtierChoice,
    "VirginNomination": I.VirginNomination, "SlayerShot": I.SlayerShot,
    "ChambermaidInfo": I.ChambermaidInfo,
    "ClockmakerInfo": I.ClockmakerInfo, "DreamerInfo": I.DreamerInfo,
}


class Row:
    """A stand-in for a reading, for the waking rules that only read its
    source character, seat and night."""

    def __init__(self, source_role, player, night):
        self.source_role = source_role
        self.player = player
        self.night = night


def board(script, claims, **kw):
    return GameState(n_players=len(claims), script=script,
                     claims={i: r for i, r in enumerate(claims)}, **kw)


def pattern(script, claims, row, opts=None, herring=None):
    """Every world's answer, digested."""
    state = board(script, claims, **(opts or {}))
    kind = KINDS[row["type"]]
    fields = {k: v for k, v in row.items() if k != "type"}
    reading = kind(**fields)
    seat = reading.source_seat(state)
    answers = []
    for world in iter_worlds(len(claims), state.claims, script=script):
        answers.append("1" if reading.holds(world, state, herring, seat)
                       else "0")
        if len(answers) >= 60_000:
            break
    joined = "".join(answers)
    return {
        "worlds": len(answers),
        "trues": joined.count("1"),
        "digest": hashlib.sha256(joined.encode()).hexdigest()[:16],
        "sourceSeat": seat,
        "hard": reading.hard(),
    }


def python_side():
    readings = {}

    def add(name, script, claims, row, opts=None, herring=None):
        readings[name] = pattern(script, claims, row, opts, herring)

    add("washerwoman", TB, TB9, {"type": "Washerwoman", "night": 1,
                                 "player": 0, "a": 1, "b": 5,
                                 "role": "Librarian"})
    add("librarian-somebody", TB, TB9,
        {"type": "Librarian", "night": 1, "player": 1, "a": 7, "b": 8,
         "role": "Recluse"})
    add("librarian-nobody", TB, TB7,
        {"type": "Librarian", "night": 1, "player": 1, "a": None,
         "b": None, "role": ""})
    add("investigator", TB, TB9,
        {"type": "Investigator", "night": 1, "player": 2, "a": 3, "b": 8,
         "role": "Poisoner"})
    for count in (0, 1, 2):
        add(f"chef-{count}", TB, TB9,
            {"type": "Chef", "night": 1, "player": 3, "count": count})
    for count in (0, 1, 2):
        add(f"empath-{count}", TB, TB9,
            {"type": "Empath", "night": 1, "player": 4, "count": count})
    add("empath-after-a-death", TB, TB9,
        {"type": "Empath", "night": 2, "player": 4, "count": 1},
        {"deaths": {3: "N2"}})
    add("empath-killed-tonight", TB, TB9,
        {"type": "Empath", "night": 2, "player": 4, "count": 2},
        {"deaths": {4: "N2"}})
    add("fortune-teller-yes", TB, TB9,
        {"type": "FortuneTeller", "night": 1, "player": 5, "a": 0, "b": 8,
         "yes": True})
    add("fortune-teller-no", TB, TB9,
        {"type": "FortuneTeller", "night": 1, "player": 5, "a": 0, "b": 8,
         "yes": False})
    add("fortune-teller-yes-herring", TB, TB9,
        {"type": "FortuneTeller", "night": 1, "player": 5, "a": 0, "b": 8,
         "yes": True}, None, 3)
    add("fortune-teller-no-herring", TB, TB9,
        {"type": "FortuneTeller", "night": 1, "player": 5, "a": 0, "b": 8,
         "yes": False}, None, 3)
    add("undertaker", TB, TB9,
        {"type": "Undertaker", "night": 2, "player": 6, "target": 7,
         "role": "Spy"}, {"deaths": {7: "E1"}})
    add("undertaker-no-execution", TB, TB9,
        {"type": "Undertaker", "night": 2, "player": 6, "target": 7,
         "role": "Spy"})
    add("undertaker-survived", TB, TB9,
        {"type": "Undertaker", "night": 2, "player": 6, "target": 7,
         "role": "Spy"}, {"executions": {1: 7}})
    add("ravenkeeper", TB, TB9,
        {"type": "Ravenkeeper", "night": 2, "player": 8, "target": 4,
         "role": "Empath"}, {"deaths": {8: "N2"}})
    add("virgin-triggered", TB, TB12,
        {"type": "VirginNomination", "night": 1, "player": 7,
         "nominator": 2, "triggered": True})
    add("virgin-quiet", TB, TB12,
        {"type": "VirginNomination", "night": 1, "player": 7,
         "nominator": 2, "triggered": False})
    add("slayer-landed", TB, TB12,
        {"type": "SlayerShot", "night": 2, "player": 8, "target": 11,
         "died": True})
    add("slayer-missed", TB, TB12,
        {"type": "SlayerShot", "night": 2, "player": 8, "target": 11,
         "died": False})
    add("grandmother", BMR, BMR9,
        {"type": "GrandmotherInfo", "night": 1, "player": 0, "target": 2,
         "role": "Chambermaid"})
    add("grandmother-evil-target", BMR, BMR9,
        {"type": "GrandmotherInfo", "night": 1, "player": 0, "target": 7,
         "role": "Godfather"})
    add("gambler-lived", BMR, BMR9,
        {"type": "GamblerGuess", "night": 2, "player": 5, "target": 2,
         "role": "Chambermaid"})
    add("gambler-died", BMR, BMR9,
        {"type": "GamblerGuess", "night": 2, "player": 5, "target": 2,
         "role": "Chambermaid"}, {"deaths": {5: "N2"}})
    SV = scripts.SECTS_AND_VIOLETS
    SV9 = ["Clockmaker", "Dreamer", "SnakeCharmer", "Mathematician",
           "Flowergirl", "TownCrier", "Oracle", "Mutant", "Sweetheart"]
    for count in (0, 1, 2, 4):
        add(f"clockmaker-{count}", SV, SV9,
            {"type": "ClockmakerInfo", "night": 1, "player": 0,
             "count": count})
    add("dreamer-own-claim", SV, SV9,
        {"type": "DreamerInfo", "night": 1, "player": 1, "target": 2,
         "good_role": "SnakeCharmer", "evil_role": "Witch"})
    add("dreamer-something-else", SV, SV9,
        {"type": "DreamerInfo", "night": 1, "player": 1, "target": 2,
         "good_role": "Oracle", "evil_role": "Witch"})
    add("dreamer-two-good", SV, SV9,
        {"type": "DreamerInfo", "night": 1, "player": 1, "target": 2,
         "good_role": "Oracle", "evil_role": "Sage"})

    add("courtier", BMR, BMR9,
        {"type": "CourtierChoice", "night": 1, "player": 7,
         "role": "Chambermaid"})
    for count in (0, 1, 2):
        add(f"chambermaid-{count}", BMR, BMR9,
            {"type": "ChambermaidInfo", "night": 2, "player": 2, "a": 4,
             "b": 6, "count": count})
    add("chambermaid-night-1", BMR, BMR9,
        {"type": "ChambermaidInfo", "night": 1, "player": 2, "a": 0, "b": 1,
         "count": 1})
    add("chambermaid-with-an-exorcist", BMR, BMR9,
        {"type": "ChambermaidInfo", "night": 2, "player": 2, "a": 3, "b": 8,
         "count": 1})

    state = board(TB, TB9)
    nobody = board(TB, ["Washerwoman", "Librarian", "Investigator", "Chef",
                        "Monk", "FortuneTeller", "Undertaker", "Recluse",
                        "Saint"])
    twice = board(TB, ["Empath", "Librarian", "Investigator", "Chef",
                       "Empath", "FortuneTeller", "Undertaker", "Recluse",
                       "Saint"])
    relaying = {
        "spoken by the Empath":
            I.Empath(1, 4, count=1).source_seat(state),
        "spoken by somebody else":
            I.Empath(1, 2, count=1).source_seat(state),
        "nobody claims it":
            I.Empath(1, 2, count=1).source_seat(nobody),
        "two seats claim it":
            I.Empath(1, 2, count=1).source_seat(twice),
        "a shot is never relayed":
            I.SlayerShot(2, 2, target=8, died=True).source_seat(state),
    }

    lives = {}
    cases = {
        "nothing recorded": {},
        "one night death": {"deaths": {2: "N2"}},
        "an execution death": {"deaths": {2: "E1"}},
        "executed and lived": {"executions": {1: 2}},
        "died, raised": {"deaths": {2: "N2"}, "resurrections": {2: "N4"}},
        "died, raised, died": {"deaths": {2: ("N2", "N6")},
                               "resurrections": {2: ("N4",)}},
        "raised the same night": {"deaths": {2: "N2"},
                                  "resurrections": {2: "N2"}},
        "quiet nights": {"quiet_nights": {2, 3}},
    }
    for name, opts in cases.items():
        st = board(TB, TB9, **opts)
        lives[name] = {
            "alive": {p: st.alive_at(p) for p in
                      ("N1", "D1", "N2", "D2", "N3", "N4", "N5", "N6", "N7")},
            "diedAt": {str(seat): list(st.died_at(seat))
                       for seat in (0, 2, 7)},
            "deathPhases": [list(x) for x in st.death_phases()],
            "executions": {str(k): v for k, v in st.executions.items()},
            "executedOn": {str(d): st.executed_on(d) for d in (1, 2)},
            "executionDeath": {str(d): st.execution_death(d) for d in (1, 2)},
            "finalPhase": st.final_phase(),
        }
    with_info = board(TB, TB9, infos=[I.Chef(4, 0, count=0),
                                      I.Chef(2, 0, count=0)])
    lives["readings push the phase along"] = {
        "finalPhase": with_info.final_phase()}

    helpers = {"neighbours": {}, "evilCounts": []}
    for name, opts in {
        "everybody alive": {},
        "one gone": {"deaths": {1: "N2"}},
        "two gone": {"deaths": {1: "N2", 3: "N2"}},
        "the reader's own night death": {"deaths": {2: "N2"}},
        "only two left": {"deaths": {0: "N2", 1: "N2", 3: "N2", 4: "N2",
                                     5: "N2", 6: "N2", 7: "N2"}},
    }.items():
        st = board(TB, TB9, **opts)
        helpers["neighbours"][name] = {
            str(p): _living_neighbours(st, 2, p) for p in (0, 2, 8)}

    worlds = []
    for world in iter_worlds(9, state.claims, script=TB):
        worlds.append(world)
        if len(worlds) >= 3:
            break
    helpers["evilCounts"] = [
        [sorted(_possible_evil_counts(w, (0, 1), "N1")),
         sorted(_possible_evil_counts(w, (7, 8), "N1")),
         sorted(_possible_evil_counts(w, (), "N1"))]
        for w in worlds]

    waking = {}
    TB_RK = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
             "FortuneTeller", "Undertaker", "Recluse", "Ravenkeeper"]
    BMR_CP = ["Grandmother", "Sailor", "Chambermaid", "Exorcist",
              "Innkeeper", "Gambler", "Gossip", "Courtier", "Professor"]
    cases = {
        "ravenkeeper": (TB, TB_RK, {"deaths": {8: "N2"}}, "Ravenkeeper", 8),
        "ravenkeeper-alive": (TB, TB_RK, {}, "Ravenkeeper", 8),
        "undertaker": (TB, TB9, {"deaths": {7: "E1"}}, "Undertaker", 6),
        "undertaker-survived": (TB, TB9, {"executions": {1: 7}},
                                "Undertaker", 6),
        "scarlet-woman": (TB, TB9, {"deaths": {8: "E1"}}, "ScarletWoman", 7),
        "courtier": (BMR, BMR_CP, {}, "Courtier", 7),
        "courtier-spent": (BMR, BMR_CP,
                           {"infos": [Row("Courtier", 7, 2)]}, "Courtier", 7),
        "professor": (BMR, BMR_CP, {}, "Professor", 8),
        "professor-spent": (BMR, BMR_CP,
                            {"deaths": {2: "N2"},
                             "resurrections": {2: "N3"}}, "Professor", 8),
        "zombuul": (BMR, BMR9, {}, "Zombuul", 8),
        "zombuul-after-a-day-death": (BMR, BMR9, {"deaths": {1: "D2"}},
                                      "Zombuul", 8),
        "assassin": (BMR, BMR9, {}, "Assassin", 7),
        "assassin-spent": (BMR, BMR9, {"infos": [Row("Assassin", 7, 2)]},
                           "Assassin", 7),
        "drunk": (TB, TB9, {}, "Drunk", 4),
    }
    for name, (script, claims, opts, role, seat) in cases.items():
        st = board(script, claims, **opts)
        found = None
        for w in iter_worlds(len(claims), st.claims, script=script):
            if w.roles[seat] == role:
                found = w
                break
        waking[name] = "no such world" if found is None else {
            "byNight": [woke(found, st, seat, n) for n in (1, 2, 3, 4, 5)],
            "asRole": [woke_as(found, st, seat, n, role) for n in (1, 2, 3)],
            "believesToken": found.believes[seat],
        }

    with_exorcist = board(BMR, BMR9)
    first = None
    for w in iter_worlds(9, with_exorcist.claims, script=BMR):
        if w.roles[3] == "Exorcist" and w.roles[8] == "Zombuul":
            first = w
            break
    if first is not None:
        waking["exorcist makes the demon open"] = {
            "demon": [uncertain(first, with_exorcist, 8, n)
                      for n in (1, 2, 3)],
            "somebodyElse": [uncertain(first, with_exorcist, 4, n)
                             for n in (2,)],
            "counts": [sorted(possible_counts(first, with_exorcist, (8, 4), n))
                       for n in (1, 2, 3)],
        }

    # Worlds written out rather than searched for, because nobody claims
    # to be a Lunatic or a Godfather: what a Chambermaid counts beside
    # each of the characters the table ruled on (02.10.2026).
    from botc.worlds import World
    GOOD = ["Grandmother", "Sailor", "Chambermaid", "Professor",
            "Innkeeper", "Gambler", "Tinker"]
    NOBODY = (None,) * 9
    LUNATIC = ["Grandmother", "Sailor", "Chambermaid", "Professor",
               "Innkeeper", "Gambler", "Lunatic"]
    direct = {
        "godfather": (GOOD + ["Godfather", "Po"], NOBODY, {}),
        "godfather-outsider-executed":
            (GOOD + ["Godfather", "Po"], NOBODY,
             {"deaths": {6: "D1"}, "executions": {1: 6}}),
        "godfather-townsfolk-executed":
            (GOOD + ["Godfather", "Po"], NOBODY,
             {"deaths": {5: "D1"}, "executions": {1: 5}}),
        "pukka": (GOOD + ["Godfather", "Pukka"], NOBODY, {}),
        "zombuul": (GOOD + ["Godfather", "Zombuul"], NOBODY, {}),
        "shabaloth-and-a-raising":
            (GOOD + ["Godfather", "Shabaloth"], NOBODY,
             {"deaths": {0: "N2"}, "resurrections": {0: "N3"}}),
        "po-and-a-raising":
            (GOOD + ["Godfather", "Po"], NOBODY,
             {"deaths": {0: "N2"}, "resurrections": {0: "N3"}}),
        "lunatic-thinks-po":
            (LUNATIC + ["Godfather", "Po"],
             (None,) * 6 + ("Po", None, None), {}),
        "lunatic-thinks-pukka":
            (LUNATIC + ["Godfather", "Pukka"],
             (None,) * 6 + ("Pukka", None, None), {}),
        "lunatic-no-token":
            (LUNATIC + ["Godfather", "Zombuul"], NOBODY,
             {"deaths": {5: "D2"}, "executions": {2: 5}}),
        # Back from the dead on night three (03.10.2026): a Sailor acts
        # at 4 and slept through whoever raised it; a Professor acts at
        # 43, after a Shabaloth and at its own slot, so it is open.
        "sailor-regurgitated":
            (GOOD + ["Godfather", "Shabaloth"], NOBODY,
             {"deaths": {1: "N2"}, "resurrections": {1: "N3"}}),
        "sailor-raised-by-the-professor":
            (GOOD + ["Godfather", "Po"], NOBODY,
             {"deaths": {1: "N2"}, "resurrections": {1: "N3"}}),
        "professor-regurgitated":
            (GOOD + ["Godfather", "Shabaloth"], NOBODY,
             {"deaths": {3: "N2"}, "resurrections": {3: "N3"}}),
    }
    for name, (roles, believes, opts) in direct.items():
        st = board(BMR, roles[:7] + ["Tinker", "Moonchild"], **opts)
        w = World(tuple(roles), tuple(believes))
        waking["direct " + name] = {
            "woke": [[woke(w, st, seat, n) for n in (1, 2, 3, 4)]
                     for seat in (3, 6, 7, 8)],
            "open": [[uncertain(w, st, seat, n) for n in (1, 2, 3, 4)]
                     for seat in (3, 6, 7, 8)],
            "counts": [[sorted(possible_counts(w, st, pair, n))
                        for n in (1, 2, 3, 4)]
                       for pair in ((7, 8), (3, 6), (6, 8), (1, 7))],
        }

    # A Marionette beside a Chambermaid, which needs a mixed script: it
    # counts as the token it holds (table ruling, 02.10.2026).
    from botc import scripts as script_mod
    mixed = script_mod.from_ids("Mixed", [
        "chambermaid", "empath", "chef", "undertaker", "monk",
        "washerwoman", "slayer", "saint", "drunk", "marionette",
        "poisoner", "imp"])
    for token in ("Empath", "Chef", "Undertaker"):
        for holder in ("Marionette", "Drunk"):
            st = board(mixed, ["Chambermaid", token, "Monk", "Washerwoman",
                               "Slayer", "Saint", "Chef"],
                       deaths={5: "D2"}, executions={2: 5})
            w = World(("Chambermaid", holder, "Imp", "Washerwoman",
                       "Slayer", "Saint", "Chef"),
                      (None, token, None, None, None, None, None))
            waking[f"token {holder} thinks {token}"] = [
                sorted(possible_counts(w, st, (1, 4), n))
                for n in (1, 2, 3, 4)]

    return {"readings": readings, "relaying": relaying, "lives": lives,
            "helpers": helpers, "waking": waking}


@unittest.skipUnless(NODE, "Node is not installed")
class TheReadingsAgree(SolverTest):

    @classmethod
    def setUpClass(cls):
        got = subprocess.run([NODE, str(ROOT / "js" / "dump_info.mjs")],
                             capture_output=True, text=True, timeout=600)
        if got.returncode:
            raise AssertionError(f"js/dump_info.mjs failed:\n{got.stderr}")
        cls.js = json.loads(got.stdout)
        cls.py = python_side()

    def test_the_same_readings_were_tried(self):
        self.assertEqual(sorted(self.js["readings"]),
                         sorted(self.py["readings"]))

    def test_every_reading_answers_the_same_in_every_world(self):
        """Not merely the same number of worlds — the same worlds. The
        digest is over the whole sequence of trues and falses."""
        for name, theirs in self.py["readings"].items():
            with self.subTest(reading=name):
                self.assertEqual(self.js["readings"][name], theirs)

    def test_the_readings_actually_discriminate(self):
        """A reading true in every world, or false in every world, would
        match trivially and prove nothing about the port."""
        useless = [name for name, got in self.py["readings"].items()
                   if got["worlds"] and got["trues"] in (0, got["worlds"])
                   # These are constant *by design*, which is the thing
                   # being checked rather than a weakness in the case.
                   # Constant *by design*, which is the thing being
                   # checked rather than a weakness in the case.
                   and name not in ("courtier", "empath-killed-tonight",
                                    "undertaker-no-execution",
                                    "undertaker-survived",
                                    "grandmother-evil-target",
                                    # Zero steps would mean the Demon is
                                    # its own nearest Minion, and a pair
                                    # of good characters is not a
                                    # Dreamer reading. Both false in
                                    # every world, which is the point.
                                    "clockmaker-0", "dreamer-two-good",
                                    # A Gambler dead by morning says
                                    # nothing by itself any more: it may
                                    # have guessed right and been killed
                                    # all the same. True in every world.
                                    "gambler-died")]
        self.assertEqual(useless, [], "these tell the two apart from nothing")

    def test_a_relayed_reading_lands_on_the_same_seat(self):
        self.assertEqual(self.js["relaying"], self.py["relaying"])

    def test_the_board_answers_the_same_about_every_moment(self):
        for name, theirs in self.py["lives"].items():
            with self.subTest(board=name):
                self.assertEqual(self.js["lives"][name], theirs)

    def test_who_woke_for_their_own_ability_matches(self):
        """Every conditional waker, on a board that makes its rule bite:
        a Ravenkeeper only on the night it dies, a Courtier only until it
        has spent, a Drunk on the schedule of the token it holds."""
        for name, theirs in self.py["waking"].items():
            with self.subTest(rule=name):
                self.assertEqual(self.js["waking"][name], theirs)

    def test_each_waking_case_actually_had_a_world(self):
        """A character nobody claims is in no world at all, and the case
        would then compare two pieces of nothing."""
        empty = [name for name, got in self.py["waking"].items()
                 if got == "no such world"]
        self.assertEqual(empty, [])

    def test_the_helpers_the_readings_lean_on_match(self):
        self.assertEqual(self.js["helpers"]["neighbours"],
                         self.py["helpers"]["neighbours"])
        self.assertEqual(self.js["helpers"]["evilCounts"],
                         self.py["helpers"]["evilCounts"])


if __name__ == "__main__":
    unittest.main()
