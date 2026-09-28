"""Scripts as data: the catalogue, the selections made from it, and the
files people actually pass around.

A script is a name and a set of characters, and nothing more. The three
published ones are three such selections; custom scripts are the general
case rather than a mode. These check that holds — including against a
real script file with characters from four different sources in it.
"""

import json
import os
import unittest

from helpers import SolverTest, game               # sets up the import path
import app                                         # noqa: E402
from botc import scripts                           # noqa: E402
from botc.catalogue import CHARACTERS, lookup, normalise  # noqa: E402
from botc.info import Empath, GameState            # noqa: E402
from botc.roles import TEAM, evil_registrations, registers_as_role  # noqa: E402
from botc.solver import solve                      # noqa: E402
from botc.worlds import enumerate_worlds           # noqa: E402

# The file in the message: Trouble Brewing plus characters from Bad Moon
# Rising, Sects & Violets and the experimental set.
EASTER = json.dumps([
    {"id": "_meta", "author": "AnqeR und Shellynax", "name": "Easter Trouble"},
    "noble", "washerwoman", "librarian", "clockmaker", "grandmother",
    "slayer", "artist", "empath", "fortuneteller", "monk", "undertaker",
    "ravenkeeper", "virgin", "mayor", "ogre", "saint", "recluse", "drunk",
    "poisoner", "spy", "scarletwoman", "marionette", "baron", "imp",
])


class TheCatalogue(SolverTest):

    def test_a_character_is_findable_however_it_is_written(self):
        for written in ("fortuneteller", "FortuneTeller", "Fortune Teller",
                        "fortune_teller", "FORTUNE TELLER"):
            with self.subTest(written=written):
                self.assertEqual(lookup(written).key, "FortuneTeller")

    def test_something_nobody_has_heard_of_is_not_invented(self):
        self.assertIsNone(lookup("Cabbage Merchant"))

    def test_team_belongs_to_the_character_not_the_script(self):
        """Which is why it stays a single global table."""
        self.assertEqual(TEAM["Imp"], "demon")
        self.assertEqual(TEAM["Grandmother"], "townsfolk")
        self.assertEqual(TEAM["Marionette"], "minion")

    def test_misregistration_is_read_from_the_record(self):
        self.assertTrue(registers_as_role("Recluse", "Imp"))
        self.assertFalse(registers_as_role("Recluse", "Monk"))
        self.assertTrue(registers_as_role("Spy", "Monk"))
        self.assertEqual(evil_registrations("Chef"), (False,))
        self.assertEqual(sorted(evil_registrations("Recluse")), [False, True])

    def test_unmodelled_characters_admit_it(self):
        # The Ogre and the Marionette stood here until phase 2 built
        # them; the Mutant and the Cerenovus are next in line.
        for key in ("Artist", "Mutant", "Cerenovus"):
            with self.subTest(character=key):
                self.assertFalse(CHARACTERS[key].modelled)
                self.assertTrue(CHARACTERS[key].note)


