"""Partien aus der Engine des Einzelspieler-Spiels als Bretter für den Solver.

Warum es das gibt
-----------------
Alles am Solver wurde bisher gegen `tests/simulate.py` geprüft, und der
Simulator wurde zusammen mit dem Solver geschrieben. Mehrere Fehler gab es
nur, weil beide dieselbe falsche Annahme hatten.

Die Engine in `J:\\dev\\clocktower` ist eine unabhängige Umsetzung von
Trouble Brewing, zweimal auditiert. Jede Partie dort kennt die volle
Wahrheit und das öffentliche Protokoll. Aus dem Protokoll wird hier ein
Brett, aus der Wahrheit eine Welt, und der Solver muss diese Welt
behalten. Verwirft er sie, hat eines der beiden Projekte einen Regelfehler
— oder diese Brücke übersetzt etwas falsch. Welches, entscheidet das Lesen
des Bretts.

Zwei Arten, ein Brett zu bauen
------------------------------
* **tisch** — nur was am Tisch öffentlich gesagt wurde: die letzte
  öffentliche Behauptung jedes Sitzes, die dazu genannten Informationen,
  Tode, Hinrichtungen, Schüsse. So benutzt jemand das Werkzeug wirklich.
  Böse Sitze lügen hier, und der Solver muss das aushalten.
* **grimoire** — jeder Sitz nennt ehrlich seinen Token und alles, was er
  wirklich erfahren hat, auch vergiftet oder betrunken. Keine Lügen, nur
  gestörte Information. Prüft die Regeln ohne das Rauschen der Bluffs.

Die Engine wird nicht verändert. Sie wird nur importiert:

    set CLOCKTOWER_ENGINE=J:\\dev\\clocktower
    python tools/engine_bridge.py --partien 200
"""

import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from botc import info as I                      # noqa: E402
from botc import solver as S                    # noqa: E402
from botc.catalogue import CHARACTERS, lookup   # noqa: E402
from botc.info import GameState                 # noqa: E402
from botc.worlds import World                   # noqa: E402


def _key(engine_id):
    """`fortune_teller` → `FortuneTeller`, über den Katalog des Solvers."""
    c = lookup(engine_id.replace("_", ""))
    if c is None:
        raise KeyError(f"unbekannter Charakter aus der Engine: {engine_id}")
    return c.key


def _reading(seat, night, role_id, data):
    """Eine Information der Engine als Zeile im Solver-Protokoll.

    Nur das Gezeigte, nie die Felder `truth` und `true`, die die Engine
    für sich selbst mitschreibt. Liefert None für Rollen ohne Information
    (Imp, Mönch, Giftmischer …) und für die Schergen-Info der ersten
    Nacht, die niemand am Tisch ausspricht.
    """
    r = role_id
    if r in ("washerwoman", "investigator"):
        a, b = data["pair"]
        cls = I.Washerwoman if r == "washerwoman" else I.Investigator
        return cls(night, seat, 0, a=a, b=b, role=_key(data["role"]))
    if r == "librarian":
        if "pair" not in data:
            return I.Librarian(night, seat, 0, a=None, b=None, role="")
        a, b = data["pair"]
        return I.Librarian(night, seat, 0, a=a, b=b, role=_key(data["role"]))
    if r == "chef":
        return I.Chef(night, seat, 0, count=int(data["number"]))
    if r == "empath":
        return I.Empath(night, seat, 0, count=int(data["number"]))
    if r == "fortune_teller":
        a, b = data["targets"]
        return I.FortuneTeller(night, seat, 0, a=a, b=b,
                               yes=bool(data["answer"]))
    if r in ("undertaker", "ravenkeeper"):
        cls = I.Undertaker if r == "undertaker" else I.Ravenkeeper
        return cls(night, seat, 0, target=int(data["target"]),
                   role=_key(data["role"]))
    return None


def world_of(state):
    """Die Wahrheit: was jeder **ausgeteilt** bekam, und was ein
    Trunkenbold zu sein glaubt.

    Aus `setup_roles`, nicht aus dem Spieler. Nach einem Sternenpass trägt
    die Engine die neue Rolle direkt beim Spieler ein, und die Welt des
    Solvers ist die Austeilung — den Wechsel findet er selbst. Mit dem
    Stand am Spielende standen zwei Imps auf dem Brett.
    """
    roles, believes = [], []
    for p in state.players:
        dealt = state.setup_roles.get(p.seat, p.role.id)
        if dealt == "drunk":
            roles.append("Drunk")
            believes.append(_key(p.role.id))
        else:
            roles.append(_key(dealt))
            believes.append(None)
    return World(tuple(roles), tuple(believes))


