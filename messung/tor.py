"""The gate for new characters: mixed games that must contain them.

   python3 messung/tor.py N NIGHTS START CHARACTER...
   python3 messung/tor.py 40 4 0 Steward Knight Shugenja Nightwatchman King

A new character has no script of its own, so `tools/play_games.py` builds
an awkward one around it (`an_awkward_script(must_have=...)`): several
droison sources, characters that move characters about, Demons from
three scripts. Each game is then asked three things.

  1. Does the solver keep the world that was played? A game it rejects
     is counted twice over: at all, and "because of the new rows" — it is
     kept once the rows the new characters produced are taken away. The
     rest were lost to something the mixing itself brings out, which the
     run with no character named measures on its own.
  2. Does the night-walk replay every night to the same deaths, told
     everything (`untold` empty)?
  3. Where the walk derives a new character's reading itself, does it
     agree with what the simulator said? Only working seats, and no
     Vortox, since those are told something untrue on purpose.

With no CHARACTER it measures the mixed scripts as they are.
"""
import collections
import random
import sys
import time

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
sys.path.insert(0, "tools")
import claims as C                                            # noqa: E402
import nightwalk                                              # noqa: E402
import play_games                                             # noqa: E402
import simulate                                               # noqa: E402
from botc import solver as S                                  # noqa: E402
from botc.info import GameState                               # noqa: E402
from botc.worlds import World                                 # noqa: E402

N, nights, start = (int(x) for x in sys.argv[1:4])
NEW = tuple(sys.argv[4:])


def is_new(row):
    return getattr(row, "source_role", None) in NEW


def asked_of(row):
    """What the walk has to be handed to answer for this row."""
    kind = type(row).__name__
    if kind == "StewardInfo":
        return row.target
    if kind == "KnightInfo":
        return (row.a, row.b)
    return None


def agrees(row, answer):
    """Does the walk's own answer allow what the simulator said?"""
    kind = type(row).__name__
    if kind in ("StewardInfo", "KnightInfo"):
        return answer is True
    if kind == "ShugenjaInfo":
        return answer is None or answer == row.clockwise
    if kind == "KingInfo":
        return (answer is False) if not row.role else (
            answer is not False and row.role in answer)
    return True


rows = collections.Counter()
dealt = collections.Counter()
lost, lost_to_new = [], []
walked = collections.Counter()
walk_bad, read_bad = [], []
t0 = time.time()
for seed in range(start, start + N):
    rng = random.Random(seed)
    script = play_games.an_awkward_script(rng, must_have=NEW)
    n = [7, 8, 9, 10, 11][seed % 5]
    deal, heard = simulate.play(n, rng, nights=nights, script=script)
    claims, wakes, _ = C.claims_for(deal, rng, script=script)

    def cost(said):
        state = GameState(n_players=n, script=script, claims=claims,
                          wakes=wakes, infos=list(said),
                          votes=dict(deal.votes),
                          nominations=dict(deal.nominations), **deal.record())
        return S.explanation_cost(
            World(tuple(deal.roles), tuple(deal.believes)), state)

    for role in deal.roles:
        if role in NEW:
            dealt[role] += 1
    for row in heard:
        if is_new(row):
            kind = type(row).__name__
            if kind == "KingInfo" and not row.role:
                kind += ", nothing"
            rows[kind] += 1
    if cost(heard) is None:
        lost.append(seed)
        if NEW and cost([r for r in heard if not is_new(r)]) is not None:
            lost_to_new.append(seed)

    # How far the game really got. `game_ends_after` is only set when
    # evil wins; an Alsaahir guessing right ends it too, and this then
    # walked nights nobody had played and counted every choosing
    # character on the board as untold (corrected 07.10.2026).
    played = deal.nights_played
    vortox = "Vortox" in deal.roles or any(
        became == "Vortox" for _at, _who, became in deal.changes)
    for night in range(1, played + 1):
        hidden = nightwalk.hidden_from(deal, night, heard)
        mine = [r for r in heard if r.night == night and is_new(r)]
        hidden[("asked", night)] = {
            **(hidden.get(("asked", night)) or {}),
            **{r.player: asked_of(r) for r in mine
               if asked_of(r) is not None}}
        try:
            got = nightwalk.walk(deal, night, hidden)
        except Exception as err:                              # noqa: BLE001
            walk_bad.append((seed, night, repr(err)))
            continue
        if night > 1:
            walked["nights"] += 1
            if got.died != deal.died_on(f"N{night}") or got.untold:
                walk_bad.append((seed, night, sorted(got.died),
                                 sorted(deal.died_on(f"N{night}")),
                                 sorted(got.untold)))
        answers = {(r[1], r[2]): r[3] for r in got.readings}
        for row in mine:
            kind = type(row).__name__
            if kind == "NightwatchmanSeen":
                # Said by whoever was woken, about a seat the walk saw
                # point at them with its ability working.
                walked["Nightwatchman"] += 1
                woke = got.woken_by_nightwatchman
                if not any(who == row.player for who in woke.values()):
                    read_bad.append((seed, night, kind, row.player, woke))
                continue
            if kind == "NightwatchmanChoice" or vortox:
                continue
            if not deal.working(row.player, night):
                continue
            key = (row.player, row.source_role)
            if key not in answers:
                continue
            walked[row.source_role] += 1
            if not agrees(row, answers[key]):
                read_bad.append((seed, night, kind, row, answers[key]))

print(f"{N} gemischte Partien ab {start}, {nights} Nächte, "
      f"mit {', '.join(NEW) or 'nichts Neuem'} ({time.time() - t0:.0f} s)")
print(f" wahre Welt verworfen: {len(lost)}, davon wegen der neuen Zeilen: "
      f"{len(lost_to_new)} {lost_to_new[:30]}")
print(f"   alle verworfenen: {lost[:40]}")
print(f" Night-Walk: {len(walk_bad)} von {walked['nights']} Nächten "
      f"weichen ab {walk_bad[:6]}")
print(f" Auskünfte, Night-Walk gegen Simulator: {len(read_bad)} weichen ab "
      f"von {sum(v for k, v in walked.items() if k != 'nights')} "
      f"{ {k: v for k, v in sorted(walked.items()) if k != 'nights'} } "
      f"{read_bad[:6]}")
print(f" ausgeteilt: {dict(sorted(dealt.items()))}")
print(f" Zeilen: {dict(sorted(rows.items()))}")
