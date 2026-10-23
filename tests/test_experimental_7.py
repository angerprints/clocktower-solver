"""The seventh five experimental characters (11.10.2026).

Pixie, Village Idiot, Lycanthrope, Harpy and Lleech. Every reading here
is the table's ruling of 11.10.2026, asked before anything was built:

  * A **Pixie** is shown a Townsfolk in play (or a Spy registering as
    one). Mad about it means claiming it, and that costs nothing. When
    its holder dies while the Pixie lives and works, the Pixie has the
    ability from the next night; the Storyteller may still refuse it,
    which costs. A "you start knowing" ability fires once then.
  * A **Village Idiot** learns a player's side each night, by
    registration. One to three are dealt, the extras in place of other
    Townsfolk; with two or more, one is drunk all game. The
    Mathematician counts it.
  * A **Lycanthrope** chooses a living player each night but the first:
    a good one dies and the Demon kills nobody, the Pukka's old poison
    included. Not the Demon's kill. One good player — the Lycanthrope
    itself too — registers evil, surely, while it lives and works.
  * A **Harpy**'s mad player saying so means a Harpy in play and alive.
    Its deaths are by day, and never the Demon.
  * A **Lleech** poisons a host from its first night while it lives,
    resting while it is off. It dies when the host dies and not before;
    off at that moment, it dies when it works again. The Slayer's shot
    at the host kills the host; a Mastermind alive at the host's
    execution keeps the Lleech alive without its ability.

They have no script, like the rest, so two are made for them here.
"""

import pathlib
import random
import sys
import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                           # noqa: E402
from botc import info as I, scripts               # noqa: E402
from botc.catalogue import CHARACTERS             # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.worlds import World, enumerate_worlds   # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent
                       / "tools"))

SEVENTH = ("Pixie", "VillageIdiot", "Lycanthrope", "Harpy", "Lleech")

# Trouble Brewing's shape, with the Scarlet Woman to take a Lleech on and
# a Mathematician to count the drunk Village Idiot.
LIKE_TB = ["washerwoman", "librarian", "chef", "empath", "fortuneteller",
           "undertaker", "monk", "ravenkeeper", "slayer", "soldier",
           "pixie", "villageidiot", "lycanthrope", "mathematician",
           "butler", "drunk", "recluse", "saint",
           "poisoner", "spy", "scarletwoman", "harpy",
           "imp", "lleech"]
# Bad Moon Rising's, with its protectors against a kill that is not the
# Demon's, a Mastermind for the Lleech's jinx and the Pukka.
LIKE_BMR = ["grandmother", "sailor", "chambermaid", "exorcist", "innkeeper",
            "gambler", "gossip", "courtier", "professor", "tealady", "fool",
            "pixie", "villageidiot", "lycanthrope",
            "goon", "lunatic", "tinker", "moonchild",
            "godfather", "devilsadvocate", "assassin", "mastermind", "harpy",
            "zombuul", "pukka", "shabaloth", "po", "lleech"]

SEVEN = scripts.from_ids("Seventh five, like Trouble Brewing", LIKE_TB)
SEVEN_BMR = scripts.from_ids("Seventh five, like Bad Moon Rising", LIKE_BMR)


def board(script, roles, infos=(), claims=None, **kw):
    n = len(roles)
    world = World(tuple(roles), (None,) * n)
    state = GameState(n_players=n, script=script,
                      claims=dict(claims if claims is not None
                                  else enumerate(roles)),
                      infos=list(infos), **kw)
    return world, state


def cost(script, roles, infos=(), **kw):
    world, state = board(script, roles, infos, **kw)
    return S.explanation_cost(world, state)


