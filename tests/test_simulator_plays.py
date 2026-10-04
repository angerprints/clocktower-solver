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

The same day it learned the rest of Bad Moon Rising: the Goon answering
whoever chooses it, and the three kills nobody had ever made — the
Assassin's, the Godfather's and a Gossip's. And one table ruling: an
ability ends with the death of whoever has it, so somebody raised is a
new instance and chooses again.
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
        """The second, independent telling of a night — Goon and all,
        since the simulator plays it too now."""
        import nightwalk
        checked = 0
        for seed, deal, heard, _state in self.played:
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
        self.assertGreater(checked, 700)

    # --- the Goon ----------------------------------------------------------------

    def goons(self):
        for seed, deal, _heard, _state in self.played:
            for night, (chooser, goon) in deal.goon_first.items():
                yield seed, deal, night, chooser, goon

    def test_all_sorts_choose_the_goon_first(self):
        who = Counter(
            "Demon" if simulate.TEAM[deal.role_at(chooser, f"N{night}")]
            == "demon" else deal.role_at(chooser, f"N{night}")
            for _seed, deal, night, chooser, _goon in self.goons())
        self.assertGreater(sum(who.values()), 40)
        for kind in ("Demon", "Sailor", "Innkeeper", "Chambermaid"):
            with self.subTest(chooser=kind):
                self.assertGreater(who[kind], 3)

    def test_whoever_chose_it_first_is_drunk_for_the_night(self):
        for seed, deal, night, chooser, _goon in self.goons():
            with self.subTest(seed=seed, night=night):
                self.assertFalse(deal.working(chooser, night))

    def test_it_ends_the_night_on_its_choosers_side(self):
        turned = 0
        for seed, deal, night, chooser, goon in self.goons():
            with self.subTest(seed=seed, night=night):
                self.assertEqual(deal.side_at(goon, f"D{night}"),
                                 deal.side_at(chooser, f"N{night}"))
            turned += deal.side_at(goon, f"D{night}") == "evil"
        self.assertGreater(turned, 5)

    def test_a_demon_that_chose_it_first_kills_nobody_after(self):
        """Drunk from that moment: the choice itself fails, and so does
        a Shabaloth's second."""
        seen = 0
        for seed, deal, night, chooser, goon in self.goons():
            if chooser != deal.demon_at(f"N{night}"):
                continue
            aimed = deal.demon_aimed.get(night) or []
            if not aimed or aimed[0] != goon:
                continue                  # a Pukka, or the Goon came second
            seen += 1
            with self.subTest(seed=seed, night=night):
                self.assertEqual(list(deal.demon_killed.get(night, ())), [])
        self.assertGreater(seen, 3)

    # --- the three other kills -------------------------------------------------------

    def test_an_assassin_strikes_once_and_it_lands(self):
        struck = 0
        for seed, deal, _heard, _state in self.played:
            for seat, night in deal.assassin_chose.items():
                target = deal.assassin_aimed[night]
                struck += 1
                with self.subTest(seed=seed, night=night):
                    self.assertGreaterEqual(night, 2)
                    # Nothing stops it but the Assassin's own state. (Dead
                    # by morning, not "died tonight": one regurgitated and
                    # struck down in the same night never came back as far
                    # as the table saw.)
                    if target in deal.alive_at(f"D{night}"):
                        self.assertFalse(deal.working(seat, night))
        self.assertGreater(struck, 20)

    def test_it_goes_through_what_keeps_anybody_else_alive(self):
        """A sober Sailor, a Fool with its free death still in hand."""
        through = 0
        for _seed, deal, _heard, _state in self.played:
            for night, target in deal.assassin_aimed.items():
                phase = f"N{night}"
                if target not in deal.died_on(phase):
                    continue
                role = deal.role_at(target, phase)
                if role == "Sailor" and deal.working(target, night):
                    through += 1
                if role == "Fool" and target not in deal.fool_spent \
                        and deal.working(target, night):
                    through += 1
        self.assertGreater(through, 0)

    def test_a_godfather_answers_an_outsider_lost_by_day_and_only_that(self):
        kills = 0
        for seed, deal, _heard, _state in self.played:
            for night, target in deal.godfather_aimed.items():
                day = night - 1
                lost = [who for who in deal.died_on(f"D{day}", f"E{day}")
                        if simulate.TEAM[deal.role_at(who, f"D{day}")]
                        == "outsider"]
                with self.subTest(seed=seed, night=night):
                    self.assertTrue(lost)
                kills += target in deal.died_on(f"N{night}")
        self.assertGreater(kills, 5)

    def test_a_gossip_kills_only_alive_and_sober_and_never_the_demon(self):
        kills = 0
        for seed, deal, _heard, _state in self.played:
            for night, target in deal.gossip_killed.items():
                phase = f"N{night}"
                gossip = next(p for p in range(deal.n)
                              if deal.role_at(p, phase) == "Gossip"
                              and p in deal.alive_at(phase))
                kills += 1
                with self.subTest(seed=seed, night=night):
                    self.assertTrue(deal.working(gossip, night))
                    self.assertNotEqual(target, deal.demon_at(phase))
                    self.assertIn(target, deal.died_on(phase))
        self.assertGreater(kills, 20)

    # --- an ability ends with whoever has it ------------------------------------------

    def test_a_courtier_names_again_only_in_a_new_life(self):
        for seed, deal, heard, _state in self.played:
            rows = [row for row in heard
                    if type(row).__name__ == "CourtierChoice"]
            for earlier, later in zip(rows, rows[1:]):
                if earlier.player != later.player:
                    continue
                with self.subTest(seed=seed):
                    self.assertTrue(any(
                        who == later.player
                        and earlier.night < int(at[1:]) <= later.night
                        for who, at, _by in deal.resurrections))

    def test_what_a_dead_courtier_named_is_sober(self):
        """From the night after it died — back or not."""
        checked = 0
        for seed, deal, _heard, _state in self.played:
            for since, holder, courtier in deal.courtier_drunks:
                for night in range(since + 1, min(since + 2, NIGHTS) + 1):
                    gone = any(phase_index(f"N{since}") <= phase_index(at)
                               < phase_index(f"N{night}")
                               for at in deal.deaths_of(courtier))
                    if not gone or holder not in deal.alive_at(f"N{night}"):
                        continue
                    others = simulate.droisoned_at(deal, night)
                    if holder not in others:
                        checked += 1
                        continue
                    # Still impaired, then by somebody else: with the
                    # naming taken away it would be no different.
                    kept, deal.courtier_drunks = deal.courtier_drunks, []
                    try:
                        with self.subTest(seed=seed, night=night):
                            self.assertIn(
                                holder, simulate.droisoned_at(deal, night))
                    finally:
                        deal.courtier_drunks = kept
        self.assertGreater(checked, 3)

    def test_a_grandmother_is_shown_somebody_new_when_she_returns(self):
        again = 0
        for seed, deal, heard, _state in self.played:
            for row in heard:
                if type(row).__name__ != "GrandmotherInfo" or row.night == 1:
                    continue
                again += 1
                with self.subTest(seed=seed, night=row.night):
                    self.assertTrue(deal.back_at(row.player,
                                                 f"N{row.night}"))
        self.assertGreater(again, 0)


