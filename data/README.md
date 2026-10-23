# Vendored data

## `nightsheet.json`

The publisher's night sheet, from the official release repository:

    https://github.com/ThePandemoniumInstitute/botc-release
    resources/data/nightsheet.json   (last changed 05.08.2026)

Two lists, `firstNight` and `otherNight`, each the order in which the
Storyteller wakes characters, with the steps `dusk`, `minioninfo`,
`demoninfo` and `dawn` among them: the 120 characters that wake at
night. The publisher's list of characters beside it, `roles.json` in
the same folder, has 181.

Kept here rather than fetched, so the project does not depend on a
network call that could fail or quietly drift.

**What it is used for**: the night order, and nothing else.
`botc/catalogue.py` turns each place into a slot, ten times the place in
the list, and `tools/gen_characters.py` carries the slots into
JavaScript. The few places where this project departs from the sheet on
purpose are listed in `_NOT_AS_IN_THE_SHEET` in `botc/catalogue.py`, each
with its reason (the Hatter after Patrick's answer C, and the characters
the sheet wakes only for a Storyteller's step).

Taken as it is on Patrick's decision of 23.10.2026 (Hatter stage 3,
A Weg 1). Until then the slots came from the older `roles.json` of the
townsquare repository, which knew 130 characters; fifteen newer ones had
been entered by hand.

**It is not a source for what a character does.** The wiki is:

    https://wiki.bloodontheclocktower.com/

**Refreshing it**: fetch the file again, re-run
`python tools/gen_characters.py`, and run the gate and the corpus to see
what the change moves.