class ScriptsAreSelections(SolverTest):

    def test_trouble_brewing_is_one_selection_among_possible_others(self):
        tb = scripts.TROUBLE_BREWING
        self.assertEqual(len(tb.keys), 22)
        self.assertEqual(len(tb.townsfolk), 13)
        self.assertEqual(len(tb.outsiders), 4)
        self.assertEqual(len(tb.minions), 4)
        self.assertEqual(len(tb.demons), 1)
        self.assertEqual(set(tb.setup_modifiers), {"Baron"})

    def test_a_script_without_the_baron_has_one_bag(self):
        from botc.worlds import _bags
        lean = scripts.from_ids("Lean", [
            "washerwoman", "librarian", "investigator", "chef", "empath",
            "recluse", "saint", "poisoner", "spy", "imp"])
        self.assertEqual(lean.setup_modifiers, {})
        self.assertEqual(len(_bags(9, lean)), 1)

    def test_a_script_missing_a_team_is_not_playable(self):
        broken = scripts.from_ids("No demon", ["washerwoman", "poisoner"])
        self.assertFalse(broken.is_playable())
        self.assertIn("unplayable", [c["kind"] for c in broken.complaints()])

    def test_the_solver_only_deals_what_is_in_the_bag(self):
        lean = scripts.from_ids("Lean", [
            "washerwoman", "librarian", "investigator", "chef", "empath",
            "recluse", "saint", "poisoner", "spy", "imp"])
        claims = {0: "Washerwoman", 1: "Librarian", 2: "Investigator",
                  3: "Chef", 4: "Empath", 5: "Recluse", 6: "Saint"}
        seen = set()
        for world in enumerate_worlds(7, claims, script=lean, max_worlds=4000):
            seen.update(world.roles)
        self.assertTrue(seen)
        self.assertLessEqual(seen, set(lean.keys),
                             "no character from off the script")
        self.assertNotIn("Baron", seen)
        self.assertNotIn("Drunk", seen)


class ReadingAScriptFile(SolverTest):

    def setUp(self):
        self.script = scripts.from_json(EASTER)

    def test_the_name_and_author_come_across(self):
        self.assertEqual(self.script.name, "Easter Trouble")
        self.assertEqual(self.script.author, "AnqeR und Shellynax")

    def test_characters_from_four_sources_all_land(self):
        keys = set(self.script.keys)
        self.assertIn("Washerwoman", keys, "Trouble Brewing")
        self.assertIn("Grandmother", keys, "Bad Moon Rising")
        self.assertIn("Clockmaker", keys, "Sects & Violets")
        self.assertIn("Marionette", keys, "experimental")

    def test_the_teams_add_up(self):
        self.assertEqual(len(self.script.townsfolk), 14)
        self.assertEqual(len(self.script.outsiders), 4)
        self.assertEqual(len(self.script.minions), 5)
        self.assertEqual(len(self.script.demons), 1)

    def test_nothing_in_it_was_unrecognised(self):
        self.assertEqual(self.script.unknown, ())

    def test_it_says_which_abilities_it_cannot_reason_about(self):
        kinds = {c["kind"]: c for c in self.script.complaints()}
        # Nothing on Easter Trouble is unbuilt any more: the Ogre and the
        # Marionette came off this list in phase 2 (28.09.2026), and all
        # that is left to say is that the Artist is recorded, not weighed.
        self.assertNotIn("unmodelled", kinds)
        # The Grandmother came off this list when it was implemented.
        # The Clockmaker came off this list when Sects & Violets arrived
        # and its reading was actually checked. The Artist came off it
        # later for a different reason: it is *recorded* rather than
        # unbuilt, and those are now said separately.
        # The Noble came off this list when its first-night reading was
        # actually checked — three players, exactly one evil **by
        # registration**, so a Spy may sit among the two good ones.
        self.assertEqual(kinds["recorded"]["characters"], ["Artist"])

    def test_a_character_nobody_knows_is_reported_not_dropped_silently(self):
        odd = scripts.from_json(json.dumps(["washerwoman", "imp", "poisoner",
                                            "cabbagemerchant"]))
        self.assertEqual(odd.unknown, ("cabbagemerchant",))
        self.assertIn("unknown", [c["kind"] for c in odd.complaints()])

    def test_only_the_readings_on_the_script_are_offered(self):
        """Easter Trouble has no Investigator and no Chef, so their rows
        are not on the menu."""
        offered = app.load_script({"json": EASTER})["script"]["info_types"]
        self.assertIn("Washerwoman", offered)
        self.assertNotIn("Investigator", offered)
        self.assertNotIn("Chef", offered)

    def test_a_wrapped_file_is_read_too(self):
        wrapped = json.dumps({"characters": ["washerwoman", "imp", "poisoner"]})
        self.assertIn("Imp", scripts.from_json(wrapped).keys)


