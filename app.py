"""Runs the visual grimoire in your browser.

Start it with:   python app.py
Then open http://127.0.0.1:8765 (it opens automatically).

Uses only the Python standard library - nothing to install.
"""

import json
import os
import socket
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from botc import info as I
from botc import limits, scripts
from botc.catalogue import CHARACTERS
from botc.roles import SETUP, WAKE, WAKE_LABELS, WAKE_PATTERNS, show
from botc.solver import (analyze, blame_for_deaths,
                         claims_cannot_fill_the_bag, diagnose,
                         mastermind_days, sensitivity)

MAX_WORLDS = 600_000

HERE = os.path.dirname(os.path.abspath(__file__))
UI_FILE = os.path.join(HERE, "ui", "index.html")
PORT = 8765


# --------------------------------------------------------------------------
# Turning the browser's JSON into solver objects
# --------------------------------------------------------------------------

def _as_list(value):
    """A seat's extra deaths or returns, however the page sent them."""
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def _int(d, key, default=0):
    v = d.get(key)
    if v is None or v == "":
        return default
    return int(v)



def _savant_says(said):
    """One Savant statement in a shape the solver can check, or None.

    Anything not recognised comes back as None, which keeps the row as
    words rather than refusing the board: a Savant's pair is allowed to
    be anything, and only the shapes in `SAVANT_KINDS` are weighed.
    """
    if not isinstance(said, dict) or said.get("kind") not in I.SAVANT_KINDS:
        return None
    out = {"kind": said["kind"]}
    for key in ("seat", "a", "b", "count"):
        if said.get(key) is not None and said.get(key) != "":
            out[key] = int(said[key])
    if said.get("role"):
        out["role"] = str(said["role"])
    if said.get("seats") is not None:
        out["seats"] = [int(x) for x in said["seats"]]
    need = {"evil": ("seat",), "good": ("seat",), "same": ("a", "b"),
            "different": ("a", "b"), "is": ("seat", "role"),
            "in_play": ("role",), "not_in_play": ("role",),
            "outsiders": ("count",), "demon_among": ("seats",)}
    if any(key not in out for key in need[out["kind"]]):
        return None
    return out


