"""Check German text for character names that are not the botc.app's.

Patrick reads every report in German, with the names exactly as the
official app writes them (the project doc
`claude/deutsche-charaktertexte-referenz.md` is the reference). A name
translated by hand — "Säufer" for the Drunk, "Zimmermädchen" for the
Chambermaid — is wrong even when it reads well, and he has had to say so
more than once (12.10.2026: "säufer gibt es nicht, es ist der
Trunkenbold").

So every report goes through this before it is uploaded:

    python3 tools/check_wording.py .projdoc/<bericht>.md

It knows the slips that have happened and the ones that are easy to make.
A wrong word quoted on its own („Säufer“) is being talked about and is
let through. Some words are names of *other* characters (the Hexe is the Witch, the
Jäger is the Huntsman); those are warnings to read, not errors, since the
text may mean exactly that character.

Exit status 1 when anything is found, so it can sit in front of an upload.
"""

import re
import sys

# A word that is never right, and what it should be.
WRONG = {
    r"Säufer\w*": "Trunkenbold (Drunk)",
    r"Zimmermädchen": "Kammerzofe (Chambermaid)",
    r"Wahnsinn\w*": "Besessenheit / besessen (madness)",
    r"wahnsinnig\w*": "besessen (mad)",
    r"Bestatter\w*": "Totengräber (Undertaker)",
    r"Wahrsager\b": "Wahrsagerin (Fortune Teller)",
    r"Teelady|Tee-Dame": "Teedame (Tea Lady)",
    r"Seemann|Matrose": "Segler (Sailor)",
    r"Hohepriester\b": "Hohepriesterin (High Priestess)",
    r"Kultanführer\w*|Sektenführer\w*": "Kultführer (Cult Leader)",
    r"Kopfgeldjägerin": "Kopfgeldjäger (Bounty Hunter)",
    r"Gift[- ]?mischerin": "Giftmischer (Poisoner)",
    r"Grubenhexe\w*|Pit-Hag": "Grubenweib (Pit-Hag)",
    r"Puppenspieler\w*": "Strippenzieher (Mastermind)",
    r"Akrobat\b": "Akrobatin (Acrobat)",
    r"Heiliger\b": "Heilige (Saint)",
    r"Gastgeber\w*": "Gastwirt (Innkeeper)",
    r"Feenwesen|Elfe\b": "Feenkind (Pixie)",
    r"Dorfidiot\w*": "Dorftrottel (Village Idiot)",
    r"Lykanthrop\w*": "Werwolf (Lycanthrope)",
    r"Unschuldige\w*": "Unschuld (Damsel)",
    r"Näherin\w*": "Schneiderin (Seamstress)",
    r"Adliger\b": "Adlige (Noble)",
    r"\bOgre\b": "Oger (Ogre)",
    r"Sweetheart": "Liebchen (Sweetheart)",
    r"\bGoon\b": "Schläger (Goon)",
}

# A real name, of a character that is easy to mean by mistake.
CHECK = {
    r"\bHexe\b": "Hexe ist die Witch. Der Pit-Hag heißt Grubenweib.",
    r"\bJäger\b": "Jäger ist der Huntsman. Der Slayer heißt Dämonenjäger.",
    r"\berschein\w*": "Für Fähigkeiten heißt es „registrieren“, nicht "
                      "„erscheinen“ (außer im Zitat eines Fähigkeitstexts).",
}


def _quoted(line, hit):
    """A wrong word quoted on its own — „Säufer“ — is being talked
    about, not used: the report saying which names are wrong."""
    before = line[hit.start() - 1:hit.start()]
    after = line[hit.end():hit.end() + 1]
    return before in ("„", "\"") and after in ("“", "\"")


def check(text):
    found = []
    for number, line in enumerate(text.splitlines(), 1):
        for pattern, right in WRONG.items():
            for hit in re.finditer(pattern, line, re.IGNORECASE):
                if _quoted(line, hit):
                    continue
                found.append(("Fehler", number, hit.group(0),
                              f"heißt {right}"))
        for pattern, note in CHECK.items():
            for hit in re.finditer(pattern, line):
                found.append(("Prüfen", number, hit.group(0), note))
    return found


def main(paths):
    bad = False
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            found = check(handle.read())
        for kind, number, word, note in found:
            print(f"{path}:{number}: {kind}: „{word}“ — {note}")
            bad = bad or kind == "Fehler"
    if not bad:
        print("Wording: keine falschen Namen gefunden.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
