"""What the solver will not do, and how it says so.

Two different failures, handled differently on purpose.

The Atheist takes the bag away — the Storyteller may break the rules and
there may be no evil at all — so no legal world exists to find. That has a
visible signature though: the board fits nothing. Raising it when that
happens is more useful than silence, as long as it is raised as a
possibility and not a diagnosis.

Legion takes the team counts away, and there is no signature at all. The
board looks ordinary and every number is wrong. Nothing can be detected,
so the only honest move is to refuse before starting.
"""

import unittest

from helpers import SolverTest, game, solved       # sets up the import path
import app                                         # noqa: E402
from botc import limits                            # noqa: E402
from botc.info import SlayerShot, Empath, VirginNomination     # noqa: E402
from botc import scripts                          # noqa: E402
from botc.solver import diagnose                   # noqa: E402

TWELVE = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
          "FortuneTeller", "Undertaker", "Monk", "Ravenkeeper", "Slayer",
          "Recluse", "Saint"]


def plus(*extra):
    """Trouble Brewing with something else dropped in."""
    return scripts.from_ids("Trouble Brewing plus",
                            list(scripts.TROUBLE_BREWING.keys) + list(extra))


def seats(deaths=None):
    deaths = deaths or {}
    return [{"name": f"P{i+1}", "claim": TWELVE[i], "death": deaths.get(i, ""),
             "certainty": "", "read": 0, "wake": ""} for i in range(12)]


class TheRegistry(SolverTest):

    def test_the_two_kinds_are_kept_apart(self):
        self.assertEqual(limits.UNSUPPORTED["Atheist"]["kind"],
                         limits.BREAKS_THE_BAG)
        self.assertEqual(limits.UNSUPPORTED["Legion"]["kind"],
                         limits.BREAKS_THE_TEAMS)

    def test_only_the_bag_breakers_have_a_signature(self):
        for name, entry in limits.UNSUPPORTED.items():
            with self.subTest(character=name):
                if entry["kind"] == limits.BREAKS_THE_BAG:
                    self.assertTrue(entry["signal"])
                else:
                    self.assertIsNone(entry["signal"],
                                      "nothing to detect means say nothing")

    def test_trouble_brewing_contains_none_of_them(self):
        self.assertEqual(limits.unsupported_on(scripts.TROUBLE_BREWING), {})

    def test_a_script_is_only_refused_for_the_team_breakers(self):
        with_atheist = plus("Atheist")
        self.assertEqual(limits.refuses(with_atheist), {},
                         "an Atheist game is not refused, only flagged")
        self.assertIn("Legion", limits.refuses(plus("Atheist", "Legion")))

    def test_every_entry_explains_itself(self):
        for name, entry in limits.UNSUPPORTED.items():
            with self.subTest(character=name):
                self.assertGreater(len(entry["why"]), 60,
                                   "a refusal has to say why")
                self.assertTrue(entry["short"])


class RefusingUpFront(SolverTest):

    def tearDown(self):
        app.SCRIPT = scripts.DEFAULT

    def test_a_script_with_legion_is_turned_away(self):
        app.SCRIPT = plus("Legion")
        reply = app.run_solve({"n_players": 12, "players": seats(), "infos": []})
        self.assertIn("error", reply)
        self.assertIn("Legion", reply["error"])
        self.assertNotIn("rows", reply)

    def test_an_atheist_on_the_script_is_not_turned_away(self):
        app.SCRIPT = plus("Atheist")
        reply = app.run_solve({"n_players": 12, "players": seats(), "infos": []})
        self.assertNotIn("error", reply)
        self.assertGreater(reply["valid"], 0)

    def test_trouble_brewing_is_never_turned_away(self):
        reply = app.run_solve({"n_players": 12, "players": seats(), "infos": []})
        self.assertNotIn("error", reply)


class WhenNothingFits(SolverTest):

    def broken(self):
        """Seat 10 claims Slayer, but a Virgin trigger says seat 10 is the
        Virgin. Good players do not lie, so nothing survives."""
        claims = {i: r for i, r in enumerate(TWELVE)}
        return game(12, claims=claims, deaths={2: "E1"},
                    infos=[VirginNomination(1, 9, nominator=2, triggered=True),
                           Empath(1, 4, count=1)])

    def test_the_board_really_does_fit_nothing(self):
        self.assertEqual(len(solved(self.broken())[0]), 0)

    def test_the_single_culprit_is_named(self):
        found = diagnose(self.broken())
        self.assertTrue(found["complete"])
        self.assertEqual(len(found["culprits"]), 1)
        self.assertIn("VirginNomination", found["culprits"][0]["label"])

    def test_a_board_that_fits_needs_no_diagnosis(self):
        reply = app.run_solve({"n_players": 12, "players": seats(), "infos": []})
        self.assertNotIn("diagnosis", reply)

    def test_the_reply_carries_the_shortlist(self):
        reply = app.run_solve({"n_players": 12, "players": seats({2: "E1"}),
                               "infos": [{"type": "VirginNomination", "night": 1,
                                          "player": 9, "nominator": 2,
                                          "triggered": True}]})
        self.assertEqual(reply["valid"], 0)
        self.assertIn("diagnosis", reply)
        self.assertTrue(reply["diagnosis"]["culprits"])

    def test_a_death_can_be_the_culprit_too(self):
        """Not just readings — anything recorded is a candidate.

        Built on a Slayer shot rather than on an executed Saint. The
        Saint used to make a board impossible on its own, and no longer
        does: a poisoned one is executed and play carries on. A shot that
        landed is a harder fact — it pins the target as the Demon or the
        Recluse — so pointing it at a seat the table has confirmed is
        something no world can explain.
        """
        claims = {i: r for i, r in enumerate(TWELVE)}
        claims[10] = "Slayer"
        state = game(12, claims=claims,
                     certainties={0: "confirmed", 1: "confirmed"},
                     deaths={0: "D2"},
                     infos=[SlayerShot(2, 10, target=0, died=True)])
        self.assertEqual(len(solved(state)[0]), 0,
                         "a confirmed Townsfolk cannot be shot as the Demon")
        kinds = {c["kind"] for c in diagnose(state)["culprits"]}
        self.assertTrue(kinds, "something has to be nameable")


