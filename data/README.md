# Vendored data

## `roles.json`

The official character data, taken from the townsquare repository that
backs botc.app:

    https://raw.githubusercontent.com/bra1n/townsquare/develop/src/roles.json

Kept here rather than fetched, so the project does not depend on a
network call that could fail or quietly drift.

**What it is used for**: the night order, and nothing else.

**It is not a source for what a character does.** The ability text here
goes stale, and for experimental characters it is stale *now* — the
Balloonist reads "learn 1 player of each character type, until there are
no more types to learn", which is a previous version. The current card is
"each night, you learn a player of a different character type than last
night", a different mechanic entirely.

Taking the text from here would have built the wrong character. The wiki
is the source for what a character does:

    https://wiki.bloodontheclocktower.com/Experimental

The night order numbers are presumably current, since the app runs from
this file — but the wiki does not print slot numbers, so that cannot be
checked against anything. Treat the ordering as the app's behaviour
rather than as verified fact. Every entry
carries `firstNight` and `otherNight` — the slot a character acts in, or
zero for a night it does not act. Those two numbers are what
`tools/gen_characters.py` reads.

The rest of the file (ability text, reminder tokens, images) is ignored:
this project derives what characters *do* from the rules rather than from
a description, and that is deliberate.

**Refreshing it**: fetch the file again and re-run
`python tools/gen_characters.py`. Anything new appears with its true slot
and needs no renumbering, because the original numbers are kept rather
than being compressed into a rank.
