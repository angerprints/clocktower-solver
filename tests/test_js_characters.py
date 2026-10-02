"""Every character rule, held against the Python original.

There are thirty-two of them and each is a few lines, so spot-checking a
handful would leave most of the port unexamined. Instead each board is
walked world by world and night by night, and everything the rules say —
which causes were offered, which shields, which sources, what each
reaches and what it costs — is folded into one digest per board.

A digest matches only if the two agreed about every rule in every world.
It says nothing about *where* a difference is, so a per-rule tally sits
beside it to narrow a failure down, and a separate test insists every
kind of rule actually fired somewhere.

Skipped when Node is not installed.
"""

import hashlib
import json
import pathlib
import shutil
import subprocess
import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                            # noqa: E402
from botc import deaths as D, impairment, scripts  # noqa: E402
from botc.info import GameState                    # noqa: E402
from botc.worlds import iter_worlds                # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
NODE = shutil.which("node")

TB = scripts.TROUBLE_BREWING
BMR = scripts.BAD_MOON_RISING

TB9 = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
       "FortuneTeller", "Undertaker", "Recluse", "Saint"]
TB12 = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
        "FortuneTeller", "Undertaker", "Monk", "Ravenkeeper", "Slayer",
        "Soldier", "Saint"]
BMR9 = ["Grandmother", "Sailor", "Chambermaid", "Exorcist", "Innkeeper",
        "Gambler", "Gossip", "Tinker", "Moonchild"]
BMR9B = ["Courtier", "Professor", "Minstrel", "TeaLady", "Pacifist", "Fool",
         "Sailor", "Goon", "Lunatic"]

KINDS = {"GamblerGuess", "GrandmotherInfo", "CourtierChoice"}


def make_info(row):
    from botc import info as I
    kind = getattr(I, row["type"])
    return kind(**{k: v for k, v in row.items() if k != "type"})


def sorted_nums(xs):
    return sorted(xs)


def describe(world, state, nights):
    """Everything the rules say about one world, as text."""
    lines = []
    for night in nights:
        for c in D.causes_on(world, state, night):
            lines.append(
                f"cause {night} {c.name} {c.kind} {c.capacity} "
                f"{c.cost:.6f} {str(c.must_fire).lower()} "
                f"{str(c.unstoppable).lower()} "
                f"{'null' if c.victim_impaired_at is None else c.victim_impaired_at} "
                f"[{','.join(str(x) for x in sorted_nums(c.seats))}]")
        for s in impairment.sources_on(world, state, night):
            prices = ",".join(
                f"{seat}:{s.price(seat):.6f}/{s.price(seat, True):.6f}"
                for seat in sorted_nums(s.seats))
            lines.append(f"source {night} {s.name} {s.capacity} [{prices}]")
        for seat in range(state.n_players):
            for kind in (D.DEMON, D.OTHER):
                for sh in D.shields_on(world, state, night, seat, kind):
                    lines.append(
                        f"shield {night} {seat} {kind} {sh.by} "
                        f"{'null' if sh.needs is None else sh.needs} "
                        f"{sh.cost:.6f} {str(sh.chosen).lower()}")
                for hit in D.implications_of(world, state, night, seat, kind):
                    lines.append(f"implies {night} {seat} {kind} "
                                 f"{hit.seat} {hit.needs}")
            for day in nights:
                for who in S.survivals_of(world, state, day, seat):
                    lines.append(f"survives {day} {seat} {who}")
    return lines


def python_side():
    boards = {}

    def run(name, script, claims, opts=None, nights=(1, 2, 3, 4)):
        opts = dict(opts or {})
        opts["infos"] = [make_info(r) for r in opts.get("infos", [])]
        state = GameState(n_players=len(claims), script=script,
                          claims={i: r for i, r in enumerate(claims)}, **opts)
        digest = hashlib.sha256()
        tally = {}
        worlds = 0
        for world in iter_worlds(len(claims), state.claims, script=script):
            worlds += 1
            lines = describe(world, state, nights)
            digest.update("\n".join(lines).encode())
            digest.update(b"\x00")
            for line in lines:
                bits = line.split(" ")
                key = f"{bits[0]} {bits[2] if len(bits) > 2 else ''}"
                tally[key] = tally.get(key, 0) + 1
            if worlds >= 4000:
                break
        boards[name] = {"worlds": worlds,
                        "digest": digest.hexdigest()[:16], "tally": tally}

    run("tb-9-bare", TB, TB9)
    run("tb-9-a-death", TB, TB9, {"deaths": {2: "N2"}})
    run("tb-9-quiet", TB, TB9, {"quiet_nights": {2}})
    run("tb-9-execution", TB, TB9, {"deaths": {7: "E1"}})
    run("tb-12-protectors", TB, TB12, {"deaths": {2: "N2"}})
    run("tb-12-two-deaths", TB, TB12, {"deaths": {2: "N2", 4: "N3"}})

    run("bmr-9-bare", BMR, BMR9)
    run("bmr-9-a-death", BMR, BMR9, {"deaths": {2: "N2"}})
    run("bmr-9-day-death", BMR, BMR9, {"deaths": {7: "D2"}})
    run("bmr-9-execution", BMR, BMR9, {"deaths": {7: "E2"}})
    run("bmr-9-moonchild-gone", BMR, BMR9, {"deaths": {8: "N2"}})
    run("bmr-9-gambler-guessed", BMR, BMR9, {
        "infos": [{"type": "GamblerGuess", "night": 2, "player": 5,
                   "target": 2, "role": "Chambermaid"}]})
    run("bmr-9-grandmother", BMR, BMR9, {
        "deaths": {2: "N2"},
        "infos": [{"type": "GrandmotherInfo", "night": 1, "player": 0,
                   "target": 2, "role": "Chambermaid"}]})

    run("bmr-9b-bare", BMR, BMR9B)
    run("bmr-9b-courtier", BMR, BMR9B, {
        "infos": [{"type": "CourtierChoice", "night": 1, "player": 0,
                   "role": "Chambermaid"}]})
    run("bmr-9b-minion-executed", BMR, BMR9B, {"deaths": {7: "E1"}})
    run("bmr-9b-survived-execution", BMR, BMR9B, {"executions": {1: 6}})
    run("bmr-9b-a-death", BMR, BMR9B, {"deaths": {3: "N2"}})

    # Two boards aimed at rules the ones above never reach. The Godfather
    # is claimed outright, which pins it to a seat in every world —
    # otherwise it sits past the four-thousand-world cap and the rule
    # looks untested. And the Courtier names a character somebody
    # actually holds, since naming one nobody holds correctly does
    # nothing at all.
    run("bmr-9-godfather-claimed", BMR,
        ["Grandmother", "Sailor", "Chambermaid", "Exorcist", "Innkeeper",
         "Gambler", "Godfather", "Tinker", "Moonchild"],
        {"deaths": {7: "D2"}})
    run("bmr-9b-courtier-lands", BMR, BMR9B, {
        "infos": [{"type": "CourtierChoice", "night": 1, "player": 0,
                   "role": "Sailor"}]})
    # And a Minion that owns up and hangs. The Minstrel sings only when
    # the one executed *died* and was a Minion, and on the boards above
    # the first four thousand worlds never put a Minion in that seat.
    run("bmr-9b-assassin-hanged", BMR,
        BMR9B[:6] + ["Assassin"] + BMR9B[7:], {"deaths": {6: "E1"}})

    registry = {
        "causes": [f.__name__ for f in D.CAUSE_RULES],
        "shields": [f.__name__ for f in D.IMMUNITY_RULES],
        "implications": [f.__name__ for f in D.IMPLICATION_RULES],
        "sources": [f.__name__ for f in impairment.SOURCE_RULES],
        "survivals": [f.__name__ for f in S.SURVIVES_EXECUTION_RULES],
    }
    return {"boards": boards, "registry": registry}