class TheyAreInTheCatalogue(SolverTest):

    def test_three_townsfolk_a_minion_and_a_demon(self):
        teams = {key: CHARACTERS[key].team for key in SEVENTH}
        self.assertEqual(teams, {"Pixie": "townsfolk",
                                 "VillageIdiot": "townsfolk",
                                 "Lycanthrope": "townsfolk",
                                 "Harpy": "minion", "Lleech": "demon"})
        for key in SEVENTH:
            self.assertTrue(CHARACTERS[key].modelled)

    def test_the_two_act_where_the_publisher_puts_them(self):
        """Fearmonger, Harpy, Mezepheles on both nights; the Village Idiot
        after the Shugenja on the first night and after the Balloonist on
        the others (the night sheet, 23.10.2026)."""
        c = CHARACTERS
        for night in ("first_night", "other_night"):
            self.assertLess(getattr(c["Fearmonger"], night),
                            getattr(c["Harpy"], night))
            self.assertLess(getattr(c["Harpy"], night),
                            getattr(c["Mezepheles"], night))
        self.assertLess(c["Shugenja"].first_night,
                        c["VillageIdiot"].first_night)
        self.assertLess(c["VillageIdiot"].first_night,
                        c["BountyHunter"].first_night)
        self.assertLess(c["Balloonist"].other_night,
                        c["VillageIdiot"].other_night)
        self.assertLess(c["VillageIdiot"].other_night, c["King"].other_night)

    def test_only_the_village_idiot_comes_more_than_once(self):
        self.assertEqual({k for k, c in CHARACTERS.items() if c.copies > 1},
                         {"VillageIdiot"})
        self.assertEqual(CHARACTERS["VillageIdiot"].copies, 3)

    def test_the_named_games_do_not_draw_them(self):
        import play_games
        for seed in range(200):
            script = play_games.an_awkward_script(random.Random(seed),
                                                  as_named=True)
            with self.subTest(seed=seed):
                self.assertFalse(set(SEVENTH) & set(script.keys))


#         0       1        2         3              4
PIX = ["Chef", "Empath", "Monk", "Soldier", "Undertaker",
       "Pixie", "Imp"]                                      # 5, 6


class ThePixie(SolverTest):

    def test_shown_a_townsfolk_in_play(self):
        self.assertEqual(cost(SEVEN, PIX, [I.PixieLearned(1, 5,
                                                          role="Empath")]),
                         1.0)

    def test_shown_one_nobody_holds_was_not_working(self):
        self.assertIsNone(cost(SEVEN, PIX, [I.PixieLearned(1, 5,
                                                           role="Mayor")]))

    def test_a_seat_claiming_a_townsfolk_may_be_the_pixie(self):
        claims = {i: r for i, r in enumerate(PIX)}
        claims[5] = "Empath"
        worlds = enumerate_worlds(7, claims, script=SEVEN)
        self.assertTrue(any(w.roles[5] == "Pixie" for w in worlds))

    def test_its_madness_costs_nothing(self):
        claims = {i: r for i, r in enumerate(PIX)}
        claims[5] = "Empath"
        world, state = board(SEVEN, PIX, claims=claims)
        mad = S.prior_weight(world, state)
        claims[5] = "Mayor"                 # a lie, and not its madness
        world, state = board(SEVEN, PIX, claims=claims)
        self.assertLess(S.prior_weight(world, state), mad)

    def test_its_readings_are_made_up_until_the_holder_dies(self):
        claims = {i: r for i, r in enumerate(PIX)}
        claims[5] = "Empath"
        wrong = I.Empath(2, 5, count=2)
        self.assertEqual(cost(SEVEN, PIX, [wrong], claims=claims), 1.0)

    def test_from_the_night_after_the_holder_dies_they_must_be_true(self):
        claims = {i: r for i, r in enumerate(PIX)}
        claims[5] = "Empath"
        deaths = {1: ("N2",)}
        # Neighbours of seat 5 on night 3: 4 and the Imp at 6.
        right = cost(SEVEN, PIX, [I.Empath(3, 5, count=1)], claims=claims,
                     deaths=deaths)
        wrong = cost(SEVEN, PIX, [I.Empath(3, 5, count=0)], claims=claims,
                     deaths=deaths)
        self.assertEqual(right, 1.0)
        # Refused by the Storyteller, which costs (11.10.2026).
        self.assertAlmostEqual(wrong, S.PIXIE_DENIED_PENALTY)

    def test_not_if_it_was_not_mad_about_it(self):
        deaths = {1: ("N2",)}
        got = S._pixie_gain(World(tuple(PIX), (None,) * 7),
                            board(SEVEN, PIX, deaths=deaths)[1], 5)
        self.assertIsNone(got)              # it claimed to be the Pixie


