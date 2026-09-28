"""The seam between the browser and the solver.

Everything here goes through `run_solve`, the same path the page uses, so
these catch the failures that only show up once JSON is involved.
"""

import unittest

from helpers import SolverTest, SPREAD                # sets up the import path
import app                                            # noqa: E402


def seats(n, claims=None, over=None):
    claims = SPREAD.get(n, []) if claims is None else claims
    over = over or {}
    out = []
    for i in range(n):
        seat = {"name": f"P{i+1}", "claim": claims[i] if i < len(claims) else "",
                "death": "", "certainty": "", "read": 0, "wake": ""}
        seat.update(over.get(i, {}))
        out.append(seat)
    return out


def solve(n=9, infos=None, claims=None, over=None):
    return app.run_solve({"n_players": n, "allow_good_lies": False,
                          "players": seats(n, claims, over),
                          "infos": infos or []})


class ResponseShape(SolverTest):

    def setUp(self):
        self.r = solve(9)

    def test_it_answers_at_all(self):
        self.assertNotIn("error", self.r)
        self.assertGreater(self.r["valid"], 0)
        self.assertLessEqual(self.r["valid"], self.r["legal"])

    def test_every_seat_gets_a_row(self):
        self.assertEqual(len(self.r["rows"]), 9)
        for i, row in enumerate(self.r["rows"]):
            self.assertEqual(row["player"], i)
            for key in ("evil_pct", "demon_pct", "drunk_pct", "lying_pct", "roles"):
                self.assertIn(key, row)

    def test_percentages_stay_in_range(self):
        for row in self.r["rows"]:
            for key in ("evil_pct", "demon_pct", "drunk_pct", "lying_pct"):
                self.assertBetween(row[key], 0.0, 100.0, f"{key}")
            for _role, pct in row["roles"]:
                self.assertBetween(pct, 0.0, 100.0)

    def test_samples_cover_every_seat(self):
        self.assertTrue(self.r["samples"])
        for world in self.r["samples"]:
            self.assertEqual(len(world), 9)

    def test_role_names_come_back_readable(self):
        """Regression: the display names were lost when the server moved
        onto the streaming analyzer, and 'Fortune Teller' shipped as
        'FortuneTeller' for several revisions."""
        names = {n for row in self.r["rows"] for n, _pc in row["roles"]}
        names |= {n.split(" (")[0] for w in self.r["samples"] for n in w}
        self.assertNotIn("FortuneTeller", names)
        self.assertNotIn("ScarletWoman", names)
        self.assertIn("Fortune Teller", names)


class Validation(SolverTest):

    def test_a_seat_that_does_not_exist_is_named_plainly(self):
        r = solve(9, infos=[{"type": "Washerwoman", "night": 1, "player": 0,
                             "a": 30, "b": 1, "role": "Chef"}])
        self.assertIn("error", r)
        self.assertIn("31", r["error"])

    def test_nobody_dies_on_the_first_night(self):
        r = solve(9, over={3: {"death": "N1"}})
        self.assertIn("error", r)
        self.assertIn("night 2", r["error"])

    def test_the_undertaker_has_nothing_to_learn_on_night_one(self):
        for kind in ("Undertaker", "Ravenkeeper"):
            with self.subTest(kind=kind):
                r = solve(9, infos=[{"type": kind, "night": 1, "player": 6,
                                     "target": 3, "role": "Imp"}])
                self.assertIn("error", r)

    def test_a_search_too_big_to_count_is_sampled_instead_of_refused(self):
        """This used to return "too many possibilities" and nothing else.
        An estimate with its uncertainty on the label beats a refusal."""
        r = solve(12, claims=[])
        self.assertNotIn("error", r)
        self.assertTrue(r["sampled"])
        self.assertGreater(r["valid"], 10 ** 6)
        self.assertGreater(r["ess"], 100)
        for row in r["rows"]:
            self.assertGreater(row["margin"], 0.0,
                               "a sampled figure must carry its uncertainty")

    def test_a_search_small_enough_to_count_is_counted(self):
        r = solve(9)
        self.assertFalse(r["sampled"])
        self.assertIsNone(r["ess"])
        for row in r["rows"]:
            self.assertEqual(row["margin"], 0.0, "an exact figure has no margin")

    def test_a_hopeless_table_returns_zero_rather_than_failing(self):
        """Twelve seats need two Outsiders, and only the Drunk can hide
        behind a Townsfolk claim. So all-Townsfolk cannot be a game."""
        only_townsfolk = ["Washerwoman", "Librarian", "Investigator", "Chef",
                          "Empath", "FortuneTeller", "Undertaker", "Monk",
                          "Ravenkeeper", "Virgin", "Slayer", "Soldier"]
        r = solve(12, claims=only_townsfolk)
        self.assertNotIn("error", r)
        self.assertEqual(r["valid"], 0)

    def test_one_character_wakes_once_a_night(self):
        r = solve(9, infos=[
            {"type": "Chef", "night": 1, "player": 3, "count": 0},
            {"type": "Chef", "night": 1, "player": 3, "count": 4}])
        self.assertIn("error", r)
        self.assertIn("once a night", r["error"])