class SolvingOnAnotherScript(SolverTest):

    def script(self):
        return scripts.from_json(EASTER)

    def test_a_board_solves_on_it(self):
        claims = {0: "Washerwoman", 1: "Librarian", 2: "Empath",
                  3: "FortuneTeller", 4: "Monk", 5: "Recluse", 6: "Saint"}
        state = GameState(n_players=7, script=self.script(), claims=claims,
                          infos=[Empath(1, 2, count=1)])
        _all, valid = solve(state)
        self.assertTrue(valid)

    def test_the_extra_characters_can_turn_up_in_worlds(self):
        state = GameState(n_players=9, script=self.script(),
                          claims={0: "Washerwoman", 1: "Librarian"})
        seen = set()
        for world in enumerate_worlds(9, state.claims, script=state.script,
                                      max_worlds=3000):
            seen.update(world.roles)
        self.assertTrue(seen & {"Grandmother", "Clockmaker", "Noble", "Artist"},
                        "characters from the wider script should be dealt")

    def test_a_state_defaults_to_trouble_brewing(self):
        self.assertEqual(GameState(n_players=7).script.name, "Trouble Brewing")


class PortableSaves(SolverTest):
    """A saved game carries its script, so a board stays readable after
    the custom script it was played on has been forgotten."""

    def test_a_board_can_be_solved_from_the_script_it_carries(self):
        seats = [{"name": "", "claim": c, "death": "", "certainty": "",
                  "read": 0, "wake": ""}
                 for c in ["Washerwoman", "Librarian", "Empath",
                           "FortuneTeller", "Monk", "Recluse", "Saint"]]
        carried = app.load_script({"json": EASTER})["script"]
        reply = app.run_solve({
            "n_players": 7, "players": seats, "infos": [],
            "script": {"name": carried["name"],
                       "characters": carried["characters"]},
        })
        self.assertNotIn("error", reply)
        self.assertGreater(reply["valid"], 0)

    def test_without_one_it_falls_back_rather_than_failing(self):
        seats = [{"name": "", "claim": c, "death": "", "certainty": "",
                  "read": 0, "wake": ""}
                 for c in ["Washerwoman", "Librarian", "Investigator", "Chef",
                           "Empath", "Recluse", "Saint"]]
        reply = app.run_solve({"n_players": 7, "players": seats, "infos": []})
        self.assertNotIn("error", reply)

    def test_the_carried_script_actually_decides_the_bag(self):
        """A claim that only exists on the carried script has to work."""
        seats = [{"name": "", "claim": c, "death": "", "certainty": "",
                  "read": 0, "wake": ""}
                 for c in ["Grandmother", "Librarian", "Empath",
                           "FortuneTeller", "Monk", "Recluse", "Saint"]]
        carried = app.load_script({"json": EASTER})["script"]
        with_script = app.run_solve({
            "n_players": 7, "players": seats, "infos": [],
            "script": {"name": carried["name"],
                       "characters": carried["characters"]}})
        without = app.run_solve({"n_players": 7, "players": seats, "infos": []})
        self.assertGreater(with_script["valid"], 0)
        self.assertIn("error", without)
        self.assertIn("Grandmother", without["error"],
                      "a claim off the script is named, not silently kept")


if __name__ == "__main__":
    unittest.main()


