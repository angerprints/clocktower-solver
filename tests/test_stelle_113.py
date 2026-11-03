"""Stelle 113 (03.11.2026): sources with no actor that die in the night.

"A character's ability always ends with death" (table ruling, v3.1.4),
and the drunkenness or poison it gave ends with it. Stelle 104 split the
night from the day after it for a source whose actor dies in the night —
but only for the sources that name an actor. The No Dashii, the
Vigormortis, the Pukka and the Goon name none (nothing rests while they
are drunk), so a No Dashii killed in the night still poisoned its
neighbours by day.

Now each says whose death ends it (`Source.holder`), and the plan splits
the day for it as for the others. The Snake Charmer's swap is left as it
was: the poison is the old Demon's for the rest of the game, whoever
holds the charmer's ability.
"""
import json
import pathlib
import subprocess
import sys
import types
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from helpers import SolverTest                    # sets up the import path

import botc.solver as S                           # noqa: E402
from botc.impairment import Source                # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEATHS = {3: ("N2",), 5: ("D2",)}


def state():
    return types.SimpleNamespace(
        deaths=DEATHS, died_at=lambda seat: DEATHS.get(seat, ()))


# name, holder, actor -> dies with night 2?
SOURCES = [("No Dashii", 3, None, True),
           ("Vigormortis", 5, None, False),       # died by day
           ("Goon", 3, None, True),
           ("Pukka", 1, None, False),             # still alive
           ("Poisoner", None, 3, True),           # an actor, as before
           ("Snake Charmer", None, None, False)]  # nobody's death ends it


class TheirDeathEndsThem(SolverTest):

    def test_in_python(self):
        sources = [Source(n, frozenset({0}), holder=h, actor=a)
                   for n, h, a, _ in SOURCES]
        got = {s.name for s in S._dying_sources(state(), 2, sources)}
        self.assertEqual(got, {n for n, _h, _a, dies in SOURCES if dies})
        self.assertEqual(S._dying_sources(state(), 3, sources), [])

    def test_in_javascript(self):
        script = (
            "import {Source} from './js/impairment.mjs';"
            "import {dyingSources} from './js/scoring.mjs';"
            "const [cases, deaths] = JSON.parse(process.argv[1]);"
            "const state = {deaths, diedAt: s => deaths[s] || []};"
            "const sources = cases.map(([n, h, a]) => new Source(n, [0],"
            " {holder: h, actor: a}));"
            "console.log(JSON.stringify([2, 3].map(night =>"
            " dyingSources(state, night, sources).map(s => s.name))));")
        payload = [[[n, h, a] for n, h, a, _ in SOURCES],
                   {str(k): list(v) for k, v in DEATHS.items()}]
        got = subprocess.run(["node", "--input-type=module", "-e", script,
                              json.dumps(payload)], cwd=ROOT,
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(got.returncode, 0, got.stderr)
        two, three = json.loads(got.stdout)
        self.assertEqual(set(two), {n for n, _h, _a, dies in SOURCES if dies})
        self.assertEqual(three, [])

    def test_the_rules_name_their_holder(self):
        import inspect
        for rule in (S.a_no_dashii_poisons_its_townsfolk_neighbours,
                     S.a_vigormortis_poisons_beside_its_dead_minions,
                     S.a_pukka_poisons_whoever_it_will_kill,
                     S._a_goons_chooser):
            self.assertIn("holder=", inspect.getsource(rule), rule.__name__)


if __name__ == "__main__":
    unittest.main()
