"""The JavaScript data layer, held against the Python one.

`js/dump_data.mjs` prints everything that layer derives — every
character's team and flags, every script's lists and modifiers, the name
lookups, the misregistration table, the wake table. This computes the
same things in Python and insists they match.

The character *data* is generated rather than transcribed
(`tools/gen_characters.py`), so what is really being checked here is the
logic that was written twice: the lookups, the derived facts, the way a
script is built out of a selection.

Skipped when Node is not installed, because the Python solver does not
need it and neither does anybody only running Python.
"""

import json
import pathlib
import shutil
import subprocess
import unittest

from helpers import SolverTest                    # sets up the import path
from botc import scripts                          # noqa: E402
from botc.catalogue import CHARACTERS, lookup, normalise  # noqa: E402
from botc.roles import (SETUP, alignment, believed_tokens,  # noqa: E402
                        believes_another, evil_registrations, is_evil,
                        knows_what_it_is, registers_as_role, show,
                        thinks_it_is_evil, wake_fits)

ROOT = pathlib.Path(__file__).resolve().parent.parent
NODE = shutil.which("node")

EASTER = json.dumps([
    {"id": "_meta", "name": "Easter Trouble",
     "author": "AnqeR und Shellynax"},
    "noble", "washerwoman", "librarian", "clockmaker", "grandmother",
    "slayer", "artist", "empath", "fortuneteller", "monk", "undertaker",
    "ravenkeeper", "virgin", "mayor", "ogre", "saint", "recluse", "drunk",
    "poisoner", "spy", "scarletwoman", "marionette", "baron", "imp"])


def script_facts(script):
    return {
        "keys": list(script.keys),
        "townsfolk": script.townsfolk,
        "outsiders": script.outsiders,
        "minions": script.minions,
        "demons": script.demons,
        "seated": script.seated_keys,
        "fabled": script.fabled,
        "modifiers": {k: [list(map(dict, [s]))[0] for s in v]
                      for k, v in script.setup_modifiers.items()},
        "unmodelled": [c.key for c in script.unmodelled()],
        "playable": script.is_playable(),
        "tooSmall": {str(n): script.too_small_for(n)
                     for n in (5, 7, 9, 12, 15)},
        "believedTokens": {k: believed_tokens(k, script)
                           for k in script.keys if believes_another(k)},
    }


def python_side():
    uploaded = scripts.from_json(EASTER)
    narrow = scripts.from_ids("A narrow script", [
        "washerwoman", "librarian", "investigator", "chef", "empath",
        "recluse", "saint", "poisoner", "spy", "imp"])
    stranger = scripts.from_ids("With a stranger", [
        "washerwoman", "imp", "poisoner", "cabbagemerchant"])
    tb_plus = scripts.from_ids(
        "x", list(scripts.TROUBLE_BREWING.keys) + ["sentinel"])

    return {
        "characters": {key: {
            "id": c.id, "name": c.name, "team": c.team,
            "wake": sorted(c.wake), "registers": sorted(c.registers),
            "setup": [dict(s) for s in c.setup],
            "believes": c.believes, "believesFrom": list(c.believes_from),
            "modelled": c.modelled, "chooses": c.chooses,
            "alignmentOpen": c.alignment_open, "nights": c.nights,
            "seated": c.seated,
            "show": show(key), "isEvil": is_evil(key),
            "alignment": alignment(key),
            "believesAnother": believes_another(key),
            "knowsWhatItIs": knows_what_it_is(key),
            "thinksItIsEvil": thinks_it_is_evil(key),
            "evilRegistrations": list(evil_registrations(key)),
        } for key, c in CHARACTERS.items()},
        "setup": {str(n): list(counts) for n, counts in SETUP.items()},
        "lookups": {name: (lookup(name).key if lookup(name) else None)
                    for name in [
                        "fortuneteller", "Fortune Teller", "FortuneTeller",
                        "FORTUNE TELLER", "scarlet woman", "scarletwoman",
                        "devils advocate", "DevilsAdvocate", "tealady",
                        "Tea Lady", "cabbage merchant", ""]},
        "normalise": {name: normalise(name) for name in [
            "Fortune Teller", "  Scarlet_Woman ", "Devil's Advocate", "Po"]},
        "registersAsRole": {
            f"{a} as {b}": registers_as_role(a, b) for a, b in [
                ("Recluse", "Imp"), ("Recluse", "Monk"),
                ("Recluse", "Recluse"), ("Spy", "Monk"), ("Spy", "Imp"),
                ("Chef", "Chef"), ("Chef", "Imp"), ("Goon", "Imp"),
                ("Imp", "Nonexistent")]},
        "wakeFits": {
            f"{a}/{b or '-'}/{s or '-'}": wake_fits(a, b, s)
            for a, b, s in [
                ("Empath", None, "every"), ("Empath", None, "never"),
                ("Drunk", "Empath", "every"), ("Drunk", "Empath", "never"),
                ("Imp", None, "first"), ("Chef", None, "")]},
        "scripts": {
            "Trouble Brewing": script_facts(scripts.TROUBLE_BREWING),
            "Bad Moon Rising": script_facts(scripts.BAD_MOON_RISING),
            "Easter Trouble": script_facts(uploaded),
            "A narrow script": script_facts(narrow),
        },
        "uploaded": {"name": uploaded.name, "author": uploaded.author,
                     "unknown": list(uploaded.unknown)},
        "withUnknown": {"unknown": list(stranger.unknown)},
        "fabledInPlay": {
            "TB asked for Sentinel": list(
                scripts.TROUBLE_BREWING.fabled_in_play(["Sentinel"])),
            "TB+Sentinel asked for Sentinel": list(
                tb_plus.fabled_in_play(["Sentinel"])),
        },
    }