class SomebodyWhoDoesNotKnowWhatTheyAre(SolverTest):
    """The Marionette, which is why "is it evil" was the wrong question.

    Trouble Brewing has one character whose holder was handed the wrong
    token, and it is good — so "evil" and "knows what it is" never came
    apart, and four places asked the first when they meant the second. A
    Marionette is evil and still believes every word it says.

    Its ability is not modelled. What is checked here is that the machinery
    around it stops treating it as a knowing bluffer.
    """

    KEYS = ["washerwoman", "librarian", "soldier", "empath", "monk", "mayor",
            "recluse", "saint", "drunk", "marionette", "poisoner", "imp"]

    def script(self):
        return scripts.from_ids("With a Marionette", self.KEYS)

    def options(self, claim, wake=None):
        from botc.worlds import _candidates
        return _candidates(claim, False, "", None, wake, self.script())

    # ------------------------------------------------------------------
    def test_a_believer_is_never_dealt_without_a_token(self):
        """Whoever holds one was handed something to believe in."""
        for role, token in self.options("Soldier"):
            if role in ("Drunk", "Marionette"):
                self.assertIsNotNone(token, f"{role} with no token")

    def test_a_believer_is_held_to_the_schedule_it_thinks_it_has(self):
        """A Marionette holding the Soldier token believes it never wakes,
        and says so. Being evil underneath does not free it to claim
        otherwise, the way a knowing bluffer would be freed."""
        never = {r for r, _t in self.options("Soldier", "never")}
        every = {r for r, _t in self.options("Soldier", "every")}
        self.assertIn("Marionette", never)
        self.assertNotIn("Marionette", every)
        self.assertIn("Imp", every, "a knowing bluffer says what it likes")

    def test_it_may_only_claim_the_token_it_was_given(self):
        """Claiming anything else would be a deliberate lie from somebody
        who thinks they are good."""
        for role, token in self.options("Soldier"):
            if role == "Marionette":
                self.assertEqual(token, "Soldier")

    def test_it_can_be_handed_an_outsider_where_the_drunk_cannot(self):
        from botc.roles import believed_tokens
        script = self.script()
        self.assertEqual(set(believed_tokens("Drunk", script)),
                         set(script.townsfolk))
        self.assertIn("Recluse", believed_tokens("Marionette", script))

    def test_naming_its_token_is_not_a_lie(self):
        """It believes it. The good-lie penalties and the bluff-collision
        penalty all key off lying, so getting this wrong would have
        charged a Marionette for a claim it holds sincerely."""
        from botc.solver import is_lying
        from botc.worlds import World
        roles = ["Washerwoman", "Marionette", "Empath", "Recluse", "Saint",
                 "Drunk", "Poisoner", "Imp", "Soldier"]
        believes = [None, "Soldier", None, None, None, "Empath", None,
                    None, None]
        world = World(tuple(roles), tuple(believes))
        state = GameState(n_players=9, script=self.script(),
                          claims={1: "Soldier", 5: "Empath", 0: "Washerwoman"})
        self.assertFalse(is_lying(world, state, 1), "the Marionette")
        self.assertFalse(is_lying(world, state, 5), "the Drunk")
        self.assertFalse(is_lying(world, state, 0), "an honest Townsfolk")

    def test_the_solver_still_runs_on_a_script_containing_one(self):
        claims = {0: "Washerwoman", 1: "Librarian", 2: "Empath", 3: "Monk",
                  4: "Mayor", 5: "Recluse", 6: "Saint"}
        state = GameState(n_players=9, script=self.script(), claims=claims,
                          infos=[Empath(1, 2, count=1)])
        _all, valid = solve(state)
        self.assertTrue(valid)
        self.assertTrue(any("Marionette" in w.roles for w in valid),
                        "it should turn up in some of them")