class PayloadHandling(SolverTest):

    def test_every_information_type_survives_the_round_trip(self):
        rows = [
            {"type": "Washerwoman", "night": 1, "player": 0, "a": 1, "b": 2, "role": "Chef"},
            {"type": "Librarian", "night": 1, "player": 1, "a": "none", "b": 0, "role": "Butler"},
            {"type": "Investigator", "night": 1, "player": 2, "a": 3, "b": 4, "role": "Poisoner"},
            {"type": "Chef", "night": 1, "player": 3, "count": 1},
            {"type": "Empath", "night": 1, "player": 4, "count": 1},
            {"type": "FortuneTeller", "night": 1, "player": 5, "a": 0, "b": 1, "yes": False},
            {"type": "Undertaker", "night": 2, "player": 6, "target": 3, "role": "Spy"},
            {"type": "Ravenkeeper", "night": 2, "player": 6, "target": 3, "role": "Imp"},
            {"type": "SlayerShot", "night": 2, "player": 4, "target": 3, "died": False},
            {"type": "VirginNomination", "night": 1, "player": 4, "nominator": 3,
             "triggered": False},
        ]
        for row in rows:
            with self.subTest(kind=row["type"]):
                self.assertIsNotNone(app.build_info(row))

    def test_the_old_virgin_name_still_loads(self):
        info = app.build_info({"type": "VirginTrigger", "night": 1,
                               "player": 4, "nominator": 3})
        self.assertTrue(info.triggered)

    def test_seat_settings_reach_the_solver(self):
        plain = solve(9)["rows"][4]["evil_pct"]
        read = solve(9, over={4: {"read": 3}})["rows"][4]["evil_pct"]
        confirmed = solve(9, over={4: {"certainty": "confirmed"}})["rows"][4]["evil_pct"]
        woken = solve(9, over={4: {"wake": "never"}})["rows"][4]["evil_pct"]
        self.assertRises(plain, read)
        self.assertPct(confirmed, 0.0, 0.01)
        self.assertNotEqual(round(woken, 2), round(plain, 2))

    def test_only_one_seat_can_be_you(self):
        r = solve(9, over={0: {"certainty": "self"}, 1: {"certainty": "self"}})
        cleared = [row["evil_pct"] for row in r["rows"][:2]]
        self.assertPct(cleared[0], 0.0, 0.01)
        self.assertGreater(cleared[1], 0.0)

    def test_junk_in_the_read_field_is_shrugged_off(self):
        r = solve(9, over={4: {"read": "not a number"}})
        self.assertNotIn("error", r)


class Meta(SolverTest):

    def test_the_page_gets_what_it_needs_to_build_its_menus(self):
        for key in ("setup", "wake_patterns", "wake_labels", "catalogue",
                    "built_in", "script"):
            self.assertIn(key, app.META)
        self.assertEqual(set(app.META["wake_labels"]),
                         set(app.META["wake_patterns"]))
        self.assertEqual(len(app.META["setup"]), 11)

    def test_the_script_carries_its_own_lists(self):
        """They moved off the top level, because they depend on which
        script is being played."""
        script = app.META["script"]
        for key in ("townsfolk", "outsiders", "minions", "demons", "display",
                    "wake_roles", "info_types", "characters"):
            self.assertIn(key, script)
        self.assertEqual(script["name"], "Trouble Brewing")

    def test_display_names_are_spelled_out(self):
        display = app.META["script"]["display"]
        self.assertEqual(display["FortuneTeller"], "Fortune Teller")
        self.assertEqual(display["ScarletWoman"], "Scarlet Woman")