#         0       1        2              3              4
VI = ["VillageIdiot", "VillageIdiot", "VillageIdiot", "Empath", "Monk",
      "Spy", "Imp"]                                         # 5, 6


class TheVillageIdiots(SolverTest):

    def test_three_of_them_can_be_dealt(self):
        claims = dict(enumerate(VI[:5] + ["Soldier", "Chef"]))
        worlds = enumerate_worlds(7, claims, script=SEVEN)
        self.assertTrue(any(list(w.roles[:3]) == ["VillageIdiot"] * 3
                            for w in worlds))

    def test_one_of_three_disagreeing_is_the_drunk_one(self):
        rows = [I.VillageIdiotInfo(1, 0, target=3, evil=False),
                I.VillageIdiotInfo(1, 1, target=3, evil=True),
                I.VillageIdiotInfo(1, 2, target=3, evil=False)]
        self.assertEqual(cost(SEVEN, VI, rows), 1.0)

    def test_two_wrong_need_more_than_the_drunk_one(self):
        rows = [I.VillageIdiotInfo(1, 0, target=3, evil=True),
                I.VillageIdiotInfo(1, 1, target=3, evil=True)]
        self.assertIsNone(cost(SEVEN, VI, rows))

    def test_a_lone_village_idiot_is_sober(self):
        roles = ["VillageIdiot", "Chef", "Monk", "Empath", "Soldier",
                 "Spy", "Imp"]
        self.assertIsNone(cost(SEVEN, roles, [
            I.VillageIdiotInfo(1, 0, target=3, evil=True)]))

    def test_a_spy_may_read_good(self):
        self.assertEqual(cost(SEVEN, VI, [
            I.VillageIdiotInfo(1, 0, target=5, evil=False)]), 1.0)

    def test_the_mathematician_counts_the_drunk_one(self):
        roles = ["VillageIdiot", "VillageIdiot", "Mathematician", "Empath",
                 "Monk", "Soldier", "Imp"]
        world, state = board(SEVEN, roles)
        state._hidden = None
        self.assertEqual(I._possible_impairment_counts(world, state, 1),
                         (0, 1))


#          0       1        2        3               4
LYC = ["Chef", "Empath", "Monk", "Soldier", "Lycanthrope", "Washerwoman",
       "Imp"]                                               # 5, 6


