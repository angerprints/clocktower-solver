"""The JavaScript enumeration, held against the Python one.

World counts alone would not be enough. Two implementations can produce
the same number of worlds and disagree about which ones — and the second
kind of mistake is the one that survives into a game and misleads
somebody. So each board is digested over its whole sorted world set,
every seat's character and every believer's token, and the digests have
to match.

Also checked: the bag shapes at every table size, the candidate lists a
claim produces, and a timeline laid over a world. Those are where a
divergence would start; the digests are where it would show.

Skipped when Node is not installed.
"""

import hashlib
import json
import pathlib
import shutil
import subprocess
import unittest

from helpers import SolverTest                    # sets up the import path
from botc import scripts                          # noqa: E402
from botc.worlds import (OffScript, Timeline, World, Change,  # noqa: E402
                         _bags, _candidates, iter_worlds)

ROOT = pathlib.Path(__file__).resolve().parent.parent
NODE = shutil.which("node")

TB = scripts.TROUBLE_BREWING
BMR = scripts.BAD_MOON_RISING

TB15 = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
        "FortuneTeller", "Undertaker", "Monk", "Ravenkeeper", "Virgin",
        "Slayer", "Soldier", "Mayor", "Recluse", "Saint"]
BMR15 = ["Grandmother", "Sailor", "Chambermaid", "Exorcist", "Innkeeper",
         "Gambler", "Gossip", "Courtier", "Professor", "Minstrel", "TeaLady",
         "Pacifist", "Fool", "Tinker", "Moonchild"]

EASTER = json.dumps([
    {"id": "_meta", "name": "Easter Trouble"},
    "noble", "washerwoman", "librarian", "clockmaker", "grandmother",
    "slayer", "artist", "empath", "fortuneteller", "monk", "undertaker",
    "ravenkeeper", "virgin", "mayor", "ogre", "saint", "recluse", "drunk",
    "poisoner", "spy", "scarletwoman", "marionette", "baron", "imp"])


def enumerated(n_players, claims, **kw):
    """Count, and a digest that only matches if the sets are the same."""
    lines = []
    try:
        for world in iter_worlds(n_players, claims, **kw):
            lines.append(",".join(
                f"{r}/{b}" if b else r
                for r, b in zip(world.roles, world.believes)))
            if len(lines) >= 600_000:
                break
    except OffScript as exc:
        return {"error": str(exc)}
    lines.sort()
    digest = hashlib.sha256("\n".join(lines).encode()).hexdigest()[:16]
    return {"count": len(lines), "digest": digest}


