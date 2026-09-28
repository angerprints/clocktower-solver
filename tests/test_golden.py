"""Fixed scenarios with recorded answers.

These numbers are **anchors, not truths**. They were produced by the code
itself, so they cannot tell you the solver is right — only that it has
stopped agreeing with the version that was reviewed. When one moves,
either you changed a prior on purpose (update the number, and say why in
the commit) or you broke something (don't).

Each case pairs its recorded figures with a plain-language claim about
what the scenario means, so a shifted number can be judged rather than
just re-recorded.
"""

import unittest

from helpers import SolverTest, game, solved, spread   # sets up the import path
from botc.info import (Chef, Empath, FortuneTeller, Investigator,  # noqa: E402
                       SlayerShot, Undertaker, VirginNomination, Washerwoman)
from botc.worlds import enumerate_worlds               # noqa: E402


def nine(claims):
    return {i: r for i, r in enumerate(claims)}


SCENARIOS = {
    "a quiet table, everyone claimed, nothing said": dict(
        state=lambda: game(7),
        worlds=126,
        evil=[28.6] * 7,
    ),
    "a full first night of information": dict(
        state=lambda: game(7, infos=[
            Washerwoman(1, 0, a=3, b=5, role="Chef"),
            Investigator(1, 2, a=4, b=6, role="Poisoner"),
            Chef(1, 3, count=0),
            Empath(1, 4, count=1),
            FortuneTeller(1, 5, a=0, b=6, yes=False)]),
        worlds=33,
        evil=[7.0, 24.5, 50.1, 11.0, 47.5, 32.5, 27.5],
    ),
    "an Empath whose two nights disagree": dict(
        state=lambda: game(9, infos=[Empath(1, 4, count=1), Empath(2, 4, count=3)]),
        worlds=330,
        evil=[15.7, 15.7, 15.7, 17.6, 13.1, 17.6, 15.7, 44.4, 44.4],
    ),
    "a Slayer shot that landed": dict(
        state=lambda: game(9, claims=nine([
            "Washerwoman", "Librarian", "Investigator", "Chef", "Slayer",
            "FortuneTeller", "Undertaker", "Recluse", "Saint"]),
            deaths={7: "D2"},
            infos=[SlayerShot(2, 4, target=7, died=True)]),
        # Re-recorded when a Demon killed in daylight started requiring
        # the Scarlet Woman to take over. The shot target is far less
        # likely to have been the Imp now, so the Recluse reading gains.
        worlds=300,
        evil=[21.7, 21.7, 21.7, 21.7, 0.0, 21.7, 21.7, 10.0, 60.0],
    ),
    "a Virgin that triggered": dict(
        state=lambda: game(9, claims=nine([
            "Virgin", "Washerwoman", "Chef", "Empath", "Monk",
            "FortuneTeller", "Undertaker", "Recluse", "Saint"]),
            deaths={2: "E1"},
            infos=[VirginNomination(1, 0, nominator=2, triggered=True)]),
        worlds=315,
        evil=[0.0, 23.2, 4.8, 23.2, 23.2, 23.2, 23.2, 39.7, 39.7],
    ),
    "a night kill, an execution and an Undertaker reading": dict(
        state=lambda: game(9, deaths={3: "N2", 8: "E1"},
                           infos=[Undertaker(2, 6, target=8, role="Spy")]),
        # Re-recorded twice. First when the Demon learned to change
        # hands: the executed seat may have started as the Imp with the
        # Scarlet Woman taking over, which is a story that did not exist
        # before.
        #
        # Then again when the Saint stopped being a flat rejection. A
        # poisoned Saint is executed and play carries on, so the executed
        # seat is no longer *certainly* evil — and the Undertaker naming
        # them the Spy no longer settles it either, because a poisoned
        # Undertaker says whatever it was told.
        worlds=185,
        evil=[17.4, 17.4, 17.4, 0.2, 17.4, 17.4, 18.2, 16.3, 78.2],
    ),
    "soft claims and a social read": dict(
        state=lambda: game(7, claims={0: "Washerwoman", 1: "Librarian",
                                      2: "Investigator", 3: "Chef", 4: "Empath"},
                           reads={5: 2}, wakes={6: "never"}),
        worlds=6206,
        evil=[35.7, 35.7, 35.7, 35.7, 35.7, 15.1, 6.3],
    ),
}


