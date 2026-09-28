"""The registry machinery, held against the Python original.

The *character* rules live in the solver, which is the next phase, so at
this point the registries are empty. What can be checked now is the
machinery they feed: whether an impairment plan finds the same cheapest
arrangement, and whether a night's deaths get the same accounts.

So both implementations register the same made-up rules — a poisoner that
reaches the living, a soldier that cannot be demon-killed, a monk that
guards somebody else, a gossip that need not fire, an assassin nothing
stops, a grandmother whose grandchild drags her along — and the answers
are compared. Made up, but shaped exactly like the real ones, and between
them they reach every branch: capacity, per-seat pricing, repeats, free
and unavoidable sources, aimed and always-on shields, must-fire causes,
implied deaths, and a cause no shield touches.

Registering into the real registries would leave them dirty for every
test that ran afterwards, so this swaps them out and puts them back.

Skipped when Node is not installed.
"""

import contextlib
import json
import pathlib
import shutil
import subprocess
import unittest

from helpers import SolverTest                    # sets up the import path
from botc import deaths as D, scripts             # noqa: E402
from botc.impairment import Source, plan_night     # noqa: E402
from botc.info import GameState                    # noqa: E402
from botc.worlds import World                      # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
NODE = shutil.which("node")

TB = scripts.TROUBLE_BREWING
TB9 = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
       "FortuneTeller", "Undertaker", "Recluse", "Saint"]

WORLD = World(("Washerwoman", "Librarian", "Soldier", "Monk", "Empath",
               "Gossip", "Undertaker", "Poisoner", "Imp"), (None,) * 9)


class Row:
    """A stand-in for a Grandmother reading."""

    def __init__(self, player, target, night=1):
        self.source_role = "Grandmother"
        self.player = player
        self.target = target
        self.night = night


@contextlib.contextmanager
def only_these_rules():
    """Swap the registries out, and put them back afterwards."""
    saved = (list(D.CAUSE_RULES), list(D.IMMUNITY_RULES),
             list(D.IMPLICATION_RULES))
    D.CAUSE_RULES.clear()
    D.IMMUNITY_RULES.clear()
    D.IMPLICATION_RULES.clear()
    try:
        yield
    finally:
        for holder, was in zip((D.CAUSE_RULES, D.IMMUNITY_RULES,
                                D.IMPLICATION_RULES), saved):
            holder.clear()
            holder.extend(was)


def register():
    @D.cause_rule
    def the_demon_kills(w, s, night):
        if night < 2:
            return []
        return [D.Cause("Demon", D.DEMON, s.alive_set(f"N{night}"),
                        capacity=1, must_fire=True)]

    @D.cause_rule
    def a_gossip_may_kill(w, s, night):
        if w.find("Gossip") is None or night < 2:
            return []
        return [D.Cause("Gossip", D.OTHER, frozenset(range(9)),
                        capacity=1, cost=0.4)]

    @D.cause_rule
    def an_assassin_kills_through_anything(w, s, night):
        if "Assassin" not in s.script.keys or night < 3:
            return []
        return [D.Cause("Assassin", D.OTHER, frozenset(range(9)),
                        capacity=1, cost=0.25, unstoppable=True)]

    @D.immunity_rule
    def the_soldier_cannot_be_demon_killed(w, s, night, seat, kind):
        if kind != D.DEMON:
            return []
        if w.role_at(seat, f"N{night}") != "Soldier":
            return []
        return [D.Shield("Soldier", needs=seat)]

    @D.immunity_rule
    def the_monk_guards_against_the_demon(w, s, night, seat, kind):
        if kind != D.DEMON or night < 2:
            return []
        monk = w.find_at("Monk", f"N{night}")
        if monk is None or monk == seat:
            return []
        return [D.Shield("Monk", needs=monk, chosen=True)]

    @D.immunity_rule
    def the_dead_cannot_die_again(w, s, night, seat, kind):
        if seat in s.alive_set(f"N{night}"):
            return []
        return [D.Shield("already dead", cost=0.45)]

    @D.implication_rule
    def a_grandmother_grieves(w, s, night, victim, kind):
        if kind != D.DEMON:
            return []
        for info in s.infos:
            if getattr(info, "source_role", None) == "Grandmother" \
                    and info.target == victim:
                return [D.Implication(seat=info.player, needs=info.player)]
        return []


