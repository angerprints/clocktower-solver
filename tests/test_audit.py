"""Every reading the page offers, checked to actually do something.

Not what it does — that is each character's own tests — but that it does
*anything*: the row can be built, the solver accepts it, and the answer
moves. A reading that changes nothing is either broken or pointless, and
neither is visible from the outside.

Two things this found are worth keeping written down, because both were
the probe being wrong rather than the code, and both are easy traps:

  * A reading only bites when somebody **claims** its character. A
    Courtier row on a board where nobody claims Courtier fires only in
    the worlds where that seat happens to hold it, which is a small
    enough slice to look like nothing at all.

  * A reading only bites when it could be **false**. A Chambermaid told
    the true number changes nothing, correctly.
"""

import unittest

from helpers import SolverTest                    # sets up the import path
import app                                        # noqa: E402
from botc import scripts                          # noqa: E402
from botc.catalogue import CHARACTERS             # noqa: E402


def answer(script, claims, infos, events=None, **extra):
    ids = [CHARACTERS[k].id for k in script.keys]
    seats = [{"name": "", "claim": c, "events": (events or {}).get(i, []),
              "certainty": "", "read": 0, "wake": ""}
             for i, c in enumerate(claims)]
    return app.run_solve({"n_players": len(claims), "players": seats,
                          "infos": infos, "days_done": [1, 2, 3],
                          "script": {"name": script.name, "characters": ids},
                          **extra})