class ABagTooShallow(SolverTest):
    """A script with too few of a team returns nothing and says nothing.

    This was found by writing a Marionette test on a script with three
    Townsfolk and wondering why a seven-player game produced no worlds.
    """

    SMALL = ["washerwoman", "soldier", "empath", "recluse", "saint",
             "drunk", "poisoner", "imp"]

    def test_it_says_so_rather_than_returning_nothing(self):
        script = scripts.from_ids("Too small", self.SMALL)
        short = script.too_small_for(9)
        self.assertTrue(short)
        self.assertEqual(short[0]["team"], "townsfolk")
        self.assertIn("too small", [c["kind"] for c in script.complaints(9)])

    def test_a_deep_enough_bag_says_nothing(self):
        self.assertEqual(scripts.TROUBLE_BREWING.too_small_for(15), [])
        self.assertEqual(
            [c for c in scripts.TROUBLE_BREWING.complaints(15)
             if c["kind"] == "too small"], [])

    def test_it_accounts_for_what_a_setup_changer_could_ask_for(self):
        """The Baron wants two more Outsiders than the table size says,
        so a script with two Outsiders is short even when the plain
        distribution fits."""
        thin = scripts.from_ids("Thin outsiders", [
            "washerwoman", "librarian", "investigator", "chef", "empath",
            "fortuneteller", "undertaker", "monk", "ravenkeeper",
            "recluse", "saint", "poisoner", "baron", "imp"])
        self.assertEqual(scripts.TROUBLE_BREWING.too_small_for(9), [])
        self.assertTrue(any(s["team"] == "outsider"
                            for s in thin.too_small_for(9)))

    def test_the_page_is_told_at_the_table_size_being_played(self):
        got = app.load_script({"characters": self.SMALL, "name": "Too small",
                               "n_players": 9})["script"]
        self.assertIn("too small", [c["kind"] for c in got["complaints"]])
        fine = app.load_script({"characters": self.SMALL, "name": "Too small",
                                "n_players": 5})["script"]
        self.assertNotIn("too small", [c["kind"] for c in fine["complaints"]])


