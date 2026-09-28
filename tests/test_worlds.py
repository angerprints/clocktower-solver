"""Every world the enumerator produces must be a legal game of Trouble
Brewing, and claims must narrow it the way the rules say."""

import unittest

from helpers import (SolverTest, counts, enumerate_worlds, spread,
                     tokens_used, TEAM)
from botc.roles import SETUP, TOWNSFOLK, OUTSIDERS, MINIONS


class SetupLegality(SolverTest):

    def test_every_table_size_produces_legal_worlds(self):
        for n in range(5, 16):
            with self.subTest(players=n):
                claims = spread(n) if n in (7, 9, 12) else {}
                worlds = enumerate_worlds(n, claims, max_worlds=400)
                self.assertTrue(worlds, f"{n} players produced nothing")
                tf, out, mi, de = SETUP[n]
                for w in worlds:
                    c = counts(w)
                    self.assertEqual(c["demon"], de)
                    self.assertEqual(c["minion"], mi)
                    # Either the plain split, or the Baron's -2/+2
                    baron = "Baron" in w.roles
                    self.assertEqual(c["townsfolk"], tf - 2 if baron else tf)
                    self.assertEqual(c["outsider"], out + 2 if baron else out)

    def test_seat_count_matches(self):
        for w in enumerate_worlds(9, spread(9), max_worlds=50):
            self.assertEqual(len(w.roles), 9)
            self.assertEqual(len(w.believes), 9)

    def test_no_token_is_used_twice(self):
        for w in enumerate_worlds(9, spread(9), max_worlds=2000):
            used = tokens_used(w)
            self.assertEqual(len(used), len(set(used)),
                             f"a token appears twice: {used}")

    def test_drunk_holds_a_townsfolk_token_nobody_else_has(self):
        seen = 0
        for w in enumerate_worlds(9, spread(9), max_worlds=6000):
            for i, r in enumerate(w.roles):
                if r != "Drunk":
                    self.assertIsNone(w.believes[i])
                    continue
                seen += 1
                self.assertIn(w.believes[i], TOWNSFOLK)
                self.assertNotIn(w.believes[i], w.roles)
        self.assertGreater(seen, 0, "no Drunk turned up to check")

    def test_baron_is_present_exactly_when_the_split_shifted(self):
        for w in enumerate_worlds(9, spread(9), max_worlds=4000):
            c = counts(w)
            self.assertEqual("Baron" in w.roles, c["outsider"] == SETUP[9][1] + 2)


class ClaimsPrune(SolverTest):

    def test_a_claim_leaves_only_three_readings(self):
        """Really that role, the Drunk holding its token, or evil."""
        for w in enumerate_worlds(7, spread(7), max_worlds=4000):
            for seat, claimed in spread(7).items():
                role = w.roles[seat]
                ok = (role == claimed
                      or (role == "Drunk" and w.believes[seat] == claimed)
                      or TEAM[role] in ("minion", "demon"))
                self.assertTrue(ok, f"seat {seat} claimed {claimed}, got {role}")

    def test_unclaimed_seats_stay_open(self):
        claims = {0: "Washerwoman"}
        roles = {w.roles[5] for w in enumerate_worlds(7, claims, max_worlds=9000)}
        self.assertGreater(len(roles), 6, "an unclaimed seat should be wide open")

    def test_confirmed_pins_exactly_one_role(self):
        worlds = enumerate_worlds(7, spread(7), {4: "confirmed"}, max_worlds=3000)
        self.assertTrue(worlds)
        for w in worlds:
            self.assertEqual(w.roles[4], "Empath")

    def test_self_allows_the_role_or_the_drunk_and_nothing_else(self):
        seen = set()
        for w in enumerate_worlds(9, spread(9), {4: "self"}, max_worlds=8000):
            seen.add((w.roles[4], w.believes[4]))
        self.assertEqual(seen, {("Empath", None), ("Drunk", "Empath")})

    def test_hiding_adds_outsiders_but_not_other_townsfolk(self):
        roles = set()
        for w in enumerate_worlds(9, spread(9), {4: "hiding"}, max_worlds=20000):
            roles.add(w.roles[4])
        self.assertIn("Recluse", roles)
        self.assertIn("Saint", roles)
        self.assertNotIn("Monk", roles, "hiding must not open other Townsfolk")

    def test_unsure_opens_everything(self):
        roles = set()
        for w in enumerate_worlds(9, spread(9), {4: "unsure"}, max_worlds=40000):
            roles.add(w.roles[4])
        self.assertIn("Monk", roles)
        self.assertIn("Recluse", roles)

    def test_pruning_shrinks_rather_than_grows_the_search(self):
        plain = len(enumerate_worlds(9, spread(9), max_worlds=10 ** 6))
        pinned = len(enumerate_worlds(9, spread(9), {4: "confirmed"},
                                      max_worlds=10 ** 6))
        self.assertLess(pinned, plain)


if __name__ == "__main__":
    unittest.main()