class RaisingTheAtheist(SolverTest):

    def tearDown(self):
        app.SCRIPT = scripts.DEFAULT

    def contradictory(self):
        """Twelve seats all claiming Townsfolk. The bag needs two
        Outsiders and only the Drunk can hide behind a claim, so no legal
        world exists — and no single entry accounts for it, because there
        are no entries."""
        only_townsfolk = ["Washerwoman", "Librarian", "Investigator", "Chef",
                          "Empath", "FortuneTeller", "Undertaker", "Monk",
                          "Ravenkeeper", "Virgin", "Slayer", "Soldier"]
        return [{"name": f"P{i+1}", "claim": only_townsfolk[i], "death": "",
                 "certainty": "", "read": 0, "wake": ""} for i in range(12)]

    def test_with_no_culprit_the_possibility_is_raised(self):
        app.SCRIPT = plus("Atheist")
        reply = app.run_solve({"n_players": 12, "players": self.contradictory(),
                               "infos": []})
        self.assertEqual(reply["valid"], 0)
        named = [u["name"] for u in reply["diagnosis"].get("unsupported", [])]
        self.assertEqual(named, ["Atheist"])

    def test_it_is_not_raised_on_a_script_without_one(self):
        reply = app.run_solve({"n_players": 12, "players": self.contradictory(),
                               "infos": []})
        self.assertEqual(reply["valid"], 0)
        self.assertEqual(reply["diagnosis"].get("unsupported", []), [])

    def test_it_is_not_raised_when_one_entry_explains_everything(self):
        """A shortlist is the likelier story, so the exotic one stays
        out of the way."""
        app.SCRIPT = plus("Atheist")
        reply = app.run_solve({"n_players": 12, "players": seats({2: "E1"}),
                               "infos": [{"type": "VirginNomination", "night": 1,
                                          "player": 9, "nominator": 2,
                                          "triggered": True}]})
        self.assertTrue(reply["diagnosis"]["culprits"])
        self.assertEqual(reply["diagnosis"].get("unsupported", []), [])


if __name__ == "__main__":
    unittest.main()


class WhenTheClaimsCannotFillTheBag(SolverTest):
    """A common way to end up with nothing, and one the entry-by-entry
    search cannot see.

    Twelve seats all claiming Townsfolk, when every bag for that table
    needs two Outsiders and only the Drunk can sit behind a Townsfolk
    claim. Removing a reading will never fix it, so the shortlist comes
    back empty and says nothing useful — hence this being asked first.
    """

    TWELVE_TOWNSFOLK = ["Washerwoman", "Librarian", "Investigator", "Chef",
                        "Empath", "FortuneTeller", "Undertaker", "Monk",
                        "Ravenkeeper", "Virgin", "Slayer", "Soldier"]

    def board(self, claims, **kw):
        from botc.info import GameState
        return GameState(n_players=len(claims), script=scripts.TROUBLE_BREWING,
                         claims={i: r for i, r in enumerate(claims)}, **kw)

    def test_it_notices_and_says_why(self):
        from botc.solver import claims_cannot_fill_the_bag
        said = claims_cannot_fill_the_bag(self.board(self.TWELVE_TOWNSFOLK))
        self.assertIsNotNone(said)
        self.assertIn("2 Outsiders", said)

    def test_the_drunk_counts_once_and_not_twelve_times(self):
        """Every Townsfolk claim could individually be hiding the Drunk.
        Only one of them can actually be, which is what makes the bag
        unfillable — counting them one at a time made this never fire."""
        from botc.solver import claims_cannot_fill_the_bag
        said = claims_cannot_fill_the_bag(self.board(self.TWELVE_TOWNSFOLK))
        self.assertIn("only 1", said)

    def test_two_outsider_claims_are_enough(self):
        from botc.solver import claims_cannot_fill_the_bag
        fine = self.TWELVE_TOWNSFOLK[:10] + ["Recluse", "Saint"]
        self.assertIsNone(claims_cannot_fill_the_bag(self.board(fine)))

    def test_so_is_marking_somebody_as_hiding(self):
        from botc.solver import claims_cannot_fill_the_bag
        nearly = self.TWELVE_TOWNSFOLK[:11] + ["Saint"]
        self.assertIsNone(claims_cannot_fill_the_bag(
            self.board(nearly, certainties={0: "hiding"})))

    def test_the_page_is_told_instead_of_an_empty_shortlist(self):
        seats = [{"name": "", "claim": c, "death": "", "certainty": "",
                  "read": 0, "wake": ""} for c in self.TWELVE_TOWNSFOLK]
        reply = app.run_solve({"n_players": 12, "players": seats, "infos": []})
        self.assertEqual(reply["valid"], 0)
        self.assertIn("bag", reply["diagnosis"])
        self.assertEqual(reply["diagnosis"]["culprits"], [])