class TheLycanthrope(SolverTest):

    def test_one_good_body_and_no_demon_kill(self):
        self.assertEqual(cost(SEVEN, LYC, [
            I.LycanthropeChose(2, 4, target=3)], deaths={3: ("N2",)}), 1.0)

    def test_it_kills_a_soldier_the_demon_could_not(self):
        self.assertEqual(cost(SEVEN, LYC, deaths={3: ("N2",)}), 1.0)
        without = ["Chef", "Empath", "Monk", "Soldier", "Mayor",
                   "Washerwoman", "Imp"]
        self.assertLess(cost(SEVEN, without, deaths={3: ("N2",)}) or 0, 1.0)

    def test_two_bodies_are_not_both_its_and_the_demons(self):
        self.assertIsNone(cost(SEVEN, LYC, deaths={0: ("N2",),
                                                    1: ("N2",)}))

    def test_the_faux_paw_reads_evil_to_an_empath(self):
        # Seat 1's neighbours are 0 and 2, both good: one evil reading
        # means one of them is the faux paw.
        self.assertEqual(cost(SEVEN, LYC, [I.Empath(1, 1, count=1)]), 1.0)
        self.assertIsNone(cost(SEVEN, LYC, [I.Empath(1, 1, count=2)]))

    def test_the_faux_paw_may_be_the_lycanthrope_itself(self):
        # The Empath moved beside the Lycanthrope and the Imp: two evil
        # neighbours, so the Lycanthrope is the faux paw.
        roles = ["Chef", "Washerwoman", "Monk", "Soldier", "Lycanthrope",
                 "Empath", "Imp"]
        self.assertEqual(cost(SEVEN, roles, [I.Empath(1, 5, count=2)]), 1.0)

    def test_only_one_faux_paw(self):
        roles = ["Chef", "Empath", "Monk", "VillageIdiot", "Lycanthrope",
                 "Washerwoman", "Imp"]
        one = [I.VillageIdiotInfo(1, 3, target=0, evil=True)]
        two = one + [I.VillageIdiotInfo(2, 3, target=2, evil=True)]
        self.assertEqual(cost(SEVEN, roles, one), 1.0)
        self.assertIsNone(cost(SEVEN, roles, two))

    def test_a_target_alive_in_the_morning_read_evil_or_was_the_faux_paw(self):
        self.assertEqual(cost(SEVEN, LYC, [
            I.LycanthropeChose(2, 4, target=0)], deaths={3: ("N2",)}), 1.0)


#           0       1        2        3              4
HARP = ["Chef", "Empath", "Monk", "Soldier", "Undertaker", "Harpy",
        "Imp"]                                              # 5, 6


class TheFauxPawUnderAXaan(SolverTest):
    """Open item 57 (12.10.2026). A Noble holds only with the faux paw
    reading evil — but on the Xaan's night the Lycanthrope is poisoned
    like every Townsfolk, so the faux paw reads good, and the Noble was
    told something false because it was poisoned too. Only the first way
    out was asked."""

    SCRIPT = scripts.from_ids("Faux paw and Xaan", [
        "noble", "lycanthrope", "chef", "empath", "monk", "soldier",
        "saint", "recluse", "xaan", "spy", "imp"])
    #          0          1            2       3        4         5
    ROLES = ["Noble", "Lycanthrope", "Chef", "Saint", "Empath", "Xaan",
             "Imp"]                                           # 6

    def test_the_noble_may_have_been_poisoned_instead(self):
        # The Lycanthrope chose the Chef on night two and the Chef lived,
        # so the Chef is the faux paw; on night one, the Xaan's night
        # (one Outsider), the Noble saw it as the one evil player.
        rows = [I.NobleInfo(1, 0, a=2, b=3, c=4),
                I.LycanthropeChose(2, 1, target=2)]
        self.assertIsNotNone(cost(self.SCRIPT, self.ROLES, rows,
                                  deaths={4: ("N2",)}, days_done={1}))

    def test_without_the_xaan_it_simply_worked(self):
        roles = ["Noble", "Lycanthrope", "Chef", "Saint", "Empath", "Spy",
                 "Imp"]
        rows = [I.NobleInfo(1, 0, a=2, b=3, c=4),
                I.LycanthropeChose(2, 1, target=2)]
        working = cost(self.SCRIPT, roles, rows, deaths={4: ("N2",)},
                       days_done={1})
        self.assertIsNotNone(working)
        # And it is no dearer than the board without the Noble's row.
        self.assertEqual(working, cost(self.SCRIPT, roles, rows[1:],
                                       deaths={4: ("N2",)}, days_done={1}))