def build_info(d):
    kind = d["type"]
    night = _int(d, "night", 1)
    player = _int(d, "player", 0)
    trust = max(-3, min(3, _int(d, "trust", 0)))

    if kind == "Washerwoman":
        return I.Washerwoman(night, player, trust, a=_int(d, "a"), b=_int(d, "b"),
                             role=d["role"])
    if kind == "Librarian":
        if d.get("a") in (None, "", "none"):
            return I.Librarian(night, player, trust, a=None, b=None, role="")
        return I.Librarian(night, player, trust, a=_int(d, "a"), b=_int(d, "b"),
                           role=d["role"])
    if kind == "Investigator":
        return I.Investigator(night, player, trust, a=_int(d, "a"), b=_int(d, "b"),
                              role=d["role"])
    if kind == "Chef":
        return I.Chef(night, player, trust, count=_int(d, "count"))
    if kind == "Empath":
        return I.Empath(night, player, trust, count=_int(d, "count"))
    if kind == "Noble":
        return I.NobleInfo(night, player, trust,
                           a=_int(d, "a"), b=_int(d, "b"), c=_int(d, "c"))
    if kind == "Became":
        return I.BecameInfo(night, player, trust,
                            role=d.get("role") or "",
                            was=d.get("was") or "")
    if kind == "Alsaahir":
        return I.AlsaahirGuess(
            night, player, trust,
            demons=frozenset(d.get("demons") or ()),
            minions=frozenset(d.get("minions") or ()),
            won=bool(d.get("won")))
    if kind == "Acrobat":
        return I.AcrobatChoice(night, player, trust,
                               target=_int(d, "target"))
    if kind == "Balloonist":
        return I.BalloonistInfo(night, player, trust,
                                target=_int(d, "target"))
    if kind == "FortuneTeller":
        return I.FortuneTeller(night, player, trust, a=_int(d, "a"), b=_int(d, "b"),
                               yes=bool(d.get("yes")))
    if kind == "Undertaker":
        return I.Undertaker(night, player, trust, target=_int(d, "target"),
                            role=d["role"])
    if kind == "Ravenkeeper":
        return I.Ravenkeeper(night, player, trust, target=_int(d, "target"),
                             role=d["role"])
    if kind == "GrandmotherInfo":
        return I.GrandmotherInfo(night, player, trust,
                                 target=_int(d, "target"), role=d["role"])
    if kind == "ChambermaidInfo":
        return I.ChambermaidInfo(night, player, trust, a=_int(d, "a"),
                                 b=_int(d, "b"), count=_int(d, "count"))
    if kind == "GamblerGuess":
        return I.GamblerGuess(night, player, trust, target=_int(d, "target"),
                              role=d["role"])
    if kind == "ClockmakerInfo":
        return I.ClockmakerInfo(night, player, trust, count=_int(d, "count"))
    if kind == "DreamerInfo":
        return I.DreamerInfo(night, player, trust, target=_int(d, "target"),
                             good_role=d["good_role"],
                             evil_role=d["evil_role"])
    if kind == "EvilTwinPair":
        return I.EvilTwinPair(night, player, trust, a=_int(d, "a"),
                              b=_int(d, "b"))
    if kind == "MoonchildChoice":
        return I.MoonchildChoice(night, player, trust,
                                 target=_int(d, "target"))
    if kind == "ExorcistChoice":
        return I.ExorcistChoice(night, player, trust,
                                target=_int(d, "target"))
    if kind == "InnkeeperChoice":
        return I.InnkeeperChoice(night, player, trust, a=_int(d, "a"),
                                 b=_int(d, "b"))
    if kind == "SailorChoice":
        return I.SailorChoice(night, player, trust,
                              target=_int(d, "target"))
    if kind == "OgreChoice":
        return I.OgreChoice(night, player, trust, target=_int(d, "target"))
    if kind == "CerenovusMadness":
        return I.CerenovusMadness(night, player, trust,
                                  role=str(d.get("role") or ""))
    if kind == "PitHagChoice":
        return I.PitHagChoice(night, player, trust, target=_int(d, "target"),
                              role=d["role"])
    if kind == "SnakeCharmerChoice":
        return I.SnakeCharmerChoice(night, player, trust,
                                    target=_int(d, "target"),
                                    swapped=bool(d.get("swapped")))
    if kind == "PhilosopherChoice":
        return I.PhilosopherChoice(night, player, trust, role=d["role"])
    if kind == "SageInfo":
        return I.SageInfo(night, player, trust, a=_int(d, "a"),
                          b=_int(d, "b"))
    if kind == "KlutzChoice":
        return I.KlutzChoice(night, player, trust, target=_int(d, "target"))
    if kind == "OracleInfo":
        return I.OracleInfo(night, player, trust, count=_int(d, "count"))
    if kind == "SeamstressInfo":
        return I.SeamstressInfo(night, player, trust, a=_int(d, "a"),
                                b=_int(d, "b"), same=bool(d.get("same")))
    if kind == "JugglerInfo":
        guesses = tuple((int(g["player"]), g["role"])
                        for g in d.get("guesses") or []
                        if g.get("role") is not None)
        return I.JugglerInfo(night, player, trust, guesses=guesses,
                             count=_int(d, "count"))
    if kind == "SavantInfo":
        return I.SavantInfo(night, player, trust,
                            first=str(d.get("first") or ""),
                            second=str(d.get("second") or ""),
                            first_says=_savant_says(d.get("first_says")),
                            second_says=_savant_says(d.get("second_says")))
    if kind == "ArtistInfo":
        return I.ArtistInfo(night, player, trust,
                            question=str(d.get("question") or ""),
                            answer=bool(d.get("answer")))
    if kind == "FlowergirlInfo":
        return I.FlowergirlInfo(night, player, trust,
                                voted=bool(d.get("voted")))
    if kind == "TownCrierInfo":
        return I.TownCrierInfo(night, player, trust,
                               nominated=bool(d.get("nominated")))
    if kind == "MathematicianInfo":
        return I.MathematicianInfo(night, player, trust,
                                   count=_int(d, "count"))
    if kind == "CourtierChoice":
        return I.CourtierChoice(night, player, trust, role=d["role"])
    if kind in ("VirginNomination", "VirginTrigger"):
        return I.VirginNomination(night, player, trust, nominator=_int(d, "nominator"),
                                  triggered=bool(d.get("triggered", True)))
    if kind == "SlayerShot":
        return I.SlayerShot(night, player, trust, target=_int(d, "target"),
                            died=bool(d.get("died")))
    raise ValueError(f"Unknown information type: {kind}")