class EveryOfferedReadingDoesSomething(SolverTest):

    def moves(self, script, claims, row, events=None):
        base = answer(script, claims, [])
        self.assertFalse(base.get("error"), base.get("error"))
        self.assertTrue(base["valid"], "the base board has no worlds")
        got = answer(script, claims, [row], events)
        self.assertFalse(got.get("error"), got.get("error"))
        changed = (got["valid"] != base["valid"]
                   or [round(r["evil_pct"], 4) for r in got["rows"]]
                   != [round(r["evil_pct"], 4) for r in base["rows"]])
        self.assertTrue(changed,
                        f"{row['type']} changed nothing at all")

    SV = ["Clockmaker", "Dreamer", "Oracle", "Seamstress", "Juggler",
          "Flowergirl", "TownCrier", "Mutant", "Sweetheart"]

    def test_the_sects_and_violets_readings(self):
        sv = scripts.SECTS_AND_VIOLETS
        rows = [
            ({"type": "ClockmakerInfo", "night": 1, "player": 0,
              "count": 1}, None),
            ({"type": "DreamerInfo", "night": 1, "player": 1, "target": 2,
              "good_role": "Sage", "evil_role": "Witch"}, None),
            ({"type": "OracleInfo", "night": 3, "player": 2, "count": 1},
             {4: ["N2"]}),
            ({"type": "SeamstressInfo", "night": 2, "player": 3, "a": 0,
              "b": 1, "same": True}, None),
            ({"type": "JugglerInfo", "night": 3, "player": 4, "count": 2,
              "guesses": [{"player": 0, "role": "Clockmaker"},
                          {"player": 1, "role": "Dreamer"}]}, None),
            ({"type": "FlowergirlInfo", "night": 3, "player": 5,
              "voted": True}, None),
            ({"type": "TownCrierInfo", "night": 3, "player": 6,
              "nominated": True}, None),
        ]
        for row, events in rows:
            with self.subTest(reading=row["type"]):
                self.moves(sv, self.SV, row, events)

    def test_the_mathematician_bites_now(self):
        """It was silent for most of this script's life, deliberately:
        its number is the size of the impairment set, and four characters
        that droison were unbuilt. All four are built, so it speaks."""
        sv = scripts.SECTS_AND_VIOLETS
        self.assertEqual([c.name for c in sv.characters()
                          if c.impairs and not c.modelled], [])
        # On a lineup where somebody actually claims it — the trap this
        # file exists to document, walked into once while writing it.
        claims = ["Clockmaker", "Dreamer", "SnakeCharmer", "Mathematician",
                  "Flowergirl", "TownCrier", "Oracle", "Mutant",
                  "Sweetheart"]
        counts = {n: answer(sv, claims,
                            [{"type": "MathematicianInfo", "night": 2,
                              "player": 3, "count": n}])["valid"]
                  for n in (0, 2)}
        self.assertNotEqual(counts[0], counts[2],
                            "the number it heard should matter now")

    def test_a_courtier_needs_somebody_to_claim_it(self):
        """The trap this audit fell into. A row whose character nobody
        claims fires only in the worlds where some seat happens to hold
        it, which is a thin enough slice to look like nothing."""
        bmr = scripts.BAD_MOON_RISING
        unclaimed = ["Grandmother", "Sailor", "Chambermaid", "Exorcist",
                     "Innkeeper", "Gambler", "Gossip", "Tinker", "Moonchild"]
        claimed = list(unclaimed)
        claimed[3] = "Courtier"
        reading = {"type": "ChambermaidInfo", "night": 1, "player": 2,
                   "a": 0, "b": 1, "count": 0}
        courtier = {"type": "CourtierChoice", "night": 1, "player": 3,
                    "role": "Chambermaid"}

        thin = answer(bmr, unclaimed, [reading])
        thin_plus = answer(bmr, unclaimed, [reading, courtier])
        self.assertEqual(thin["valid"], thin_plus["valid"])

        real = answer(bmr, claimed, [reading])
        real_plus = answer(bmr, claimed, [reading, courtier])
        self.assertGreater(real_plus["valid"], real["valid"],
                           "a claimed Courtier should excuse the reading")

    def test_the_solver_only_pays_for_what_would_be_false(self):
        """Asked of a *world*, not of a board.

        The first version of this compared board totals and expected them
        equal, which was the wrong question: a reading is true or false
        in a world, and across a whole board it is false in some of them.
        Adding a Courtier excuses exactly those, so the totals move — as
        they should.
        """
        import botc.solver as S
        from botc.info import ChambermaidInfo, CourtierChoice, GameState
        from botc.worlds import World
        bmr = scripts.BAD_MOON_RISING
        claims = ["Grandmother", "Sailor", "Chambermaid", "Courtier",
                  "Innkeeper", "Gambler", "Gossip", "Tinker", "Moonchild"]
        world = World(("Grandmother", "Sailor", "Chambermaid", "Courtier",
                       "Innkeeper", "Gambler", "Gossip", "Tinker", "Pukka"),
                      (None,) * 9)
        courtier = CourtierChoice(1, 3, role="Chambermaid")

        def cost(count, with_courtier):
            rows = [ChambermaidInfo(1, 2, a=0, b=1, count=count)]
            if with_courtier:
                rows.append(courtier)
            state = GameState(n_players=9, script=bmr,
                              claims={i: r for i, r in enumerate(claims)},
                              infos=rows)
            return S.explanation_cost(world, state)

        # True in this world: nothing to excuse, so the Courtier is worth
        # nothing either way.
        self.assertPct(cost(2, False), 1.0, 1e-9)
        self.assertPct(cost(2, True), 1.0, 1e-9)
        # False in this world: excusing it costs something on its own,
        # and nothing once a Courtier declared it.
        self.assertLess(cost(0, False), 1.0)
        self.assertPct(cost(0, True), 1.0, 1e-9)


