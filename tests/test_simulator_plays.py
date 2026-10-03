"""What the simulator plays, checked against what it writes down.

Until 03.10.2026 four things on these scripts never happened in a played
game: nobody walked away from an execution, nobody came back from the
dead, a Moonchild the Demon took named nobody, and a Witch cursed every
night and killed nobody. The solver had a rule for each, written from
the rulebook and held to hand-made boards only — and a rule no game ever
exercises is a rule nothing measures.

These tests are about the simulator: that it plays each of the four
often enough to count, that what it records is what happened, and that
the solver keeps the true world when it does.
"""

import random
from collections import Counter

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                           # noqa: E402
from botc import scripts                          # noqa: E402
from botc.info import GameState, phase_index      # noqa: E402
from botc.worlds import World                     # noqa: E402

import claims as C                                # noqa: E402
import simulate                                   # noqa: E402

BMR = scripts.BAD_MOON_RISING
SV = scripts.SECTS_AND_VIOLETS
NIGHTS = 4
GAMES = 300


def games(script, count=GAMES, nights=NIGHTS):
    """(seed, deal, heard, state), the way every sweep builds them."""
    for seed in range(count):
        n = [7, 8, 9, 10, 11][seed % 5]
        rng = random.Random(seed)
        deal, heard = simulate.play(n, rng, nights=nights, script=script)
        claims, wakes, _notes = C.claims_for(deal, rng, script=script)
        state = GameState(n_players=n, script=script, claims=claims,
                          wakes=wakes, infos=list(heard),
                          votes=dict(deal.votes),
                          nominations=dict(deal.nominations),
                          **deal.record())
        yield seed, deal, heard, state