def run_solve(payload):
    script = _script_from(payload)
    blocked = limits.refuses(script)
    if blocked:
        name, entry = next(iter(blocked.items()))
        return {"error": f"This script contains the {name}, and the solver "
                         f"cannot reason about it: {entry['why']} Nothing it "
                         f"produced would be trustworthy, so it will not "
                         f"pretend."}

    n = int(payload["n_players"])
    players = payload.get("players", [])

    claims, deaths, names, certainties, reads, wakes = {}, {}, [], {}, {}, {}
    suspects = {}
    votes, nominations = {}, {}
    witch_deaths, madness_executions = {}, {}
    executions, resurrections = {}, {}
    seen_self = False
    for i in range(n):
        p = players[i] if i < len(players) else {}
        names.append(p.get("name") or f"Seat {i + 1}")
        if p.get("claim"):
            if p["claim"] not in script.seated_keys:
                return {"error": f"Seat {i + 1} claims "
                                 f"{show(p['claim'])}, which is not on "
                                 f"{script.name}. Change the script, or the "
                                 f"claim."}
            claims[i] = p["claim"]
            cert = p.get("certainty") or ""
            if cert == "self" and not seen_self:
                seen_self = True
                certainties[i] = "self"
            elif cert in ("confirmed", "unsure", "hiding"):
                certainties[i] = cert
        # A seat's status carries two independent facts: whether they
        # died and when, and whether the town executed them and when. The
        # codes keep them together for the browser and split here.
        #   N2  died night 2          D3  died day 3, no execution
        #   X3  executed day 3, died  S3  executed day 3, survived
        for phase in _as_list(p.get("died")):
            deaths.setdefault(i, []).append(phase)
        for phase in _as_list(p.get("raised")):
            resurrections.setdefault(i, []).append(phase)

        # Everything that happened to this seat, in one list. The page
        # builds it a day at a time, so a seat can go down, come back and
        # go down again without anybody typing a phase code.
        for status in _as_list(p.get("events")) + [p.get("death") or ""]:
            status = (status or "").strip()
            if not status:
                continue
            kind, day = status[0].upper(), status[1:]
            if not day.isdigit():
                return {"error": f"Seat {i + 1} has an unreadable status."}
            if kind in ("X", "S"):
                day = int(day)
                if day in executions and executions[day] != i:
                    return {"error": f"Seat {i + 1} and seat "
                                     f"{executions[day] + 1} are both marked "
                                     f"as executed on day {day}. The town "
                                     f"only executes once a day."}
                executions[day] = i
                if kind == "X":
                    deaths.setdefault(i, []).append(f"D{day}")
            elif kind == "W":
                # Dropped dead as they nominated: a Witch is about.
                witch_deaths[day] = i
                deaths.setdefault(i, []).append(f"D{day}")
            elif kind == "M":
                # Executed for breaking madness: a Cerenovus is about.
                madness_executions[day] = i
                executions[day] = i
                deaths.setdefault(i, []).append(f"D{day}")
            elif kind == "R":
                # Raised: dead, then back. One entry, because that is how
                # it looks from the table.
                resurrections.setdefault(i, []).append(f"N{int(day)}")
            else:
                deaths.setdefault(i, []).append(status)
        try:
            r = int(p.get("read") or 0)
        except (TypeError, ValueError):
            r = 0
        if r:
            reads[i] = max(-3, min(3, r))
        # A suspicion about their information rather than their side.
        if p.get("suspect"):
            suspects[i] = True
        # Who voted and who nominated, day by day. Only the Flowergirl
        # and the Town Crier ask, but a day is where the answer lives.
        for day in p.get("voted") or []:
            votes.setdefault(int(day), set()).add(i)
        for day in p.get("nominated") or []:
            nominations.setdefault(int(day), set()).add(i)
        said = p.get("wake") or ""
        if said in WAKE_PATTERNS:
            wakes[i] = said

    for seat, phases in deaths.items():
        for phase in _as_list(phases):
            if phase.upper() == "N1":
                return {"error": "Nobody dies on the first night in Trouble "
                                 "Brewing — the Demon's first kill is "
                                 "night 2."}

    fabled = script.fabled_in_play(payload.get("fabled") or ())

    quiet = set()
    for value in payload.get("quiet_nights", []) or []:
        night = int(value)
        if night < 2:
            return {"error": "Nobody dies on the first night anyway — a quiet "
                             "night only says something from night 2 onward."}
        died = [seat + 1 for seat, phases in deaths.items()
                if f"N{night}" in _as_list(phases)]
        if died:
            return {"error": f"Night {night} is marked as quiet, but seat "
                             f"{died[0]} is recorded as dying that night."}
        quiet.add(night)

    raw_infos = payload.get("infos", [])
    for d in raw_infos:
        for key in ("player", "a", "b", "target", "nominator"):
            v = d.get(key)
            if v in (None, "", "none"):
                continue
            if not (0 <= int(v) < n):
                return {"error": f"{d['type']} refers to seat {int(v) + 1}, "
                                 f"but this game only has {n} seats."}
        if d["type"] in ("Undertaker", "Ravenkeeper") and _int(d, "night", 1) < 2:
            return {"error": f"{d['type']} information cannot come from night 1 "
                             f"— there is no death to learn from yet."}
    # One character produces one reading a night. Two rows of the same kind
    # for the same seat on the same night is always a slip, and the solver
    # would quietly excuse both with a single poisoning if we let it through.
    seen = set()
    for d in raw_infos:
        key = (d["type"], _int(d, "night", 1), _int(d, "player", 0))
        if key in seen:
            return {"error": f"Two {d['type']} readings for seat "
                             f"{key[2] + 1} on night {key[1]}. A character "
                             f"only wakes once a night — remove one."}
        seen.add(key)

    # The Demon kills before the Empath, Undertaker and Fortune Teller
    # wake, so a seat killed tonight hears nothing tonight.
    #
    # Three exceptions, and they are exceptions for different reasons. The
    # Ravenkeeper is woken *by* dying. A Slayer shot and a Virgin
    # nomination happen in daylight, so a night death is beside the point.
    # And a Gambler that guessed wrong is dead *because* it acted — its
    # reading is the thing that killed it.
    # The Sage and the Klutz are woken *by* dying, the same as the
    # Ravenkeeper — refusing their rows because they died that night is
    # exactly backwards.
    # And every choice made before the Demon swings: a Snake Charmer at
    # slot 11 points before a kill at 24 or later, and so do a Pit-Hag,
    # Innkeeper, Sailor, Exorcist, Philosopher and Courtier. A swapped
    # Snake Charmer killed on night five had its night-five choice refused
    # (29.09.2026). The Moonchild is woken by dying, like the Sage.
    ACTED_ANYWAY = ("Ravenkeeper", "SageInfo", "KlutzChoice",
                    "SlayerShot", "VirginNomination",
                    "GamblerGuess", "MoonchildChoice",
                    "SnakeCharmerChoice", "PitHagChoice", "InnkeeperChoice",
                    "SailorChoice", "ExorcistChoice", "PhilosopherChoice",
                    "CourtierChoice", "CerenovusMadness")
    for d in raw_infos:
        speaker = _int(d, "player", 0)
        night = _int(d, "night", 1)
        if (f"N{night}" in _as_list(deaths.get(speaker))
                and d["type"] not in ACTED_ANYWAY):
            return {"error": f"Seat {speaker + 1} was killed on night {night}, "
                             f"so they never woke to learn this. Only the "
                             f"Ravenkeeper gets information on the night "
                             f"they die."}

    # The Undertaker learns about the player the town executed and killed
    # yesterday. There is nothing else it can be pointed at.
    for d in raw_infos:
        if d["type"] != "Undertaker":
            continue
        day = _int(d, "night", 1) - 1
        executed = executions.get(day)
        died = executed if f"D{day}" in _as_list(deaths.get(executed)) else None
        if died is None:
            return {"error": f"The Undertaker wakes on night {day + 1} only "
                             f"if an execution killed somebody on day {day}. "
                             f"Mark that seat as executed first."}
        if _int(d, "target", 0) != died:
            return {"error": f"The Undertaker learns about seat {died + 1}, "
                             f"who was executed on day {day} — not about "
                             f"seat {_int(d, 'target', 0) + 1}."}

    # `confirmed` is set after building rather than threaded through:
    # `trust` is a positional argument in some thirty constructors and
    # adding another beside it would mean touching every one.
    infos = []
    for d in raw_infos:
        row = build_info(d)
        row.confirmed = bool(d.get("confirmed"))
        infos.append(row)

    state = I.GameState(n_players=n, script=script, fabled=fabled,
                        claims=claims, certainties=certainties,
                        reads=reads, wakes=wakes, suspects=suspects, deaths=deaths,
                        executions=executions, resurrections=resurrections,
                        quiet_nights=quiet,
        days_done={int(d) for d in payload.get("days_done", []) or []},
        votes=votes, nominations=nominations,
        witch_deaths=witch_deaths, madness_executions=madness_executions, infos=infos, names=names)

    if payload.get("sensitivity"):
        return _sensitivity_reply(state)

    result = analyze(state, allow_good_lies=bool(payload.get("allow_good_lies")),
                     max_worlds=MAX_WORLDS)

    samples = []
    for w in result["samples"]:
        seats = []
        for p, r in enumerate(w.roles):
            tag = show(r)
            if w.believes[p]:
                tag += f" (thinks {show(w.believes[p])})"
            seats.append(tag)
        samples.append(seats)

    if result["valid"] == 0:
        result["diagnosis"] = _why_nothing_fits(state)

    rows = []
    for row in result["rows"]:
        pretty = dict(row)
        pretty["roles"] = [[show(r), round(pc, 1)] for r, pc in row["roles"][:6]]
        pretty["margin"] = round(row.get("margin", 0.0), 1)
        rows.append(pretty)

    reply = {"legal": result["legal"], "valid": result["valid"],
             "sampled": result["sampled"], "ess": result["ess"],
             "rows": rows, "samples": samples}
    if "diagnosis" in result:
        reply["diagnosis"] = result["diagnosis"]

    hints = result.get("mastermind") or mastermind_days(state)
    if hints:
        reply["mastermind"] = hints

    # What each night death looks like it came from. Worked out afresh
    # every solve; nothing here was typed in.
    #
    # Taken from the solve itself, which weighs every surviving world.
    # This used to recompute it from `samples` — the eight *most
    # plausible* worlds — which is not a sample of anything: it is the
    # top of the ranking, and the top of the ranking agrees with itself.
    # On a board where two bodies fell in one night it reported the Demon
    # at 94% and never mentioned the Gossip, where weighing all ten
    # thousand worlds gives Demon 76%, Gossip 19%, Assassin 5%. Found by
    # a second implementation, which had no reason to make the same
    # mistake.
    if result.get("readings"):
        reply["readings"] = result["readings"]

    if result.get("blame"):
        reply["blame"] = {str(night): {str(seat): causes
                                       for seat, causes in seats.items()}
                          for night, seats in result["blame"].items()}
    return reply