class EveryLayerOffersTheSameReadings(SolverTest):
    """The page, the server and the solver each keep their own list."""

    def test_nothing_is_offered_that_cannot_be_built(self):
        import botc.info as I
        # A reading's name in the ledger is not always its class name.
        # An Acrobat announces a *choice* and a Balloonist is told
        # *information*, so the classes say so even though the page calls
        # both by the character.
        # "Became" has no source character — it is the speaker saying
        # where their own came from — so the checks below skip the
        # source-must-exist question for it.
        aliases = {"VirginTrigger": "VirginNomination",
                   "Became": "BecameInfo",
                   "Acrobat": "AcrobatChoice",
                   "Balloonist": "BalloonistInfo",
                   "Alsaahir": "AlsaahirGuess",
                   "Noble": "NobleInfo"}
        for kind in app.INFO_SOURCES:
            with self.subTest(reading=kind):
                self.assertTrue(hasattr(I, aliases.get(kind, kind)),
                                f"{kind} has no class behind it")

    def test_every_source_character_exists(self):
        for source in app.INFO_SOURCES.values():
            if source is None:
                continue          # the speaker is the source
            with self.subTest(source=source):
                self.assertIn(source, CHARACTERS)

    def test_the_page_has_fields_for_each(self):
        import pathlib
        import re
        html = (pathlib.Path(__file__).resolve().parent.parent
                / "ui" / "index.html").read_text()
        fields = set(re.findall(r"^\s*(\w+):\s*\[\[", html, re.M))
        for kind in app.INFO_SOURCES:
            with self.subTest(reading=kind):
                self.assertIn(kind, fields,
                              f"{kind} is offered but has no fields")

    def test_and_offers_nothing_extra(self):
        import pathlib
        import re
        html = (pathlib.Path(__file__).resolve().parent.parent
                / "ui" / "index.html").read_text()
        fields = set(re.findall(r"^\s*(\w+):\s*\[\[", html, re.M))
        self.assertEqual(fields - set(app.INFO_SOURCES), set())

    def test_each_script_only_offers_what_it_can_produce(self):
        for name, script in scripts.BUILT_IN.items():
            offered = app.script_meta(script, 9)["info_types"]
            for kind in offered:
                source = app.INFO_SOURCES[kind]
                with self.subTest(script=name, reading=kind):
                    if source is None:
                        # No producing character: offered when the script
                        # holds anything that hands a token on.
                        self.assertTrue(
                            any(k in script.keys for k in app.HANDS_ON))
                    else:
                        self.assertIn(source, script.keys)


if __name__ == "__main__":
    unittest.main()