class OnBadMoonRising(SolverTest):

    @classmethod
    def setUpClass(cls):
        cls.played = list(games(BMR))

    # --- an execution somebody walks away from ----------------------------

    def test_every_way_of_walking_away_is_played(self):
        why = Counter(reason for _s, deal, _h, _st in self.played
                      for reason in deal.walked_because.values())
        for reason in ("Sailor", "TeaLady", "DevilsAdvocate", "Pacifist",
                       "Fool"):
            with self.subTest(saved_by=reason):
                self.assertGreater(why[reason], 10)

    def test_it_is_on_the_record_as_an_execution_and_not_a_death(self):
        for seed, deal, _heard, state in self.played:
            for day, seat in deal.executions.items():
                with self.subTest(seed=seed, day=day):
                    self.assertEqual(state.executed_on(day), seat)
                    self.assertIsNone(state.execution_death(day))
                    self.assertIn(seat, state.alive_set(f"N{day + 1}"))

    def test_nobody_else_is_executed_that_day(self):
        """"That still counts as the execution for today.\""""
        for seed, deal, _heard, _state in self.played:
            for day in deal.executions:
                with self.subTest(seed=seed, day=day):
                    self.assertEqual(deal.died_on(f"E{day}"), set())

    def test_a_fool_is_only_spared_once_a_life(self):
        for seed, deal, _heard, _state in self.played:
            spent = Counter()
            for seat, at in deal.fool_spent_ever:
                back = sum(1 for who, when, _by in deal.resurrections
                           if who == seat
                           and phase_index(when) <= phase_index(at))
                spent[(seat, back)] += 1
            with self.subTest(seed=seed):
                self.assertTrue(all(n == 1 for n in spent.values()), spent)

    # --- the dead coming back ------------------------------------------------

    def test_both_hands_raise_the_dead(self):
        by = Counter(who for _s, deal, _h, _st in self.played
                     for _seat, _at, who in deal.resurrections)
        self.assertGreater(by["Shabaloth"], 10)
        self.assertGreater(by["Professor"], 10)

    def test_a_professor_only_raises_a_townsfolk_and_only_once(self):
        from botc.roles import TEAM
        for seed, deal, _heard, _state in self.played:
            raised = [(seat, at) for seat, at, by in deal.resurrections
                      if by == "Professor"]
            with self.subTest(seed=seed):
                for seat, at in raised:
                    self.assertEqual(TEAM[deal.role_at(seat, at)],
                                     "townsfolk")
                # Once a life: a second one needs the Professor itself
                # to have been regurgitated in between.
                if len(raised) > 1:
                    self.assertTrue(any(
                        deal.role_at(seat, at) == "Professor"
                        for seat, at, by in deal.resurrections
                        if by == "Shabaloth"))

    def test_a_shabaloth_only_brings_back_whom_it_took_the_night_before(self):
        for seed, deal, _heard, _state in self.played:
            for night, seat in deal.regurgitated.items():
                with self.subTest(seed=seed, night=night):
                    self.assertGreaterEqual(night, 3)
                    self.assertIn(seat, deal.demon_killed[night - 1])

    def test_nobody_returns_and_dies_in_the_same_night(self):
        """The table would have seen nothing, and "back at night three,
        dead at night three" reads as alive."""
        for seed, deal, _heard, _state in self.played:
            for seat, at, _by in deal.resurrections:
                with self.subTest(seed=seed, seat=seat):
                    self.assertNotIn(at, deal.deaths_of(seat))

    def test_the_record_and_the_deal_agree_on_who_is_alive(self):
        """Two tellings of one life: the simulator's, which it plays by,
        and the `GameState`'s, which the solver reads."""
        for seed, deal, _heard, state in self.played:
            for night in range(1, NIGHTS + 1):
                for phase in (f"N{night}", f"D{night}"):
                    with self.subTest(seed=seed, phase=phase):
                        self.assertEqual(set(deal.alive_at(phase)),
                                         set(state.alive_set(phase)))

    def test_the_page_would_post_the_same_board(self):
        """The same game through the status codes a seat carries on the
        page — X3 executed and died, S3 executed and lived, R3 back."""
        import app
        import make_fixtures as F
        caught = {}
        real = app.analyze

        def spy(state, *a, **k):
            caught["state"] = state
            raise SystemExit

        app.analyze = spy
        try:
            for seed, deal, _heard, state in self.played[:80]:
                # The old local app refuses a death on the first night,
                # which a Tinker can manage. Known, and on the roadmap.
                if deal.died_on("N1"):
                    continue
                n = [7, 8, 9, 10, 11][seed % 5]
                board = F.played("x", BMR, seed, n, NIGHTS)
                try:
                    app.run_solve(board["payload"])
                except SystemExit:
                    pass
                posted = caught.pop("state")
                with self.subTest(seed=seed):
                    self.assertEqual(posted.deaths, state.deaths)
                    self.assertEqual(
                        {s: tuple(p) for s, p in posted.resurrections.items()},
                        {s: tuple(p) for s, p in state.resurrections.items()})
                    self.assertEqual(posted.executions, state.executions)
        finally:
            app.analyze = real

    # --- a Moonchild the Demon took --------------------------------------------

    def picks(self):
        for seed, deal, heard, state in self.played:
            for row in heard:
                if type(row).__name__ == "MoonchildChoice":
                    yield seed, deal, row

    def test_one_taken_at_night_names_somebody_the_next_day(self):
        at_night = [(seed, deal, row) for seed, deal, row in self.picks()
                    if deal.deaths_of(row.player)[-1] == f"N{row.night - 1}"]
        self.assertGreater(len(at_night), 10)
        killed = [row for _s, deal, row in at_night
                  if row.target in deal.died_on(f"N{row.night}")]
        self.assertGreater(len(killed), 3)

    def test_it_names_somebody_whether_or_not_anything_comes_of_it(self):
        """The choice is public, so it is written down every time."""
        for seed, deal, _heard, _state in self.played:
            for seat in range(deal.n):
                for at in deal.deaths_of(seat):
                    if deal.role_at(seat, at) != "Moonchild":
                        continue
                    night = int(at[1:]) + 1
                    if night > NIGHTS or deal.back_at(seat, f"N{night}"):
                        continue
                    if deal.game_ends_after is not None \
                            and night > deal.game_ends_after:
                        continue
                    with self.subTest(seed=seed, died=at):
                        self.assertIn(night, deal.moonchild_picked)

    def test_only_a_good_player_dies_of_it(self):
        for seed, deal, row in self.picks():
            if row.target not in deal.died_on(f"N{row.night}"):
                continue
            if row.target in deal.demon_killed.get(row.night, ()):
                continue                  # the Demon got there first
            with self.subTest(seed=seed, night=row.night):
                self.assertEqual(deal.side_at(row.target, f"N{row.night}"),
                                 "good")

    # --- and the point of all of it -----------------------------------------------

    def test_the_true_world_survives_every_game(self):
        for seed, deal, _heard, state in self.played:
            truth = World(tuple(deal.roles), tuple(deal.believes))
            with self.subTest(seed=seed, roles=deal.roles):
                self.assertIsNotNone(S.explanation_cost(truth, state))

    def test_the_night_walk_tells_every_night_the_same_way(self):
        """The second, independent telling of a night. Where no Goon is
        about: the simulator does not play the Goon turning or making
        anybody drunk, and the walk does."""
        import nightwalk
        checked = 0
        for seed, deal, heard, _state in self.played:
            if "Goon" in deal.roles:
                continue
            for night in range(2, NIGHTS + 1):
                if deal.game_ends_after is not None \
                        and night > deal.game_ends_after:
                    continue
                got = nightwalk.walk(
                    deal, night, nightwalk.hidden_from(deal, night, heard))
                with self.subTest(seed=seed, night=night):
                    self.assertEqual(got.died, deal.died_on(f"N{night}"))
                    self.assertEqual(got.untold, set())
                checked += 1
        self.assertGreater(checked, 400)