SOURCES = {
    "believer": Source("believer", frozenset({3}), capacity=1),
    "poisoner": Source("Poisoner", frozenset({0, 1, 2, 3, 4}), capacity=1,
                       cost=0.35, repeat_cost=0.7),
    "sailor": Source("Sailor", frozenset({1, 5}), capacity=1,
                     cost=lambda seat: 0.5 if seat == 1 else 0.15),
    "innkeeper": Source("Innkeeper", frozenset({6, 7}), capacity=2, cost=0.5),
    "courtier": Source("Courtier", frozenset({8}), capacity=1, cost=1.0),
}


def python_side():
    plans = {}

    def try_plan(name, use, required, forbidden, previous=None):
        got = plan_night([SOURCES[k] for k in use], required, forbidden,
                         previous or {})
        plans[name] = None if got is None else {
            "cost": round(got[0], 9), "hits": got[1]}

    try_plan("nothing needed", ["poisoner"], [], [])
    try_plan("one seat, one source", ["poisoner"], [0], [])
    try_plan("one seat, out of reach", ["poisoner"], [7], [])
    try_plan("one seat, repeated", ["poisoner"], [0], [], {"Poisoner": 0})
    try_plan("one seat, a different one", ["poisoner"], [0], [],
             {"Poisoner": 1})
    try_plan("free source covers it", ["believer", "poisoner"], [3], [])
    try_plan("free source reaches a forbidden seat", ["believer"], [], [3])
    try_plan("required and forbidden at once", ["poisoner"], [0], [0])
    try_plan("two seats, two sources", ["poisoner", "sailor"], [0, 5], [])
    try_plan("two seats, one source", ["poisoner"], [0, 1], [])
    try_plan("two seats, one source with room", ["innkeeper"], [6, 7], [])
    try_plan("the cheaper arrangement wins", ["poisoner", "sailor"], [1], [])
    try_plan("price depends on the seat", ["sailor"], [5], [])
    try_plan("price depends on the seat, the other one", ["sailor"], [1], [])
    try_plan("three seats, three sources",
             ["poisoner", "sailor", "innkeeper"], [0, 5, 6], [])
    try_plan("three seats, not enough reach",
             ["poisoner", "sailor"], [0, 5, 8], [])
    try_plan("a forbidden seat blocks an arrangement",
             ["poisoner", "sailor"], [1], [0])
    try_plan("a free source that costs nothing to use", ["courtier"], [8], [])

    def board(**kw):
        return GameState(n_players=9, script=TB,
                         claims={i: r for i, r in enumerate(TB9)}, **kw)

    def rounded(accounts):
        return [{"cost": round(c, 9), "impaired": sorted(imp),
                 "working": sorted(wk),
                 "earlier": {str(n): sorted(v) for n, v in before.items()}}
                for c, imp, wk, before in accounts]

    nights = {}

    def try_night(name, night, died, **kw):
        nights[name] = rounded(
            D.explain_night(WORLD, board(**kw), night, set(died)))

    try_night("nobody died on night one", 1, [])
    try_night("one body", 2, [0])
    try_night("the Soldier died", 2, [2])
    try_night("the Monk died", 2, [3])
    try_night("a quiet night", 2, [])
    try_night("two bodies", 2, [0, 1])
    try_night("three bodies", 2, [0, 1, 4])
    try_night("a body already dead", 3, [0], deaths={0: "N2"})
    try_night("a quiet night with somebody already gone", 3, [],
              deaths={0: "N2"})

    granny = {"infos": [Row(player=4, target=1)]}
    try_night("the grandchild alone", 2, [1], **granny)
    try_night("the grandchild and the grandmother", 2, [1, 4], **granny)
    try_night("the grandmother alone", 2, [4], **granny)

    with_assassin = scripts.from_ids("TB and an Assassin",
                                     list(TB.keys) + ["assassin"])
    assassin_board = GameState(n_players=9, script=with_assassin,
                               claims={i: r for i, r in enumerate(TB9)})
    nights["the Soldier died with an Assassin about"] = rounded(
        D.explain_night(WORLD, assassin_board, 3, {2}))

    registry = {
        "causes": [f.__name__ for f in D.CAUSE_RULES],
        "shields": [f.__name__ for f in D.IMMUNITY_RULES],
        "implications": [f.__name__ for f in D.IMPLICATION_RULES],
        "shieldsOnASoldier": [
            [s.by, s.needs, s.cost, s.chosen]
            for s in D.shields_on(WORLD, board(), 2, 2, D.DEMON)],
        "shieldsOnSomebodyElse": [
            [s.by, s.needs, s.cost, s.chosen]
            for s in D.shields_on(WORLD, board(), 2, 0, D.DEMON)],
        "shieldsAgainstOther": [
            [s.by, s.needs, s.cost, s.chosen]
            for s in D.shields_on(WORLD, board(), 2, 2, D.OTHER)],
    }

    return {"plans": plans, "nights": nights, "registry": registry}