class TheBuiltSiteMatchesTheSource(SolverTest):
    """The one gap in the layers.

    Python is checked against JavaScript, the solver against the walk,
    the page's fields against the app's readings — and nothing checked
    the **built site** against the source it was built from.

    A stale build looks exactly like a missing character. Two characters
    added in one session were reported missing from the hosted page, and
    every check available said they were present, because every check
    was reading a layer the hosted page does not use. The site computes
    its own catalogue from bundled data at load time; if that bundle is
    old, nothing else knows.
    """

    def built(self):
        """What `solver.meta()` gives the page, run out of `docs/`."""
        import json
        import pathlib
        import subprocess
        root = pathlib.Path(__file__).resolve().parent.parent
        docs = root / "docs"
        if not (docs / "api.mjs").exists():
            self.skipTest("no built site to check")
        got = subprocess.run(
            ["node", "--input-type=module", "-e",
             'const m = await import("./docs/api.mjs");'
             'process.stdout.write(JSON.stringify(m.meta().catalogue));'],
            cwd=root, capture_output=True, text=True, timeout=120)
        if got.returncode != 0:
            self.fail(f"the built site would not load: {got.stderr[:200]}")
        return json.loads(got.stdout)

    def test_every_character_reaches_the_page(self):
        """Anything the solver knows, somebody can tick."""
        theirs = {c["key"] for c in self.built()}
        ours = set(CHARACTERS)
        self.assertEqual(ours - theirs, set(),
                         "in the solver and not on the built page — "
                         "run tools/build_site.py")

    def test_and_the_page_invents_nobody(self):
        theirs = {c["key"] for c in self.built()}
        self.assertEqual(theirs - set(CHARACTERS), set(),
                         "on the built page and not in the solver")

    def test_the_teams_agree(self):
        """A character on the wrong team lands in the wrong tick-list
        heading, which is how somebody fails to find it."""
        theirs = {c["key"]: c["team"] for c in self.built()}
        for key, char in CHARACTERS.items():
            with self.subTest(character=key):
                self.assertEqual(theirs.get(key), char.team)

    def test_the_ledger_offers_the_same_readings_on_both_sides(self):
        """Picking a character is not enough — its reading has to be
        enterable too.

        `INFO_SOURCES` exists twice, once in `app.py` and once in
        `js/api.mjs`, and three characters reached the Python table and
        not the JavaScript one. They could be ticked onto a script on the
        hosted page and then had no row to fill in: usable in the model,
        useless at a table.
        """
        import json
        import pathlib
        import subprocess
        root = pathlib.Path(__file__).resolve().parent.parent
        if not (root / "docs" / "api.mjs").exists():
            self.skipTest("no built site to check")
        got = subprocess.run(
            ["node", "--input-type=module", "-e",
             'const m = await import("./docs/api.mjs");'
             'process.stdout.write(JSON.stringify(m.INFO_SOURCES || null));'],
            cwd=root, capture_output=True, text=True, timeout=120)
        theirs = json.loads(got.stdout or "null")
        if theirs is None:
            self.skipTest("INFO_SOURCES is not exported to compare")
        self.assertEqual(set(app.INFO_SOURCES), set(theirs))

    def test_the_build_regenerates_the_character_data(self):
        """A build step that depends on a human is not a build step.

        `js/characters.mjs` is written out of the Python catalogue by
        `tools/gen_characters.py`, and `build_site.py` used to assume
        somebody had remembered to run it. Nobody did. A character added
        to Python reached the solver, the tests, the ledger and the
        gates, and never reached the built site.

        That took a dozen rounds to find, because every artifact *except*
        the generated one was correct and each confirmed the last. The
        only thing that would have caught it is this: does building
        actually rebuild?
        """
        import pathlib
        import subprocess
        import sys
        root = pathlib.Path(__file__).resolve().parent.parent
        source = (root / "tools" / "build_site.py").read_text()
        self.assertIn("gen_characters.py", source,
                      "the build does not regenerate the character data")
        # And it has to happen before the copy, or it regenerates into a
        # folder that has already been written.
        self.assertLess(source.index("gen_characters.py"),
                        source.index("shutil.copy2(module"),
                        "the data is generated after it is copied")

    def test_the_page_asks_for_a_stamped_entry_point(self):
        """A browser caches an ES module hard, so a stale copy can be
        served under a fresh service worker. Only the entry point needs
        the stamp — everything below resolves relative to a URL that now
        carries it."""
        import pathlib
        root = pathlib.Path(__file__).resolve().parent.parent
        page = root / "docs" / "index.html"
        if not page.exists():
            self.skipTest("no built site to check")
        self.assertRegex(page.read_text(), r'from "\./api\.mjs\?v=[0-9a-f]{6,}"')

    def test_every_offered_reading_can_be_built_in_javascript(self):
        """The hosted page runs the JavaScript, so a reading the ledger
        offers and the JavaScript cannot build kills Solve outright.

        Three readings shipped that way — Acrobat, Balloonist and
        Alsaahir existed in Python and not in `js/info.mjs` at all. The
        moment anybody entered one and pressed Solve the whole solve died
        with "Unknown kind of reading". Nothing caught it because every
        check compared Python against Python.
        """
        import json
        import pathlib
        import subprocess
        root = pathlib.Path(__file__).resolve().parent.parent
        got = subprocess.run(
            ["node", "--input-type=module", "-e",
             'const m = await import("./js/info.mjs");'
             'process.stdout.write(JSON.stringify(Object.keys(m.KINDS)));'],
            cwd=root, capture_output=True, text=True, timeout=120)
        kinds = set(json.loads(got.stdout))
        self.assertEqual(set(app.INFO_SOURCES) - kinds, set(),
                         "offered by the ledger, unbuildable in JavaScript")


