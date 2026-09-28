"""The page, with no server running.

The solver moved into the browser, and the point of that is a phone that
does not need a laptop in the room. So the check is not "does the
JavaScript agree with Python" — that is `test_js_solve.py` — but "does
the page work with nothing behind it".

`tests/harness/page_boot.mjs` pulls the module script straight out of
`ui/index.html`, gives it just enough DOM to get through boot, and makes
every `fetch` fail loudly while counting the attempts. Then it solves a
board.

Not a substitute for opening the page: a stub DOM proves nothing about
layout. What it proves is that the module loads, that every declaration
is in place before anything reaches for it, and that a board is answered
on the device. All three broke at some point during the cutover, and none
of them would have shown up in a test of the solver.

Skipped when Node is not installed.
"""

import json
import pathlib
import re
import shutil
import subprocess
import unittest

from helpers import SolverTest                    # sets up the import path

ROOT = pathlib.Path(__file__).resolve().parent.parent
NODE = shutil.which("node")
PAGE = ROOT / "ui" / "index.html"


class ThePageAsksNobodyForAnything(SolverTest):
    """Read off the page itself, so it cannot drift from what ships."""

    def setUp(self):
        self.html = PAGE.read_text()

    def test_the_script_is_a_module(self):
        """Without this the page cannot import the solver at all."""
        self.assertIn('<script type="module">', self.html)

    def test_it_imports_the_solver(self):
        self.assertIn('from "../js/api.mjs"', self.html)

    def test_there_are_no_calls_left_at_all(self):
        """Everything is answered here now, including the guesswork
        check — which was the last one to go, because it needed the
        sampler."""
        self.assertEqual(re.findall(r'fetch\("(/api/[a-z]+)"', self.html), [])

    def test_the_guesswork_check_is_solved_locally_too(self):
        self.assertIn("solver.guessworkFor(", self.html)


@unittest.skipUnless(NODE, "Node is not installed")
class ItBootsAndSolvesOnTheDevice(SolverTest):

    @classmethod
    def setUpClass(cls):
        got = subprocess.run(
            [NODE, str(ROOT / "tests" / "harness" / "page_boot.mjs")],
            capture_output=True, text=True, timeout=300)
        if got.returncode:
            raise AssertionError(f"the page failed to boot:\n{got.stderr}")
        cls.got = json.loads(got.stdout.strip().splitlines()[-1])

    def test_the_page_boots(self):
        self.assertTrue(self.got["booted"])

    def test_nothing_was_fetched(self):
        """The whole point. One attempt would mean a phone with no laptop
        in the room gets a broken page."""
        self.assertEqual(self.got["fetched"], 0)

    def test_a_board_is_answered_on_the_device(self):
        self.assertEqual(self.got["valid"], 630)
        self.assertEqual(self.got["seats"], 9)


@unittest.skipUnless(NODE, "Node is not installed")
class TheServerStillHandsOverTheModules(SolverTest):
    """`app.py` is a convenience now rather than a requirement, but the
    page still has to be able to import from it."""

    # Asked of the handler rather than of the source text. The first
    # version of this matched a line of `app.py` and broke the moment
    # that line was refactored, which told us about the spelling and
    # nothing about the behaviour.
    def served(self, path):
        """What the handler would do with this path, without a socket."""
        import app

        class Probe(app.Handler):
            def __init__(self):                   # no connection needed
                self.path = path
                self.sent = None

            def _send(self, code, body, ctype="application/json"):
                self.sent = (code, len(body), ctype)
                return True

            def send_response(self, code):
                self.sent = [code, 0, None]

            def send_header(self, key, value):
                if key == "Content-Type":
                    self.sent[2] = value
                if key == "Content-Length":
                    self.sent[1] = int(value)

            def end_headers(self):
                pass

            @property
            def wfile(self):
                class Sink:
                    def write(self, data):
                        pass
                return Sink()

        probe = Probe()
        handled = probe._static(path)
        return (probe.sent if handled else None)

    def test_it_serves_every_solver_module(self):
        for name in ("api.mjs", "worlds.mjs", "characters.rules.mjs",
                     "scoring.mjs", "report.mjs"):
            with self.subTest(module=name):
                got = self.served(f"/js/{name}")
                self.assertIsNotNone(got, f"/js/{name} was not served")
                code, length, kind = got
                self.assertEqual(code, 200)
                self.assertGreater(length, 0)
                self.assertIn("javascript", kind)

    def test_it_refuses_a_path_with_a_directory_in_it(self):
        for path in ("/js/../app.py", "/js/sub/api.mjs",
                     "/icons/../../app.py"):
            with self.subTest(path=path):
                got = self.served(path)
                # Either not matched at all, or matched and refused.
                self.assertTrue(got is None or got[0] == 404, got)

    def test_it_refuses_something_that_is_not_there(self):
        self.assertEqual(self.served("/js/nope.mjs")[0], 404)


if __name__ == "__main__":
    unittest.main()
