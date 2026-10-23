"""The night in the order it runs (Hatter stage 3, 23.10.2026).

Patrick's answers (claude/hutmacher-stufe-3-lesarten.md):

  A  Weg 1: the publisher's night sheet, as it is (`data/nightsheet.json`).
  B  Weg 1: the Hatter keeps answer C — after a death by day the evil
     players choose at the very start of the night, after a death at night
     straight after it.
  C  Weg 1: a new character whose turn has passed acts the next night;
     what it knows "from the start" it learns at once (answer D).
  D  Weg 1: the Demon kills once a night.
  E  Weg 1: the night is read in its order for everything, so a change
     later in a night no longer reaches back into a reader earlier in it
     (open item 36).

Stage 3a is the sheet; 3b the night read in its order: every change has
the slot it was made at (`Change.slot`), every row is read at its
character's turn (`worlds.READ_AT`), every rule at its character's turn,
and the causes of a night's deaths at theirs.
"""
import json
import pathlib
import random
import subprocess
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent
                       / "tools"))
from helpers import SolverTest                    # sets up the import path

import botc.solver as S                           # noqa: E402
from botc import deaths as D, impairment, info as I, scripts  # noqa: E402
from botc import worlds as W                      # noqa: E402
from botc.catalogue import CHARACTERS, slot_of   # noqa: E402
from botc.worlds import Change, Timeline, World, reading_at  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


class TheSheet(SolverTest):
    """3a: the publisher's night sheet, taken as it is."""

    def test_it_is_the_publishers(self):
        sheet = json.loads((ROOT / "data" / "nightsheet.json").read_text())
        named = set(sheet["firstNight"]) | set(sheet["otherNight"])
        named -= {"dusk", "dawn", "minioninfo", "demoninfo"}
        # Every character that wakes at night; the publisher's list of
        # characters beside it has 181.
        self.assertEqual(len(named), 120)
        self.assertFalse((ROOT / "data" / "roles.json").exists())

    def test_a_slot_is_ten_times_the_place(self):
        sheet = json.loads((ROOT / "data" / "nightsheet.json").read_text())
        for key in ("Poisoner", "Imp", "Empath", "SnakeCharmer"):
            place = sheet["otherNight"].index(CHARACTERS[key].id)
            self.assertEqual(CHARACTERS[key].other_night, 10 * place, key)

    def test_the_acrobat_picks_before_the_demons(self):
        """The older file had it after them, at 39."""
        c = CHARACTERS
        self.assertLess(c["Poisoner"].other_night, c["Acrobat"].other_night)
        self.assertLess(c["Acrobat"].other_night, c["Imp"].other_night)

    def test_the_hatter_keeps_answer_c(self):
        """B Weg 1: before anybody on the sheet, not after the killers."""
        first = min(c.other_night for c in CHARACTERS.values()
                    if c.other_night and c.key != "Hatter")
        self.assertLess(CHARACTERS["Hatter"].other_night, first)

    def test_the_storytellers_steps_wake_nobody(self):
        for key in ("Wraith", "Xaan", "Princess", "Banshee", "Riot",
                    "Vizier"):
            self.assertEqual((CHARACTERS[key].first_night,
                              CHARACTERS[key].other_night), (0, 0), key)
        self.assertEqual(CHARACTERS["LordOfTyphon"].first_night, 0)
        self.assertGreater(CHARACTERS["LordOfTyphon"].other_night, 0)

    def test_slot_of(self):
        self.assertEqual(slot_of("Washerwoman", 1),
                         CHARACTERS["Washerwoman"].first_night)
        self.assertIsNone(slot_of("Washerwoman", 2))
        self.assertIsNone(slot_of("NobodyAtAll", 2))


DEALT = ("SnakeCharmer", "PitHag", "NoDashii", "Clockmaker", "Empath",
         "Savant", "Juggler")


