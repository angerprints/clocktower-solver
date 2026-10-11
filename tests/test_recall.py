"""Stories that differ only in who turned evil are not told twice.

With a Bounty Hunter dealt, every world is told once for each Townsfolk
that may be the evil one, and beside a Mezepheles once more for each
player and night it could have turned somebody. Most of those differ in a
seat nothing on the board asks about. The solver writes down whose side
was asked about while it explains a story, and recalls the answer for the
stories that differ only where nobody looked (11.10.2026, open item 52).

Nothing here may change an answer: that is what these tests hold it to.
"""

import json
import pathlib
import random
import shutil
import subprocess
import unittest

from helpers import SolverTest                    # sets up the import path
import app                                        # noqa: E402
import botc.solver as S                           # noqa: E402
from botc import info as I                        # noqa: E402
from botc.worlds import Timeline, TurnedEvil, World   # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORPUS = ROOT / "tests" / "fixtures" / "conformance.json"
NODE = shutil.which("node")


def bit(phase):
    return 1 << (I.phase_index(phase) + 2)


class WhoseSideWasAsked(SolverTest):

    def setUp(self):
        I.listen_for_sides(True)

    def tearDown(self):
        I.listen_for_sides(False)

    WORLD = World(("Chef", "Empath", "Monk", "Imp", "Poisoner"),
                  (None,) * 5)

    def test_a_world_writes_it_down(self):
        I.begin_reads()
        self.WORLD.evil_at(2, "N2")
        self.WORLD.alignment_at(4, "D1")
        self.assertEqual(I.end_reads(), {2: bit("N2"), 4: bit("D1")})

    def test_a_timeline_writes_it_down(self):
        view = Timeline(self.WORLD, (TurnedEvil("N0", 1, None, "evil"),))
        I.begin_reads()
        self.assertTrue(view.evil_at(1, "N1"))
        self.assertEqual(I.end_reads(), {1: bit("N1")})

    def test_asking_whether_a_seat_knows_it_turned_counts(self):
        view = Timeline(self.WORLD, (TurnedEvil("N2", 1, None, "evil"),))
        I.begin_reads()
        self.assertFalse(I.knows_it_turned_evil(view, 1, "N1"))
        self.assertTrue(I.knows_it_turned_evil(view, 1, "N3"))
        self.assertEqual(I.end_reads(), {1: bit("N1") | bit("N3")})

    def test_what_was_asked_inside_is_heard_outside(self):
        I.begin_reads()
        I.begin_reads()
        self.WORLD.evil_at(0, "N1")
        inner = I.end_reads()
        self.WORLD.evil_at(3, "N1")
        outer = I.end_reads()
        self.assertEqual(inner, {0: bit("N1")})
        self.assertEqual(outer, {0: bit("N1"), 3: bit("N1")})

    def test_a_character_is_not_a_side(self):
        I.begin_reads()
        self.WORLD.role_at(2, "N2")
        self.WORLD.demon_at("N2")
        self.assertEqual(I.end_reads(), {})

    def test_nothing_is_written_when_nobody_listens(self):
        I.listen_for_sides(False)
        I.begin_reads()
        self.WORLD.evil_at(2, "N2")
        self.assertEqual(I.end_reads(), {})