SCRIPT = scripts.DEFAULT


def load_script(payload):
    """Turn a chosen or uploaded script into what the page needs.

    Three ways in: a built-in by name, a list of characters the person
    picked themselves, or the contents of a `.json` a Storyteller handed
    round. All three end up as the same thing.
    """
    if payload.get("json") is not None:
        script = scripts.from_json(payload["json"])
    elif payload.get("characters") is not None:
        script = scripts.from_ids(payload.get("name", "Custom script"),
                                  payload["characters"],
                                  payload.get("author", ""))
    else:
        script = scripts.BUILT_IN.get(payload.get("name"), scripts.DEFAULT)
    return {"script": script_meta(script, payload.get("n_players"))}


def _script_from(payload):
    """The script this board was played on.

    A saved game carries its own, so a board stays readable after the
    custom script it was played on has been forgotten. Falling back to
    the current selection keeps ordinary solves working.
    """
    carried = payload.get("script")
    if carried:
        return scripts.from_ids(carried.get("name", ""),
                                carried.get("characters", []),
                                carried.get("author", ""))
    return SCRIPT


def _why_nothing_fits(state):
    """Nothing survived. Say what would have to give.

    One removable entry usually means a mis-entered reading or somebody
    lying. No single entry accounting for it is the interesting case, and
    on a script that lets the Storyteller break the rules it is worth
    naming that possibility — without claiming it, since a board can be
    contradictory in ordinary ways too.
    """
    # The claims themselves are a common cause, and one the entry-by-entry
    # search cannot see, so it is asked first — but not instead of the
    # rest. A bag that cannot be filled is also exactly what an Atheist
    # game looks like, so both get said.
    bag = claims_cannot_fill_the_bag(state)
    if bag:
        out = {"culprits": [], "complete": True, "bag": bag}
    else:
        found = diagnose(state)
        out = {"culprits": found["culprits"], "complete": found["complete"]}

    if not out["culprits"] and out["complete"]:
        loose = limits.could_explain_nothing_fitting(state.script)
        out["unsupported"] = [{"name": name, "short": entry["short"],
                               "why": entry["why"], "signal": entry["signal"]}
                              for name, entry in loose.items()]
    return out