def squashed(name):
    """A name with its shape removed, so two conventions can be compared.

    Not snake_case, because that cannot be recovered from camelCase: "on
    a quiet day" and "on aquiet day" are both `onAQuietDay`, and any
    converter has to guess. Dropping the separators entirely compares the
    letters, which is what actually has to match.
    """
    return name.replace("_", "").lower()


@unittest.skipUnless(NODE, "Node is not installed")
class TheCharacterRulesAgree(SolverTest):

    @classmethod
    def setUpClass(cls):
        got = subprocess.run(
            [NODE, str(ROOT / "js" / "dump_characters.mjs")],
            capture_output=True, text=True, timeout=900)
        if got.returncode:
            raise AssertionError(
                f"js/dump_characters.mjs failed:\n{got.stderr}")
        cls.js = json.loads(got.stdout)
        cls.py = python_side()

    def test_the_same_boards_were_tried(self):
        self.assertEqual(sorted(self.js["boards"]), sorted(self.py["boards"]))

    def test_every_board_agrees_rule_for_rule_in_every_world(self):
        for name, theirs in self.py["boards"].items():
            with self.subTest(board=name):
                mine = self.js["boards"][name]
                self.assertEqual(mine["worlds"], theirs["worlds"])
                # The tally first: it says which kind of rule diverged,
                # which the digest cannot.
                self.assertEqual(mine["tally"], theirs["tally"])
                self.assertEqual(mine["digest"], theirs["digest"])

    def test_every_registry_holds_the_same_rules_in_order(self):
        for kind, theirs in self.py["registry"].items():
            with self.subTest(registry=kind):
                self.assertEqual(
                    [squashed(n) for n in self.js["registry"][kind]],
                    [squashed(n) for n in theirs])

    def test_every_rule_is_registered_on_both_sides(self):
        """A count rather than a list, so adding a character fails here
        and has to be looked at — but counted from Python rather than
        written down, so the two are held to each other rather than to a
        number somebody has to remember to bump."""
        mine = {k: len(v) for k, v in self.js["registry"].items()}
        theirs = {k: len(v) for k, v in self.py["registry"].items()}
        self.assertEqual(mine, theirs)
        self.assertGreater(sum(theirs.values()), 30)

    def test_every_kind_of_rule_fired_somewhere(self):
        """A rule that never fires would agree trivially. This does not
        prove each of the thirty-two fired, but it does prove no whole
        category was silently missing from the boards chosen."""
        seen = set()
        for got in self.py["boards"].values():
            for key in got["tally"]:
                seen.add(key.split(" ")[0])
        self.assertEqual(seen, {"cause", "source", "shield", "implies",
                                "survives"})

    def test_the_boards_between_them_offer_every_named_cause(self):
        named = set()
        for got in self.py["boards"].values():
            for key, count in got["tally"].items():
                if key.startswith("cause ") and count:
                    named.add(key.split(" ", 1)[1])
        for cause in ("Demon", "Gossip", "Tinker", "Assassin", "Gambler",
                      "Moonchild", "Godfather"):
            with self.subTest(cause=cause):
                self.assertIn(cause, named)

    def test_the_boards_between_them_offer_every_named_source(self):
        named = set()
        for got in self.py["boards"].values():
            for key, count in got["tally"].items():
                if key.startswith("source ") and count:
                    named.add(key.split(" ", 1)[1])
        for source in ("believer", "Poisoner", "Sailor", "Goon", "Courtier",
                       "Minstrel", "Innkeeper"):
            with self.subTest(source=source):
                self.assertIn(source, named)


if __name__ == "__main__":
    unittest.main()