if __name__ == "__main__":
    unittest.main()


class WhatHappenedToASeat(SolverTest):
    """One list per seat, in the order things happened.

    It used to be three fields: a status, a list of extra deaths and a
    list of returns, the last two typed in as phase codes. A seat can go
    down, come back and go down again, and none of that should need
    anybody to know what "N4" means.
    """

    TWELVE = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
              "FortuneTeller", "Undertaker", "Monk", "Ravenkeeper", "Slayer",
              "Recluse", "Saint"]

    def seats(self, events=None):
        events = events or {}
        return [{"name": "", "claim": self.TWELVE[i],
                 "events": events.get(i, []), "certainty": "", "read": 0,
                 "wake": ""} for i in range(12)]

    def solve(self, events=None, **kw):
        return app.run_solve({"n_players": 12, "players": self.seats(events),
                              "infos": [], **kw})

    def test_a_seat_with_nothing_recorded_is_alive(self):
        self.assertGreater(self.solve()["valid"], 0)

    def test_one_death_reads_the_same_as_it_used_to(self):
        as_events = self.solve({3: ["N2"]})
        old_style = app.run_solve({
            "n_players": 12, "infos": [],
            "players": [dict(s, death="N2" if i == 3 else "")
                        for i, s in enumerate(self.seats())]})
        self.assertEqual(as_events["valid"], old_style["valid"])
        self.assertEqual([r["evil_pct"] for r in as_events["rows"]],
                         [r["evil_pct"] for r in old_style["rows"]])

    def test_an_execution_and_a_death_are_still_separate_facts(self):
        died = self.solve({3: ["X1"]})
        walked = self.solve({3: ["S1"]})
        self.assertGreater(died["valid"], 0)
        self.assertEqual(walked["valid"], 0,
                         "nothing on Trouble Brewing survives an execution")

    def test_two_seats_cannot_be_executed_on_one_day(self):
        reply = self.solve({3: ["X1"], 5: ["X1"]})
        self.assertIn("error", reply)
        self.assertIn("once a day", reply["error"])

    def test_a_seat_can_go_down_come_back_and_go_down_again(self):
        from botc.catalogue import CHARACTERS
        from botc import scripts
        chars = [CHARACTERS[k].id for k in scripts.BAD_MOON_RISING.keys]
        claims = ["Grandmother", "Sailor", "Chambermaid", "Professor",
                  "Innkeeper", "Gambler", "Gossip", "Tinker", "Moonchild"]
        seats = [{"name": "", "claim": c, "events": [], "certainty": "",
                  "read": 0, "wake": ""} for c in claims]
        seats[2]["events"] = ["N2", "R4", "N6"]
        reply = app.run_solve({
            "n_players": 9, "players": seats, "infos": [],
            "script": {"name": "Bad Moon Rising", "characters": chars}})
        self.assertNotIn("error", reply)
        self.assertGreater(reply["valid"], 0)

    def test_the_old_three_field_shape_still_loads(self):
        """Saved games predate this. They have to keep working."""
        old = [dict(s, death="N2" if i == 3 else "",
                    died=["N5"] if i == 3 else [],
                    raised=["N4"] if i == 3 else [])
               for i, s in enumerate(self.seats())]
        for seat in old:
            seat.pop("events", None)
        reply = app.run_solve({"n_players": 12, "players": old, "infos": []})
        self.assertNotIn("error", reply)