class OnTheTableRatherThanInTheBag(SolverTest):
    """The Fabled, and the Sentinel in particular.

    A Fabled is not dealt to anybody. The Storyteller puts it out and
    shows everyone, so *whether it is in play* is public and gets told to
    the solver. What it did is hidden, and that is the whole point of the
    Sentinel: it may add an Outsider, remove one, or change nothing, and
    the table cannot tell which.
    """

    def script(self):
        return scripts.from_ids(
            "Trouble Brewing with a Sentinel",
            list(scripts.TROUBLE_BREWING.keys) + ["sentinel"])

    def claims(self):
        return {i: r for i, r in enumerate([
            "Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
            "FortuneTeller", "Undertaker", "Monk", "Ravenkeeper", "Virgin",
            "Recluse", "Saint"])}

    # ------------------------------------------------------------------
    def test_it_is_never_dealt_to_a_seat(self):
        from botc.worlds import enumerate_worlds
        script = self.script()
        self.assertIn("Sentinel", script.fabled)
        self.assertNotIn("Sentinel", script.seated_keys)
        for world in enumerate_worlds(12, self.claims(), script=script,
                                      fabled=("Sentinel",), max_worlds=3000):
            self.assertNotIn("Sentinel", world.roles)

    def test_being_on_the_script_is_not_being_in_play(self):
        """Available is not the same as chosen, so a script listing one
        changes nothing until it is ticked."""
        from botc.worlds import _bags
        script = self.script()
        self.assertEqual(_bags(12, script, ()),
                         _bags(12, scripts.TROUBLE_BREWING, ()))

    def test_in_play_it_offers_three_answers_and_no_way_to_tell(self):
        from botc.worlds import _bags
        shapes = {(c["townsfolk"], c["outsider"])
                  for _p, c in _bags(12, self.script(), ("Sentinel",))}
        # An Outsider more or fewer swaps with a Townsfolk. The table
        # still seats twelve either way.
        self.assertIn((8, 1), shapes, "one fewer Outsider")
        self.assertIn((7, 2), shapes, "unchanged")
        self.assertIn((6, 3), shapes, "one more")

    def test_there_is_no_it_stayed_out_branch(self):
        """Unlike the Baron, which is in the bag if and only if it shifted
        the counts. A Fabled that is out was never on the table at all,
        and one that is on the table is in play whatever it did."""
        from botc.worlds import _bags
        for _present, counts in _bags(12, self.script(), ("Sentinel",)):
            self.assertIn(counts["outsider"], (1, 2, 3, 4))

    def test_the_ceiling_is_the_script_not_a_number(self):
        """How many Outsiders can be in play is however many Outsider
        characters the script has, because each is unique. There is no
        fixed limit — a script with eight can seat eight."""
        from botc.catalogue import CHARACTERS, Character
        from botc.worlds import _bags

        # Put back exactly as found rather than deleted. These four are
        # real Sects & Violets Outsiders now, and deleting them took them
        # out of the live catalogue for every test that ran afterwards.
        narrow = self.script()
        made_up = ("Klutz", "Sweetheart", "Mutant", "Barber")
        was = {k: CHARACTERS.get(k) for k in made_up}
        for extra in made_up:
            CHARACTERS[extra] = Character(extra, extra.lower(), extra,
                                          "outsider", frozenset({"never"}))
        try:
            wide = scripts.from_ids("More outsiders", list(narrow.keys) + [
                "klutz", "sweetheart", "mutant", "barber"])
            self.assertEqual(len(narrow.outsiders), 4)
            self.assertEqual(len(wide.outsiders), 8)
            most = lambda sc: max(c["outsider"] for _p, c
                                  in _bags(12, sc, ("Sentinel",)))
            self.assertEqual(most(narrow), 4, "all four it has")
            self.assertEqual(most(wide), 5, "Baron plus the Sentinel")
        finally:
            for extra, before in was.items():
                if before is None:
                    del CHARACTERS[extra]
                else:
                    CHARACTERS[extra] = before

    def test_every_bag_still_seats_the_whole_table(self):
        """The bug this guards: the Sentinel moved the Outsider count
        without moving the Townsfolk count back, so a twelve-player game
        was being dealt bags for eleven and thirteen. It went unnoticed
        because a wrong-sized bag still produces worlds — just not worlds
        of that game.
        """
        from botc.worlds import _bags
        for n in (5, 7, 12, 15):
            for _present, counts in _bags(n, self.script(), ("Sentinel",)):
                with self.subTest(players=n, bag=counts):
                    self.assertEqual(sum(counts.values()), n)

    def test_a_modifier_that_does_not_balance_is_refused(self):
        """Rather than quietly dealing the wrong number of people."""
        from botc.catalogue import CHARACTERS, Character
        from botc.worlds import _bags
        lopsided_before = CHARACTERS.get("Lopsided")
        CHARACTERS["Lopsided"] = Character(
            "Lopsided", "lopsided", "Lopsided", "fabled",
            frozenset({"never"}), seated=False, setup=({"outsider": 1},))
        try:
            odd = scripts.from_ids("Lopsided", list(self.script().keys)
                                   + ["lopsided"])
            self.assertEqual(_bags(12, odd, ("Lopsided",)), [],
                             "an unbalanced shift leaves no legal bag")
        finally:
            if lopsided_before is None:
                del CHARACTERS["Lopsided"]
            else:
                CHARACTERS["Lopsided"] = lopsided_before

    def test_it_costs_worlds_without_giving_information(self):
        """Which is what a Sentinel is for. It buys uncertainty."""
        script, claims = self.script(), self.claims()
        without = GameState(n_players=12, script=script, claims=claims)
        with_it = GameState(n_players=12, script=script, claims=claims,
                            fabled=("Sentinel",))
        self.assertGreater(len(solve(with_it)[1]), len(solve(without)[1]) * 2)

    def test_a_fabled_not_on_the_script_is_ignored(self):
        script = scripts.TROUBLE_BREWING
        self.assertEqual(script.fabled_in_play(["Sentinel"]), ())

    def test_the_page_is_offered_the_ones_it_can_tick(self):
        got = app.load_script({
            "characters": list(scripts.TROUBLE_BREWING.keys) + ["sentinel"],
            "name": "TB plus", "n_players": 12})["script"]
        self.assertEqual([f["key"] for f in got["fabled"]], ["Sentinel"])
        self.assertNotIn("Sentinel", got["characters"],
                         "not offered as something a seat could claim")
        self.assertTrue(got["fabled"][0]["note"])

    def test_the_choice_reaches_the_solver(self):
        chars = list(scripts.TROUBLE_BREWING.keys) + ["sentinel"]
        seats = [{"name": "", "claim": c, "death": "", "certainty": "",
                  "read": 0, "wake": ""} for c in self.claims().values()]
        board = {"n_players": 12, "players": seats, "infos": [],
                 "script": {"name": "TB plus", "characters": chars}}
        off = app.run_solve(dict(board, fabled=[]))
        on = app.run_solve(dict(board, fabled=["Sentinel"]))
        self.assertGreater(on["valid"], off["valid"] * 2)