class TwoStoriesThatDifferWhereNobodyLooked(SolverTest):

    N0, N2, N3, N4 = (I.phase_index(p) for p in ("N0", "N2", "N3", "N4"))

    def same(self, mine, theirs, reads):
        return S._differ_only_unasked(mine, theirs, reads)

    def test_the_same_story(self):
        self.assertTrue(self.same({1: self.N0}, {1: self.N0},
                                  {1: bit("N1")}))

    def test_another_townsfolk_nobody_asked_about(self):
        self.assertTrue(self.same({1: self.N0}, {2: self.N0},
                                  {0: bit("N1"), 3: bit("N2")}))

    def test_not_if_either_was_asked_about(self):
        self.assertFalse(self.same({1: self.N0}, {2: self.N0},
                                   {1: bit("N1")}))
        self.assertFalse(self.same({1: self.N0}, {2: self.N0},
                                   {2: bit("N4")}))

    def test_a_turn_only_matters_from_its_night_on(self):
        asked_before = {5: bit("N1") | bit("N2")}
        self.assertTrue(self.same({5: self.N3}, {}, asked_before))
        self.assertFalse(self.same({5: self.N3}, {}, {5: bit("N3")}))
        self.assertFalse(self.same({5: self.N3}, {}, {5: bit("D4")}))

    def test_two_nights_differ_only_in_between(self):
        # Evil from night two in one story and from night four in the
        # other: they disagree on nights two and three, and day two and
        # three, and nowhere else.
        self.assertTrue(self.same({5: self.N2}, {5: self.N4},
                                  {5: bit("N1") | bit("N4") | bit("D5")}))
        self.assertFalse(self.same({5: self.N2}, {5: self.N4},
                                   {5: bit("D3")}))

    @unittest.skipUnless(NODE, "Node is not installed")
    def test_javascript_says_the_same(self):
        rng = random.Random(8)
        cases = []
        for _ in range(400):
            def flips():
                return {seat: rng.choice([-2, 2, 4, 6])
                        for seat in rng.sample(range(5), rng.randint(0, 2))}
            reads = {seat: rng.getrandbits(12)
                     for seat in rng.sample(range(5), rng.randint(0, 3))}
            cases.append((flips(), flips(), reads))
        mine = [S._differ_only_unasked(a, b, r) for a, b, r in cases]
        got = subprocess.run(
            [NODE, "--input-type=module", "-e",
             'const m = await import("./js/phases.mjs");'
             "const cases = JSON.parse(process.argv[1]);"
             "const map = o => new Map(Object.entries(o).map("
             "([k, v]) => [Number(k), v]));"
             "process.stdout.write(JSON.stringify(cases.map(([a, b, r]) =>"
             " m.differOnlyUnasked(map(a), map(b), map(r)))));",
             json.dumps(cases)],
            cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertEqual(json.loads(got.stdout), mine)


def boards(prefix="x-eight-"):
    corpus = json.loads(CORPUS.read_text())
    return [c for c in corpus["cases"] if c["name"].startswith(prefix)]


def counted(payload):
    for key in S.STORIES:
        S.STORIES[key] = 0
    got = app.run_solve(json.loads(json.dumps(payload)))
    return got, dict(S.STORIES)


class TheShortcutsChangeNothing(SolverTest):

    def tearDown(self):
        S.CHECK_RECALLS = False

    def test_every_recalled_story_costs_what_it_would_have(self):
        """Each story the shortcuts would settle is explained anyway and
        compared; a difference raises. On every board of the eighth five
        in the corpus, which is where the stories come from."""
        S.CHECK_RECALLS = True
        for case in boards():
            with self.subTest(board=case["name"]):
                got, _stories = counted(case["payload"])
                self.assertEqual(got["valid"], case["expect"]["valid"])

    def test_they_are_taken(self):
        recalled = skipped = explained = 0
        for case in boards("x-eight-played-"):
            _got, stories = counted(case["payload"])
            recalled += stories["recalled"]
            skipped += stories["skipped"]
            explained += stories["explained"]
        self.assertGreater(recalled, 1000)
        self.assertGreater(skipped, 1000)
        # More stories are settled without being told than are told.
        self.assertGreater(recalled + skipped, explained)

    def test_nothing_is_written_down_on_other_scripts(self):
        corpus = json.loads(CORPUS.read_text())
        case = next(c for c in corpus["cases"]
                    if c["name"] == "tb-9-night-kill")
        _got, stories = counted(case["payload"])
        self.assertEqual(stories, {"explained": 0, "recalled": 0,
                                   "skipped": 0})
        self.assertFalse(I._LISTENING[0])

    @unittest.skipUnless(NODE, "Node is not installed")
    def test_javascript_takes_the_same_ones(self):
        """Not only the same answers (the corpus holds both to that) but
        the same stories told, recalled and skipped — so one side cannot
        drift into a shortcut the other does not take."""
        chosen = boards("x-eight-played-")[:6] + boards("x-eight-7-")[:6]
        mine = {c["name"]: counted(c["payload"])[1] for c in chosen}
        got = subprocess.run(
            [NODE, "--input-type=module", "-e",
             'const api = await import("./js/api.mjs");'
             'const s = await import("./js/scoring.mjs");'
             "const out = {};"
             "for (const [name, payload] of JSON.parse(process.argv[1])) {"
             " for (const k of Object.keys(s.STORIES)) s.STORIES[k] = 0;"
             " api.solveBoard(payload);"
             " out[name] = {...s.STORIES}; }"
             "process.stdout.write(JSON.stringify(out));",
             json.dumps([[c["name"], c["payload"]] for c in chosen])],
            cwd=ROOT, capture_output=True, text=True, timeout=600)
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertEqual(json.loads(got.stdout), mine)


class EverySideGoesThroughOneDoor(SolverTest):
    """The shortcuts are only sound if nothing reads a seat's side behind
    the back of `alignment_at`. Held to it by where the stored sides are
    touched at all."""

    def test_in_python(self):
        for path in sorted((ROOT / "botc").glob("*.py")):
            text = path.read_text()
            uses = text.count("_sides_by_seat")
            with self.subTest(file=path.name):
                # Built in `__post_init__`, read in `alignment_at`.
                self.assertEqual(uses, 2 if path.name == "worlds.py" else 0)

    def test_in_javascript(self):
        for path in sorted((ROOT / "js").glob("*.mjs")):
            text = path.read_text()
            with self.subTest(file=path.name):
                self.assertEqual(text.count(".sides.get("),
                                 1 if path.name == "worlds.mjs" else 0)
        worlds = (ROOT / "js" / "worlds.mjs").read_text()
        self.assertEqual(worlds.count("if (LISTENING) noteSideRead("), 2)


if __name__ == "__main__":
    unittest.main()
