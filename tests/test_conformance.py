"""The corpus, checked against the implementation that produced it.

`tests/fixtures/conformance.json` is a set of boards paired with the
answers this solver gives. It exists because the solver is being written
a second time in JavaScript, so a phone can run it without a laptop in
the room — and a port that is ninety-eight percent right is worse than no
port, because it looks like it works.

So the corpus is the contract. JavaScript will be held to it, and this
file holds Python to it too: while the port is being written, the
reference must not quietly drift underneath it. A deliberate change to
the solver means regenerating the corpus and reading the diff, which is
exactly the moment to notice you changed more than you meant to.

    python tests/make_fixtures.py     # regenerate, then read the diff
"""

import json
import pathlib
import unittest

from helpers import SolverTest                    # sets up the import path
import app                                        # noqa: E402

CORPUS = pathlib.Path(__file__).resolve().parent / "fixtures" / \
    "conformance.json"


def corpus():
    return json.loads(CORPUS.read_text())


class TheCorpusIsUsable(SolverTest):
    """Things that have to be true of the corpus itself, before it is
    worth checking anything against."""

    def setUp(self):
        self.data = corpus()

    def test_it_exists_and_has_a_useful_spread(self):
        self.assertGreater(len(self.data["cases"]), 60)

    def test_every_case_is_named_and_named_once(self):
        names = [c["name"] for c in self.data["cases"]]
        self.assertEqual(len(names), len(set(names)))

    def test_nothing_in_it_was_sampled(self):
        """A sampled answer depends on a random walk, so it could never
        be reproduced by another implementation. If one gets in, the
        corpus stops being a contract and starts being a coin toss."""
        for case in self.data["cases"]:
            with self.subTest(case=case["name"]):
                self.assertFalse(case["expect"].get("sampled"))

    def test_it_covers_both_published_scripts_and_others(self):
        names = {c["payload"]["script"]["name"] for c in self.data["cases"]}
        self.assertIn("Trouble Brewing", names)
        self.assertIn("Bad Moon Rising", names)
        self.assertGreater(len(names), 10, "custom scripts too")

    def test_it_covers_the_awkward_answers_as_well_as_the_ordinary(self):
        kinds = {"solved": 0, "no worlds": 0, "refused": 0}
        for case in self.data["cases"]:
            got = case["expect"]
            if "error" in got:
                kinds["refused"] += 1
            elif not got["valid"]:
                kinds["no worlds"] += 1
            else:
                kinds["solved"] += 1
        for kind, count in kinds.items():
            with self.subTest(kind=kind):
                self.assertGreater(count, 2, f"only {count} {kind}")

    def test_it_covers_every_kind_of_reading(self):
        seen = {row["type"] for case in self.data["cases"]
                for row in case["payload"].get("infos", [])}
        for kind in ("Washerwoman", "Librarian", "Investigator", "Chef",
                     "Empath", "FortuneTeller", "Undertaker", "Ravenkeeper",
                     "SlayerShot", "VirginNomination", "GrandmotherInfo",
                     "ChambermaidInfo", "GamblerGuess", "CourtierChoice"):
            with self.subTest(reading=kind):
                self.assertIn(kind, seen)

    def test_it_covers_the_things_a_board_can_record(self):
        payloads = [c["payload"] for c in self.data["cases"]]
        events = [e for p in payloads for s in p["players"]
                  for e in s.get("events", [])]
        self.assertTrue(any(e[0] == "N" for e in events), "night deaths")
        self.assertTrue(any(e[0] == "X" for e in events), "executions")
        self.assertTrue(any(e[0] == "S" for e in events), "survived one")
        self.assertTrue(any(e[0] == "R" for e in events), "raised")
        self.assertTrue(any(p.get("quiet_nights") for p in payloads))
        self.assertTrue(any(p.get("fabled") for p in payloads))
        self.assertTrue(any(s.get("certainty") for p in payloads
                            for s in p["players"]))
        self.assertTrue(any(s.get("read") for p in payloads
                            for s in p["players"]))
        self.assertTrue(any(s.get("wake") for p in payloads
                            for s in p["players"]))


class PythonStillAgreesWithIt(SolverTest):
    """The reference held to its own record."""

    @classmethod
    def setUpClass(cls):
        cls.data = corpus()
        cls.tol = 10 ** -cls.data["places"] * 1.5

    def test_every_board_gives_the_answer_it_gave_before(self):
        for case in self.data["cases"]:
            with self.subTest(case=case["name"]):
                got = app.run_solve(json.loads(json.dumps(case["payload"])))
                want = case["expect"]

                if "error" in want:
                    self.assertIn("error", got)
                    self.assertEqual(got["error"], want["error"])
                    continue

                self.assertNotIn("error", got)
                self.assertEqual(got["valid"], want["valid"])
                self.assertEqual(got["sampled"], want["sampled"])
                self.assertEqual(len(got["rows"]), len(want["rows"]))
                for i, (mine, theirs) in enumerate(zip(got["rows"],
                                                       want["rows"])):
                    for key, value in theirs.items():
                        self.assertAlmostEqual(
                            mine[key], value, delta=self.tol,
                            msg=f"{case['name']} seat {i + 1} {key}")

    def test_what_killed_each_body_agrees_too(self):
        for case in self.data["cases"]:
            want = case["expect"].get("blame")
            if not want:
                continue
            with self.subTest(case=case["name"]):
                got = app.run_solve(json.loads(json.dumps(case["payload"])))
                self.assertEqual(set(got.get("blame", {})), set(want))
                for night, seats in want.items():
                    for seat, causes in seats.items():
                        mine = got["blame"][night][seat]
                        self.assertEqual(set(mine), set(causes))
                        for cause, share in causes.items():
                            self.assertAlmostEqual(mine[cause], share,
                                                   delta=self.tol)

    def test_the_diagnosis_of_a_dead_board_agrees_too(self):
        for case in self.data["cases"]:
            want = case["expect"].get("diagnosis")
            if not want:
                continue
            with self.subTest(case=case["name"]):
                got = app.run_solve(json.loads(json.dumps(case["payload"])))
                self.assertEqual(got.get("diagnosis"), want)


if __name__ == "__main__":
    unittest.main()
