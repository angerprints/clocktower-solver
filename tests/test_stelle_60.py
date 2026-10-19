"""Stelle 60 (15.–19.10.2026): small classes the Slayer brought out.

(a) The Scarlet Woman steps up in daylight, and on a later night a Snake
    Charmer chooses her. Run all at once, the charmer (slot 11) is asked
    before the Demon's lineage (last) and looks for the Demon where it
    was dealt, so the swap with her was never offered. A dealt Demon that
    died before the last swap now counts as a second mover, and the
    board is read a night at a time.
(b) Patrick, Weg 2: a Savant may visit the Storyteller at any time of the
    day. On a day a Demon is made in daylight (a Slayer's hit, an
    execution, and the Scarlet Woman steps up) the pair may be about the
    morning or the evening.
(c) Found at the gate of (b): the Savant read a Cult Leader's side, and a
    Goon's, as dealt. Now as every other reading does — open either way,
    for the Vortox's question too.
"""
import json
import pathlib
import random
import subprocess
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent
                       / "tools"))
from helpers import SolverTest                    # sets up the import path

import botc.solver as S                           # noqa: E402
from botc import info as I, scripts               # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.worlds import Change, Timeline, World   # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
GROUP_5 = ("Philosopher", "Slayer", "Virgin", "Golem", "Alsaahir", "Zealot",
           "Butler")
OPEN = ("Philosopher", "Slayer", "Virgin")
# name, seed, players, nights, must have
PLAYED = (
    ("charmer-takes-the-heir", 127, 9, 4, GROUP_5),
    ("charmer-takes-the-heir", 2001, 8, 6, OPEN),
    ("savant-before-the-hit", 1209, 11, 4, GROUP_5),
    ("savant-cult-leader", 1747, 9, 4, ("Savant", "Vortox")),
    ("savant-cult-leader-vortox", 1791, 8, 4,
     ("Savant", "CultLeader", "Philosopher")),
    ("savant-goon-vortox", 2738, 10, 4, ("Savant", "Lycanthrope", "Goon")),
)


def game(seed, n, nights, must):
    import claims as C
    import play_games
    import simulate
    rng = random.Random(seed)
    script = play_games.an_awkward_script(rng, must_have=must)
    deal, heard = simulate.play(n, rng, nights=nights, script=script)
    cl, wk, _ = C.claims_for(deal, rng, script=script)
    st = GameState(n_players=n, script=script, claims=cl, wakes=wk,
                   infos=list(heard), votes=dict(deal.votes),
                   nominations=dict(deal.nominations), **deal.record())
    return deal, st


class ThePlayedGamesAreKept(SolverTest):

    def test_every_one(self):
        for name, seed, n, nights, must in PLAYED:
            deal, st = game(seed, n, nights, must)
            with self.subTest(name=name, seed=seed):
                self.assertIsNotNone(S.explanation_cost(deal.world(), st))

    def test_a_charmer_after_a_heir_is_read_night_by_night(self):
        for name, seed, n, nights, must in PLAYED[:2]:
            deal, st = game(seed, n, nights, must)
            with self.subTest(seed=seed):
                # The Scarlet Woman took over in daylight, and a charmer
                # later swapped with her.
                self.assertTrue(any(p[0] == "D" and r == "Vigormortis"
                                    for p, _s, r in deal.changes))
                self.assertEqual(S._movers_in(deal.world(), st), 2)


IDS = ["savant", "slayer", "chef", "empath", "washerwoman", "monk",
       "scarletwoman", "poisoner", "imp", "cultleader", "goon", "vortox"]
SAV = scripts.from_ids("Savant", IDS)
#      0         1         2       3         4              5
S7 = ["Savant", "Slayer", "Chef", "Empath", "ScarletWoman", "Imp",
      "Washerwoman", "Monk"]


def savant(night, first, second):
    return I.SavantInfo(night, 0, first="", second="", first_says=first,
                        second_says=second)


class TheSavantAsksMorningOrEvening(SolverTest):
    """(b): the Imp is hit on day 2 and the Scarlet Woman steps up."""

    def setUp(self):
        self.st = GameState(n_players=8, script=SAV,
                            claims=dict(enumerate(S7)), days_done={1, 2})
        self.w = Timeline(World(tuple(S7), (None,) * 8),
                          (Change("D2", 4, "Imp"),))

    def test_before_the_hit(self):
        # The Demon among 5, 6, 7 was true in the morning; seat 2 is no
        # Monk either way.
        row = savant(2, {"kind": "demon_among", "seats": [5, 6, 7]},
                     {"kind": "is", "seat": 2, "role": "Monk"})
        self.assertTrue(row.holds(self.w, self.st, None))

    def test_after_the_hit(self):
        row = savant(2, {"kind": "demon_among", "seats": [3, 4, 6]},
                     {"kind": "is", "seat": 2, "role": "Monk"})
        self.assertTrue(row.holds(self.w, self.st, None))

    def test_never_true(self):
        row = savant(2, {"kind": "demon_among", "seats": [1, 2, 3]},
                     {"kind": "is", "seat": 2, "role": "Monk"})
        self.assertFalse(row.holds(self.w, self.st, None))

    def test_a_day_without_a_new_demon_has_one_board(self):
        row = savant(1, {"kind": "demon_among", "seats": [5, 6, 7]},
                     {"kind": "is", "seat": 2, "role": "Monk"})
        self.assertEqual(row._visits(self.w), [self.w])


class TheSavantReadsAnOpenSide(SolverTest):
    """(c): a Goon's side is the Storyteller's, real or read."""

    def test_a_goon_either_way(self):
        roles = ["Savant", "Goon", "Chef", "Empath", "Poisoner", "Vortox",
                 "Monk"]
        st = GameState(n_players=7, script=SAV, claims=dict(enumerate(roles)),
                       days_done={1})
        w = World(tuple(roles), (None,) * 7)
        says = {"kind": "good", "seat": 1}
        self.assertEqual(I.savant_truths(says, w, "D1", s=st), {True, False})
        self.assertEqual(I.savant_truths(says, w, "D1", True, st),
                         {True, False})
        # Under a Vortox both false: possible, the Goon may be evil.
        row = savant(1, says, {"kind": "is", "seat": 2, "role": "Monk"})
        self.assertFalse(row.is_true(w, st))


def _payloads():
    from make_fixtures import played
    out = []
    for name, seed, n, nights, must in PLAYED:
        import play_games
        rng = random.Random(seed)
        script = play_games.an_awkward_script(rng, must_have=must)
        out.append(played(name, script, seed, n, nights, rng=rng)["payload"])
    return out


class BothLanguagesAgree(SolverTest):

    def test_on_the_played_games(self):
        import app
        cases = _payloads()
        script = ("import {solveBoard} from './js/api.mjs';"
                  "const ps=JSON.parse(process.argv[1]);"
                  "console.log(JSON.stringify(ps.map(p => {"
                  " const r = solveBoard(p); return r.error || r.valid; })));")
        got = subprocess.run(["node", "--input-type=module", "-e", script,
                              json.dumps(cases)], cwd=ROOT,
                             capture_output=True, text=True, timeout=600)
        self.assertEqual(got.returncode, 0, got.stderr)
        py = []
        for p in cases:
            r = app.run_solve(p)
            py.append(r.get("error") or r["valid"])
        self.assertEqual(json.loads(got.stdout), py)
        self.assertTrue(all(isinstance(v, int) and v > 0 for v in py), py)


if __name__ == "__main__":
    unittest.main()