class OnSectsAndViolets(SolverTest):

    @classmethod
    def setUpClass(cls):
        cls.played = list(games(SV))

    def test_a_cursed_nominator_drops_dead(self):
        deaths = [(seed, deal, day, seat)
                  for seed, deal, _h, _st in self.played
                  for day, seat in deal.witch_deaths.items()]
        self.assertGreater(len(deaths), 20)
        for seed, deal, day, seat in deaths:
            with self.subTest(seed=seed, day=day):
                self.assertEqual(deal.cursed[day], seat)
                self.assertIn(seat, deal.nominations[day],
                              "the nomination still counts")
                self.assertEqual(deal.deaths_of(seat)[-1], f"D{day}")
                self.assertGreater(len(deal.alive_at(f"D{day}")), 3,
                                   "at three alive the Witch has no ability")

    def test_it_is_on_the_record_as_a_witchs_doing(self):
        for seed, deal, _heard, state in self.played:
            with self.subTest(seed=seed):
                self.assertEqual(dict(state.witch_deaths),
                                 dict(deal.witch_deaths))
                for day, seat in deal.witch_deaths.items():
                    self.assertIn(f"D{day}", state.died_at(seat))
                    self.assertIsNone(state.execution_death(day)
                                      if state.executed_on(day) == seat
                                      else None)

    def test_the_demon_never_nominates_under_a_curse(self):
        for seed, deal, _heard, _state in self.played:
            for day, seat in deal.witch_deaths.items():
                with self.subTest(seed=seed, day=day):
                    self.assertNotEqual(seat, deal.demon_at(f"D{day}"))

    def test_the_true_world_survives_unless_a_barber_hid(self):
        """The one kind of game the solver gives up on purpose (table
        ruling, 29.09.2026) — and a Witch's kill adds no other."""
        lost = 0
        for seed, deal, _heard, state in self.played:
            truth = World(tuple(deal.roles), tuple(deal.believes))
            if S.explanation_cost(truth, state) is not None:
                continue
            claimed = S.barber_claimants(state)
            hid = [p for p, at in deal.deaths.items()
                   if deal.role_at(p, at) == "Barber" and p not in claimed]
            with self.subTest(seed=seed, roles=deal.roles):
                self.assertTrue(hid, "impossible, and not a hidden Barber")
            lost += 1
        self.assertLessEqual(lost, 8)