class TheMoments(SolverTest):
    """3b: a change at its slot, a reader at its turn."""

    def view(self, slot):
        world = World(DEALT, (None,) * len(DEALT))
        return Timeline(world, (Change("N2", 0, "Juggler", None, slot),))

    def test_a_reader_earlier_in_the_night_does_not_see_it(self):
        view = self.view(CHARACTERS["PitHag"].other_night)
        charmer = CHARACTERS["SnakeCharmer"].other_night
        with reading_at("N2", 0, charmer):
            self.assertEqual(view.role_at(0, "N2"), "SnakeCharmer")
        empath = CHARACTERS["Empath"].other_night
        with reading_at("N2", 0, empath):
            self.assertEqual(view.role_at(0, "N2"), "Juggler")
        # The whole night, as everything read before.
        self.assertEqual(view.role_at(0, "N2"), "Juggler")

    def test_a_reader_sees_what_its_own_turn_did(self):
        pit = CHARACTERS["PitHag"].other_night
        view = self.view(pit)
        with reading_at("N2", 0, pit):
            self.assertEqual(view.role_at(0, "N2"), "Juggler")

    def test_only_its_own_night(self):
        view = self.view(CHARACTERS["PitHag"].other_night)
        with reading_at("N2", 0, CHARACTERS["SnakeCharmer"].other_night):
            self.assertEqual(view.role_at(0, "N3"), "Juggler")
            self.assertEqual(view.role_at(0, "D1"), "SnakeCharmer")
        self.assertIsNone(W.READ_AT[0])

    def test_a_change_without_a_slot_is_the_end_of_the_night(self):
        view = self.view(None)
        with reading_at("N2", 0, CHARACTERS["Empath"].other_night):
            self.assertEqual(view.role_at(0, "N2"), "SnakeCharmer")
        self.assertEqual(view.role_at(0, "N2"), "Juggler")

    def test_the_board_as_the_night_began_is_before_every_slot(self):
        view = self.view(CHARACTERS["Washerwoman"].first_night or 10)
        self.assertEqual(view.role_at(0, "B1"), "SnakeCharmer")


class TheRows(SolverTest):
    """Every row is read at its character's turn."""

    def test_every_kind_of_row_is_wrapped(self):
        for cls in (I.Empath, I.SnakeCharmerChoice, I.PitHagChoice,
                    I.ChambermaidInfo, I.GamblerGuess):
            self.assertTrue(hasattr(cls.holds, "__wrapped__"), cls)

    def test_a_rows_turn(self):
        row = I.Empath(night=2, player=4, count=0)
        self.assertEqual(W._row_slot(row),
                         ("N2", CHARACTERS["Empath"].first_night,
                          CHARACTERS["Empath"].other_night))

    def test_a_row_whose_character_does_not_wake_reads_the_whole_night(self):
        row = I.Empath(night=2, player=4, count=0)
        row.source_role = "Savant"
        self.assertIsNone(W._row_slot(row))

    def test_the_turn_ends_with_the_row(self):
        world = World(DEALT, (None,) * len(DEALT))
        state = I.GameState(n_players=len(DEALT),
                            script=scripts.SECTS_AND_VIOLETS,
                            claims={4: "Empath"}, infos=[])
        I.Empath(night=2, player=4, count=1).holds(world, state, None)
        self.assertIsNone(W.READ_AT[0])


class TheRules(SolverTest):
    """Every change a rule makes on a night has its character's slot."""

    def test_stamped(self):
        got = S.stamped((Change("N2", 1, "Imp"), Change("D2", 2, "Imp"),
                         Change("N3", 3, "Imp", None, 7)), "SnakeCharmer")
        self.assertEqual(got[0].slot, CHARACTERS["SnakeCharmer"].other_night)
        self.assertIsNone(got[1].slot)
        self.assertEqual(got[2].slot, 7)

    def test_a_subclass_stays_itself(self):
        got = S.stamped((W.TeaParty("N2", 1, "Imp", "evil"),), "Imp")
        self.assertIsInstance(got[0], W.TeaParty)

    def test_every_rule_with_a_character_names_a_real_one(self):
        names = {rule.__name__ for rule in S.TRANSITION_RULES}
        for name, key in S._TURN_OF.items():
            self.assertIn(name, names)
            self.assertIn(key, CHARACTERS)

    def test_every_cause_with_a_turn_is_a_rule(self):
        names = {rule.__name__ for rule in D.CAUSE_RULES}
        for name in D.CAUSE_TURNS:
            self.assertIn(name, names)

    def test_the_demons_are_done_before_the_assassin(self):
        demons = [c.other_night for c in CHARACTERS.values()
                  if c.team == "demon" and c.other_night
                  and c.key != "Leviathan"]
        self.assertGreater(S._DEMONS_DONE, max(demons))
        self.assertLess(S._DEMONS_DONE, CHARACTERS["Assassin"].other_night)


def _gate(seed, must, nights=4):
    import claims as C
    import play_games
    import simulate
    n = [7, 8, 9, 10, 11][seed % 5]
    rng = random.Random(seed)
    script = play_games.an_awkward_script(rng, must_have=must)
    deal, heard = simulate.play(n, rng, nights=nights, script=script)
    claims, wakes, _ = C.claims_for(deal, rng, script=script)
    return n, script, deal, heard, claims, wakes