@unittest.skipUnless(NODE, "Node is not installed")
class TheRegistriesAgree(SolverTest):

    @classmethod
    def setUpClass(cls):
        got = subprocess.run([NODE, str(ROOT / "js" / "dump_rules.mjs")],
                             capture_output=True, text=True, timeout=300)
        if got.returncode:
            raise AssertionError(f"js/dump_rules.mjs failed:\n{got.stderr}")
        cls.js = json.loads(got.stdout)
        with only_these_rules():
            register()
            cls.py = python_side()

    def test_the_same_plans_were_tried(self):
        self.assertEqual(sorted(self.js["plans"]), sorted(self.py["plans"]))

    def test_every_impairment_plan_matches(self):
        for name, theirs in self.py["plans"].items():
            with self.subTest(plan=name):
                self.assertEqual(self.js["plans"][name], theirs)

    def test_the_plans_cover_both_outcomes(self):
        """Half the value is in the arrangements that cannot be made. If
        they all succeeded, a version that never returned nothing would
        pass."""
        impossible = [n for n, got in self.py["plans"].items() if got is None]
        self.assertGreaterEqual(len(impossible), 4)
        self.assertGreaterEqual(
            len(self.py["plans"]) - len(impossible), 10)

    def test_every_nights_accounting_matches(self):
        for name, theirs in self.py["nights"].items():
            with self.subTest(night=name):
                self.assertEqual(self.js["nights"][name], theirs)

    def test_the_nights_cover_the_awkward_shapes(self):
        """A quiet night, more bodies than causes, a body that followed
        from another, and a kill nothing could stop."""
        self.assertEqual(self.py["nights"]["nobody died on night one"],
                         [{"cost": 1.0, "impaired": [], "working": [],
                           "earlier": {}}])
        self.assertTrue(self.py["nights"]["a quiet night"],
                        "something has to have stopped the Demon")
        self.assertEqual(self.py["nights"]["three bodies"], [],
                         "two causes cannot leave three bodies")
        self.assertTrue(self.py["nights"]["the grandchild and the grandmother"],
                        "one kill, two bodies")

    def test_the_registries_hold_the_same_rules_in_the_same_order(self):
        """Order matters — the accounts come out in the order the rules
        offered them, and the comparisons above are order-sensitive.

        Compared as snake_case against camelCase rather than verbatim:
        each language spells its function names its own way, and holding
        one to the other's convention would be comparing spelling rather
        than behaviour.
        """
        def same(js_name):
            out, previous_lower = "", False
            for ch in js_name:
                if ch.isupper() and previous_lower:
                    out += "_"
                out += ch.lower()
                previous_lower = ch.islower() or ch.isdigit()
            return out

        for kind in ("causes", "shields", "implications"):
            with self.subTest(registry=kind):
                self.assertEqual([same(n) for n in self.js["registry"][kind]],
                                 self.py["registry"][kind])

    def test_the_shields_offered_match(self):
        for key in ("shieldsOnASoldier", "shieldsOnSomebodyElse",
                    "shieldsAgainstOther"):
            with self.subTest(shields=key):
                self.assertEqual(self.js["registry"][key],
                                 self.py["registry"][key])


if __name__ == "__main__":
    unittest.main()