class TheCatalogueSurvivesTheTests(SolverTest):
    """No test may leave the catalogue changed.

    Three tests registered made-up characters to prove that adding one
    needs no code change, and cleaned up with `del`. That was written
    when those names belonged to nobody — and every one of them later
    became a real character: the Godfather with Bad Moon Rising, and the
    Klutz, Sweetheart, Mutant and Barber with Sects & Violets. From then
    on those tests were quietly deleting real entries from the live
    catalogue, and everything running afterwards saw a script with a hole
    in it.

    Nothing caught it for two whole scripts, because the damage only
    shows when something built at *import* time goes looking for a
    character a later test took away. So this asks the question directly
    rather than waiting for a symptom.
    """

    def test_no_test_file_leaves_it_changed(self):
        import unittest as ut
        from botc.catalogue import CHARACTERS

        before = {k: c for k, c in CHARACTERS.items()}
        suite = ut.TestLoader().loadTestsFromNames(
            ["test_seams", "test_transitions", "test_limits"])
        ut.TextTestRunner(stream=open(os.devnull, "w"), verbosity=0).run(suite)

        self.assertEqual(sorted(CHARACTERS), sorted(before),
                         "a test added or removed a character and left it")
        for key, character in before.items():
            with self.subTest(character=key):
                self.assertIs(CHARACTERS[key], character,
                              "a test replaced a character and left it")

    def test_every_built_in_script_still_builds(self):
        """The symptom the above prevents: a script assembled at import
        time cannot be rebuilt once a character it names has gone."""
        for name, script in scripts.BUILT_IN.items():
            with self.subTest(script=name):
                self.assertEqual(len(script.characters()), len(script.keys))