def _fixed(name, seed, nights=4):
    import claims as C
    import simulate
    script = {"SV": scripts.SECTS_AND_VIOLETS}[name]
    n = [7, 8, 9, 10, 11][seed % 5]
    rng = random.Random(seed)
    deal, heard = simulate.play(n, rng, nights=nights, script=script)
    claims, wakes, _ = C.claims_for(deal, rng, script=script)
    return n, script, deal, heard, claims, wakes


def _cost(n, script, deal, heard, claims, wakes):
    state = I.GameState(n_players=n, script=script, claims=claims,
                        wakes=wakes, infos=list(heard),
                        votes=dict(deal.votes),
                        nominations=dict(deal.nominations), **deal.record())
    return S.explanation_cost(deal.world(), state)


class FoundOnTheWay(SolverTest):
    """Games the gate lost on the way, and why they no longer are."""

    def test_the_impairment_plan_reads_the_whole_night(self):
        """A No Dashii kills the Barber, then swaps with a Clockmaker. Its
        kill is read at the Demons' turn — and the poison sources asked
        from there were kept for the plan, with the No Dashii's
        neighbours from before the swap (Sects & Violets, seed 722)."""
        game = _fixed("SV", 722)
        self.assertIsNotNone(_cost(*game))

    def test_a_poison_from_before_a_party_at_night(self):
        """A Vigormortis's dead Minion poisoned the Snake Charmer at its
        turn; later that night the Demon chose the Leviathan. Asked only
        at the end of the night, the poison was gone (gate, seed 1242)."""
        self.assertIsNotNone(_cost(*_gate(1242, ("Hatter", "Leviathan",
                                                 "Summoner"))))

    def test_a_shabaloth_raises_at_its_turn(self):
        """It brought somebody back, then chose the Leviathan at the party
        after the Demons' turn; asked at the end of the night, nobody had
        raised anybody (gate, seed 2897)."""
        self.assertIsNotNone(_cost(*_gate(
            2897, ("Hatter", "EvilTwin", "Godfather", "Gambler",
                   "Philosopher"))))

    def test_room_for_two_parties(self):
        """A Hatter killed at night, raised, and executed: two parties,
        and the stories of both did not fit (gate, seed 1509)."""
        self.assertIsNotNone(_cost(*_gate(
            1509, ("Hatter", "Marionette", "Lunatic", "Drunk",
                   "ScarletWoman"))))

    def test_sources_are_of_the_whole_night_whoever_asks(self):
        n, script, deal, heard, claims, wakes = _fixed("SV", 722)
        state = I.GameState(n_players=n, script=script, claims=claims,
                            wakes=wakes, infos=list(heard),
                            votes=dict(deal.votes),
                            nominations=dict(deal.nominations),
                            **deal.record())
        world = deal.world()
        whole = impairment.sources_on(world, state, 2)
        with reading_at("N2", 0, S._DEMONS_DONE):
            turn = impairment.sources_on(world, state, 2)
        self.assertEqual([sorted(s.seats) for s in whole],
                         [sorted(s.seats) for s in turn])


HAT_IDS = ["hatter", "poisoner", "spy", "baron", "eviltwin", "imp", "po",
           "chef", "empath", "fortuneteller", "monk", "washerwoman",
           "investigator", "soldier", "gambler", "saint"]
HAT_ROLES = ["Chef", "Empath", "FortuneTeller", "Monk", "Washerwoman",
             "Hatter", "Poisoner", "Imp"]
HAT_CLAIMS = ["Chef", "Empath", "FortuneTeller", "Monk", "Washerwoman",
              "Hatter", "Soldier", "Investigator"]