class TheHarpy(SolverTest):

    def test_a_mad_player_saying_so_needs_a_harpy(self):
        row = [I.HarpyMadness(1, 0, second=3)]
        self.assertEqual(cost(SEVEN, HARP, row), 1.0)
        without = ["Chef", "Empath", "Monk", "Soldier", "Undertaker",
                   "Poisoner", "Imp"]
        self.assertLess(cost(SEVEN, without, row), 1.0)

    def test_a_dead_harpy_makes_nobody_mad(self):
        # As for the Cerenovus: that world has no story for the row.
        self.assertIsNone(cost(SEVEN, HARP, [I.HarpyMadness(2, 0, second=3)],
                               deaths={5: ("D1",)}))


#           0       1        2         3            4
LEECH = ["Chef", "Empath", "Monk", "Soldier", "Undertaker", "Spy",
         "Lleech", "ScarletWoman"]                          # 5, 6, 7


class TheLleech(SolverTest):

    def test_executed_while_its_host_lives_it_walks_away(self):
        self.assertEqual(cost(SEVEN, LEECH, executions={1: 6}), 1.0)

    def test_its_host_hanged_takes_it_too(self):
        # Seat 4 executed and dead, the Lleech dead the same day; the
        # Scarlet Woman takes it on and kills on night two.
        self.assertEqual(cost(SEVEN, LEECH, executions={1: 4},
                              deaths={4: ("D1",), 6: ("D1",),
                                      0: ("N2",)}), 1.0)

    def test_outliving_its_hanged_host_it_was_not_working(self):
        roles = ["Chef", "Empath", "Monk", "Soldier", "Undertaker",
                 "Washerwoman", "Lleech", "Mayor"]
        world, state = board(SEVEN, roles, executions={1: 4},
                             deaths={4: ("D1",), 0: ("N2",)})
        state._epoch = -1
        # Nothing here can poison it, so seat 4 was not its host...
        state._hidden = (None, 4)
        self.assertIsNone(S._explain_once(world, state))
        # ...and somebody who never died was.
        state._hidden = (None, -1)
        self.assertEqual(S._explain_once(world, state), 1.0)
        state._hidden = None

    def test_it_poisons_its_host(self):
        rows = [I.Empath(1, 1, count=1)]   # neighbours 0 and 2: false
        self.assertEqual(cost(SEVEN, LEECH, rows), 1.0)

    def test_the_slayer_shooting_its_host_kills_the_host(self):
        roles = ["Chef", "Empath", "Slayer", "Soldier", "Undertaker",
                 "Spy", "Lleech", "ScarletWoman"]
        shot = I.SlayerShot(1, 2, target=0, died=True)
        self.assertEqual(cost(SEVEN, roles, [shot],
                              deaths={0: ("D1",), 6: ("D1",),
                                      1: ("N2",)}), 1.0)

    def test_a_shot_at_the_lleech_does_nothing(self):
        roles = ["Chef", "Empath", "Slayer", "Soldier", "Undertaker",
                 "Spy", "Lleech", "ScarletWoman"]
        self.assertEqual(cost(SEVEN, roles,
                              [I.SlayerShot(1, 2, target=6, died=False)]),
                         1.0)

    def test_a_mastermind_keeps_it_alive_without_its_ability(self):
        roles = ["Grandmother", "Sailor", "Chambermaid", "Exorcist",
                 "Innkeeper", "Mastermind", "Lleech", "Gambler"]
        got = cost(SEVEN_BMR, roles, executions={1: 4},
                   deaths={4: ("D1",)}, days_done={1})
        self.assertIsNotNone(got)


class TheScarletWomanAtNight(SolverTest):
    """A Demon that is not the Imp dying at night: she takes it on, as in
    daylight (11.10.2026)."""

    def test_she_steps_up_after_a_lleech_goes_with_its_host(self):
        roles = ["Chef", "Empath", "Monk", "Lycanthrope", "Undertaker",
                 "Washerwoman", "Lleech", "ScarletWoman"]
        self.assertEqual(cost(SEVEN, roles, [
            I.LycanthropeChose(2, 3, target=0)],
            deaths={0: ("N2",), 6: ("N2",), 1: ("N3",)}), 1.0)