@unittest.skipUnless(NODE, "Node is not installed")
class TheDataLayerAgrees(SolverTest):
    """One test per section, so a failure says which part diverged."""

    @classmethod
    def setUpClass(cls):
        got = subprocess.run([NODE, str(ROOT / "js" / "dump_data.mjs")],
                             capture_output=True, text=True, timeout=60)
        if got.returncode:
            raise AssertionError(f"js/dump_data.mjs failed:\n{got.stderr}")
        cls.js = json.loads(got.stdout)
        cls.py = python_side()

    def test_the_same_characters_exist(self):
        self.assertEqual(sorted(self.js["characters"]),
                         sorted(self.py["characters"]))

    def test_every_character_matches_field_for_field(self):
        for key, theirs in self.py["characters"].items():
            with self.subTest(character=key):
                self.assertEqual(self.js["characters"][key], theirs)

    def test_the_standard_bag_matches(self):
        self.assertEqual(self.js["setup"], self.py["setup"])

    def test_names_are_looked_up_the_same_way(self):
        """Including the misses: a character nobody has heard of has to
        stay unknown rather than being invented."""
        self.assertEqual(self.js["lookups"], self.py["lookups"])
        self.assertEqual(self.js["normalise"], self.py["normalise"])

    def test_misregistration_matches(self):
        self.assertEqual(self.js["registersAsRole"],
                         self.py["registersAsRole"])

    def test_the_wake_table_matches(self):
        self.assertEqual(self.js["wakeFits"], self.py["wakeFits"])

    def test_every_script_matches(self):
        for name, theirs in self.py["scripts"].items():
            with self.subTest(script=name):
                self.assertEqual(self.js["scripts"][name], theirs)

    def test_a_script_file_is_read_the_same_way(self):
        self.assertEqual(self.js["uploaded"], self.py["uploaded"])
        self.assertEqual(self.js["withUnknown"], self.py["withUnknown"])

    def test_the_fabled_are_filtered_the_same_way(self):
        self.assertEqual(self.js["fabledInPlay"], self.py["fabledInPlay"])


@unittest.skipUnless(NODE, "Node is not installed")
class TheGeneratedDataIsCurrent(SolverTest):
    """`js/characters.mjs` is generated from the catalogue. If the
    catalogue moves and nobody regenerates, everything above still
    passes on stale data — so check the file matches what the generator
    would write now."""

    def test_regenerating_would_change_nothing(self):
        import tools.gen_characters as gen
        before = (ROOT / "js" / "characters.mjs").read_text()
        gen.build()
        after = (ROOT / "js" / "characters.mjs").read_text()
        self.assertEqual(before, after,
                         "js/characters.mjs is stale — "
                         "run python tools/gen_characters.py")


if __name__ == "__main__":
    unittest.main()