def _sensitivity_reply(state):
    """How much of each seat's reading rests on a guess rather than
    on the evidence."""
    got = sensitivity(state)
    return {
        "sensitivity": True,
        "rows": [{"player": r["player"], "evil_pct": round(r["evil_pct"], 1),
                  "low": round(r["low"], 1), "high": round(r["high"], 1),
                  "swing": round(r["swing"], 1),
                  "driver": (r["driver"] or "").replace("_", " ").lower()}
                 for r in got["rows"]],
    }


def script_meta(script, n_players=None):
    """Everything the page needs to draw itself for this script."""
    keys = list(script.seated_keys)
    return {
        "name": script.name,
        "author": script.author,
        "characters": [CHARACTERS[k].id for k in keys],
        "townsfolk": script.townsfolk,
        "outsiders": script.outsiders,
        "minions": script.minions,
        "demons": script.demons,
        "display": {k: show(k) for k in keys},
        "wake_roles": {pat: [k for k in script.townsfolk + script.outsiders
                             if not CHARACTERS[k].believes and pat in WAKE[k]]
                       for pat in WAKE_PATTERNS},
        # Which ledger rows make sense here: a reading only exists if the
        # character that produces it is in the bag.
        # "Became" has no producing character — it is the speaker saying
        # where their own came from — so it is offered whenever the
        # script holds anything that hands a token on.
        "info_types": [
            name for name, source in INFO_SOURCES.items()
            if (any(k in script.keys for k in HANDS_ON) if source is None
                else source in script.keys)],
        "complaints": script.complaints(n_players),
        "playable": script.is_playable(),
        # Shown as checkboxes rather than dealt: the table knows which are
        # in play, so the solver is told rather than working it out.
        "fabled": [{"key": k, "name": CHARACTERS[k].name,
                    "note": CHARACTERS[k].note or
                            ("it may add an Outsider, remove one, or change "
                             "nothing — and you cannot tell which")}
                   for k in script.fabled],
    }