def _game_over_at(state):
    """Die Phase, in der die Stadt durch den Tod des Dämons gewann, oder
    None.

    Diese Phase und alles danach fällt weg. **Der Solver nimmt an, dass
    das Spiel weiterläuft**: Stirbt der Dämon und niemand übernimmt, ist
    das für ihn unmöglich, obwohl die Regel einfach „die Stadt gewinnt"
    sagt. Das passiert am Tag (der Dämon wird hingerichtet oder
    erschossen) und in der Nacht (der letzte Dämon tötet sich selbst, und
    kein Scherge lebt mehr). Während einer Partie stimmt die Annahme, und
    nach dem Spielende fragt niemand mehr. Eine offene Designfrage, keine
    Fehlersuche — siehe ROADMAP.md.
    """
    from engine.roles import Alignment
    if not state.deaths:
        return None
    # Dasselbe von der anderen Seite: Eine funktionierende Heilige, die
    # hingerichtet wird, beendet das Spiel. Der Solver schließt aus einem
    # weiterlaufenden Spiel, dass sie gestört war (solver.py, bei den
    # Hinrichtungen), und verwirft deshalb die Partie, in der sie wirklich
    # das Ende war.
    if state.win_reason == "heilige" and state.executions:
        return f"D{state.executions[-1].day}"
    if state.winner != Alignment.GOOD:
        return None
    final = {p.seat for p in state.players if p.role.id == "imp"}
    last = state.deaths[-1]
    if last.seat not in final:
        return None
    return f"N{last.night}" if last.nachts else f"D{last.day}"


def _keep(phase, cut):
    from botc.info import phase_index
    return cut is None or phase_index(phase) < phase_index(cut)


def _record(state):
    """Was jeder am Tisch gesehen hat: Tode, Hinrichtungen, Schüsse."""
    cut = _game_over_at(state)

    deaths = {}
    for d in state.deaths:
        phase = f"N{d.night}" if d.nachts else f"D{d.day}"
        if _keep(phase, cut):
            deaths.setdefault(d.seat, []).append(phase)
    deaths = {s: tuple(v) for s, v in deaths.items()}

    executions = {e.day: e.seat for e in state.executions
                  if e.seat is not None and _keep(f"D{e.day}", cut)}

    last_night = state.night
    while last_night > 1 and not _keep(f"N{last_night}", cut):
        last_night -= 1
    night_dead = {d.night for d in state.deaths if d.nachts}
    quiet = {n for n in range(2, last_night + 1) if n not in night_dead}

    last_day = state.day
    while last_day > 0 and not _keep(f"D{last_day}", cut):
        last_day -= 1
    days = set(range(1, last_day + 1))

    shots = [I.SlayerShot(s.day, s.seat, 0, target=s.ziel,
                          died=bool(s.getroffen))
             for s in state.schuesse if _keep(f"D{s.day}", cut)]
    return deaths, executions, quiet, days, shots, cut


def board_from(state, mode="tisch"):
    """Das Brett, das ein Spieler am Tisch in den Solver tippen würde."""
    deaths, executions, quiet, days, shots, cut = _record(state)
    claims, infos = {}, list(shots)

    if mode == "grimoire":
        for p in state.players:
            claims[p.seat] = _key(p.role.id)
        for e in state.info_log:
            if not _keep(f"N{e.night}", cut):
                continue
            row = _reading(e.seat, e.night, e.role_id, e.data)
            if row is not None:
                infos.append(row)
    else:
        latest = {}
        for c in state.claims:
            if c.an is None:
                latest[c.seat] = c
        for seat, c in latest.items():
            claims[seat] = _key(c.role_id)
            # Nur die Aussagen zur letzten Behauptung. Wer vorher etwas
            # anderes behauptet hat, hat dazu auch anderes erzählt.
            for c2 in state.claims:
                if c2.an is not None or c2.seat != seat \
                        or c2.role_id != c.role_id:
                    continue
                for a in c2.aussagen:
                    if not _keep(f"N{a.night}", cut):
                        continue
                    row = _reading(seat, a.night, a.role_id, a.data)
                    if row is not None:
                        infos.append(row)

    # Doppelte Zeilen, weil dieselbe Aussage an mehreren Tagen wiederholt
    # wurde, sind eine Aussage.
    seen, unique = set(), []
    for row in infos:
        k = repr(row)
        if k not in seen:
            seen.add(k)
            unique.append(row)

    return GameState(n_players=len(state.players), claims=claims,
                     deaths=deaths, executions=executions,
                     quiet_nights=quiet, days_done=days, infos=unique)


def play(seed, players, complexity, generosity, hirn):
    from engine.difficulty import Difficulty
    from engine.game import play_difficulty
    d = Difficulty(complexity=complexity, generosity=generosity, skill=3)
    return play_difficulty(seed, d, player_count=players, hirn=hirn).state


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--partien", type=int, default=100)
    ap.add_argument("--spieler", default="5,6,7,8,9")
    ap.add_argument("--modus", choices=("tisch", "grimoire"), default="tisch")
    ap.add_argument("--hirn", action="store_true",
                    help="Bots mit Solver (langsamer, echtere Bluffs)")
    ap.add_argument("--start", type=int, default=0)
    args = ap.parse_args()

    engine = os.environ.get("CLOCKTOWER_ENGINE")
    if engine:
        sys.path.insert(0, engine)

    sizes = [int(x) for x in args.spieler.split(",")]
    bad, t0 = [], time.time()
    for i in range(args.start, args.start + args.partien):
        n = sizes[i % len(sizes)]
        cx, gen = 1 + i % 5, 1 + (i // 5) % 5
        state = play(i, n, cx, gen, args.hirn)
        board = board_from(state, args.modus)
        if S.explanation_cost(world_of(state), board) is None:
            bad.append((i, n, cx, gen))
    print(f"{args.partien} Partien, Modus {args.modus}: "
          f"{len(bad)} verwerfen die Wahrheit "
          f"({time.time() - t0:.0f} s)")
    for b in bad[:20]:
        print("  Partie %d · %d Spieler · Komplexität %d · Großzügigkeit %d"
              % b)


if __name__ == "__main__":
    main()
