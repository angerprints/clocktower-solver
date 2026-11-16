"""An evil bluffer reports what its character would, off the table's claims
(16.11.2026, Patrick's answers A and B in claude/hauptziel-bluff-lesarten.md)."""
import random
import unittest

from helpers import SolverTest                    # sets up the import path
import claims as C                                # noqa: E402
import simulate                                   # noqa: E402
import botc.solver as S                           # noqa: E402
from botc import scripts                          # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.roles import TEAM, is_evil              # noqa: E402

TB = scripts.TROUBLE_BREWING
BMR = scripts.BAD_MOON_RISING
SV = scripts.SECTS_AND_VIOLETS

# Characters whose real holder in Trouble Brewing is told something at
# night, every night it lives or on its first.
INFO = {"Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
        "FortuneTeller", "Undertaker"}


def game(seed, script=TB, nights=4):
    rng = random.Random(seed)
    n = [7, 8, 9, 10][seed % 4]
    deal, heard = simulate.play(n, rng, nights=nights, script=script)
    claims, wakes, notes = C.claims_for(deal, rng, script=script)
    last = min(nights, deal.game_ends_after or nights)
    return n, deal, heard, claims, wakes, notes, last


class TheBluffersSpeak(SolverTest):

    def test_a_bluffed_info_character_reports(self):
        # Every bluffer claiming one of them and alive on night 2 has said
        # something by then — the Undertaker only once somebody was
        # executed, so it is left out of the count.
        checked = 0
        for seed in range(40):
            n, deal, heard, claims, wakes, notes, last = game(seed)
            told = C.told_table(deal, heard, claims, notes, last, seed)
            for seat in C.bluffers(deal, notes):
                role = claims[seat]
                if role not in INFO - {"Undertaker"} or last < 2:
                    continue
                if deal.deaths.get(seat) in ("N1", "D1", "E1"):
                    continue
                checked += 1
                self.assertTrue(any(getattr(r, "player", None) == seat
                                    for r in told), (seed, seat, role))
        self.assertGreater(checked, 10)

    def test_the_story_is_the_claims(self):
        # A bluffed Empath or Chef counts nobody evil, a bluffed Undertaker
        # names what the executed seat claimed, and a bluffed
        # Investigator's Minion is a good player.
        seen = set()
        for seed in range(60):
            n, deal, heard, claims, wakes, notes, last = game(seed)
            rng = random.Random(f"bluff-{seed}")
            team = {p for p in range(n) if is_evil(deal.roles[p])}
            for r in C.bluffed_rows(deal, claims, notes, last, rng):
                kind = type(r).__name__
                seen.add(kind)
                if kind in ("Empath", "Chef"):
                    self.assertEqual(r.count, 0, (seed, kind))
                if kind == "Undertaker" and r.target in claims:
                    self.assertEqual(r.role, claims[r.target], seed)
                if kind == "Investigator":
                    self.assertEqual(TEAM[r.role], "minion")
                    self.assertTrue({r.a, r.b} - team, seed)
        self.assertTrue({"Empath", "Chef", "Investigator"} <= seen, seen)

    def test_the_game_itself_is_untouched(self):
        # Read off a copy: nothing the bluffers say changes the deal.
        for seed in range(15):
            n, deal, heard, claims, wakes, notes, last = game(seed)
            before = repr(deal.record())
            C.told_table(deal, heard, claims, notes, last, seed)
            self.assertEqual(before, repr(deal.record()), seed)

    def test_the_true_world_still_fits(self):
        # A made-up reading from a seat that is evil is priced, never
        # impossible: the true world keeps a cost.
        for script, seeds in ((TB, range(25)), (BMR, range(10)),
                              (SV, range(10))):
            for seed in seeds:
                n, deal, heard, claims, wakes, notes, last = game(
                    seed, script)
                told = C.told_table(deal, heard, claims, notes, last, seed)
                state = GameState(n_players=n, script=script, claims=claims,
                                  wakes=wakes, infos=told,
                                  votes=dict(deal.votes),
                                  nominations=dict(deal.nominations),
                                  **deal.record(told=False))
                self.assertIsNotNone(
                    S.explanation_cost(deal.world(), state),
                    (script.name, seed))


if __name__ == "__main__":
    unittest.main()