class TheSimulatorPlaysThem(SolverTest):

    def games(self, script, how_many=300):
        import simulate
        for seed in range(how_many):
            n = [7, 8, 9, 10, 11][seed % 5]
            yield seed, simulate.play(n, random.Random(seed), nights=4,
                                      script=script)

    def test_up_to_three_village_idiots_and_one_drunk(self):
        seen = set()
        for seed, (deal, _heard) in self.games(SEVEN):
            idiots = [p for p in range(deal.n)
                      if deal.roles[p] == "VillageIdiot"]
            if not idiots:
                continue
            seen.add(len(idiots))
            with self.subTest(seed=seed):
                self.assertLessEqual(len(idiots), 3)
                if len(idiots) >= 2:
                    self.assertIn(deal.vi_drunk, idiots)
                else:
                    self.assertIsNone(deal.vi_drunk)
        self.assertEqual(seen, {1, 2, 3})

    def test_the_lycanthrope_quiets_the_demon(self):
        quiet = 0
        for seed, (deal, _heard) in self.games(SEVEN):
            for night in deal.lyc_quiet:
                quiet += 1
                with self.subTest(seed=seed, night=night):
                    self.assertEqual(deal.demon_killed.get(night, []), [])
        self.assertGreater(quiet, 20)

    def test_a_lleech_dies_with_its_host_or_ends_the_game(self):
        ended = 0
        for script in (SEVEN, SEVEN_BMR):
            for seed, (deal, _heard) in self.games(script):
                if deal.ended_why == "lleech":
                    ended += 1
        self.assertGreater(ended, 20)

    def test_no_other_script_plays_differently(self):
        import hashlib
        import simulate
        digest = hashlib.sha256()
        for seed in range(60):
            deal, heard = simulate.play(9, random.Random(seed), nights=3,
                                        script=scripts.BAD_MOON_RISING)
            digest.update(repr((deal.roles, sorted(deal.deaths.items()),
                                [repr(r) for r in heard])).encode())
        from test_experimental_2 import BMR_SIXTY
        self.assertEqual(digest.hexdigest()[:16], BMR_SIXTY)

    def test_the_true_world_is_kept(self):
        import claims as C
        import simulate
        lost = []
        for script in (SEVEN, SEVEN_BMR):
            for seed in range(120):
                n = [7, 8, 9, 10, 11][seed % 5]
                rng = random.Random(seed)
                deal, heard = simulate.play(n, rng, nights=4, script=script)
                cl, wk, _ = C.claims_for(deal, rng, script=script)
                state = GameState(n_players=n, script=script, claims=cl,
                                  wakes=wk, infos=list(heard),
                                  votes=dict(deal.votes),
                                  nominations=dict(deal.nominations),
                                  **deal.record())
                if S.explanation_cost(deal.world(), state) is None:
                    lost.append((script.name, seed))
        self.assertEqual(lost, [])


KNOWN = set()


class TheNightWalkReplaysThem(SolverTest):
    """The Lycanthrope and the Harpy act at their slots; a Lleech follows
    its host at the end of the night."""

    def test_the_deaths_come_out_the_same(self):
        import nightwalk
        import simulate
        nights = 0
        for script in (SEVEN, SEVEN_BMR):
            for seed in range(150):
                n = [7, 8, 9, 10, 11][seed % 5]
                deal, heard = simulate.play(n, random.Random(seed), nights=4,
                                            script=script)
                for night in range(2, deal.nights_played + 1):
                    if (script.name, seed, night) in KNOWN:
                        continue
                    hidden = nightwalk.hidden_from(deal, night, heard)
                    got = nightwalk.walk(deal, night, hidden)
                    nights += 1
                    with self.subTest(script=script.name, seed=seed,
                                      night=night):
                        self.assertEqual(got.died,
                                         deal.died_on(f"N{night}"))
                        self.assertEqual(got.untold, set())
        self.assertGreater(nights, 500)


if __name__ == "__main__":
    unittest.main()