class TheGameEndsWhenEvilHasWon(SolverTest):
    """Two players alive and one of them the Demon: evil wins, and the
    game stops there.

    It did not, until 04.10.2026. The simulator played every night it was
    asked for, down to one player, and each measurement taken over
    several nights counted those as games: of 6,000 Trouble Brewing games
    over six nights, 5,608 were already won by evil, and 5,147 of them
    ran on.
    """

    @classmethod
    def setUpClass(cls):
        cls.played = [(script, seed, deal, heard)
                      for script in (None, BMR, SV)
                      for seed, deal, heard, _state
                      in games(script or scripts.TROUBLE_BREWING, nights=6)]

    @staticmethod
    def standing(deal):
        """Who is really alive at the end — a Zombuul on the board as
        dead included."""
        return [p for p in range(deal.n)
                if deal.deaths.get(p) is None or p == deal.zombuul_up]

    def test_it_happens_on_every_script(self):
        ended = Counter(script.name if script else "TB"
                        for script, _s, deal, _h in self.played
                        if deal.ended_at is not None)
        self.assertEqual(len(ended), 3)
        for name, count in ended.items():
            with self.subTest(script=name):
                self.assertGreater(count, 100)

    def test_it_ends_at_night_and_by_day(self):
        when = Counter(deal.ended_at[0] for _sc, _s, deal, _h in self.played
                       if deal.ended_at is not None)
        self.assertGreater(when["N"], 100)
        self.assertGreater(when["E"], 100)

    def test_a_game_that_ended_has_two_left_and_the_demon_is_one(self):
        for _script, seed, deal, _heard in self.played:
            if deal.ended_why != "two alive":
                continue
            with self.subTest(seed=seed, ended=deal.ended_at):
                left = self.standing(deal)
                self.assertLessEqual(len(left), 2)
                self.assertIn(deal.demon_at(deal.ended_at), left)

    def test_a_game_still_open_has_three_or_a_masterminds_day(self):
        for _script, seed, deal, _heard in self.played:
            if deal.ended_at is not None or deal.mastermind_day is not None:
                continue
            with self.subTest(seed=seed):
                self.assertGreater(len(self.standing(deal)), 2)

    def test_nothing_happens_after_the_end(self):
        """No death, no return, no reading and no vote later than the
        moment evil won."""
        for _script, seed, deal, heard in self.played:
            if deal.ended_at is None:
                continue
            end = phase_index(deal.ended_at)
            last = int(deal.ended_at[1:])
            with self.subTest(seed=seed, ended=deal.ended_at):
                self.assertEqual(deal.game_ends_after, last)
                for seat in range(deal.n):
                    for at in deal.deaths_of(seat):
                        self.assertLessEqual(phase_index(at), end)
                for _seat, at, _by in deal.resurrections:
                    self.assertLessEqual(phase_index(at), end)
                self.assertLessEqual(
                    max((row.night for row in heard), default=0), last)
                # A game that ended at dawn has no day after that night.
                days = last - 1 if deal.ended_at[0] == "N" else last
                for day in list(deal.votes) + list(deal.nominations) \
                        + list(deal.executions):
                    self.assertLessEqual(day, days)

    def test_a_day_without_an_execution_ends_it_under_a_vortox(self):
        """"Each day, if no-one is executed, evil wins." The solver takes
        a day like that as proof no Vortox was working, so a game that
        went on past one would be a board it is right to refuse."""
        ended = 0
        for script, seed, deal, _heard in self.played:
            if script is not SV:
                self.assertNotEqual(deal.ended_why, "vortox")
                continue
            last = deal.game_ends_after or 6
            for day in range(1, last + 1):
                if deal.ended_at in (f"N{day}", f"D{day}") or day == 6:
                    break                 # that day was never finished
                hanged = deal.died_on(f"E{day}") or day in deal.executions
                demon = deal.demon_at(f"E{day}")
                under = (deal.role_at(demon, f"E{day}") == "Vortox"
                         and deal.working(demon, day, by_day=True))
                if hanged or not under:
                    continue
                with self.subTest(seed=seed, day=day):
                    self.assertEqual(deal.ended_at, f"E{day}")
                    self.assertEqual(deal.ended_why, "vortox")
                ended += 1
        self.assertGreater(ended, 2)

    def test_a_zombuul_on_the_board_as_dead_still_counts(self):
        """The game goes on with it and two others: three are alive."""
        went_on = 0
        for script, seed, deal, _heard in self.played:
            up = deal.zombuul_up
            if up is None:
                continue
            others = [p for p in self.standing(deal) if p != up]
            if deal.ended_at is None and len(others) == 2:
                went_on += 1
            if deal.ended_at is not None:
                with self.subTest(seed=seed):
                    self.assertLessEqual(len(others), 1)
        self.assertGreater(went_on, 0)

    def test_nobody_is_raised_into_a_game_already_won(self):
        """A Professor acts after the Demon. With two left when its turn
        comes, there is no turn."""
        for _script, seed, deal, _heard in self.played:
            for seat, at, by in deal.resurrections:
                if by != "Professor":
                    continue
                # Everybody dead before the Professor's turn that night:
                # all earlier deaths, and tonight's by the Demon.
                night = int(at[1:])
                before = {p for p in range(deal.n) if p != seat
                          and any(phase_index(x) < phase_index(at)
                                  for x in deal.deaths_of(p))
                          and p != deal.zombuul_up
                          and p in deal.deaths}
                before |= set(deal.demon_killed.get(night, ()))
                with self.subTest(seed=seed, night=night):
                    self.assertGreater(deal.n - len(before) - 1, 2)

    def test_the_night_walk_tells_the_last_night_too(self):
        """The last night is played to its end, so the second telling of
        it has everything to go on."""
        import nightwalk
        checked = 0
        for script, seed, deal, heard in self.played:
            if script is not BMR or deal.ended_at is None \
                    or deal.ended_at[0] != "N":
                continue
            night = int(deal.ended_at[1:])
            got = nightwalk.walk(
                deal, night, nightwalk.hidden_from(deal, night, heard))
            with self.subTest(seed=seed, night=night):
                self.assertEqual(got.died, deal.died_on(f"N{night}"))
                self.assertEqual(got.untold, set())
            checked += 1
        self.assertGreater(checked, 50)


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