class BothSidesKnowTheSameRules(SolverTest):
    """Every registry, compared by name across the two languages.

    Three readings — Acrobat, Balloonist, Alsaahir — shipped with no
    JavaScript implementation at all. The hosted page runs the
    JavaScript, so entering one and pressing Solve died with "Unknown
    kind of reading". Nothing caught it because every check compared
    Python against Python.

    These compare the registries themselves, which is the only thing that
    catches a rule written on one side and forgotten on the other. Six
    layers: readings, transitions, causes, impairment sources, waking
    conditions and death immunities.
    """

    def js(self, expr):
        import json
        import pathlib
        import subprocess
        root = pathlib.Path(__file__).resolve().parent.parent
        got = subprocess.run(
            ["node", "--input-type=module", "-e",
             'await import("./js/characters.rules.mjs");'
             'const s = await import("./js/scoring.mjs");'
             'const d = await import("./js/deaths.mjs");'
             'const i = await import("./js/impairment.mjs");'
             'const w = await import("./js/waking.mjs");'
             'const m = await import("./js/info.mjs");'
             'const nm = a => a.map(f => f.name || String(f));'
             f'process.stdout.write(JSON.stringify({expr}));'],
            cwd=root, capture_output=True, text=True, timeout=180)
        if got.returncode != 0:
            self.fail(f"the JavaScript would not load: {got.stderr[:200]}")
        return set(json.loads(got.stdout))

    def snake(self, names):
        import re
        return {re.sub(r"(?<!^)(?=[A-Z])", "_", n).lower() for n in names}

    def both(self, label, theirs, ours):
        self.assertEqual(ours - theirs, set(),
                         f"{label}: in Python and not in JavaScript")
        self.assertEqual(theirs - ours, set(),
                         f"{label}: in JavaScript and not in Python")

    def test_the_readings_match(self):
        """The one that actually broke. `KINDS` is what `makeInfo` looks
        in, so a reading the ledger offers and this does not hold kills
        the whole solve."""
        import botc.info as PI
        alias = {"Acrobat": "AcrobatChoice", "Balloonist": "BalloonistInfo",
                 "Alsaahir": "AlsaahirGuess", "Became": "BecameInfo",
                 "Noble": "NobleInfo"}
        theirs = {alias.get(x, x) for x in self.js("Object.keys(m.KINDS)")}
        ours = {n for n in dir(PI)
                if isinstance(getattr(PI, n), type)
                and issubclass(getattr(PI, n), PI.Info)
                and n != "Info"
                and getattr(PI, n).__name__ == n}   # skip aliases
        self.both("readings", theirs, ours)

    def test_the_transition_rules_match(self):
        import botc.solver as solver
        self.both("transitions", self.snake(self.js("nm(s.TRANSITION_RULES)")),
                  {r.__name__ for r in solver.TRANSITION_RULES})

    def test_the_cause_rules_match(self):
        from botc import deaths
        self.both("causes", self.snake(self.js("nm(d.CAUSE_RULES)")),
                  {r.__name__ for r in deaths.CAUSE_RULES})

    def test_the_impairment_sources_match(self):
        from botc import impairment
        self.both("sources", self.snake(self.js("nm(i.SOURCE_RULES)")),
                  {r.__name__ for r in impairment.SOURCE_RULES})

    def test_the_waking_conditions_match(self):
        from botc import waking
        self.both("waking", self.js("Object.keys(w.CONDITION_RULES)"),
                  set(waking.CONDITION_RULES))

    def test_the_death_immunities_match(self):
        from botc import deaths
        self.both("immunities", self.snake(self.js("nm(d.IMMUNITY_RULES)")),
                  {r.__name__ for r in deaths.IMMUNITY_RULES})
