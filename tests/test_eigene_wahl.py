"""Whose recorded choice binds (17.11.2026, Patrick's answer A Weg 1 in
claude/eigene-wahl-lesarten.md): an Innkeeper's, a Sailor's or an
Acrobat's row is the choice of the seat that holds the character in the
world, and of nobody else. Until now one holder took anybody's row as its
own, so a liar's row bound the real one.

Bad Moon Rising seed 175: a Chambermaid lying for no reason claims the
Innkeeper and names two dead players on night 4; the real Innkeeper
claims the Fool and says nothing. Read as the real Innkeeper's choice, the
drunk had to be one of the two dead, and the true world was lost.
"""
import dataclasses
import json
import pathlib
import random
import subprocess
import unittest

from helpers import SolverTest                    # sets up the import path
import claims as C                                # noqa: E402
import simulate                                   # noqa: E402
import botc.solver as S                           # noqa: E402
from botc import scripts                          # noqa: E402
from botc.catalogue import CHARACTERS             # noqa: E402
from botc.info import GameState, InnkeeperChoice  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
BMR = scripts.BAD_MOON_RISING


# The claims seed 175 drew until 18.11.2026, pinned: since then chaos is
# rare (claude/hauptziel-chaos-2-lesarten.md, A Weg 1) and the dice no
# longer give this table its two liars. The game itself is unchanged.
CLAIMS = {0: "Gambler", 1: "Pacifist", 2: "Moonchild", 3: "Gossip",
          4: "Innkeeper", 6: "Fool", 7: "TeaLady", 8: "Sailor",
          9: "Grandmother"}
WAKES = {5: "every"}
NOTES = {0: "good Gambler, claiming honestly",
         1: "good Pacifist, claiming honestly",
         2: "evil, bluffing as the Moonchild",
         3: "good Gossip, claiming honestly",
         4: "good Chambermaid, claiming the Innkeeper for no reason",
         5: "good Exorcist, softclaiming \u201cevery\u201d",
         6: "good Innkeeper, claiming the Fool for no reason",
         7: "evil, bluffing as the TeaLady",
         8: "evil, bluffing as the Sailor",
         9: "good Grandmother, claiming honestly"}


def game(seed=175):
    rng = random.Random(seed)
    n = [7, 8, 9, 10][seed % 4]
    import simulate as _sim     # the Demon as before 19.11.2026
    with _sim.victims_as_before():
        deal, heard = simulate.play(n, rng, nights=4, script=BMR)
    claims, wakes, notes = dict(CLAIMS), dict(WAKES), dict(NOTES)
    told = C.told_table(deal, heard, claims, notes,
                        min(4, deal.game_ends_after or 4), seed)
    return n, deal, claims, wakes, notes, told


def state_of(n, deal, claims, wakes, rows):
    return GameState(n_players=n, script=BMR, claims=claims, wakes=wakes,
                     infos=list(rows), votes=dict(deal.votes),
                     nominations=dict(deal.nominations),
                     **deal.record(told=False))


def payload(n, deal, claims, wakes, rows):
    players = [{"claim": claims.get(seat, ""), "events": deal.events(seat),
                "wake": wakes.get(seat, ""),
                "voted": sorted(d for d, who in deal.votes.items()
                                if seat in who),
                "nominated": sorted(d for d, who in deal.nominations.items()
                                    if seat in who)}
               for seat in range(n)]
    infos = []
    for row in rows:
        got = {"type": type(row).__name__, "night": row.night,
               "player": row.player}
        for field in dataclasses.fields(row):
            if field.name in ("night", "player", "trust", "confirmed"):
                continue
            value = getattr(row, field.name)
            if isinstance(value, (tuple, frozenset, set)):
                value = list(value)
            got[field.name] = value
        infos.append(got)
    told = deal.record()
    return {"n_players": n, "players": players, "infos": infos,
            "quiet_nights": sorted(told["quiet_nights"]),
            "days_done": sorted(told["days_done"]),
            "game_over": told["game_over"],
            "script": {"name": BMR.name,
                       "characters": [CHARACTERS[k].id for k in BMR.keys]}}


class ALiarsInnkeeperRowBindsNobody(SolverTest):

    def test_the_game(self):
        n, deal, claims, wakes, notes, told = game()
        self.assertEqual(deal.roles[4], "Chambermaid")
        self.assertEqual(claims[4], "Innkeeper")
        self.assertEqual(deal.roles[6], "Innkeeper")
        self.assertIn("for no reason", notes[4])
        row = [r for r in told if isinstance(r, InnkeeperChoice)
               and r.player == 4 and r.night == 4]
        self.assertEqual(len(row), 1)

    def test_the_true_world_is_kept(self):
        n, deal, claims, wakes, _notes, told = game()
        self.assertIsNotNone(S.explanation_cost(
            deal.world(), state_of(n, deal, claims, wakes, told)))

    def test_the_holders_own_row_still_binds(self):
        # The liar's row, said by the real Innkeeper: now it is its
        # choice, both named are dead, and the drunk it needs is gone.
        n, deal, claims, wakes, _notes, told = game()
        rows = [dataclasses.replace(r, player=6)
                if isinstance(r, InnkeeperChoice) and r.player == 4
                and r.night == 4 else r for r in told]
        self.assertIsNone(S.explanation_cost(
            deal.world(), state_of(n, deal, claims, wakes, rows)))

    def test_both_languages_agree(self):
        n, deal, claims, wakes, _notes, told = game()
        case = payload(n, deal, claims, wakes, told)
        js = ("import {readBoard} from './js/api.mjs';"
              "import {explanationCost} from './js/scoring.mjs';"
              "import {World} from './js/worlds.mjs';"
              "const [p, roles, believes]=JSON.parse(process.argv[1]);"
              "const {state}=readBoard(p);"
              "console.log(JSON.stringify(explanationCost("
              "new World(roles, believes), state)));")
        got = subprocess.run(
            ["node", "--input-type=module", "-e", js,
             json.dumps([case, list(deal.roles),
                         list(deal.world().believes)])],
            cwd=ROOT, capture_output=True, text=True, timeout=600)
        self.assertEqual(got.returncode, 0, got.stderr)
        from_js = json.loads(got.stdout)
        from_py = S.explanation_cost(deal.world(),
                                     state_of(n, deal, claims, wakes, told))
        self.assertIsNotNone(from_js)
        self.assertAlmostEqual(from_js, from_py, places=6)


if __name__ == "__main__":
    unittest.main()
