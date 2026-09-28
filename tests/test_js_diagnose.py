"""The JavaScript diagnosis, held against the Python one.

When a board survives no world, saying so and stopping is nearly useless
mid-game — the useful answer is which entry to look at again. Python has
done that for a while; this checks the JavaScript reaches the same
verdict, entry for entry.

Three things get compared: the shortlist of removable entries, the
"claims cannot fill the bag" sentence, and the characters raised when no
single entry accounts for it. Plus the refusals, which are the other half
of the same idea — a script the solver will not attempt at all.

Skipped when Node is not installed.
"""

import json
import pathlib
import shutil
import subprocess
import unittest

from helpers import SolverTest                    # sets up the import path
import app                                        # noqa: E402
from botc import limits, scripts                  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
NODE = shutil.which("node")

TB9 = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
       "FortuneTeller", "Undertaker", "Recluse", "Saint"]
TB12 = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
        "FortuneTeller", "Undertaker", "Monk", "Ravenkeeper", "Virgin",
        "Slayer", "Soldier"]

# Boards that survive no world, each for a different reason.
BOARDS = {
    "twelve Townsfolk claims": {
        "n_players": 12, "infos": [],
        "players": [{"claim": c, "events": []} for c in TB12],
    },
    "a shot at a confirmed seat": {
        "n_players": 9,
        "players": [{"claim": c, "events": (["D2"] if i == 0 else []),
                     "certainty": ("confirmed" if i < 2 else "")}
                    for i, c in enumerate(TB9)],
        "infos": [{"type": "SlayerShot", "night": 2, "player": 4,
                   "target": 0, "died": True}],
    },
    # Two readings from different seats that cannot both hold, with
    # everybody else vouched for so no poisoning can excuse either. The
    # first attempt at this used two Chef readings from one seat, which
    # the input checking refuses before the diagnosis ever runs — a board
    # has to be *contradictory* rather than *malformed* to be worth
    # diagnosing.
    "two readings that cannot both hold": {
        "n_players": 9,
        # Every seat vouched for, which is what makes it unfixable: with
        # nobody left to be the Poisoner, neither reading can be excused.
        # Leaving two seats open let the solver excuse one and six worlds
        # survived — a board has to be *contradictory* rather than merely
        # awkward to be worth diagnosing.
        "players": [{"claim": c, "events": [], "certainty": "confirmed"}
                    for c in TB9],
        "infos": [{"type": "Chef", "night": 1, "player": 3, "count": 0},
                  {"type": "Empath", "night": 1, "player": 4, "count": 2}],
    },
}


def js(payloads):
    script = """
    const api = await import("./js/api.mjs");
    const {refuses} = await import("./js/limits.mjs");
    const scr = await import("./js/scripts.mjs");
    const boards = %s;
    const out = {solved: {}, refusals: {}};
    for (const [name, payload] of Object.entries(boards)) {
      const r = api.solveBoard(payload);
      out.solved[name] = {valid: r.valid, error: r.error || null,
                          diagnosis: r.diagnosis || null};
    }
    for (const extra of ["legion", "riot", "atheist"]) {
      const s = scr.fromIds("x", [...scr.TROUBLE_BREWING.keys, extra]);
      out.refusals[extra] = Object.keys(refuses(s));
    }
    console.log(JSON.stringify(out));
    """ % json.dumps(payloads)
    got = subprocess.run([NODE, "--input-type=module", "-e", script],
                         capture_output=True, text=True, timeout=900,
                         cwd=str(ROOT))
    if got.returncode:
        raise AssertionError(got.stderr)
    return json.loads(got.stdout.strip().splitlines()[-1])


@unittest.skipUnless(NODE, "Node is not installed")
class TheDiagnosisAgrees(SolverTest):

    @classmethod
    def setUpClass(cls):
        cls.js = js(BOARDS)
        cls.py = {name: app.run_solve(json.loads(json.dumps(payload)))
                  for name, payload in BOARDS.items()}

    def test_the_boards_really_do_fit_nothing(self):
        """Otherwise there is no diagnosis to compare and the whole file
        passes on empty."""
        for name, got in self.py.items():
            with self.subTest(board=name):
                self.assertEqual(got["valid"], 0)
                self.assertIn("diagnosis", got)

    def test_the_same_entries_are_named(self):
        for name in BOARDS:
            with self.subTest(board=name):
                mine = self.js["solved"][name]["diagnosis"]["culprits"]
                theirs = self.py[name]["diagnosis"]["culprits"]
                self.assertEqual(
                    sorted((c["kind"], c["label"]) for c in mine),
                    sorted((c["kind"], c["label"]) for c in theirs))

    def test_the_search_finished_on_both_sides(self):
        for name in BOARDS:
            with self.subTest(board=name):
                self.assertEqual(
                    self.js["solved"][name]["diagnosis"]["complete"],
                    self.py[name]["diagnosis"]["complete"])

    def test_an_unfillable_bag_is_explained_the_same_way(self):
        name = "twelve Townsfolk claims"
        mine = self.js["solved"][name]["diagnosis"].get("bag")
        theirs = self.py[name]["diagnosis"].get("bag")
        self.assertIsNotNone(theirs)
        self.assertEqual(mine, theirs)

    def test_between_them_the_boards_cover_both_shapes(self):
        """One board where an entry is to blame, one where the claims
        are. A file testing only one shape would miss half of it."""
        blamed = any(self.py[n]["diagnosis"]["culprits"] for n in BOARDS)
        bagged = any(self.py[n]["diagnosis"].get("bag") for n in BOARDS)
        self.assertTrue(blamed)
        self.assertTrue(bagged)


@unittest.skipUnless(NODE, "Node is not installed")
class TheRefusalsAgree(SolverTest):

    @classmethod
    def setUpClass(cls):
        cls.js = js({})["refusals"]

    def test_the_teams_breakers_are_refused_on_both_sides(self):
        for extra in ("legion", "riot"):
            with self.subTest(character=extra):
                script = scripts.from_ids(
                    "x", list(scripts.TROUBLE_BREWING.keys) + [extra])
                self.assertEqual(sorted(self.js[extra]),
                                 sorted(limits.refuses(script)))
                self.assertTrue(self.js[extra], "it has to refuse something")

    def test_the_bag_breaker_is_raised_rather_than_refused(self):
        """An Atheist game is unsolvable, but it has a signature — a
        board that fits nothing — so it is worth naming when that
        happens rather than refusing every board on the script."""
        script = scripts.from_ids(
            "x", list(scripts.TROUBLE_BREWING.keys) + ["atheist"])
        self.assertEqual(self.js["atheist"], [])
        self.assertEqual(list(limits.refuses(script)), [])
        self.assertEqual(list(limits.could_explain_nothing_fitting(script)),
                         ["Atheist"])

    def test_the_wording_is_generated_rather_than_copied(self):
        """The entries are what somebody reads when their script is
        refused, so two hand-written copies would drift."""
        import tools.gen_limits as gen
        before = (ROOT / "js" / "limits.mjs").read_text()
        gen.build()
        self.assertEqual(before, (ROOT / "js" / "limits.mjs").read_text(),
                         "js/limits.mjs is stale — "
                         "run python tools/gen_limits.py")


if __name__ == "__main__":
    unittest.main()