def python_side():
    sentinel = scripts.from_ids("TB and a Sentinel",
                                list(TB.keys) + ["sentinel"])
    easter = scripts.from_json(EASTER)
    narrow = scripts.from_ids("A narrow script", [
        "washerwoman", "librarian", "investigator", "chef", "empath",
        "recluse", "saint", "poisoner", "spy", "imp"])

    boards = {}

    def add(name, n, claims, **kw):
        boards[name] = enumerated(n, {i: r for i, r in enumerate(claims)}, **kw)

    for n in (5, 6, 7, 8, 9, 10, 12, 15):
        add(f"tb-{n}", n, TB15[:n], script=TB)
    for n in (5, 6, 7, 8, 9, 10, 12):
        add(f"bmr-{n}", n, BMR15[:n], script=BMR)

    add("tb-9-outsider-claims", 9,
        ["Washerwoman", "Librarian", "Butler", "Drunk", "Empath",
         "FortuneTeller", "Undertaker", "Recluse", "Saint"], script=TB)
    add("tb-9-evil-claim", 9,
        ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
         "FortuneTeller", "Undertaker", "Recluse", "Imp"], script=TB)
    add("tb-9-some-unclaimed", 9,
        ["Washerwoman", "", "Investigator", "", "Empath", "", "Undertaker",
         "Recluse", "Saint"], script=TB)
    add("tb-9-off-script", 9,
        ["Grandmother", "Librarian", "Investigator", "Chef", "Empath",
         "FortuneTeller", "Undertaker", "Recluse", "Saint"], script=TB)

    for kind in ("self", "confirmed", "hiding", "unsure"):
        add(f"tb-9-certainty-{kind}", 9, TB15[:9], script=TB,
            certainties={0: kind, 4: kind})

    add("tb-9-good-lies", 9, TB15[:9], script=TB, allow_good_lies=True)

    for said in ("never", "first", "every", "other", "sometimes"):
        add(f"tb-9-wake-{said}", 9,
            ["", "Librarian", "Investigator", "Chef", "Empath",
             "FortuneTeller", "Undertaker", "Recluse", "Saint"],
            script=TB, wakes={0: said})

    add("tb-9-forced", 9, TB15[:9], script=TB,
        forced={2: {"Investigator", "Drunk"}})

    add("tb-9-sentinel", 9, TB15[:9], script=sentinel, fabled=["Sentinel"])
    add("tb-9-sentinel-not-asked", 9, TB15[:9], script=sentinel)

    add("easter-9", 9,
        ["Noble", "Washerwoman", "Clockmaker", "Grandmother", "Artist",
         "Empath", "Monk", "Ogre", "Saint"], script=easter)
    add("easter-12", 12,
        ["Noble", "Washerwoman", "Clockmaker", "Grandmother", "Artist",
         "Empath", "Monk", "Undertaker", "Virgin", "Mayor", "Ogre", "Saint"],
        script=easter)
    sv = scripts.SECTS_AND_VIOLETS
    # A Mutant stands behind any Townsfolk claim, good lies or not, and
    # is not held to what it says about waking.
    add("sv-9", 9, ["Clockmaker", "Dreamer", "Oracle", "Sage", "Juggler", "Klutz", "Barber", "Seamstress", "Sweetheart"], script=sv)
    add("sv-9-wake", 9, ["", "Dreamer", "Oracle", "Sage", "Juggler",
                         "Klutz", "Barber", "Seamstress", "Sweetheart"],
        script=sv, wakes={0: "every"})
    add("narrow-7", 7,
        ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
         "Recluse", "Saint"], script=narrow)

    bag_shapes = {}
    for tag, script, fabled in (("tb", TB, ()), ("bmr", BMR, ()),
                                ("tb-sentinel", sentinel, ("Sentinel",)),
                                ("easter", easter, ())):
        for n in (5, 7, 9, 12, 15):
            bag_shapes[f"{tag}-{n}"] = [
                [sorted(present),
                 [counts[t] for t in
                  ("townsfolk", "outsider", "minion", "demon")]]
                for present, counts in _bags(n, script, fabled)]

    lists = {}
    for tag, claim, kw in (
        ("tb-townsfolk", "Empath", {}),
        ("tb-outsider", "Recluse", {}),
        ("tb-drunk-claim", "Drunk", {}),
        ("tb-evil-claim", "Imp", {}),
        ("tb-unclaimed", None, {}),
        ("tb-good-lies", "Empath", {"allow_good_lies": True}),
        ("tb-self", "Empath", {"certainty": "self"}),
        ("tb-confirmed", "Empath", {"certainty": "confirmed"}),
        ("bmr-townsfolk", "Chambermaid", {"script": BMR}),
        ("bmr-lunatic-bluff", "Grandmother", {"script": BMR}),
        ("sv-townsfolk", "Oracle", {"script": scripts.SECTS_AND_VIOLETS}),
        ("sv-outsider", "Sweetheart", {"script": scripts.SECTS_AND_VIOLETS}),
        ("sv-good-lies", "Oracle", {"script": scripts.SECTS_AND_VIOLETS,
                                    "allow_good_lies": True}),
    ):
        script = kw.pop("script", TB)
        lists[tag] = sorted(
            f"{r}/{b}" if b else r
            for r, b in _candidates(claim, kw.pop("allow_good_lies", False),
                                    kw.pop("certainty", ""), None, None,
                                    script))

    base = World(("Washerwoman", "Librarian", "Investigator", "Chef",
                  "Empath", "FortuneTeller", "Undertaker", "ScarletWoman",
                  "Imp"), (None,) * 9)
    handover = Timeline(base, (Change("D2", 7, "Imp"),))
    timeline = {
        "before: demon": base.demon_at("N2"),
        "after: demon at N2": handover.demon_at("N2"),
        "after: demon at N3": handover.demon_at("N3"),
        "after: seat 8 at N2": handover.role_at(7, "N2"),
        "after: seat 8 at N3": handover.role_at(7, "N3"),
        "after: seat 8 evil at N1": handover.evil_at(7, "N1"),
        "after: find Imp at N2": handover.find_at("Imp", "N2"),
        "after: find Imp at N3": handover.find_at("Imp", "N3"),
        "after: team of seat 8 at N3": handover.team_at(7, "N3"),
    }

    return {"boards": boards, "bagShapes": bag_shapes,
            "candidateLists": lists, "timeline": timeline}


@unittest.skipUnless(NODE, "Node is not installed")
class TheEnumerationAgrees(SolverTest):

    @classmethod
    def setUpClass(cls):
        got = subprocess.run([NODE, str(ROOT / "js" / "dump_worlds.mjs")],
                             capture_output=True, text=True, timeout=600)
        if got.returncode:
            raise AssertionError(f"js/dump_worlds.mjs failed:\n{got.stderr}")
        cls.js = json.loads(got.stdout)
        cls.py = python_side()

    def test_the_same_boards_were_tried(self):
        self.assertEqual(sorted(self.js["boards"]), sorted(self.py["boards"]))

    def test_every_board_produces_the_same_worlds(self):
        """Not merely the same number of them. The digest covers each
        seat's character and each believer's token, so it only matches if
        the two sets are identical."""
        for name, theirs in self.py["boards"].items():
            with self.subTest(board=name):
                self.assertEqual(self.js["boards"][name], theirs)

    def test_nothing_was_truncated(self):
        """A capped run would depend on the order worlds came out in, and
        the digest is meant to depend only on which worlds there are."""
        for name, got in self.py["boards"].items():
            with self.subTest(board=name):
                self.assertLess(got.get("count", 0), 600_000)

    def test_an_off_script_claim_is_refused_the_same_way(self):
        got = self.js["boards"]["tb-9-off-script"]
        self.assertIn("error", got)
        self.assertEqual(got["error"],
                         self.py["boards"]["tb-9-off-script"]["error"])

    def test_the_bag_shapes_match(self):
        for name, theirs in self.py["bagShapes"].items():
            with self.subTest(bag=name):
                self.assertEqual(self.js["bagShapes"][name], theirs)

    def test_every_bag_still_seats_the_table(self):
        for name, shapes in self.py["bagShapes"].items():
            n = int(name.rsplit("-", 1)[1])
            for _present, counts in shapes:
                with self.subTest(bag=name):
                    self.assertEqual(sum(counts), n)

    def test_the_candidate_lists_match(self):
        for name, theirs in self.py["candidateLists"].items():
            with self.subTest(claim=name):
                self.assertEqual(self.js["candidateLists"][name], theirs)

    def test_a_timeline_over_a_world_matches(self):
        self.assertEqual(self.js["timeline"], self.py["timeline"])


if __name__ == "__main__":
    unittest.main()