# Each ledger row comes from a character. A script without that character
# has no such reading, so the row is not offered.
HANDS_ON = ("Farmer", "PitHag", "SnakeCharmer")

INFO_SOURCES = {
    # The experimental ones. An audit test compares this table against
    # the fields the page offers, and caught both of these — added to the
    # ledger and not here, so the page would have shown a row the app
    # would not have listed as available.
    # No source character: it is the *speaker* saying where their
    # character came from. Offered whenever the script has something that
    # can be handed on, which `script_meta` special-cases.
    "Became": None,
    "Noble": "Noble",
    "Acrobat": "Acrobat", "Balloonist": "Balloonist",
    "Alsaahir": "Alsaahir",
    "Washerwoman": "Washerwoman", "Librarian": "Librarian",
    "Investigator": "Investigator", "Chef": "Chef", "Empath": "Empath",
    "FortuneTeller": "FortuneTeller", "Undertaker": "Undertaker",
    "Ravenkeeper": "Ravenkeeper", "SlayerShot": "Slayer",
    "GrandmotherInfo": "Grandmother", "ChambermaidInfo": "Chambermaid",
    "GamblerGuess": "Gambler", "CourtierChoice": "Courtier",
    "VirginNomination": "Virgin",
    "ClockmakerInfo": "Clockmaker", "DreamerInfo": "Dreamer",
    "MathematicianInfo": "Mathematician",
    "FlowergirlInfo": "Flowergirl", "TownCrierInfo": "TownCrier",
    "OracleInfo": "Oracle", "SeamstressInfo": "Seamstress",
    "JugglerInfo": "Juggler", "SavantInfo": "Savant",
    "ArtistInfo": "Artist", "SageInfo": "Sage", "KlutzChoice": "Klutz",
    "EvilTwinPair": "EvilTwin", "PhilosopherChoice": "Philosopher",
    "SnakeCharmerChoice": "SnakeCharmer", "PitHagChoice": "PitHag",
    "MoonchildChoice": "Moonchild", "ExorcistChoice": "Exorcist",
    "InnkeeperChoice": "Innkeeper", "SailorChoice": "Sailor",
    "OgreChoice": "Ogre", "CerenovusMadness": "Cerenovus",
}


