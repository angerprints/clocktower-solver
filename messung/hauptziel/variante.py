"""python3 variant.py VARIANT SCRIPT OUT FIRST LAST — dmeas with a patched price
for made-up rows. Run from a checkout's root. Variants:

  p<x>                 FABRICATED_INFO_PENALTY = x per row (now 0.4)
  wahl_frei            a made-up choice row costs nothing
  je_spieler           only a player's first made-up row in a world costs
  je_spieler_wahl_frei both
"""
import sys
import runpy

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
import botc.solver as S                                   # noqa: E402

v = sys.argv[1]
orig_cost = S.invention_cost
orig_failures = S._plain_failures
seen = set()


def choice_free(info):
    return getattr(info, "is_a_choice", False)


def per_player_failures(world, state, outcome=None):
    seen.clear()
    return orig_failures(world, state, outcome)


def cost(info):
    if "wahl_frei" in v and choice_free(info):
        return 1.0
    if v.startswith("je_spieler"):
        who = getattr(info, "player", None)
        if who is not None:
            if who in seen:
                return 1.0
            seen.add(who)
    return orig_cost(info)


# beh_<fit>_<misfit>: a made-up row costs <fit> if it holds in the world of
# the table's claims (everybody what they say), else <misfit> — what an
# evil bluffer says under Patrick's answer B (16.11.2026).
from botc.worlds import World                             # noqa: E402
current = [None]
claim_worlds = {}
stats = {"fit": 0, "misfit": 0, "error": 0}


def claim_world(state):
    key = id(state)
    got = claim_worlds.get(key)
    if got is not None and got[0] is state:
        return got[1]
    claims = dict(state.claims or {})
    spare = [t for t in state.script.townsfolk if t not in claims.values()]
    roles = []
    for p in range(state.n_players):
        roles.append(claims.get(p) or (spare[0] if spare else "Soldier"))
    cw = World(tuple(roles), tuple([None] * state.n_players))
    claim_worlds[key] = (state, cw)
    return cw


def fits_claims(info, state):
    cw = claim_world(state)
    seat = getattr(info, "player", None)
    try:
        if type(info).__name__ == "FortuneTeller":
            ok = any(info.holds(cw, state, rh, seat)
                     for rh in range(state.n_players) if rh != seat)
        else:
            ok = info.holds(cw, state, None, seat)
    except Exception:
        stats["error"] += 1
        return True
    stats["fit" if ok else "misfit"] += 1
    return ok


def beh_failures(world, state, outcome=None):
    current[0] = state
    return orig_failures(world, state, outcome)


if v.startswith("beh_"):
    _, fit, misfit = v.split("_")[:3]
    fit, misfit = float(fit), float(misfit)

    def beh_cost(info):
        if v.endswith("_wahlfrei") and choice_free(info):
            return 1.0
        trust = getattr(info, "trust", 0) or 0
        base = fit if fits_claims(info, current[0]) else misfit
        return min(1.0, base / (S.INFO_TRUST_STEP ** trust))
    S.invention_cost = beh_cost
    S._plain_failures = beh_failures
    import atexit
    atexit.register(lambda: print("Behauptungswelt:", stats, file=sys.stderr))
elif v.startswith("p"):
    S.FABRICATED_INFO_PENALTY = float(v[1:])
else:
    S.invention_cost = cost
    if v.startswith("je_spieler"):
        S._plain_failures = per_player_failures

sys.argv = ["dmeas.py", sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], "4"]
runpy.run_path("messung/dmeas.py", run_name="__main__")