class WhatBecameOfEachReading(SolverTest):
    """Four outcomes, not two.

    A reading can hold; or be false and need excusing; or have been made
    up by the Storyteller for somebody holding the wrong token; or have no
    possible source in the world at all. The middle two are the speaker
    being wrong *without lying*, which is the distinction that matters
    when the table is trying to work out whether somebody is drunk.
    """

    NINE = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
            "FortuneTeller", "Undertaker", "Recluse", "Saint"]

    def solve(self, infos, suspect=None):
        seats = [{"name": "", "claim": c, "events": [], "certainty": "",
                  "read": 0, "wake": "", "suspect": i == suspect}
                 for i, c in enumerate(self.NINE)]
        return app.run_solve({"n_players": 9, "players": seats,
                              "infos": infos})

    def empath(self, count):
        return [{"type": "Empath", "night": 1, "player": 4, "count": count}]

    def test_every_reading_is_accounted_for(self):
        got = self.solve(self.empath(1) +
                         [{"type": "Chef", "night": 1, "player": 3,
                           "count": 1}])
        self.assertEqual(len(got["readings"]), 2)
        for row in got["readings"]:
            with self.subTest(row=row["index"]):
                self.assertPct(sum(row["shares"].values()), 1.0, 1e-6)

    def test_a_reading_that_fits_mostly_holds(self):
        got = self.solve(self.empath(1))
        self.assertGreater(got["readings"][0]["shares"].get("held", 0), 0.4)

    def test_one_that_barely_fits_mostly_does_not(self):
        """Two evil neighbours on night one is a big claim, and most of
        the weight ends up somewhere other than "they were right"."""
        got = self.solve(self.empath(2))
        self.assertLess(got["readings"][0]["shares"].get("held", 0), 0.15)

    def test_the_three_ways_of_being_wrong_are_told_apart(self):
        shares = self.solve(self.empath(2))["readings"][0]["shares"]
        for mark in ("made up", "excused", "invented"):
            with self.subTest(outcome=mark):
                self.assertGreater(shares.get(mark, 0), 0.01)

    def test_marking_a_seat_shifts_it_towards_the_wrong_token(self):
        """The marker is a suspicion about their information, not their
        side — so it should move "made up" up and evil *down*."""
        plain = self.solve(self.empath(2))
        marked = self.solve(self.empath(2), suspect=4)
        self.assertGreater(marked["readings"][0]["shares"]["made up"],
                           plain["readings"][0]["shares"]["made up"])
        self.assertGreater(marked["rows"][4]["drunk_pct"],
                           plain["rows"][4]["drunk_pct"])
        self.assertLess(marked["rows"][4]["evil_pct"],
                        plain["rows"][4]["evil_pct"])

    def test_marking_nobody_changes_nothing(self):
        plain = self.solve(self.empath(1))
        marked = self.solve(self.empath(1), suspect=None)
        self.assertEqual(plain["rows"][4]["drunk_pct"],
                         marked["rows"][4]["drunk_pct"])


class TheDayEnding(SolverTest):
    """An execution ends a day; so does the town deciding not to.

    The page needs to know which day it is to offer the right statuses,
    and it works that out from what has been recorded. Before this, an
    execution advanced nothing — so recording one on day two left the
    board offering day two's statuses forever.
    """

    NINE = ["Grandmother", "Sailor", "Chambermaid", "Exorcist", "Innkeeper",
            "Gambler", "Gossip", "Tinker", "Moonchild"]

    def solve(self, events=None, done=None):
        from botc.catalogue import CHARACTERS
        from botc import scripts
        chars = [CHARACTERS[k].id for k in scripts.BAD_MOON_RISING.keys]
        seats = [{"name": "", "claim": c, "events": (events or {}).get(i, []),
                  "certainty": "", "read": 0, "wake": ""}
                 for i, c in enumerate(self.NINE)]
        return app.run_solve({
            "n_players": 9, "players": seats, "infos": [],
            "days_done": done or [],
            "script": {"name": "Bad Moon Rising", "characters": chars}})

    def test_the_server_accepts_it(self):
        self.assertNotIn("error", self.solve(done=[2, 3]))

    def test_it_changes_no_answer_by_itself(self):
        plain = self.solve()
        marked = self.solve(done=[2, 3])
        self.assertEqual(plain["valid"], marked["valid"])
        self.assertEqual([r["evil_pct"] for r in plain["rows"]],
                         [r["evil_pct"] for r in marked["rows"]])

    def test_an_execution_is_still_recorded_the_same_way(self):
        got = self.solve(events={2: ["X2"]})
        self.assertNotIn("error", got)
        self.assertGreater(got["valid"], 0)