META = {
    "setup": {str(k): v for k, v in SETUP.items()},
    "wake_patterns": WAKE_PATTERNS,
    "wake_labels": WAKE_LABELS,
    "catalogue": sorted(
        ({"id": c.id, "key": c.key, "name": c.name, "team": c.team,
          "modelled": c.modelled, "note": c.note}
         for c in CHARACTERS.values()),
        key=lambda c: (c["team"], c["name"])),
    # In the order they were published, which is the order a player
    # learns them and the order they sit on a shelf. Sorting by name put
    # Bad Moon Rising first and Trouble Brewing last, which is nobody's
    # idea of where to start.
    "built_in": list(scripts.BUILT_IN),
    "script": None,        # filled in below, once script_meta exists
}
META["script"] = script_meta(SCRIPT)


# --------------------------------------------------------------------------
# Server
# --------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        # Everything the page needs besides the page: the solver modules
        # it imports, the manifest that lets it be added to a home
        # screen, the worker that keeps a copy on the device, and the
        # icons. This server hands them over and then has nothing to do
        # with the answer.
        served = self._static(self.path)
        if served is not None:
            return served
        if self.path in ("/", "/index.html"):
            try:
                with open(UI_FILE, "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(500, b"ui/index.html is missing.", "text/plain")
            return
        if self.path == "/api/meta":
            self._send(200, json.dumps(META))
            return
        self._send(404, json.dumps({"error": "Not found"}))

    # What may be asked for, where it lives, and what to call it. A
    # fixed table rather than a directory walk, so nothing outside these
    # three folders is reachable however the path is spelled.
    STATIC = {
        "/js/": ("js", ".mjs", "text/javascript; charset=utf-8"),
        "/icons/": (os.path.join("ui", "icons"), ".png", "image/png"),
    }

    def _static(self, path):
        """Serve a file from the allowed folders, or return None."""
        if path == "/manifest.webmanifest":
            return self._file(os.path.join(HERE, "ui",
                                           "manifest.webmanifest"),
                              "application/manifest+json")
        if path == "/sw.js":
            # From the root, because a worker can only control pages at
            # or below where it was served from — one served at /ui/ could
            # not control /.
            return self._file(os.path.join(HERE, "ui", "sw.js"),
                              "text/javascript; charset=utf-8")
        for prefix, (folder, suffix, kind) in self.STATIC.items():
            if not path.startswith(prefix) or not path.endswith(suffix):
                continue
            name = os.path.basename(path)
            # Only by its own name: a path with a directory in it never
            # gets this far.
            if name != path[len(prefix):]:
                break
            return self._file(os.path.join(HERE, folder, name), kind)
        return None

    def _file(self, path, kind):
        if not os.path.isfile(path):
            self._send(404, json.dumps({"error": "Not found"}))
            return True
        with open(path, "rb") as handle:
            body = handle.read()
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        # A worker is checked for updates on every load, so a stale one
        # cached by the browser would pin an old solver in place.
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)
        return True

    def do_POST(self):
        if self.path == "/api/script":
            length = int(self.headers.get("Content-Length", 0))
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
                self._send(200, json.dumps(load_script(payload)))
            except Exception as exc:              # noqa: BLE001
                self._send(200, json.dumps(
                    {"error": f"That script could not be read: {exc}"}))
            return
        if self.path != "/api/solve":
            self._send(404, json.dumps({"error": "Not found"}))
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
            self._send(200, json.dumps(run_solve(payload)))
        except Exception as exc:                      # noqa: BLE001
            self._send(200, json.dumps({"error": f"{type(exc).__name__}: {exc}"}))

    def log_message(self, *args):
        pass                                          # keep the console quiet