class Golden(SolverTest):

    def test_world_counts_have_not_moved(self):
        for name, case in SCENARIOS.items():
            with self.subTest(scenario=name):
                valid, _rows = solved(case["state"]())
                self.assertEqual(len(valid), case["worlds"])

    def test_probabilities_have_not_moved(self):
        for name, case in SCENARIOS.items():
            with self.subTest(scenario=name):
                _valid, rows = solved(case["state"]())
                got = [round(r["evil_pct"], 1) for r in rows]
                self.assertEqual(len(got), len(case["evil"]))
                for seat, (a, b) in enumerate(zip(got, case["evil"])):
                    self.assertPct(a, b, 0.15, f"{name}, seat {seat + 1}")


class WhatTheScenariosMean(SolverTest):
    """The claims the golden figures are supposed to embody.

    If a golden number changes and these still hold, the change was a
    tuning decision. If one of these breaks, something is actually wrong.
    """

    def test_an_untouched_table_suspects_everyone_equally(self):
        _v, rows = solved(SCENARIOS["a quiet table, everyone claimed, nothing said"]["state"]())
        spread_ = {round(r["evil_pct"], 1) for r in rows}
        self.assertEqual(len(spread_), 1, "no information means no suspect")

    def test_a_landed_shot_clears_the_shooter_completely(self):
        _v, rows = solved(SCENARIOS["a Slayer shot that landed"]["state"]())
        self.assertPct(rows[4]["evil_pct"], 0.0, 0.01)

    def test_a_landed_shot_leaves_the_target_demon_or_recluse(self):
        _v, rows = solved(SCENARIOS["a Slayer shot that landed"]["state"]())
        roles = dict(rows[7]["roles"])
        self.assertPct(roles.get("Imp", 0) + roles.get("Recluse", 0), 100.0, 0.1)

    def test_a_triggered_virgin_is_certain_and_the_nominator_nearly_so(self):
        _v, rows = solved(SCENARIOS["a Virgin that triggered"]["state"]())
        self.assertPct(dict(rows[0]["roles"]).get("Virgin", 0), 100.0, 0.1)
        self.assertBetween(rows[2]["evil_pct"], 0.1, 12.0,
                           "only the Spy should survive as an evil nominator")

    def test_an_executed_saint_claim_must_have_been_bluffing(self):
        _v, rows = solved(SCENARIOS["a night kill, an execution and an Undertaker reading"]["state"]())
        # Strongly, not certainly. Being executed and dying used to rule
        # the Saint out outright; a poisoned one is executed and the game
        # goes on, so "the Spy" is the likeliest reading rather than the
        # only one.
        self.assertGreater(rows[8]["evil_pct"], 70.0)
        self.assertEqual(rows[8]["roles"][0][0], "Spy")

    def test_a_night_two_victim_is_all_but_cleared(self):
        _v, rows = solved(SCENARIOS["a night kill, an execution and an Undertaker reading"]["state"]())
        self.assertLess(rows[3]["evil_pct"], 2.0)


class SearchSize(SolverTest):
    """Pruning regressions are silent: the answer stays right and the
    machine just does far more work to reach it. These pin the sizes."""

    SIZES = {
        (7, "claims only"): (lambda: enumerate_worlds(7, spread(7)), 126),
        (9, "claims only"): (lambda: enumerate_worlds(9, spread(9)), 630),
        (9, "one seat confirmed"): (
            lambda: enumerate_worlds(9, spread(9), {4: "confirmed"}), 450),
        (9, "one seat hiding"): (
            lambda: enumerate_worlds(9, spread(9), {4: "hiding"}), 1002),
        (9, "one seat not trusted"): (
            lambda: enumerate_worlds(9, spread(9), {4: "unsure"}), 4746),
        (12, "claims only"): (lambda: enumerate_worlds(12, spread(12)), 15120),
    }

    def test_settings_cost_what_they_should(self):
        """Confirming narrows, hiding widens a little, not trusting widens
        a lot. If that ordering ever inverts, a setting is misbehaving."""
        plain = len(enumerate_worlds(9, spread(9)))
        confirmed = len(enumerate_worlds(9, spread(9), {4: "confirmed"}))
        hiding = len(enumerate_worlds(9, spread(9), {4: "hiding"}))
        unsure = len(enumerate_worlds(9, spread(9), {4: "unsure"}))
        self.assertLess(confirmed, plain)
        self.assertLess(plain, hiding)
        self.assertLess(hiding, unsure)

    def test_the_search_is_the_size_it_was(self):
        for (n, what), (build, expected) in self.SIZES.items():
            with self.subTest(players=n, setting=what):
                self.assertEqual(len(build()), expected)


if __name__ == "__main__":
    unittest.main()