class TheHatterAtNight(SolverTest):
    """3c: a Hatter dead at night, its party straight after its death (C,
    L Weg 2), at the slot after each killer's turn."""

    def state(self, ids=HAT_IDS):
        script = scripts.from_ids("Hutmacher", ids)
        return I.GameState(n_players=len(HAT_ROLES), script=script,
                           claims=dict(enumerate(HAT_CLAIMS)), infos=[],
                           days_done={1, 2}, deaths={5: ("N2",)})

    def test_after_the_demons(self):
        self.assertEqual(S.tea_slots(self.state(), 2), [S._DEMONS_DONE + 1])

    def test_not_after_a_lycanthrope_that_named_somebody_else(self):
        st = self.state(HAT_IDS + ["lycanthrope"])
        self.assertIn(CHARACTERS["Lycanthrope"].other_night + 1,
                      S.tea_slots(st, 2, 5))
        st.infos.append(I.LycanthropeChose(night=2, player=1, target=3))
        self.assertEqual(S.tea_slots(st, 2, 5), [S._DEMONS_DONE + 1])

    def test_and_after_an_assassin_on_the_board(self):
        got = S.tea_slots(self.state(HAT_IDS + ["assassin"]), 2)
        self.assertEqual(got, [S._DEMONS_DONE + 1,
                               CHARACTERS["Assassin"].other_night + 1])

    def test_the_stories(self):
        st = self.state()
        world = World(tuple(HAT_ROLES), (None,) * len(HAT_ROLES))
        stories = S.possible_timelines(world, st)
        tea = [c for changes, _w in stories for c in changes
               if isinstance(c, W.TeaParty)]
        self.assertTrue(tea)
        self.assertTrue(all(c.phase == "N2" and c.slot == S._DEMONS_DONE + 1
                            for c in tea))
        self.assertIn((), [changes for changes, _w in stories])

    def test_the_demons_kill_is_the_old_demons(self):
        """D Weg 1: the Imp killed the Hatter; it took the Po at the
        party, which kills from tomorrow. Read at the Demons' turn the
        party has not happened yet."""
        world = World(tuple(HAT_ROLES), (None,) * len(HAT_ROLES))
        view = Timeline(world, (W.TeaParty("N2", 7, "Po", "evil",
                                           S._DEMONS_DONE + 1),))
        with reading_at("N2", 0, S._DEMONS_DONE):
            self.assertEqual(view.role_at(7, "N2"), "Imp")
        self.assertEqual(view.role_at(7, "N2"), "Po")

    def test_it_is_reckoned(self):
        got = S.analyze(self.state())
        self.assertEqual(got.get("unreckoned") or {}, {})
        self.assertGreater(got["valid"], 0)


class TheAcrobat(SolverTest):
    """It picks at its turn, early; it falls once the night has done all
    that could droison its pick (3a)."""

    def test_the_simulator_and_the_walk_agree_on_the_goon(self):
        """The Acrobat chose the Goon first and was the one made drunk;
        the simulator picked for it after the Demons (gate, seed 2276)."""
        import nightwalk
        n, script, deal, heard, _c, _w = _gate(
            2276, ("Hatter", "EvilTwin", "Godfather", "Gambler",
                   "Philosopher"))
        got = nightwalk.walk(deal, 2, nightwalk.hidden_from(deal, 2, heard))
        self.assertEqual(got.died, deal.died_on("N2"))

    def test_a_night_with_a_pukka_after_the_pick(self):
        """The walk settled the fall at the Acrobat's early turn and missed
        a Pukka's poison later the same night (gate, seed 258, before the
        simulator picked at the Acrobat's turn too)."""
        import nightwalk
        n, script, deal, heard, _c, _w = _gate(
            258, ("Hatter", "Leviathan", "Summoner"))
        got = nightwalk.walk(deal, 3, nightwalk.hidden_from(deal, 3, heard))
        self.assertEqual(got.died, deal.died_on("N3"))


class BothLanguagesAgree(SolverTest):
    """The moments are the same numbers in JavaScript."""

    def test_moments(self):
        cases = [("N2", None, None, None), ("N2", "N2", 0, 220),
                 ("N3", "N2", 0, 220), ("N2", None, 130, 750),
                 ("N1", None, 130, 750), ("B1", "N2", 0, 220),
                 ("D2", None, 0, 750)]
        changes = [("N2", None, False), ("N2", 280, False), ("N2", None, True),
                   ("N2", 390, True), ("N1", -1, False), ("D1", 5, False)]
        py = {"moment": [], "at": []}
        for phase, at, first, other in cases:
            if at is None and first is None:
                py["moment"].append(W.moment(phase))
            else:
                with reading_at(at, first, other):
                    py["moment"].append(W.moment(phase))
        for phase, slot, tea in changes:
            cls = W.TeaParty if tea else Change
            py["at"].append(W._at(cls(phase, 1, "Imp", None, slot)))
        script = f"""
import {{moment, changeAt, readingAt}} from "./js/worlds.mjs";
const cases = {json.dumps(cases)};
const changes = {json.dumps(changes)};
const out = {{moment: [], at: []}};
for (const [phase, at, first, other] of cases) {{
  if (at === null && first === null) out.moment.push(moment(phase));
  else out.moment.push(readingAt(at, first, other, () => moment(phase)));
}}
for (const [phase, slot, tea] of changes)
  out.at.push(changeAt({{phase, seat: 1, role: "Imp", side: null, slot,
                        tea: tea || undefined}}));
console.log(JSON.stringify(out));
"""
        got = subprocess.run(["node", "--input-type=module", "-e", script],
                             cwd=ROOT, capture_output=True, text=True,
                             check=True)
        js = json.loads(got.stdout)
        for a, b in zip(py["moment"], js["moment"]):
            self.assertAlmostEqual(a, b)
        for a, b in zip(py["at"], js["at"]):
            self.assertAlmostEqual(a, b)


if __name__ == "__main__":
    unittest.main()