def lan_address():
    """This machine's address on the local network, as a phone sees it.

    Asks the operating system which interface it would use to reach the
    outside world and reports that one's address. No packets are sent —
    a UDP socket has nowhere to send them until something is written —
    so this works with the wifi up and the internet down.
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("10.255.255.255", 1))
        return probe.getsockname()[0]
    except OSError:
        return None
    finally:
        probe.close()


def lan_addresses():
    """Every address this machine might answer on, likeliest first.

    One guess is not enough on a machine with a virtual network adapter —
    Docker, WSL, VirtualBox and a VPN all add addresses that look
    plausible and that a phone cannot reach. Better to list them and let
    the eye pick the one that matches the phone's own wifi address.
    """
    found = []
    best = lan_address()
    if best:
        found.append(best)
    try:
        for entry in socket.getaddrinfo(socket.gethostname(), None,
                                        socket.AF_INET):
            addr = entry[4][0]
            if addr not in found and not addr.startswith("127."):
                found.append(addr)
    except OSError:
        pass
    return found


def main():
    # Off the machine only when asked. The grimoire has no password on
    # it, so anybody on the same network could open your game — fine at
    # home, less so on a café's wifi.
    share = "--lan" in sys.argv
    host = "0.0.0.0" if share else "127.0.0.1"
    server = HTTPServer((host, PORT), Handler)

    url = f"http://127.0.0.1:{PORT}"
    print(f"Grimoire running at {url}   (press Ctrl+C to stop)")
    if share:
        found = lan_addresses()
        if found:
            print("\nOn your phone, type this in full — including the "
                  "http:// —")
            for i, addr in enumerate(found):
                note = "" if i == 0 else "   (try this one if the first fails)"
                print(f"    http://{addr}:{PORT}{note}")
            print("\nIt must be http, not https. If the phone says it "
                  "cannot make a secure\nconnection, it upgraded the "
                  "address behind your back — see the README.")
        else:
            print("Could not work out this machine's network address — "
                  "check the wifi is connected.")
        print("\nAnybody on this wifi can open it. Do not use --lan on a "
              "network you do not trust.")
    else:
        print("Add --lan to reach it from a phone on the same wifi.")

    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