class HowFarEachCharacterIsReasonedAbout(SolverTest):
    """Three states, not two.

    `modelled` was doing two jobs at once: "not built yet" and "built as
    far as it will ever be". A Savant sitting in the same list as an
    unstarted Demon tells somebody the wrong thing about both — and it
    had me reporting three finished characters as a backlog.
    """

    def test_the_three_states_exist(self):
        from botc.catalogue import FULLY, NOT, PARTLY
        self.assertEqual({FULLY, PARTLY, NOT}, {"fully", "partly", "not"})

    def test_recorded_but_not_weighed_is_its_own_thing(self):
        from botc.catalogue import CHARACTERS, PARTLY
        for key in ("Savant", "Artist"):
            with self.subTest(character=key):
                self.assertEqual(CHARACTERS[key].handled, PARTLY)
                self.assertFalse(CHARACTERS[key].modelled)

    def test_and_so_is_nothing_to_read(self):
        from botc.catalogue import CHARACTERS
        self.assertTrue(CHARACTERS["Mutant"].settled,
                        "madness leaves no mark, so it is finished")
        self.assertFalse(CHARACTERS["Marionette"].settled,
                         "that one is simply not started")

    def test_modelled_still_means_what_every_caller_meant(self):
        """A dozen places ask it, and all of them mean: can the solver be
        trusted about this ability. Recording without weighing does
        not count."""
        from botc.catalogue import CHARACTERS
        self.assertTrue(CHARACTERS["Clockmaker"].modelled)
        # Three characters have stood here as the "not built" example
        # and every one of them got built, which is the nicest way for a
        # test to keep failing. Nothing on the published scripts is
        # unbuilt now, so the example comes from the experimental pile.
        # The Marionette was the third until phase 2 built it.
        for key in ("Savant", "Mutant", "Cerenovus"):
            with self.subTest(character=key):
                self.assertFalse(CHARACTERS[key].modelled)

    def test_the_script_panel_says_three_different_things(self):
        sv = scripts.SECTS_AND_VIOLETS
        kinds = {c["kind"]: c for c in sv.complaints(9)}
        # No "unmodelled" group any more: everything on this script is
        # either reasoned about, recorded without being weighed, or
        # leaves nothing on the board to read.
        self.assertNotIn("unmodelled", kinds)
        self.assertIn("recorded", kinds)
        self.assertIn("nothing to read", kinds)
        self.assertEqual(kinds["recorded"]["characters"],
                         ["Savant", "Artist"])
        # The Cerenovus joined the Mutant here: madness leaves no mark of
        # its own, and what the table *can* see — somebody executed for
        # breaking it — is recorded as a status rather than modelled as
        # an ability.
        self.assertEqual(sorted(kinds["nothing to read"]["characters"]),
                         ["Cerenovus", "Mutant"])

    def test_nothing_appears_in_two_groups(self):
        for name, script in scripts.BUILT_IN.items():
            groups = script.handling()
            seen = [c.key for group in groups.values() for c in group]
            with self.subTest(script=name):
                self.assertEqual(len(seen), len(set(seen)))
                self.assertEqual(sorted(seen),
                                 sorted(c.key for c in script.unmodelled()))

    def test_every_unfinished_character_says_what_is_missing(self):
        for name, script in scripts.BUILT_IN.items():
            for c in script.unmodelled():
                with self.subTest(script=name, character=c.key):
                    self.assertTrue(c.note, "a blank note explains nothing")


class EveryPublishedScriptIsFinished(SolverTest):
    """Nothing on Trouble Brewing, Bad Moon Rising or Sects & Violets is
    waiting to be built.

    Which is not the same as everything being *solved*. Four characters
    across the three are finished at less than that, and each is finished
    for a reason rather than a backlog:

      * a **Savant** and an **Artist** say things that can be anything at
        all, so the words are kept and shown and not weighed;
      * a **Mutant** and a **Cerenovus** work through madness, which
        leaves no mark on the board — what the table *can* see is
        recorded as a status instead;
      * a **Mastermind** changes how the game is won rather than what
        happens on it, and the one part that does show — play carrying on
        after the Demon is executed — is modelled.

    The test that matters is the second one: nothing may sit in the
    "coming" pile unnoticed.
    """

    def test_every_character_is_accounted_for(self):
        for name, script in scripts.BUILT_IN.items():
            groups = script.handling()
            with self.subTest(script=name):
                self.assertEqual([c.name for c in groups["coming"]], [],
                                 "something is still waiting to be built")

    def test_and_the_ones_that_stop_short_say_why(self):
        for name, script in scripts.BUILT_IN.items():
            groups = script.handling()
            for kind in ("recorded", "nothing to read"):
                for character in groups[kind]:
                    with self.subTest(script=name, character=character.key):
                        self.assertTrue(character.note,
                                        "a blank note explains nothing")

    def test_nothing_that_droisons_is_left_unbuilt(self):
        """Which is what let the Mathematician start speaking: its number
        is the size of the impairment set, so it had to stay silent while
        anything that could go wrong was unaccounted for."""
        for name, script in scripts.BUILT_IN.items():
            with self.subTest(script=name):
                self.assertEqual(
                    [c.name for c in script.characters()
                     if c.impairs and not c.modelled], [])
