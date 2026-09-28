# Blood on the Clocktower – Solver (5–15 players)

A visual grimoire from the players' side of the table. Set the seating,
enter what everyone claims and what they say they learned, and it
enumerates every world still consistent with all of it.

**Trouble Brewing and Bad Moon Rising are both in**, along with the
Sentinel, and any custom script can be picked character by character or
loaded from the JSON a Storyteller hands round. Nothing to install:
Python and a browser.

    python app.py          # opens the grimoire
    python app.py --lan    # ...and lets a phone on the same wifi reach it
    python run_tests.py    # 821 tests, before trusting any change

Jump to [the folder layout](#files) if you would rather read the code.

---

## What is in this file

| | |
|---|---|
| Part 1 | Setting up, and using it from a phone |
| Part 2 | Scripts: picking one, loading one, saving a game |
| Part 3 | Bad Moon Rising, character by character |
| Part 4 | Using the grimoire |
| Part 5 | How the solver thinks |
| Part 6 | Working in code instead |
| Part 7 | Tests |
| Part 8 | The seams, and why they are there |
| Part 9 | Writing it again in JavaScript |
| Part 10 | Putting it on a phone for good |
| Part 11 | Where to take it next |
| Files | The folder layout |

---

## Part 1 – Setting up a dev environment from scratch

You need exactly two things: Python and an editor.

### 1. Install Python

**Windows**
1. Go to https://www.python.org/downloads/ and click "Download Python 3.12" (or newer).
2. Run the installer. **Important:** tick *"Add python.exe to PATH"* at the bottom, then "Install Now".
3. Check it: Windows key → type `cmd` → Enter → type `python --version`.
   You should see `Python 3.12.x`.

**macOS**
1. Open Terminal (Cmd+Space → "Terminal").
2. Type `python3 --version`. If it says 3.10 or newer, you're done.
3. Otherwise grab the installer from python.org.

**Linux**: `sudo apt install python3 python3-venv` (Debian/Ubuntu).

### 2. Install an editor

Download VS Code from https://code.visualstudio.com/. Once installed,
click the Extensions icon on the left (four squares), search for
**Python**, and install the one published by Microsoft.

### 3. Open the project

1. Unpack this folder somewhere sensible, e.g. `C:\Projects\botc-solver`.
2. VS Code → *File → Open Folder* → pick that folder.
   Open the **folder**, not the individual file — that keeps the working
   directory correct when you hit Run.
3. Open a terminal inside VS Code: *Terminal → New Terminal*.

**The folder layout must look like this**, or `import botc` will fail:

```
botc-solver/
├── app.py
├── example_game.py
├── README.md
├── ui/
│   └── index.html
└── botc/
    ├── __init__.py
    ├── roles.py
    ├── worlds.py
    ├── info.py
    └── solver.py
```

### 4. Create a virtual environment

A "venv" is a sandboxed Python install per project. Not strictly needed
here (this project only uses the standard library), but it's the habit
worth building:

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

Your prompt will now start with `(.venv)`.

### 5. First run

```bash
python app.py
```

Your browser opens on the grimoire at http://127.0.0.1:8765. Press
Ctrl+C in the terminal to stop it. Nothing gets installed and nothing
leaves your machine — it's the standard library serving one HTML page.

### 6. Using it from your phone

**The solver runs in the browser now**, so a phone answers its own boards
and `app.py` is a convenience rather than a requirement. What the server
still does is hand over the files — and a browser will not import a
module from a `file://` page, so it is still the way in.

Nothing needs it any more. Every answer — solving, the guesswork check,
the diagnosis when a board fits nothing — is worked out on the device.

Both devices have to be on **the same wifi**. This will not work over
mobile data, and it will not work if your laptop is on a 5GHz network and
your phone on the 2.4GHz one with client isolation between them.

**1. Start it with `--lan`:**

```bash
python app.py --lan
```

**2. Read the address it prints.** It looks like this, with your own
numbers:

```
Grimoire running at http://127.0.0.1:8765   (press Ctrl+C to stop)
On this network:   http://192.168.1.34:8765
```

**3. Type that second address into your phone's browser.** All of it,
including `http://` and the `:8765` — Safari will otherwise try to search
for it.

**4. Add it to your home screen.** In Safari, the share button, then *Add
to Home Screen*. It opens without the browser chrome from then on, with
its own icon and title — which is most of what makes it feel like an app.

**It will still need the laptop, and that is worth knowing before you
rely on it.** There is a service worker that keeps a copy of the whole
thing on the device, and a browser will only register one on a **secure**
origin — https or localhost. A LAN address over plain http is neither, so
it quietly does nothing. Everything works while the laptop is awake; it
is just not kept for later. Real offline needs https, which means hosting
it or wrapping it in an app — see Part 10.

### If Safari says it cannot make a secure connection

It never reached the server. Safari tried **https**, and the grimoire only
speaks plain http — so the failure is at Safari's end, before anything
gets sent.

Work through these in order:

**Type the address in full, with `http://` at the front.** Given a bare
`192.168.1.34:8765`, Safari fills in `https://` for you.

**Clear what Safari remembers.** Once it has tried https for an address it
keeps trying, even after you type http. Settings → Safari → Clear History
and Website Data, then type it again in full. Or open it in a Private tab,
which starts from nothing.

**Turn off the https upgrade.** Recent iOS upgrades http addresses on its
own. It is in Settings → Apps → Safari, under Privacy & Security, called
something like *Use HTTPS Upgrades* or *Always Use Secure Connections* —
the wording moves between versions. Turn it off, or add an exception.

**Try another browser.** Chrome or Firefox on iOS are the same engine
underneath but do not share Safari's upgrade setting, so they are a quick
way to tell whether that is what is happening.

**Check the address is the right one.** `--lan` prints every address your
machine might answer on, because Docker, WSL, VirtualBox and VPNs all add
ones that look plausible and that a phone cannot reach. The one you want
usually starts with the same two numbers as your phone's own address —
iOS shows that under Settings → Wi-Fi → the ⓘ beside your network.

**Prove the server is reachable at all** by opening that same address in
a browser *on the computer itself* — not `127.0.0.1`, the network one. If
that fails too, it is the firewall below rather than the phone.

**If the phone cannot reach it**, the usual cause is your computer's
firewall. On Windows the first run pops a dialogue asking whether to
allow Python on private networks — say yes; if you said no, it is in
Windows Defender Firewall under *Allow an app*. On macOS it is System
Settings → Network → Firewall, where Python needs to be allowed to accept
incoming connections. On Linux, `sudo ufw allow 8765` if ufw is running.

**Your laptop has to stay awake and running** for the whole game. Close
the terminal and the phone loses it mid-sentence.

**One caution.** `--lan` puts the grimoire on the network with no password
on it, so anybody on that wifi could open your game. That is fine at home
and at a friend's. Do not use it on a café's wifi, or a conference's.
Without the flag it stays on your own machine, which is the default for
that reason.

---

## Part 2 – Scripts

A script is a name and a set of characters, and nothing else. The
published ones are three such selections; a custom script is the general
case rather than a mode.

**Change** beside the script name opens the picker. Three ways in:

- **A published script** from the list.
- **A script file** — the JSON a Storyteller hands round, the same format
  the official app reads. `_meta` gives the name and author, and
  characters may be plain ids or full objects.
- **Tick your own** from the catalogue.

Characters the catalogue has never heard of are named rather than dropped
in silence, because a missing character means the team counts are wrong
and everything downstream with them. So is a bag too shallow for the
table: a script with three Townsfolk cannot fill a nine-player game, and
without the warning the search simply returns nothing with no reason
given. The check accounts for what a setup-changer could ask for, so a
script with exactly two Outsiders and a Baron is flagged too.

**Characters in the bag but not reasoned about** get their own warning.
They can be dealt, counted and claimed — so the setup stays right — but
their abilities do nothing. Marked with a `*` in the picker. A Grandmother
whose reading is never checked looks exactly like a Grandmother who hasn't
spoken yet, which is why it says so instead of leaving you to find out.

**The Fabled are ticked, not deduced.** A Fabled is not dealt to anybody
— the Storyteller puts it on the table and shows everyone — so whether it
is in play is public and the solver is simply told. What it *did* stays
hidden, which is the whole point of the Sentinel: it may add an Outsider,
remove one, or change nothing, and nothing at the table distinguishes
those. Ticking it takes a 12-player game from 15,120 worlds to 49,680, and
gives you no information in exchange. That is the Sentinel working as
designed, and now you can see the price.

An Outsider more or fewer swaps with a Townsfolk — the table still seats
the same people. How many Outsiders can be in play is not a fixed number
but however many Outsider characters the script has, since each is
unique: a script with eight Outsiders can seat eight. And a bag that
does not seat the whole table is thrown out, which catches a modifier
written with only one side of the swap.

Note the difference from the Baron, which is in the bag *if and only if*
it shifted the counts — the two facts are welded. A Fabled has no such
welding: being on the script only means it is available, and being on the
table means it is in play whatever it did. "Changed nothing" is one of
its answers, not its absence.

**The ledger follows the script.** A reading only exists if the character
that produces it is in the bag, so a script without an Investigator never
offers an Investigator row.

**On a phone the circle stays whole and still.** Showing a slice would
have been the obvious way to fit fifteen seats on a narrow screen, and it
throws away the one thing the circle is for: every adjacency the game
turns on — the Empath's neighbours, the Chef's pairs, the Tea Lady's two
sides — is in the arrangement.

It did once spin, so the seat you tapped came to your thumb. Tried at a
table, that read as a trick rather than a help: the table shifting under
you costs more than the reach saves. Removed.

**The token size is worked out from the dial rather than guessed.** Two
things bound it: a token has to fit between its neighbours on the ring,
and it has to stay inside the guide circles instead of being cut through
by one. Both depend on the screen width and the seat count, so both are
measured.

The version before this set a size at a breakpoint, and the arithmetic
says why that was wrong. On a 390px phone the seats sit 160px from the
centre and the outer guide circle is at 185px — so a 76px token spans 122
to 198px and overruns the circle by 13px. The gold line ran straight
through every token. The constraint was never the space between
neighbours, which is what I had assumed and sized against; it was the
guide circle, which I had not thought about at all.

Measured now, a phone gets a **51px** token — larger than the 46px the
breakpoint had guessed — and it clears both circles at every screen width
from 390px up and every table from five to fifteen.

Only one thing still changes at the breakpoint, and it is about space
rather than size: on a narrow screen only the seat you are on carries its
writing, the rest being in the inspector below where you are looking
anyway.

**The token is the seat.** Whatever is written under it hangs off the
bottom rather than being part of it — which sounds like a detail and is
not. The box used to hold token *and* label and be centred as a whole, so
a seat carrying a label sat higher on the ring than one without. On a
phone, where only the selected seat shows its label, that put one token
22px out of the circle while every other one was on it.

Everything written under a token sits on a **plate**, so the dial's guide
circles no longer show through it. Moving the seats was the obvious fix
and does not work: the labels hang *downward* in screen space rather than
outward from the centre, so a seat at the bottom pushes its label across
the rim while one at the top pushes it across the inner circle, and no
radius avoids both. Clearing the rim would have meant pulling the seats
in far enough to waste most of the board.

The top bar keeps **Solve** and the guesswork check. Save, Open and Clear
are pressed once a game between them and now sit behind a **…** menu
instead of competing with the button pressed every few minutes. Notes
lost its top-bar button entirely — it is a drawer with its own header
now.

**The token turns** once the board actually settles which side a seat is
on — blue for Townsfolk, teal for Outsider, red for Minion, darker red
for Demon — and shows the seat number until then. The seat number moves
to the name line, where the ledger still needs it.

The threshold was chosen by looking at what the numbers do rather than by
taste. A seat that has merely *claimed* a Townsfolk sits at about 71%
Townsfolk on a nine-player board, and an Outsider claim at 60% — so a
lower bar would turn every token the moment claims were entered, and the
dial would be repeating what the seats said rather than telling you
anything. Readings that genuinely confirm somebody push it to the high
eighties, so the bar is 85% with a clear 40-point lead. On a test board
that meant nothing turned on claims alone, nothing turned after two
readings, and three seats turned once an execution and a night kill had
confirmed them.

A seat can be the top suspect and still show its number: 47% Demon is not
a Demon, and the evil ring is already saying what there is to say.

**A small tag beside a seat** opens what is attached to it. For a seat
that has spoken, every reading sourced from it — including ones somebody
else passed on, marked as such. For a seat that has claimed nothing but
said when it wakes, which characters that still allows: a seat saying
"every night" narrows to a handful, and that used to live in a lookup
table you had to go and find. Whatever has happened to the seat is listed
underneath.

The readings are phrased in the game's own words — "1 evil neighbour",
"shot Ines, nothing happened" — rather than as the fields they are stored
in.

The left-hand column is three **drawers** — Information, Notes and
Timeline. Only the one you are using needs to be on screen, and a shut
drawer costs nothing but its title bar, which is what keeps the column
short enough to sit beside the board rather than pushing it off the
bottom. Each header carries a count, so you can see there are readings
recorded without opening it. Which drawers were open travels with the
saved game.

**Notes** is a page per day, newest first, and gains a day as the game
reaches it — the same way the ledger does. Nothing typed there changes a
single number: it is where the Gossip statements go, and anything else
worth remembering that the solver has no business weighing.

**Save** and **Open** write a game to a file with the script embedded. A
board played on a custom script stays readable long after that script file
has been lost, which it would not if it merely referenced one by name.

## Part 3 – Bad Moon Rising

*(Sects & Violets is on the script list and every one of its characters
can be dealt and claimed. What each one does is being added a few at a
time, and until then the script says so rather than pretending.)*

### The first two of Sects & Violets

**Clockmaker.** How many steps from the Demon to its nearest Minion:
around the circle, the shorter way, and the nearest when there is more
than one. First night only, so the dead never come into it. Zero is
false in every world, because it would mean the Demon is its own nearest
Minion.

**Dreamer.** One good character and one evil one, and the seat asked
about is one of the two. That is *two* constraints rather than one — the
pair has to be one of each side as well — which is what makes it strong:
in a world where the Dreamer is genuine it narrows a seat to a choice of
two. A pair of good characters is not a Dreamer reading at all, and no
world is built around one.

Together they bite hard. On a nine-seat board, a Dreamer naming a seat's
own claim clears it to 92%; naming something it did not claim raises
suspicion; and adding "the Demon and a Minion are adjacent" takes that
seat to **78% evil with the Witch on top**.

**And three tests that had been quietly wrong for two scripts.** The
whole Sects & Violets file passed alone and failed in the full suite,
which is always pollution rather than the code.

Three tests register made-up characters to prove that adding one needs no
code change, and cleaned up with `del`. That was written when those names
belonged to nobody — and every one of them later became real: the
Godfather with Bad Moon Rising, and the Klutz, Sweetheart, Mutant and
Barber with Sects & Violets. From then on they were deleting real entries
from the live catalogue, and everything running afterwards saw a script
with a hole in it.

Nothing caught it for two whole scripts, because the damage only shows
when something built at *import* time goes looking for a character a
later test took away. All three put back what they found now, and a test
asks the question directly rather than waiting for the symptom — checked
by reintroducing the bug and watching it fail.

**Mathematician.** How many abilities went wrong tonight — a reading
about the solver's own workings rather than about the table, and the only
one of its kind. Its number *is* the size of the impairment set, so it
constrains how much of the night may have misfired rather than who holds
what.

It is checked as a *range* rather than a number, because the solver never
decides where a Poisoner went unless something forces it. What it does
know is the shape: whoever is always impaired — anybody holding somebody
else's token, a whole table a Minstrel has silenced — plus at most one
seat per source that has to land somewhere. Every count between the two
ends is reachable.

A number outside that range does not make the board impossible. It means
the Mathematician was itself droisoned, which is a thing that goes wrong
too, and those worlds survive at a price.

**And it says nothing at all on a script it cannot account for.** Sects &
Violets droisons in four different ways — No Dashii, Vigormortis,
Philosopher, Sweetheart — and none of them is built yet. Left to itself
the check would conclude that nothing can ever go wrong there, and a
Mathematician truthfully saying 1 would have every real world thrown
away. So on a script with characters still to come it constrains nothing
and says so, which is the same direction the Librarian and the Saint were
wrong in: ruling out a game that happens is worse than admitting
ignorance.

**Flowergirl and Town Crier.** Whether the Demon voted, and whether a
Minion nominated, during the day just gone — so a reading on night three
is about day two. Both needed something the board did not record, so
seats now carry a "voted today" and "nominated today" tick against
whichever day the game has reached, and the ledger gathers them under the
line that closes each day.

The Town Crier's two answers are not mirror images. A **yes** needs only
one nominator who *could* have shown as a Minion, since the Storyteller
chooses how anybody registers. A **no** is the harder claim: every
nominator has to have been able to show as something else — which a Spy
can and an ordinary Minion cannot. Same asymmetry as the Librarian being
told nobody.

They read as you would hope. Three seats vote and the Flowergirl says the
Demon was among them: those three go to 39% and everyone else drops. Say
it was not, and it reverses exactly. One seat nominates and the Town Crier
hears a Minion: that seat goes to **59%**.

### Playing games out

The three published scripts are done, so the next thing is not another
character: it is finding out how good the answers actually are. The
simulator has always dealt boards; now it plays them, and writes down
what happened.

`tests/claims.py` is the part that is not rules. Good players mostly tell
the truth — a full claim, or a softclaim of when they wake, which the
board already records as a wake pattern. About one in ten lies anyway,
nearly all Outsiders hiding behind a Townsfolk claim, plus the occasional
chaos claim with no logic behind it. Evil is handed three bluffs that are
not in play and takes one at random rather than cleverly, because the
moment it reasons about which bluff is *plausible* it is doing a weak
version of the solver's job and the two would agree by sharing an
assumption rather than by being right.

The chaos claim is the part worth defending. Every other lie is one the
solver already prices, so a simulation producing only those would keep
agreeing with the solver's own assumptions and prove nothing.

**Evil had to learn to divide its bluffs.** Left to chance, two Minions
picked from the same three independently and collided with *each other*
two-thirds of the time — a table nobody has played at, and one that made
the solver's job far easier than it should be. They take one each now,
and when there are more evil players than bluffs the last one
double-claims a character a good player really has. At fifteen players
that happens in almost every game, which is what a real table looks like.

`tools/play_games.py` writes a protocol: the true assignment, then phase
by phase what the Storyteller did, what each seat learned, who claimed
what and *why*, and where the solver stood at that moment. Plus the same
game as a save file, so it can be opened in the grimoire and stepped
through by hand. That second part matters more than it sounds — the first
thing this measures is the **simulator**, not the solver, and if it
resolves an ability wrongly then everything downstream is confidently
wrong in the same direction. No assertion catches that; a person reading
a played-out game does.

### Repairing a board somebody lied to

Rather than widening the search, posit a lie only when the board needs
one — the same shape the Pit-Hag uses. Solve normally; if nothing fits,
try each seat as the liar and keep whichever leaves the board best
explained. It costs nothing on an ordinary board.

**A board can fit badly as well as fit nothing**, and that took a played
game to see. In one, a good player chaos-claimed the Saint while somebody
really *was* the Saint. Seven worlds survived — so the solver had an
answer — and the real Demon was evil in none of them. Nothing was
impossible; the solver had simply committed, hard, to the wrong side of a
double-claim, and reported the true Demon at **0%**.

So repair fires on a cornered board too: a handful of surviving worlds
out of a legal space in the thousands is not confidence, it is a board
that has been told something untrue. That game now names the liar
correctly and puts the Demon second at 21%.

The repaired board has to be *better explained*, not merely larger.
Opening a claim always admits more worlds, so counting them would repair
every board on the table.

### What is next

`NEXT.md` holds the plan, in phases sized to finish in one sitting each:
make the tests runnable again, then the seed-8 mystery, then the rest of
the Sects & Violets readings, then calibration. They are ordered so that
no phase depends on one below it.

### Tests that stopped finishing

`test_claims` grew past the point of completing at all, which meant the
work it covered could not be verified. Timing each class separately
showed the cost was not spread — four classes were all of it, and the
worst was not recent work.

Seed counts came down, and the curves are cached: three tests each
recomputed the same fourteen five-night games, solving every night of
each. That alone was 145 seconds for no coverage.

The trimming caught a test in the act of being wrong: `assertGreater(
solved, 15)` against twenty games became unreachable at six, so it failed
for a reason that said nothing about the solver. Counting a share is what
it meant all along, and there are probably more like it.

### Two levers on a reading

A ledger row now carries two separate judgements, and they answer
different questions.

**"believe it"** — how far you think the reading *happened*, which
prices a world where the row was invented. It matters when somebody
relays information second-hand and no seat has claimed the character it
came from: did an Empath say that at all?

**"checked out"** — whether the table later agreed the reading was
*right*. Evidence that its source really is who they claim, worth an
odds multiplier of 2.5 and accumulating per reading: an Undertaker with
three confirmed rows goes from 43% to 76% "really the Undertaker" while
its evil reading falls from 23% to 2.4%. It never reaches certainty,
because a Spy reading the grimoire can feed a Minion true information all
game — which is what separates it from the seat-level "confirmed" that
pins a character outright, and why it is not offered on a Virgin or
Slayer row.

**The first of those had never been reachable.** `trustSel` was written,
`TRUST_WORDS` was written, the constant was tuned and the solver logic
was tested — and nothing on the page ever called the function, so every
reading sat at neutral for the life of the project. Wiring it up took one
line and immediately showed it working: weight on worlds containing an
Empath moves 5% to 30% across the range.

It only bites when *some* worlds hold the character and others do not.
When no world can, every world pays the same invention cost and it
cancels out of the percentages — which is arithmetically right, and why
three probes in a row showed nothing before the fourth showed everything.

### The Drunk had nothing to say

It never spoke. `honest_info` skipped any seat that was not *working*,
which meant a Drunk was silent for the whole game — and silence reads as
a seat with nothing to prove. A Drunk that talks confidently and turns
out wrong is exactly what draws suspicion at a real table, so its absence
removed the main source of honestly-wrong information.

It wakes on the schedule of the character it *believes* it is now, and
hears that character's kind of answer: mostly false, sometimes true by
accident. Nobody bluffs as the Drunk any more either — it is not a token
anyone has ever been handed, and the same goes for the Marionette and the
Lunatic.

Two bugs fell out immediately, both the same assumption: **that every
reading comes from a working seat**. A test asked a misregistration
question of an invented reading — a Drunk holding an Investigator token
can be told anything about anybody, which is not misregistration. And the
falsifier assumed every pair-reading has a pair, so a Librarian told
*nobody* crashed it.

### A seed is a bad name for a property, again

`CONFIDENTLY_WRONG` drifted for the third time. It is not a seed now:
`a_confidently_wrong_game()` searches a range for a board with the
property, which costs a few seconds and cannot go stale.

One of those tests was also asserting something no longer true — that
repair *fires* on a board with two hidden Outsiders. With four hundred
worlds surviving, that board is not cornered and repair never triggers.
The real point stands, and the claim is narrowed to it: one posited lie
cannot cover two.

### Three characters that move the board

A Philosopher gains an ability, a Snake Charmer swaps character and side
with a Demon, a Pit-Hag turns somebody into something else. None of them
reports information; all of them change who holds what.

`role_at` used to assume every change was a Demon handover and that the
heir was an Imp. It works from a general change list now, with a
`side_at` beside it for the cases where side and character move
independently — the Snake Charmer swap sends character one way and
alignment the other.

Three bugs came out of building them, and all three were the same
mistake in different clothes: **reading the deal instead of the
timeline**, or **treating a choice as information**.

`demon_at` read the deal rather than the changes, so a Demon that swapped
away with a Snake Charmer went on killing from a seat that was no longer
the Demon. The simulator's `_make_false` flipped every boolean by name,
`swapped` among them, so a charmer that chose an ordinary player came out
claiming it had swapped with them. And the Philosopher's gained ability
was immune to a Vortox entirely.

### A droisoned character cannot misregister

Registration is a **plain ability**, and a plain ability simply does not
function when its holder is droisoned. A Storyteller chooses freely what
a droisoned *information* role yields, because the information is
arbitrary — but a poisoned Recluse is a Recluse and shows as one.

The interesting part is where the check could not go.
`registers_as_role` takes two character names, and giving it a world and
a phase would not have helped: **whether a seat was droisoned is not
known when `holds` runs.** Droisoning is *chosen*, by the impairment
plan, which settles afterwards.

So a row says what it **leaned on** — which seats had to misregister for
it to hold — and those seats are forbidden from being droisoned that
night. The plan already understood "must not be impaired"; this is the
first caller to use it for registration.

It is correctly permissive: an Investigator leaning on the Recluse plus a
false Empath still fits, because the Poisoner can be elsewhere. It rules
out the combination, not the board.

**Count readings have none, deliberately.** A Chef, Empath or Oracle
holds if its number falls anywhere in a range built from every
combination of how everybody could register — so there is no single seat
the answer depended on. A Chef told "one" beside two Recluses leaned on
*one of them*, and which is not a question the reading can answer.
Handling it means carrying alternative explanations rather than one, and
that is written down rather than half-built.

### A fix in one place made a test forty times slower

Worth recording because nothing connected the two except the clock.

Boards needing repair went from about one in six to **one in forty** once
the simulator stopped producing claims nobody could make. So three tests
that *search* for such a board went from playing six games to playing
nearly forty — 249 seconds between them, and no cause anywhere near the
tests themselves.

They stop at the first qualifying board now. One is the whole claim.

### The deal is not the timeline

Characters move. A Pit-Hag creates one, a Snake Charmer swaps two, a
Barber lets the Demon trade a pair, a Farmer hands its own on. So asking
`d.roles[seat]` — what a seat was *dealt* — is the wrong question
wherever the answer should be what it holds **now**.

That mistake has been found four separate times, each as an impossible
board on a mixed script:

  * `demon_at` was hardcoded to the Imp, so two whole scripts reported no
    Demon at all;
  * and then read the deal rather than the changes, so a Demon that
    swapped away went on killing from a seat that was no longer the
    Demon;
  * the Demon's *kill* read the deal, so a seat dealt a Snake Charmer and
    holding a Zombuul by night two killed generically — on a night after
    an execution, which a Zombuul may not do;
  * and an Evil Twin built its list of good players from the deal, so a
    seat a Pit-Hag had just made the Evil Twin still read as good and
    picked **itself** as its own twin.

After the fourth, the rest were swept rather than waited for: the
Grandmother's grief, the Barber's swap, the Soldier's protection, the
Vortox's inversion, the No Dashii's neighbours and the Vigormortis's dead
Minions all ask the timeline now.

### The first experimental character

**The Farmer**: dies at night, and an alive good player becomes the
Farmer.

  * **Any** night death does it — a Gossip kill, an Assassin, a Pukka's
    poison — not only the Demon's, which is what separates it from the
    Grandmother's grief. An execution does nothing.
  * Heirs are chosen by **registration**, so a Spy may be handed it and
    **stays evil**. An evil Farmer is a real thing, the same shape as a
    Pit-Hag creation keeping its own side.
  * It **chains**: the new Farmer is a new instance.
  * A Vortox does not touch it. It yields a character change, not
    information — which the new `is_information` answers in one place
    rather than character by character.
  * It never wakes. Being told your new character is a *game rule*, not
    the Farmer's ability, so a Chambermaid does not count it.

Chaining needed a fix worth keeping: `find_at` returns the *first* seat
holding a character, which is the Farmer that was dealt — and that seat
goes on being a Farmer in the base world after it dies, so the chain
never looked past it. Every holder is collected now. The Farmer is the
first character where several seats genuinely hold it across one game.

Forty mixed-script games with the Farmer forced onto every script: **no
impossible boards.**

### Legal is not true

Misregistration is the mechanic that lets a Storyteller give false
information **legally**. A Spy shown as the Slayer is still a Spy — the
reading is false, and being permitted does not make it true.

`registers_as_role` answers one question — *could the Storyteller have
said this* — and for a long time the Vortox inversion asked it too. But a
Vortox falsifies what an ability *yields*, so it needs the other
question: *was it so*. A legal misregistered reading therefore looked
true, the Vortox had to be droisoned to explain it, and boards that
really happened were priced as though something had gone wrong.

The two are separate now. `is_really_role` asks about the seat, and rows
that can misregister carry an `is_true` beside their `holds`.

### A gained ability has no holder

The solver finds characters by asking who *holds* them, and a Philosopher
that has **taken** an ability breaks that: nobody holds the Snake
Charmer, so `find_at` says there is no charmer and the swap could never
have happened — while the table has heard a Snake Charmer row and the
board has plainly changed.

Worth watching for wherever else a character is looked up rather than
passed in. The Philosopher is the only source of it today; anything that
grants an ability without moving a token will have the same shape.

### A Tea Lady who never protected anybody

She keeps both her living neighbours alive when both are good. The solver
has modelled her since she went in and the simulator never did — so a
Demon killed straight through her, and the board had no legal world
because nothing could explain why she failed.

The **tenth** character found dealt-and-never-acting, all by the same
route: a board the solver refuses, traced back to something the simulator
does not implement. The lesson has not changed since the first one — a
character the simulator never fires is a character whose rule has never
been checked.

### The Alsaahir, and the Po's charge

**Once per day, if you publicly guess which players are Minion(s) and
which are Demon(s), good wins.** A day ability, like the Slayer, and not
in the vendored data at all.

Every seat whose *current character* is a Minion or Demon, alive or dead
— which covers a good Minion made by a Pit-Hag, and a Fang Gu that jumped
leaving two Demons to name, the corpse and the seat that inherited. A
failed guess rules out that whole configuration, which is stronger than
anything else in the ledger.

Its one real bug was `is_a_choice`. A Vortox falsifies *information*, and
nobody tells the Alsaahir anything — it is a public statement whose
consequence the table watches, like a Slayer's shot.

And the board it shared with three other gates was the **Po**: it charges
by taking *nobody*, and the solver asked whether *anybody* died on the
charging night. A Tinker that simply went, an Acrobat that fell, a
Gambler that guessed wrong — all die with the Po charging quietly beside
them. Whether the Po killed cannot be read off the deaths, because the
deaths are what is being explained.

### A build step that depends on a human is not a build step

Two characters were added to the Python catalogue. They reached the
solver, the tests, the ledger and all four gates — and never reached the
built site, because `js/characters.mjs` is written out of Python by
`tools/gen_characters.py`, a **separate script run by hand**, and
`build_site.py` only copied whatever was already sitting there.

It took a dozen rounds to find. Every artifact was checked and every one
was correct: the Python catalogue, the generated JavaScript, the built
`docs/`, the shipped zip, and the zip extracted and *run as a browser
would*. Each confirmed the last, because all of them were downstream of
Python and none was downstream of the **generator**. The one time it
appeared to work, the generator had been run by hand for another reason.

The build runs it now, and before the copy rather than after — the first
attempt regenerated into a folder already written.

The entry point is stamped too: `./api.mjs?v=<fingerprint>`, sharing the
service worker's hash, because a browser caches an ES module hard enough
that a stale copy can be served under a fresh worker.

**What would have caught it**: does building actually rebuild? Nothing
asked that. Everything asked whether the layers agreed, and they did —
about a stale answer.

### The walk visits slots, not seats

A Snake Charmer at slot 11 takes the Demon's character. The Demon acts at
32. But the walk iterated **seats**, in an order fixed by who held what
when the night began — so the seat now holding the Demon had already been
visited at 11 and never came round again. Nobody killed, on a night the
record said somebody died.

It iterates the slot numbers now and asks, at each one, *which seat holds
a character with this slot right now*. The question is asked after every
change rather than once at the start, and a seat may act twice if two
characters pass through it, which is correct: the Storyteller wakes
whoever holds the token when that token's turn comes.

The simulator always worked this way, which is exactly why the two
disagreed.

**It had been wrong since the Snake Charmer went in**, and was hidden
because the simulator was swapping twice a night — every early chooser
acted once in the early pass and again in the readings pass, and two
swaps of the same pair cancel. Fixing the double pass exposed a fault the
walk had carried all along.

### The rules run in the order the night ran

Each transition rule sees the previous ones' work through a `Timeline`
and appends its own changes, and `role_at` takes the last change at a
phase — so **the sequence the rules run in is the sequence of the
night**. The registry's comment said "order does not matter; they
compose". It did matter.

They ran Barber, Pit-Hag, Farmer, Snake Charmer: slots 40, 16, 48 and 11,
almost exactly backwards. On a night with a charmer swap at 11 and a
Pit-Hag at 16 the Pit-Hag's change landed first and the swap overwrote
it, so the Pit-Hag's own row read as false and explaining it needed a
Pit-Hag nothing could droison.

The other way to fix this was to sort the chain afterwards, which needs a
field `Change` does not have — the *actor's* slot, not the granted
character's. Ordering the rules needs nothing new at all. Raised at the
table, and much the cheaper of the two.

### A Demon that stops being one

**One bug, not two.** The swap rule copied the wrong character. It read the Demon's role
from the *view it was handed*, which the Pit-Hag rule had already
modified — so on a night with both, the charmer received the Pit-Hag's
gift instead of the Demon's character and **the Demon vanished from the
board entirely**. No cause for any night kill, and every world refused.

Found by the table, from a single observation: if the Pit-Hag died on
night four it was the Vigormortis that killed it, so there had to be a
Vigormortis. There was not.

`demon_at` looked broken too and was not. It tracks changes that grant a
demon role, and a swap *is* such a change — it only failed while the swap
was putting the wrong character in it. Rewriting it to read the board
then threw away eight legal worlds on Trouble Brewing, because **holding
a demon character is not the same as being the Demon**: after a Scarlet
Woman takeover the executed Imp still holds the Imp, and the board cannot
say which of the two is the acting Demon.

### A ceiling that was ignored

`solveBoard` takes a `maxWorlds` and passed `EXACT_LIMIT` to `analyze`
regardless, so the hosted page's real ceiling was 40,000 whatever it
asked for. Python's is 600,000, so one corpus board with 51,516 worlds
was enumerated exactly on one side and sampled on the other — three
points of difference on a board where no rule differs at all.

Worth knowing for what it says about comparing the two languages: the
answers can diverge because one of them *gave up*, and that reads exactly
like a rules disagreement.

### Both sides must know the same rules

Three readings — Acrobat, Balloonist and Alsaahir — shipped with **no
JavaScript implementation at all**. The hosted page runs the JavaScript,
so entering one and pressing Solve died with "Unknown kind of reading".
Nothing caught it, because every check compared Python against Python.

Six registries are now compared by name across the two languages:
readings, transitions, causes, impairment sources, waking conditions and
death immunities. All six agreed when the tests went in — the gap was
only ever in the readings — and both kinds of failure were verified by
breaking them deliberately.

That is the only thing that catches a rule written on one side and
forgotten on the other, and it is worth more than any amount of testing
one side thoroughly.

### The built site is a layer too

Python is checked against JavaScript, the solver against the walk, the
page's fields against the app's readings — and nothing checked the
**built site** against the source it was built from.

Two characters added in one session were reported missing from the hosted
page. Every check available said they were present, because every check
was reading a layer the hosted page does not use: the site computes its
own catalogue from bundled data at load time, and that bundle was old.

**A stale build looks exactly like a missing character.** Three
assertions now run `solver.meta()` out of `docs/` and compare it against
the Python catalogue — every character reaches the page, the page invents
nobody, and the teams agree, since a character under the wrong heading is
how somebody fails to find it.

Worth noting how it was found: not by a test, but by somebody saying "the
Balloonist is not on there — am I wrong or you?" The answer was me, three
times over, because I kept checking the layer that was easiest to reach
rather than the one being looked at.

### An honest heir was priced below the lie

A Farmer that dies at night hands the character to a living good player,
who then says "I am the Farmer" — truthfully. `is_lying` compares against
the character the seat was **dealt**, so it says yes, and a good seat
that lies pays `TOWNSFOLK_LIE_PENALTY` at 0.02. A Demon bluffing the same
character pays `BLUFF_COLLISION_PENALTY` at 0.3.

**The honest explanation was fifteen times less likely than the lie.**

It is *weighting*, not legality, and that is the whole reason three
earlier attempts moved nothing: each widened the world enumeration, and
nothing needed widening. Both worlds were always legal and always
generated; one was simply priced absurdly.

Two things the fix had to get right. The exemption depends on the
**world**, not the seat: exempting the seat outright made the demon's
bluff cheaper too and the answer got worse, 95.5 per cent to 98.6. And
the seat that died is not its own heir.

It does not overturn the board it was found on — seat three is the Imp in
153,000 surviving worlds and the Farmer in 62,000, and a fifteen-fold
correction on a subset does not beat that. With that little information a
specific inheritable claim really is more often a bluff. The fix stands
on its own merits: an honest player should not be charged as a liar.

### Measure the bug, do not guess it

Standing instruction from the table, and it was earned.

A test asserting "all three readings appear" started failing after the
Pit-Hag was corrected to act from the second night. The first fix was to
widen the sample from 40 games to 90 — a guess, on the reasoning that a
rarer event needs more trials. It fixed nothing and cost four hundred
seconds of test time.

Measured instead: **none at all in 90 three-night games, none in the
first 40 four-night ones, first hit at seed 96, 19 games in 300 producing
a row.** A Pit-Hag has to be dealt, survive, stay sober, and then win a
one-in-four draw on one of only two eligible nights. The fix was a fourth
night *and* 120 games — neither of which the guess would have reached.

The same session produced three other wrong diagnoses asserted without
reading the code that would have settled them: that the transition rules
cannot see each other (they are sequenced, each seeing the last through a
`Timeline`), that a Po had killed itself (a swap had moved the Po
elsewhere), and that a chain check needed the impairment plan when the
check simply had a duplicate definition shadowing it.

Every one would have been a single command to check.

### The vendored data is not a source for what characters do

`data/roles.json` gives the **old** Balloonist — "learn 1 player of each
character type, until there are no more types to learn". The current card
is "each night, you learn a player of a different character type than
last night", which is a different mechanic. Building from the file would
have produced the wrong character.

It is authoritative for the **night order** and nothing else. The wiki is
the source for abilities.

### The Balloonist, and a reading that only means something in sequence

Every other row here can be judged against a world on its own. A
Balloonist's night means nothing without the night before it, so the
chain is checked once per world rather than row by row.

Registration is what makes it a search instead of a comparison: a Recluse
counts as Outsider, Minion *or* Demon, so one seat can satisfy several
links — the wiki notes a devious Storyteller could show the Recluse every
single night. Under a Vortox the reading must be false, and false here
means consecutive types were the **same**.

Two things it taught:

  * **The type is the one shown *then*.** A seat shown on night one can
    swap into a Demon by night two, and what the Balloonist saw was the
    character it held when the token was pointed at.
  * **A chain is only judged where the claim is true.** These rows are
    what somebody *said*; in a world where that seat is not the
    Balloonist they are a lie, and the chain has no business fitting.

### A character is not done until it reaches the ledger

The Farmer and the Acrobat both passed their forty-game gates while being
impossible to *enter* — built in the solver, the walk and the simulator,
and never wired into the page. "Done" had meant done in the model.

An audit test compares the fields the page offers against the readings
the app lists, and caught both. The gate is now: solver, walk, simulator,
forty mixed games, **and the ledger**.

### A rule asked in six places belongs at the choke point

A **Tea Lady** keeps both her living neighbours alive when both are good.
Full stop, whatever the death comes from — a Demon, a Gambler's wrong
guess, an Acrobat's droisoned pick, a Tinker simply going.

The simulator had her, and reached her from **one** of the six ways to
die. So a Tinker died beside a working Tea Lady and the solver — which
applies her shield to every cause — had to demand she was impaired, with
nothing on the board able to impair her. That board had no legal world.

The night-walk did not have her at all, and agreed anyway, by luck.

She lives in `kill()` now rather than at each cause, which is the same
shape as `droisoned_at` (five sources had been missing from it) and
`hidden_from` (four inputs). **When a rule has to be asked in several
places, the fix is to put it where they all pass through**, not to
remember it at each.

### The Acrobat, which needed all of this

**Each night, choose a player: if they are or become drunk or poisoned
tonight, you die.**

It could not be modelled in the three-pass design at all. The inference
needs the impairment plan and the death causes settled together, and both
directions were tried and withdrawn — a surviving Acrobat means the pick
was clean *or* the Acrobat was itself droisoned, and a dead one is only
informative if its own ability killed it.

In the walk it is four lines, because the night has already happened by
the time it is asked. Verified exact on thirty-five nights.

### The switch stays off, and that is the finding

`WALK_CHECKS_STORIES` works. Across 45 published boards it checked 259
candidate stories, refused 9, and lost **no true world** — every board
still solved. It correctly identifies timelines that could not have
produced the record.

And it is worthless, measured on the board where it refuses most:

    switch off   672 worlds,  5.7 seconds
    switch on    672 worlds, 60.9 seconds
    every seat's evil percentage identical to two places

Three and a half thousand stories refused on that board, and not one
number moved. **Every story the walk rejects would have scored zero
anyway** — the plain path already refuses them, more cheaply, by other
means. The walk is a second opinion that never disagrees with the
verdict, only with the reasoning, at eleven times the cost.

So it stays off. Not because it is wrong or unfinished: because the
question it answers was already answered.

What the walk is still for is what it has always been good at: **an
independent second implementation of the night**. It replays 180 of 180
nights and has found bugs by disagreeing with the simulator — a Drunk
performing real Snake Charmer swaps, early choosers acting twice a night,
a Demon that stopped being one. Two implementations that disagree are
worth more than one that is trusted.

Getting here took three sessions and several wrong turns, including two
attempts to fix an ordering fault that was real and not the cause. The
measurement that settled it was one board compared twice — which was
available from the start.

### The walk searches a night, it does not check one

`WALK_CHECKS_STORIES` is in `best_story`, off by default, and it works.

The first design said "propose then walk": the impairment plan proposes
where each source went, the walk replays it. **The proposing half did not
exist** — `plan_night` answers "can these sources impair exactly who is
*required*", so with nothing required it places nobody.

Worse, the Demon's aim could not simply be handed over either: the aim is
what the deaths are *evidence for*, so feeding them back would make the
check confirm whatever it was told.

Both problems dissolve if the walk **searches** instead. Enumerate every
arrangement of the droison sources, crossed with everything the Demon
could have aimed at — nobody, any seat, any pair for a Shabaloth, any
three for a Po — and keep what reproduces the record.

    nights 120, explained 120
    walks per night: median 5, mean 10.3
    whole corpus: off 46.1s, on 48.8s, 0 of 138 answers differ

It agrees everywhere and costs six per cent. That is enough to land it
and not enough to make it authoritative: those 138 boards were all built
by the old path, so they can confirm agreement and never disagreement.
What would earn switching it on is a board where the two differ and the
walk is right.

### The walk meets the solver

`WALK_CHECKS_STORIES` sits in `best_story`, off by default: each
candidate story would be *replayed* before being scored. Three things
came out of building it.

**The seam is small.** The walk asks a board four things — `n`,
`role_at`, `side_at`, `alive_at` — and a solver world answers two
already, so the adapter is a dozen lines. It replays **180 of 180**
nights over the views the solver actually scores. Hand it the bare
`World` rather than the `Timeline` wrapped around it and that falls to
174: a world says who was *dealt* what, and a swap lives in the view.

**Cost is not the obstacle.** A walk is 15 microseconds against
`_explain`'s 156. A check that discards a story early *saves* time, which
is the opposite of the worry that prompted measuring it.

**But the plan is a cost model, not a generator.** `plan_night` answers
"can these sources impair exactly who is **required**" — so with nothing
required it places nobody, and the walk has nothing to replay. The design
said "propose then walk" and the proposing half does not exist. Turning
the switch on needs a way to *enumerate* where each source could have
gone, which is a new search; the measurement above says checking each
candidate would be affordable once it does.

### A Snake Charmer swaps immediately

Settled at the table, and it took four fixes of the same shape.

A charmer acts at slot 11 and every Demon at 24 or later, so by the time
the night's kill is made the charmer holds the Demon — and it is the
charmer's seat that kills. The old Demon is a poisoned good Snake
Charmer and kills nobody. It also **cannot swap again**: the poisoning is
permanent, so pointing at the Demon a second time does nothing.

Both sides had recorded the swap at the day *after*. The solver's comment
explained why: writing it at the night made the charmer's own row read as
invented, and a world where the swap really happened scored 0.4 against
1.0 for one where it could not. Exactly backwards.

That symptom was real and the cause was elsewhere. **A row belongs to
whoever acted**, which is the board as it stood when the night began; the
board afterwards is a different question, and the phase cannot tell them
apart. Four places were asking the second question and needing the first:
the transition rule, the row-to-speaker attribution, the ability check
that charged the penalty, and the simulator's own early-choice pass.

### The walk starts before the night, not after it

`role_at(seat, "N2")` already contains every change stamped at N2, so
the walk was starting from the board *after* tonight and then walking the
night — applying tonight's changes a second time. For a Pit-Hag creation
that is invisible, because setting a seat to a character it already holds
does nothing. For a swap it is a bug: doing it twice swaps the pair back.

It starts at the end of the previous day now and *becomes* the board by
walking. Anything else is applying history twice and hoping it is
idempotent.

### The walk says when it has not been told

Three comparisons in a row failed because a probe forgot a hidden input,
and each time the failure pointed at the walk. Being under-informed
looked exactly like being wrong.

`hidden_from` now builds every hidden input in one place — making the
correct path cheaper than the mistake, which works better than resolving
to remember — and the walk records `untold`: characters that always act,
are alive and working, and that it was told nothing about.

Turned on, it flagged 41 of 180 fully-informed nights. Every one was
real: three characters whose announced rows nothing was reading, an
Exorcist that never acted at all, and a check that ran before the night
when it had to run after. It reads zero now.

### One function, two questions

Three times now a single function has been answering two questions that
agree for almost every character — which is exactly why each went
unnoticed for so long.

  * `registers_as_role` answers *could this have been said*. A Vortox
    needs *is it true*, because misregistration makes information legal
    and not true. Split into `is_really_role`.
  * `holds` answers whether a reading is consistent with a world. The
    Vortox inversion needs whether it was **so**. Split into `is_true`.
  * `woke` answers *did this seat wake*, which decides what a player
    could honestly claim about their nights. A Chambermaid asks *did its
    own ability fire*. A Lunatic is shown a Demon's night and made to
    choose victims who never die: it wakes, and none of it is its own
    ability working. Split into `woke_for_own_ability`.

### Anything that droisons belongs in one place

`droisoned_at` answers "is this seat drunk or poisoned tonight", and four
separate sources were found missing from it: a **Minstrel** silencing the
table after a Minion is executed, a **Philosopher** drunking whoever
really holds the character it took, and an **Innkeeper** and a **Sailor**
each drunking one of the players they touched.

Every one was recorded where it happened and absent from the one place
that answers the question. Four is a category rather than a coincidence,
so the rule is written at the site: anything that droisons must be
*there*, not merely recorded elsewhere.

### Characters that were dealt and never acted

Counting what the simulator *records* against what it *deals*, twelve
characters produced nothing at all — among them a Monk that never
guarded, a Sailor that never drunked, a Witch that never cursed.

That matters more than it looks. The walk is verified against nights the
simulator plays, so **a character the simulator never fires is one whose
rule has never been checked**. Making the Sailor and the Innkeeper act
immediately found three bugs, and the Professor was withdrawn from the
walk entirely for want of anything to check it against.

### A phase is not an instant

`N2` covers seventy-odd slots, so two things happening on the same night
are indistinguishable to `phase_index`. That cost a real bug and it took
a while to catch, because every guess along the way was wrong.

A **Barber swap** made a seat a Pit-Hag *after* a Mathematician had
counted — and since a change is stamped with a phase rather than a slot,
it back-dated to the start of the night. The Mathematician's row was then
computed against a board that no longer existed.

Three board-changing steps were running after the readings when, by slot,
they come before every character that reads:

    Acrobat 39   Barber 40   Farmer 48
    Empath 53   Oracle 59   Mathematician 71

Ordering the code is the cheap fix and it is what was done. The real fix
is the night-walk, which cannot have this bug at all: it holds one state
and moves forward through it, so "before" and "after" within a night are
structural rather than encoded in a comparison.

Two larger changes were considered and rejected — putting slots on every
change, which is a coordinate-system change across fifty-six call sites
to fix what three misplaced lines caused; and letting the walk take over
the simulator's night, which would destroy the thing that found the bug
in the first place. **Two independent derivations disagreeing** is where
nearly every bug here has come from.

### Absent is harder to notice than wrong

Twice now the bug in a reading has been that **no answer was produced at
all**, and neither time did anything look broken.

A **Ravenkeeper** reads *because* it died, and the guard asked whether it
was working before the exemption that lets the dead read — and `working`
requires being alive. So the one character that has to be dead to read
was rejected, and no Ravenkeeper reading was ever taken. The comparison
had nothing to compare and passed.

A **Philosopher** that takes the Flowergirl reads at the Flowergirl's
slot, not its own. The walk looked up "Philosopher" in its table of
readings, found nothing, and skipped it.

Every comparison here now asserts a minimum count — `assertGreater(found,
0, "no Ravenkeeper read at all")`. A test that can pass on an empty
comparison is not a test.

The same instinct made the **Professor** come out again: it was written,
and then removed, because the simulator never fires one. There was
nothing to check it against, and an honest gap is worth more than an
unverified derivation.

### The Oracle was counting the wrong moment

An Oracle reads at slot 59 and a Demon kills at 24, so by the time it
counts the dead, tonight's victim is among them. Both the simulator and
the solver used the set of players alive at the *start* of the night,
which is a different question.

Found by the night-walk deriving the count independently and
disagreeing — and then by the test suite showing the shipped solver had
the same mistake. It is the kind of error that can only surface once
something knows what order things happen in.

Getting to a clean comparison needed three filters, and they are worth
naming because they apply to every reading: a **Vortox** falsifies the
answer, so the simulator records a lie; a **droisoned** seat is told
whatever the Storyteller likes; and only with both excluded does a real
disagreement show. The Oracle looked like 13 of 25 until then, and is 23
of 23 now.

### An ability is judged when it acts

Found by the walk's own log, and it is the sharpest illustration of why
the night needs an order.

A Demon that chooses the **Goon** is made drunk by it — the Goon's card
says the first player to choose it is drunk. But the choice is already
made, so the kill still lands. Testing whether the Demon was working
*after* the Goon had turned had a Goon protecting itself from every Demon
that picked it, which is not what the card says. Twelve nights in eighty.

Whether an ability functions is decided **when the character acts**, not
after its own target has answered back. No arrangement of three separate
passes can express that; walking the night in order gets it for nothing.

### A night can be replayed

The solver settles a night in three passes — transitions, death causes,
impairment plan — and none can see the others. Almost every character
depends on the order, so that has to change.

The **Goon** is the argument. The first player to choose it tonight is
drunk, and the Goon becomes *their alignment*: a Sailor acts at slot 4
and a Poisoner at 7, so if both choose the Goon it ends the night good,
and if only the Poisoner does it ends evil. Order decides an *alignment*
there, not merely whether an ability worked, and no arrangement of "who
was droisoned" can express it.

Before rewriting anything, the question worth answering was whether a
night can be **replayed** at all. `tests/nightwalk.py` walks one slot by
slot; it reproduces **every night of all three published scripts** —
240 of 240 — and gets the Goon right in both directions.

Twenty-one characters are in it. Getting there found real things in the
simulator too: it was throwing away what the Demon *aimed* at, so a
Shabaloth kill sunk into a corpse left no trace, and overwriting the
Pukka's poison before anybody could ask which seat's came due.

That changes the size of the job. The walk is handed the hidden choices —
where the Poisoner went, who the Demon took — because in the solver those
come from the impairment plan, which already searches over exactly them.
So the redesign is a change to how a candidate is **checked**, not an
explosion in how many candidates there are. Eleven choices are already
recorded, because good players announce what they did.

Fifty more characters have slots and each needs its action written into
the walk. That is the real work, and it is now unrisky rather than a
gamble.

### A gained ability has no holder

The solver finds characters by asking who *holds* them, and a Philosopher
that has **taken** an ability breaks that: nobody holds the Snake
Charmer, so `find_at` says there is no charmer and the swap could never
have happened — while the table has heard a Snake Charmer row and the
board has plainly changed.

Worth watching for wherever else a character is looked up rather than
passed in. The Philosopher is the only source of it today; anything that
grants an ability without moving a token will have the same shape.

### A Tea Lady who never protected anybody

She keeps both her living neighbours alive when both are good. The solver
has modelled her since she went in and the simulator never did — so a
Demon killed straight through her, and the board had no legal world
because nothing could explain why she failed.

The **tenth** character found dealt-and-never-acting, all by the same
route: a board the solver refuses, traced back to something the simulator
does not implement. The lesson has not changed since the first one — a
character the simulator never fires is a character whose rule has never
been checked.

### The Alsaahir, and the Po's charge

**Once per day, if you publicly guess which players are Minion(s) and
which are Demon(s), good wins.** A day ability, like the Slayer, and not
in the vendored data at all.

Every seat whose *current character* is a Minion or Demon, alive or dead
— which covers a good Minion made by a Pit-Hag, and a Fang Gu that jumped
leaving two Demons to name, the corpse and the seat that inherited. A
failed guess rules out that whole configuration, which is stronger than
anything else in the ledger.

Its one real bug was `is_a_choice`. A Vortox falsifies *information*, and
nobody tells the Alsaahir anything — it is a public statement whose
consequence the table watches, like a Slayer's shot.

And the board it shared with three other gates was the **Po**: it charges
by taking *nobody*, and the solver asked whether *anybody* died on the
charging night. A Tinker that simply went, an Acrobat that fell, a
Gambler that guessed wrong — all die with the Po charging quietly beside
them. Whether the Po killed cannot be read off the deaths, because the
deaths are what is being explained.

### A build step that depends on a human is not a build step

Two characters were added to the Python catalogue. They reached the
solver, the tests, the ledger and all four gates — and never reached the
built site, because `js/characters.mjs` is written out of Python by
`tools/gen_characters.py`, a **separate script run by hand**, and
`build_site.py` only copied whatever was already sitting there.

It took a dozen rounds to find. Every artifact was checked and every one
was correct: the Python catalogue, the generated JavaScript, the built
`docs/`, the shipped zip, and the zip extracted and *run as a browser
would*. Each confirmed the last, because all of them were downstream of
Python and none was downstream of the **generator**. The one time it
appeared to work, the generator had been run by hand for another reason.

The build runs it now, and before the copy rather than after — the first
attempt regenerated into a folder already written.

The entry point is stamped too: `./api.mjs?v=<fingerprint>`, sharing the
service worker's hash, because a browser caches an ES module hard enough
that a stale copy can be served under a fresh worker.

**What would have caught it**: does building actually rebuild? Nothing
asked that. Everything asked whether the layers agreed, and they did —
about a stale answer.

### The walk visits slots, not seats

A Snake Charmer at slot 11 takes the Demon's character. The Demon acts at
32. But the walk iterated **seats**, in an order fixed by who held what
when the night began — so the seat now holding the Demon had already been
visited at 11 and never came round again. Nobody killed, on a night the
record said somebody died.

It iterates the slot numbers now and asks, at each one, *which seat holds
a character with this slot right now*. The question is asked after every
change rather than once at the start, and a seat may act twice if two
characters pass through it, which is correct: the Storyteller wakes
whoever holds the token when that token's turn comes.

The simulator always worked this way, which is exactly why the two
disagreed.

**It had been wrong since the Snake Charmer went in**, and was hidden
because the simulator was swapping twice a night — every early chooser
acted once in the early pass and again in the readings pass, and two
swaps of the same pair cancel. Fixing the double pass exposed a fault the
walk had carried all along.

### The rules run in the order the night ran

Each transition rule sees the previous ones' work through a `Timeline`
and appends its own changes, and `role_at` takes the last change at a
phase — so **the sequence the rules run in is the sequence of the
night**. The registry's comment said "order does not matter; they
compose". It did matter.

They ran Barber, Pit-Hag, Farmer, Snake Charmer: slots 40, 16, 48 and 11,
almost exactly backwards. On a night with a charmer swap at 11 and a
Pit-Hag at 16 the Pit-Hag's change landed first and the swap overwrote
it, so the Pit-Hag's own row read as false and explaining it needed a
Pit-Hag nothing could droison.

The other way to fix this was to sort the chain afterwards, which needs a
field `Change` does not have — the *actor's* slot, not the granted
character's. Ordering the rules needs nothing new at all. Raised at the
table, and much the cheaper of the two.

### A Demon that stops being one

**One bug, not two.** The swap rule copied the wrong character. It read the Demon's role
from the *view it was handed*, which the Pit-Hag rule had already
modified — so on a night with both, the charmer received the Pit-Hag's
gift instead of the Demon's character and **the Demon vanished from the
board entirely**. No cause for any night kill, and every world refused.

Found by the table, from a single observation: if the Pit-Hag died on
night four it was the Vigormortis that killed it, so there had to be a
Vigormortis. There was not.

`demon_at` looked broken too and was not. It tracks changes that grant a
demon role, and a swap *is* such a change — it only failed while the swap
was putting the wrong character in it. Rewriting it to read the board
then threw away eight legal worlds on Trouble Brewing, because **holding
a demon character is not the same as being the Demon**: after a Scarlet
Woman takeover the executed Imp still holds the Imp, and the board cannot
say which of the two is the acting Demon.

### A ceiling that was ignored

`solveBoard` takes a `maxWorlds` and passed `EXACT_LIMIT` to `analyze`
regardless, so the hosted page's real ceiling was 40,000 whatever it
asked for. Python's is 600,000, so one corpus board with 51,516 worlds
was enumerated exactly on one side and sampled on the other — three
points of difference on a board where no rule differs at all.

Worth knowing for what it says about comparing the two languages: the
answers can diverge because one of them *gave up*, and that reads exactly
like a rules disagreement.

### Both sides must know the same rules

Three readings — Acrobat, Balloonist and Alsaahir — shipped with **no
JavaScript implementation at all**. The hosted page runs the JavaScript,
so entering one and pressing Solve died with "Unknown kind of reading".
Nothing caught it, because every check compared Python against Python.

Six registries are now compared by name across the two languages:
readings, transitions, causes, impairment sources, waking conditions and
death immunities. All six agreed when the tests went in — the gap was
only ever in the readings — and both kinds of failure were verified by
breaking them deliberately.

That is the only thing that catches a rule written on one side and
forgotten on the other, and it is worth more than any amount of testing
one side thoroughly.

### The built site is a layer too

Python is checked against JavaScript, the solver against the walk, the
page's fields against the app's readings — and nothing checked the
**built site** against the source it was built from.

Two characters added in one session were reported missing from the hosted
page. Every check available said they were present, because every check
was reading a layer the hosted page does not use: the site computes its
own catalogue from bundled data at load time, and that bundle was old.

**A stale build looks exactly like a missing character.** Three
assertions now run `solver.meta()` out of `docs/` and compare it against
the Python catalogue — every character reaches the page, the page invents
nobody, and the teams agree, since a character under the wrong heading is
how somebody fails to find it.

Worth noting how it was found: not by a test, but by somebody saying "the
Balloonist is not on there — am I wrong or you?" The answer was me, three
times over, because I kept checking the layer that was easiest to reach
rather than the one being looked at.

### An honest heir was priced below the lie

A Farmer that dies at night hands the character to a living good player,
who then says "I am the Farmer" — truthfully. `is_lying` compares against
the character the seat was **dealt**, so it says yes, and a good seat
that lies pays `TOWNSFOLK_LIE_PENALTY` at 0.02. A Demon bluffing the same
character pays `BLUFF_COLLISION_PENALTY` at 0.3.

**The honest explanation was fifteen times less likely than the lie.**

It is *weighting*, not legality, and that is the whole reason three
earlier attempts moved nothing: each widened the world enumeration, and
nothing needed widening. Both worlds were always legal and always
generated; one was simply priced absurdly.

Two things the fix had to get right. The exemption depends on the
**world**, not the seat: exempting the seat outright made the demon's
bluff cheaper too and the answer got worse, 95.5 per cent to 98.6. And
the seat that died is not its own heir.

It does not overturn the board it was found on — seat three is the Imp in
153,000 surviving worlds and the Farmer in 62,000, and a fifteen-fold
correction on a subset does not beat that. With that little information a
specific inheritable claim really is more often a bluff. The fix stands
on its own merits: an honest player should not be charged as a liar.

### Measure the bug, do not guess it

Standing instruction from the table, and it was earned.

A test asserting "all three readings appear" started failing after the
Pit-Hag was corrected to act from the second night. The first fix was to
widen the sample from 40 games to 90 — a guess, on the reasoning that a
rarer event needs more trials. It fixed nothing and cost four hundred
seconds of test time.

Measured instead: **none at all in 90 three-night games, none in the
first 40 four-night ones, first hit at seed 96, 19 games in 300 producing
a row.** A Pit-Hag has to be dealt, survive, stay sober, and then win a
one-in-four draw on one of only two eligible nights. The fix was a fourth
night *and* 120 games — neither of which the guess would have reached.

The same session produced three other wrong diagnoses asserted without
reading the code that would have settled them: that the transition rules
cannot see each other (they are sequenced, each seeing the last through a
`Timeline`), that a Po had killed itself (a swap had moved the Po
elsewhere), and that a chain check needed the impairment plan when the
check simply had a duplicate definition shadowing it.

Every one would have been a single command to check.

### The vendored data is not a source for what characters do

`data/roles.json` gives the **old** Balloonist — "learn 1 player of each
character type, until there are no more types to learn". The current card
is "each night, you learn a player of a different character type than
last night", which is a different mechanic. Building from the file would
have produced the wrong character.

It is authoritative for the **night order** and nothing else. The wiki is
the source for abilities.

### The Balloonist, and a reading that only means something in sequence

Every other row here can be judged against a world on its own. A
Balloonist's night means nothing without the night before it, so the
chain is checked once per world rather than row by row.

Registration is what makes it a search instead of a comparison: a Recluse
counts as Outsider, Minion *or* Demon, so one seat can satisfy several
links — the wiki notes a devious Storyteller could show the Recluse every
single night. Under a Vortox the reading must be false, and false here
means consecutive types were the **same**.

Two things it taught:

  * **The type is the one shown *then*.** A seat shown on night one can
    swap into a Demon by night two, and what the Balloonist saw was the
    character it held when the token was pointed at.
  * **A chain is only judged where the claim is true.** These rows are
    what somebody *said*; in a world where that seat is not the
    Balloonist they are a lie, and the chain has no business fitting.

### A character is not done until it reaches the ledger

The Farmer and the Acrobat both passed their forty-game gates while being
impossible to *enter* — built in the solver, the walk and the simulator,
and never wired into the page. "Done" had meant done in the model.

An audit test compares the fields the page offers against the readings
the app lists, and caught both. The gate is now: solver, walk, simulator,
forty mixed games, **and the ledger**.

### A rule asked in six places belongs at the choke point

A **Tea Lady** keeps both her living neighbours alive when both are good.
Full stop, whatever the death comes from — a Demon, a Gambler's wrong
guess, an Acrobat's droisoned pick, a Tinker simply going.

The simulator had her, and reached her from **one** of the six ways to
die. So a Tinker died beside a working Tea Lady and the solver — which
applies her shield to every cause — had to demand she was impaired, with
nothing on the board able to impair her. That board had no legal world.

The night-walk did not have her at all, and agreed anyway, by luck.

She lives in `kill()` now rather than at each cause, which is the same
shape as `droisoned_at` (five sources had been missing from it) and
`hidden_from` (four inputs). **When a rule has to be asked in several
places, the fix is to put it where they all pass through**, not to
remember it at each.

### The Acrobat, which needed all of this

**Each night, choose a player: if they are or become drunk or poisoned
tonight, you die.**

It could not be modelled in the three-pass design at all. The inference
needs the impairment plan and the death causes settled together, and both
directions were tried and withdrawn — a surviving Acrobat means the pick
was clean *or* the Acrobat was itself droisoned, and a dead one is only
informative if its own ability killed it.

In the walk it is four lines, because the night has already happened by
the time it is asked. Verified exact on thirty-five nights.

### The switch stays off, and that is the finding

`WALK_CHECKS_STORIES` works. Across 45 published boards it checked 259
candidate stories, refused 9, and lost **no true world** — every board
still solved. It correctly identifies timelines that could not have
produced the record.

And it is worthless, measured on the board where it refuses most:

    switch off   672 worlds,  5.7 seconds
    switch on    672 worlds, 60.9 seconds
    every seat's evil percentage identical to two places

Three and a half thousand stories refused on that board, and not one
number moved. **Every story the walk rejects would have scored zero
anyway** — the plain path already refuses them, more cheaply, by other
means. The walk is a second opinion that never disagrees with the
verdict, only with the reasoning, at eleven times the cost.

So it stays off. Not because it is wrong or unfinished: because the
question it answers was already answered.

What the walk is still for is what it has always been good at: **an
independent second implementation of the night**. It replays 180 of 180
nights and has found bugs by disagreeing with the simulator — a Drunk
performing real Snake Charmer swaps, early choosers acting twice a night,
a Demon that stopped being one. Two implementations that disagree are
worth more than one that is trusted.

Getting here took three sessions and several wrong turns, including two
attempts to fix an ordering fault that was real and not the cause. The
measurement that settled it was one board compared twice — which was
available from the start.

### The walk searches a night, it does not check one

`WALK_CHECKS_STORIES` is in `best_story`, off by default, and it works.

The first design said "propose then walk": the impairment plan proposes
where each source went, the walk replays it. **The proposing half did not
exist** — `plan_night` answers "can these sources impair exactly who is
*required*", so with nothing required it places nobody.

Worse, the Demon's aim could not simply be handed over either: the aim is
what the deaths are *evidence for*, so feeding them back would make the
check confirm whatever it was told.

Both problems dissolve if the walk **searches** instead. Enumerate every
arrangement of the droison sources, crossed with everything the Demon
could have aimed at — nobody, any seat, any pair for a Shabaloth, any
three for a Po — and keep what reproduces the record.

    nights 120, explained 120
    walks per night: median 5, mean 10.3
    whole corpus: off 46.1s, on 48.8s, 0 of 138 answers differ

It agrees everywhere and costs six per cent. That is enough to land it
and not enough to make it authoritative: those 138 boards were all built
by the old path, so they can confirm agreement and never disagreement.
What would earn switching it on is a board where the two differ and the
walk is right.

### The walk meets the solver

`WALK_CHECKS_STORIES` sits in `best_story`, off by default: each
candidate story would be *replayed* before being scored. Three things
came out of building it.

**The seam is small.** The walk asks a board four things — `n`,
`role_at`, `side_at`, `alive_at` — and a solver world answers two
already, so the adapter is a dozen lines. It replays **180 of 180**
nights over the views the solver actually scores. Hand it the bare
`World` rather than the `Timeline` wrapped around it and that falls to
174: a world says who was *dealt* what, and a swap lives in the view.

**Cost is not the obstacle.** A walk is 15 microseconds against
`_explain`'s 156. A check that discards a story early *saves* time, which
is the opposite of the worry that prompted measuring it.

**But the plan is a cost model, not a generator.** `plan_night` answers
"can these sources impair exactly who is **required**" — so with nothing
required it places nobody, and the walk has nothing to replay. The design
said "propose then walk" and the proposing half does not exist. Turning
the switch on needs a way to *enumerate* where each source could have
gone, which is a new search; the measurement above says checking each
candidate would be affordable once it does.

### A Snake Charmer swaps immediately

Settled at the table, and it took four fixes of the same shape.

A charmer acts at slot 11 and every Demon at 24 or later, so by the time
the night's kill is made the charmer holds the Demon — and it is the
charmer's seat that kills. The old Demon is a poisoned good Snake
Charmer and kills nobody. It also **cannot swap again**: the poisoning is
permanent, so pointing at the Demon a second time does nothing.

Both sides had recorded the swap at the day *after*. The solver's comment
explained why: writing it at the night made the charmer's own row read as
invented, and a world where the swap really happened scored 0.4 against
1.0 for one where it could not. Exactly backwards.

That symptom was real and the cause was elsewhere. **A row belongs to
whoever acted**, which is the board as it stood when the night began; the
board afterwards is a different question, and the phase cannot tell them
apart. Four places were asking the second question and needing the first:
the transition rule, the row-to-speaker attribution, the ability check
that charged the penalty, and the simulator's own early-choice pass.

### The walk starts before the night, not after it

`role_at(seat, "N2")` already contains every change stamped at N2, so
the walk was starting from the board *after* tonight and then walking the
night — applying tonight's changes a second time. For a Pit-Hag creation
that is invisible, because setting a seat to a character it already holds
does nothing. For a swap it is a bug: doing it twice swaps the pair back.

It starts at the end of the previous day now and *becomes* the board by
walking. Anything else is applying history twice and hoping it is
idempotent.

### The walk says when it has not been told

Three comparisons in a row failed because a probe forgot a hidden input,
and each time the failure pointed at the walk. Being under-informed
looked exactly like being wrong.

`hidden_from` now builds every hidden input in one place — making the
correct path cheaper than the mistake, which works better than resolving
to remember — and the walk records `untold`: characters that always act,
are alive and working, and that it was told nothing about.

Turned on, it flagged 41 of 180 fully-informed nights. Every one was
real: three characters whose announced rows nothing was reading, an
Exorcist that never acted at all, and a check that ran before the night
when it had to run after. It reads zero now.

### One function, two questions

Three times now a single function has been answering two questions that
agree for almost every character — which is exactly why each went
unnoticed for so long.

  * `registers_as_role` answers *could this have been said*. A Vortox
    needs *is it true*, because misregistration makes information legal
    and not true. Split into `is_really_role`.
  * `holds` answers whether a reading is consistent with a world. The
    Vortox inversion needs whether it was **so**. Split into `is_true`.
  * `woke` answers *did this seat wake*, which decides what a player
    could honestly claim about their nights. A Chambermaid asks *did its
    own ability fire*. A Lunatic is shown a Demon's night and made to
    choose victims who never die: it wakes, and none of it is its own
    ability working. Split into `woke_for_own_ability`.

### Anything that droisons belongs in one place

`droisoned_at` answers "is this seat drunk or poisoned tonight", and four
separate sources were found missing from it: a **Minstrel** silencing the
table after a Minion is executed, a **Philosopher** drunking whoever
really holds the character it took, and an **Innkeeper** and a **Sailor**
each drunking one of the players they touched.

Every one was recorded where it happened and absent from the one place
that answers the question. Four is a category rather than a coincidence,
so the rule is written at the site: anything that droisons must be
*there*, not merely recorded elsewhere.

### Characters that were dealt and never acted

Counting what the simulator *records* against what it *deals*, twelve
characters produced nothing at all — among them a Monk that never
guarded, a Sailor that never drunked, a Witch that never cursed.

That matters more than it looks. The walk is verified against nights the
simulator plays, so **a character the simulator never fires is one whose
rule has never been checked**. Making the Sailor and the Innkeeper act
immediately found three bugs, and the Professor was withdrawn from the
walk entirely for want of anything to check it against.

### A phase is not an instant

`N2` covers seventy-odd slots, so two things happening on the same night
are indistinguishable to `phase_index`. That cost a real bug and it took
a while to catch, because every guess along the way was wrong.

A **Barber swap** made a seat a Pit-Hag *after* a Mathematician had
counted — and since a change is stamped with a phase rather than a slot,
it back-dated to the start of the night. The Mathematician's row was then
computed against a board that no longer existed.

Three board-changing steps were running after the readings when, by slot,
they come before every character that reads:

    Acrobat 39   Barber 40   Farmer 48
    Empath 53   Oracle 59   Mathematician 71

Ordering the code is the cheap fix and it is what was done. The real fix
is the night-walk, which cannot have this bug at all: it holds one state
and moves forward through it, so "before" and "after" within a night are
structural rather than encoded in a comparison.

Two larger changes were considered and rejected — putting slots on every
change, which is a coordinate-system change across fifty-six call sites
to fix what three misplaced lines caused; and letting the walk take over
the simulator's night, which would destroy the thing that found the bug
in the first place. **Two independent derivations disagreeing** is where
nearly every bug here has come from.

### Absent is harder to notice than wrong

Twice now the bug in a reading has been that **no answer was produced at
all**, and neither time did anything look broken.

A **Ravenkeeper** reads *because* it died, and the guard asked whether it
was working before the exemption that lets the dead read — and `working`
requires being alive. So the one character that has to be dead to read
was rejected, and no Ravenkeeper reading was ever taken. The comparison
had nothing to compare and passed.

A **Philosopher** that takes the Flowergirl reads at the Flowergirl's
slot, not its own. The walk looked up "Philosopher" in its table of
readings, found nothing, and skipped it.

Every comparison here now asserts a minimum count — `assertGreater(found,
0, "no Ravenkeeper read at all")`. A test that can pass on an empty
comparison is not a test.

The same instinct made the **Professor** come out again: it was written,
and then removed, because the simulator never fires one. There was
nothing to check it against, and an honest gap is worth more than an
unverified derivation.

### The Oracle was counting the wrong moment

An Oracle reads at slot 59 and a Demon kills at 24, so by the time it
counts the dead, tonight's victim is among them. Both the simulator and
the solver used the set of players alive at the *start* of the night,
which is a different question.

Found by the night-walk deriving the count independently and
disagreeing — and then by the test suite showing the shipped solver had
the same mistake. It is the kind of error that can only surface once
something knows what order things happen in.

Getting to a clean comparison needed three filters, and they are worth
naming because they apply to every reading: a **Vortox** falsifies the
answer, so the simulator records a lie; a **droisoned** seat is told
whatever the Storyteller likes; and only with both excluded does a real
disagreement show. The Oracle looked like 13 of 25 until then, and is 23
of 23 now.

### An ability is judged when it acts

Found by the walk's own log, and it is the sharpest illustration of why
the night needs an order.

A Demon that chooses the **Goon** is made drunk by it — the Goon's card
says the first player to choose it is drunk. But the choice is already
made, so the kill still lands. Testing whether the Demon was working
*after* the Goon had turned had a Goon protecting itself from every Demon
that picked it, which is not what the card says. Twelve nights in eighty.

Whether an ability functions is decided **when the character acts**, not
after its own target has answered back. No arrangement of three separate
passes can express that; walking the night in order gets it for nothing.

### A night can be replayed

The solver settles a night in three passes — transitions, death causes,
impairment plan — and none can see the others. Almost every character
depends on the order, so that has to change.

The **Goon** is the argument. *The first player to choose you tonight is
drunk, and you become their alignment.* A Sailor acts at slot 4 and a
Poisoner at 7, so if both choose the Goon it ends the night **good**; if
only the Poisoner does, **evil**. Order decides an alignment there, not
merely whether an ability worked, and no arrangement of "who was
droisoned" can express it.

Before rewriting anything, one question: **can a night be replayed at
all?** `tests/nightwalk.py` walks a night slot by slot, and it reproduced
**120 of 120** nights the simulator had already played — including the
Goon, both ways round.

The walk is handed the hidden choices rather than guessing them. That is
the shape the design settles on: eleven choices are already recorded,
because good players announce what they did, and the hidden ones are the
evil choices, which the impairment plan already searches over. So the
plan proposes and the walk checks.

Which means the largest change in this project is a change to how a
candidate is *checked*, not an explosion in how many candidates there
are. The design is written up in `docs-design/night-order.md`.

### The night has an order now

`data/roles.json` is vendored from the townsquare repository that backs
botc.app, and the catalogue reads two numbers per character from it —
`firstNight` and `otherNight`. Kept **un-renumbered**, because the gaps
are what let a character added later drop into its true position without
disturbing anything around it.

    Poisoner  7  →  Imp 24  →  Assassin 36  →  Acrobat 39  →  Farmer 48

Two consequences fall straight out. An Imp that starpasses to an Assassin
costs it the night: by slot 36 that seat is holding the Imp, and the
ability is not there to use. And an Acrobat sits between the Poisoner and
the Farmer, which is what makes "are *or become* droisoned tonight" more
than a turn of phrase — it can be poisoned before it acts and its pick
poisoned after.

The simulator walks seats in night order rather than seat order, read off
what each seat *believes* it is: a Drunk holding a Fortune Teller token
acts in the Fortune Teller's slot.

**The solver still knows none of this**, and that is the next large
piece. A night there is settled in three passes — transitions, death
causes, impairment plan — none of which can see the others.

### The Farmer, and the first experimental character

**If you die at night, an alive good player becomes the Farmer.**

The rules, settled at the table rather than guessed at: it fires on *any*
night death, not only the Demon's; nothing on an execution; nothing while
droisoned, because a droisoned **information** role yields whatever the
Storyteller likes while a plain ability simply does not function; it
chains, since the new Farmer is a new instance; and it never wakes,
because being told your new character is a **game rule** rather than any
ability — so a Chambermaid does not count it.

Heirs are chosen by **registration**, which is the interesting part: a
Spy registers as good, so a Spy may be made the Farmer, and it stays
evil. An evil Farmer is a real thing the model has to hold.

Two things came out of building it. `find_at` returns the *first* seat
holding a character, and the Farmer is the first one where several seats
genuinely hold it across a game — so chaining looked past nothing until
it collected every holder. And "nothing happened" has to stay among the
answers: whether a seat was droisoned is *chosen* by the impairment plan,
which runs after transitions are settled, so both stories are offered and
the plan pays for whichever it needs.

### The deal is not the timeline

The same mistake, four times, each found by a played game: `demon_at`
twice, the kind of kill a Demon makes, and an Evil Twin that named itself
as its own twin. Every one asked *what was this seat dealt* when the
question is *what does it hold now*.

Two were reachable only through mixed scripts — a Snake Charmer swap
creating a Zombuul mid-game, which then killed on a night a Zombuul may
not, and a Pit-Hag making a good seat the Evil Twin.

After the fourth, the rest were swept for rather than waited for: six
more sites moved to the timeline, including the Grandmother's grief, the
Barber's swap, the Soldier's protection, the Vortox's inversion, and the
No Dashii's and Vigormortis's neighbours.

### Characters that have never met

The published three are three selections out of an enormous number, and
each exercises its own characters against its own neighbours. A homebrew
script can mix them freely, so the machinery has to hold up on scripts
nobody has played.

Forty games on deliberately awkward mixes — nine droison sources at once,
four characters that move roles around, demons from three different
scripts — found **eight bugs**, none of which can arise on a published
script:

  * A **Baron** counted as waking on the first night. Being shown the
    other evil players is not waking for your own ability, so a
    Chambermaid beside one reads none, not one. It lived in two places.
  * A **Gambler** that guessed wrong did not die. The comment had said it
    did since the character went in.
  * Whether a **conditional** character woke was a thirty per cent coin.
    Whether an Undertaker wakes is whether somebody was executed
    yesterday. Found through a Philosopher holding a Chambermaid counting
    an Undertaker — three characters from two scripts.
  * A **dead Grandmother** grieved for a grandchild lost after her own
    execution.
  * A **Grandmother under a Vortox** was shown a true character. She is
    shown a false one, and still a good one: seeing only good characters
    is what her ability does, and a Vortox changes what an ability yields
    rather than what kind of thing it yields.
  * A **Pit-Hag** could turn the Demon into a Clockmaker, leaving the
    game with no Demon at all — good had won and the record ran on for
    two more nights.
  * A **Librarian** told *nobody* passed through the falsifier unchanged,
    leaving a true reading on a Vortox board.
  * A **Town Crier** said no Minion nominated on a day a Spy had — legal,
    because a Spy may be shown as a Townsfolk, and not true. The same
    conflation as below, in a second character.
  * And the legal-versus-true conflation itself.

Two characters have now been found with that conflation, and there are
likely more: anything that counts or names by registration. They surface
the same way, when a misregistering character meets a Vortox — which is
a pairing no published script can produce.

### A Vortox falsifies information, not choices

Several rows are not information at all — they are a choice the seat made
and announced. Nobody told a Philosopher what it took, a Courtier which
character to name, a Klutz where to point or a Gambler what to guess.

Treating those as readings made every board with a Philosopher on it
impossible, whatever the Philosopher chose. Ten row types are marked as
choices now and pass through untouched. The default is *information*,
which is the safe direction: a reading wrongly inverted shows up as an
impossible board, and a choice wrongly inverted shows up as nothing at
all.

**And a second bug sat underneath the first.** The rule is that the
choice survives but what it *gained* does not — a Philosopher that took
the Town Crier gets that ability, and its answer is inverted like anybody
else's. Writing the test for that found the overlay returning GENUINE
without ever checking for a Vortox, so a Philosopher holding the
Clockmaker gave the true answer on a board where the real Clockmaker
could not. The gained ability was quietly immune.

Worth noting how it was found: the ruling came in two halves, and the
second half — *the info this ability generates will be inverted* — is the
one that exposed it. A shorter answer would have left the bug in place.

### A free source that still has to choose

A ruling settled a disagreement — a poisoning from a Vigormortis kill
registers on the night it killed — and following it through found a real
bug in the weighing.

`_possible_impairment_counts` treated any **free** source as impairing
everybody it reached. But free is not the same as certain: a Vigormortis
reaches the two Townsfolk beside a dead Minion and poisons *one*, and the
Storyteller chooses which. So the possible range came out (0, 0) where
the truth was (0, 1), and a Mathematician correctly saying 1 made the
whole board impossible.

The distinction the code was missing: a Drunk holding somebody else's
token impairs its whole reach, because there is nothing to choose. A
Vigormortis is free *and* has to pick. Only the first belongs in "always
impaired".

### A seed is a bad name for a property

`CONFIDENTLY_WRONG` — the seed of a game where the solver is sure and
wrong — has now moved twice: once when `deal` learned to take a script,
again when days gained nominations and votes. Both times the randomness
was consumed differently and the old seed produced an ordinary game.

The tests that use it now measure the *property* — an innocent seat far
ahead of the real Demon — rather than a hand-picked percentage that
drifts for reasons unrelated to what is being demonstrated. The same
applies to a 40% threshold replaced in the same pass.

### A row shape Python had never been handed

The page sends a Juggler's guesses as `{player, role}` and the tests hand
over `[seat, role]`. The JavaScript learned to read both months ago;
Python never did, because nothing had ever fed it the page's shape — the
conformance corpus is built from tuples, and so is every test.

A simulator producing the page's shape found it in one game. Worth
noting what the corpus cannot do: it compares the two implementations
against each other, so a gap only shows when something arrives in a shape
neither was tested with.

### Reading the wrong field, three times

A seat softclaimed "conditional" and the search produced no world with
that seat as itself, so the true world was never enumerated at all.

"Conditional" is not something a player can say. The patterns anybody can
claim are `every`, `first`, `never`, `other` and `sometimes` — and a
character's `nights` is not one of them: it describes the *shape* of an
ability, "conditional" for a Sage, "other" for a Demon.

That is the third time this exact confusion has cost something. A
Chambermaid read `nights` and concluded Demons sleep through the first
night. The solver's own waking check did the same. Now the simulator's
softclaims. Three separate places, one misreading, and the `wake` set had
the honest answer in all three.

Fixing it made repair-on-demand **usable**, too. Opening one seat while
allowing hidden Outsiders on the other eight hit the 300,000-world cap at
208 seconds a seat — half an hour to repair a single board. On a tenth of
the budget, with the result weighed on a sample, it is a couple of
minutes. And boards needing repair at all went from roughly one in six to
one in forty: most of what used to need it was the simulator producing a
claim nobody could have made.

### A green light for a typo

`run_tests.py waking` reported "Ran 0 tests — all good". The file is
`test_wakes`. For a session that hid the very tests being looked for, and
every run in between looked like a pass.

It exits 2 now, lists the files, and suggests the one that was meant —
compared by spelling rather than by prefix, which is the difference
between catching this and not: "waki" is not a substring of "wakes". A
keyword that filters everything away fails the same way, as does any run
that ends with no tests.

A silent zero is the worst answer a test runner can give. It is the only
kind of failure that looks exactly like success.

### The suite runs in parts now

It had grown past what fits in one sitting, and a run that is killed
halfway prints no summary at all: the failure is somewhere in a wall of
dots and nothing says which. `run_tests.py 2/4` runs the second quarter,
split alphabetically so the same quarter is the same files every time and
a failure can be chased.

That mattered immediately. A single `F` sat unidentified across two whole
sessions, and hunting it by elimination is what finally found it.

**And a near miss worth recording.** I ran `run_tests.py waking`, which
matches no file, and it reported "Ran 0 tests — all good". The file is
`test_wakes`. A pattern matching nothing should be an error rather than a
pass, and for one session it hid the very tests I was looking for.

### Bad Moon Rising, and two bugs in the solver

Teaching the simulator to play a script properly is worth it for what it
finds in the thing being tested. Of twenty-five games, the number the
solver called **impossible** went nine, three, two, then none — and the
last two were not the simulator.

**A Pukka's kill demanded a poison nothing provided.** It kills whoever
it poisoned the night before, and the kill rule said so
(`victim_impaired_at=night - 1`) while no impairment source ever poisoned
anybody. Every Pukka board was impossible. It went unnoticed because a
board only breaks once a death is recorded on the right night, and no
test or corpus board ever had one.

**And every Demon wakes on the first night**, to learn its Minions and
its bluffs. The waking check read the single `nights` word, which says
"other" for a Demon — but that describes when it *kills*. A Chambermaid
sitting beside a Demon and correctly counting two produced a board with
no legal world at all.

The `wake` set had the honest answer all along. Reading it alone was the
wrong fix, though: "every" does not bother to list "first", so every
Empath and Poisoner slept through night one instead — a worse bug than
the one being repaired. Both are checked now, and the Zombuul needed its
own line, since it is conditional and its condition described the killing
schedule rather than the waking one.

Eleven corpus boards moved, in both directions, which is what a waking
correction should look like.

**And the fix for the first had a bug of its own.** The new Pukka source
reached the whole table at no cost — and a free source reaching everybody
excuses *any* reading for nothing, which duly made a false Chambermaid
reading costless. It is priced like the Poisoner now: 0.35 to land, 0.7
to land twice, because *which* seat it chose is a coincidence the story
has to pay for.

Caught by an audit test written weeks earlier for an entirely different
reason — it asserts that explaining away something false costs something.
The sources that are genuinely free, a Sweetheart or a No Dashii, are
free because they reach one seat or two that nobody chose.

### Teaching the simulator the other scripts

Started with the bag, which was the blocker: `deal` read the module-level
Trouble Brewing lists, so every game the simulator produced was Trouble
Brewing whatever anybody asked for. It takes a script now, handles the
setup changers by name — Baron, Godfather, Fang Gu — and deals legal bags
on all three.

Two bugs of the same shape fell out immediately, both from finally
dealing something that was not Trouble Brewing:

**`demon_at` was hardcoded to the Imp**, so every Bad Moon Rising and
Sects & Violets game reported no Demon at all. The same class of mistake
as the starpass being offered to every Demon, found the same way.

**And the chaos claim drew from the global character list**, producing a
Fortune Teller on Bad Moon Rising — where the solver correctly refuses a
board with a claim that is not in the bag.

Four Bad Moon Rising readings are in: Grandmother, Chambermaid, Gambler's
guess, Courtier's choice. Along with them, a rule the simulator had never
needed: **a Grandmother whose grandchild the Demon takes dies with it**.
Without that it produced boards the solver called impossible, and the
solver was right.

**Bad Moon Rising games are not trustworthy yet**, and the reason is
written at the top of `_demon_kill`. Every Demon on that script kills in
its own way — the Pukka poisons a night before it kills, the Zombuul
skips a night, the Shabaloth kills twice, the Po may kill nobody and then
three — and the simulator kills like an Imp regardless. Of twenty-five
games, nine still produce a board the solver calls impossible, and it is
the simulator breaking the rules in every one.

### The Storyteller learns to mislead

The simulator had never produced a **misregistration**. Every game it
dealt was one where the Storyteller told the plain truth — the easy half
of the problem, and the only half the solver had ever been tested
against, despite misregistration being handled carefully everywhere in
the solver itself.

It now shows a Spy as a Townsfolk or an Outsider, and a Recluse as a
Minion or the Demon, about a third of the time it has the option. A
Fortune Teller can ping on a Recluse too. Each lie is legal twice over:
the seat can register that way, and the character named is one nobody
else holds — a Storyteller pointing at a character somebody really has is
asking to be caught.

The solver takes it well. Across games containing one, the Demon was the
top suspect every time, at between 25% and 77%: being misled costs
something and does not break anything.

### A board the solver gets confidently wrong

The same exercise found something it does not take well, and it is worth
recording plainly.

Two good players lied in one game. The search can represent an Outsider
hiding and cannot represent a Townsfolk claiming a *different* Townsfolk,
so the true world was never enumerated at all. Ninety-six worlds
survived, the solver named an innocent seat at **58%**, and the real
Demon sat at zero.

Repair on demand did not fire, because the board was not cornered — it
had an answer and a confident one. A guard on "does anybody look like the
Demon" was written and then removed: that board looked *more* certain
than a correct one, so confidence is not the signal, and a check that
fires on the wrong signal is worse than no check.

Nothing inside the solver distinguishes a board it has solved from one it
has been lied to about. Fixing it needs the search to afford a Townsfolk
lying, which today it cannot — so it is a documented limit with a test
that pins the behaviour, rather than a bug quietly left open.

### A save that could not be opened

The played games wrote a save file the app refused. A save has to *be*
the document the page reads, and this one was nested inside a larger
report with no `script` block — so the page saw a file it did not
recognise and said so. Neither the harness nor any test noticed, because
nothing had ever tried to open one.

Each game is now its own file, and a test asks the two questions the page
asks on load. There is a prose transcript beside it, which is the format
worth reading: the question being asked of these games is about the
*simulator* — did the right people wake, is what each was told true, did
the Poisoner land where it says — and that is far easier to see in
sentences than in nested objects.

Writing the transcripts caught something immediately, though it was the
report rather than the simulator. Executions are recorded as `E1`, not
`D1`, so matching the phase exactly dropped every one of them: the
transcript showed an Undertaker reading a seat that had apparently never
died. The simulator was right and the write-up was lying about it.

### Longer games, and what they showed

Three nights turned out to be too early to judge anything. Five nights,
nine players:

    seed 201:  15% -> 16% -> 19% -> 22% -> 24% -> 28% -> 41% -> 76% -> 92%
    seed 203:  10% -> 11% -> 12% -> 13% -> 21% -> 23% -> 24% -> 48% -> 50%

The Demon's share rises in every game played so far, and in the
five-night games it ends as the top suspect in two of three. A low
reading early is not a failure — the evidence genuinely does not
distinguish it yet — but a reading that *fell* as information arrived
would be, and none did.

That also found a crash. The search for the best repair started from
`None` and the comparison indexed it, so every board that fitted
*something* worked and the first that fitted nothing fell over. Three
nights never produced one; five did.

### What the simulator can and cannot do

Worth stating plainly, because everything above is measured against it:
**the simulator only knows Trouble Brewing.** It deals from that script
with no way to ask for another, and resolves eight characters —
Washerwoman, Librarian, Investigator, Chef, Empath, Fortune Teller,
Undertaker, Ravenkeeper. For Bad Moon Rising and Sects & Violets it can
resolve none of the seventeen good characters on either.

So calibration, when it comes, will calibrate the solver against
Trouble Brewing and say nothing about the other two. Teaching it the
rest is real work: every character needs its information derived
independently of the solver, which is the only thing that makes the
check worth anything.

### Measuring the right thing

The first version asked whether the exact world survived, which is a
stricter question than anybody needs answered. A good player lying
scrambles who holds what without changing who the Demon is — and catching
the Demon is the whole job. A solver that names it while getting three
Townsfolk wrong has done what it is for.

So the protocol reports where the true Demon ranked, what percentage it
was given, and whether it was ever **ruled out entirely**. That last one
is the only hard bug: a low reading is often correct, since the evidence
may genuinely not distinguish it yet, but zero is never a reading — it is
a world thrown away that happened.

Twelve nine-player games, three nights each: the Demon ranked fourth of
nine on average and was never ruled out. Fourth of nine after three
nights, with two evil bluffing and a good player lying, is a solver
working rather than a solver failing.

### A lie the search cannot represent

The first six games found something in the solver that had been there
from the beginning: **a Townsfolk claiming to be a different Townsfolk is
a world the search never generates**, in any mode. `allow_good_lies`
opens exactly one more door — an Outsider hiding — and nothing else.

Which means `TOWNSFOLK_LIE_PENALTY`, at 0.02, has never been reachable.
It has sat in the weighting since the first version, been carried through
the JavaScript port, and been swept by the sensitivity check, and no
board has ever been scored with it.

The obvious fix is wrong. Letting every Townsfolk claim be any Townsfolk
takes a nine-player board from a hundred worlds to a quarter of a million
and hits the cap — so the truth goes missing anyway, now through
truncation. Games containing that lie are set aside and counted, and the
constant is left where it is until there is a way to reach it that does
not cost the search.

### Naming the madness

The seat status read "executed for breaking madness", and marking it
confirms a **Cerenovus** — that specific character, by name, in the rule.
But other characters madden people: a Mutant is mad about being an
Outsider with no Cerenovus anywhere. A status named after the *symptom*
promises a deduction the rule cannot make, and would have somebody
marking a Mutant execution and getting a Cerenovus they never had.

It says "ceremadness" now, which is the size of the promise. A test
checks the label against the rule, so a future maddening character cannot
quietly inherit it.

### What playing with it found

The audit found nothing; using it found five things, which is roughly the
expected ratio.

**The script list was alphabetical**, so Bad Moon Rising came first and
Trouble Brewing last — nobody's idea of where to start. Publication order
now, taken from the order the dictionary is written in.

**Ledger rows were named inconsistently.** Trouble Brewing's read
"Washerwoman" and Sects & Violets' read "ClockmakerInfo", because the
label table was hand-kept and every new reading arrived missing from it.
Derived from the source character now, with a short list of exceptions
for the readings named after an *act* rather than a character — a Slayer
shot, a Gambler's guess.

**Half the readings had no description at all**, so the speech bubble
showed a blank line where the sentence should be. Same cause: a switch
statement that nobody extended. All thirty now say what they mean, and a
check asserts none is missing.

**And Bad Moon Rising was offering four readings when it has eight.** The
Moonchild's pick, the Exorcist's choice, the Innkeeper's pair and the
Sailor's choice were all unrecordable — and every one of them carries a
real deduction that the solver simply could not draw.

That last one is the substantial fix. A Sailor drunks one of two and does
not say which; recorded, that narrows the drunk from nine seats to two.
An Exorcist naming the Demon explains a silent night, so a recorded
choice plus a quiet night points at that seat. A Moonchild's pick only
kills the good, so whether that seat died is evidence either way. None of
these has an answer to be wrong about — the value is entirely in what
follows, and the death and impairment rules cannot know where a choice
landed unless somebody writes it down.

### The wiring audit

Three passes over the page, looking for the kind of fault a solver test
cannot see.

**Every interactive control has a live handler.** Checked by booting the
page and reading the handlers off the elements rather than off the
source — several are bound through a local variable, and a regex reports
those as dead. Two false positives came back that way, and one of them,
a bubble's close button, only exists while a bubble is open.

**Every field the page records reaches the solver.** One looked missing
and was not: names are passed as `s.name`, and my pattern searched for
`seat.name`.

**And a saved game survives being reopened.** This is the one worth
keeping: a field that saves but does not load is invisible until somebody
returns to a game mid-session and finds half of it gone — and by then the
game is the thing they lost. `test_round_trip.py` loads a game with
something in *every* field, boots the page, and compares what comes back
against what went in. A second test insists the harness actually covers
every field, because a round trip that checked three of them would pass
for ever.

Nothing was broken. That is the outcome an audit should usually have, and
the three checks stay.

### All three scripts, done

Nothing on Trouble Brewing, Bad Moon Rising or Sects & Violets is waiting
to be built. That is not the same as everything being *solved*: five
characters across the three are finished at less than that, and each for
a reason rather than a backlog.

A **Savant** and an **Artist** say things that can be anything at all, so
the words are kept and shown and not weighed. A **Mutant** and a
**Cerenovus** work through madness, which leaves no mark on the board —
what the table *can* see, an execution for breaking it, is recorded as a
status instead. A **Mastermind** changes how the game is won rather than
what happens on it, and the part that does show, play carrying on after
the Demon is executed, is modelled.

A test asserts the "coming" pile is empty on every published script, so
nothing can sit there unnoticed again.

### The Pit-Hag, and the last of the script

Recorded rather than searched for, and that is the whole design. A
Pit-Hag acts on any night, on any seat, for no reason the table sees —
enumerating that would multiply the search by seats times characters
times nights, almost all of it stories nothing is asking for. But when it
*is* known it is known loudly: somebody says they changed, and from then
on they answer as something else.

Three things follow from the rules. The character has to have been **not
in play**, read off the true assignment rather than the tokens — a Drunk
holding the Fortune Teller token does not stop a real one being made,
because there is no Fortune Teller, only somebody who thinks so. The
**side does not move**, so a Townsfolk turned into the Poisoner is a good
Poisoner. And making a **Demon** makes that night's deaths the
Storyteller's: nought to everybody, no shield touching them, and
attributed to the Pit-Hag rather than the Demon.

**"Your first night" had to stop meaning night one.** Every first-night
reading read the board at `N1`, which is right for a character dealt at
the start and wrong for one created on night four. They read their own
night now — identical for an ordinary Washerwoman, different for a made
one. That was the machinery the Philosopher half-built and the Pit-Hag
needed properly.

### The Mathematician, finally

A mental note from several sessions back, come due. Its guard said "say
nothing while a character that can droison is unbuilt", and Sects &
Violets had four of them. The Pit-Hag was the last, so the guard let go
on its own — and a test written at the time to notice that moment failed
exactly when it should have. It now asserts the opposite: that the number
the Mathematician heard actually matters.

### The Snake Charmer

The only handover where the star moves **sideways** rather than on.
Choosing the Demon while working swaps character *and* side both ways:
the Snake Charmer becomes the Demon, and the Demon becomes a good Snake
Charmer — poisoned from that moment for the rest of the game. The new
Demon is untouched.

Recorded rather than guessed, because the outcome is visible. A choice
that did nothing is worth having too: it says that seat was not the
Demon. A recorded swap takes the charmer's seat to **78% Demon** and
clears the one they charmed to nothing.

**Two bugs on the way, and the second is the one worth keeping.**

A row saying "we swapped" constrained nothing — it answered true
unconditionally, so nothing forced the target to have *been* the Demon.

And applying the swap **at the night** was wrong. The swap happens
because the ability worked, so it was still the Snake Charmer when it
did; writing the change at the night made the speaker stop holding that
character at the very moment its row is attributed. The row read as
*invented*, and a world where the swap could really have happened scored
**0.4 against 1.0** for one where it could not. Exactly backwards. It
applies from the day after now.

A third thing, in a test rather than the code, and worth the same note as
the Outsider trap: the first draft built its world around a **Vortox**,
on a board that marks a day as ended with nobody executed — which rules a
working Vortox out on its own. Every world came back impossible for a
reason that had nothing to do with the Snake Charmer.

### The Vortox

The one that needed a fourth ability state, and the smallest change of
the three in the end — because `ability_state` is consulted in exactly
one place.

**It is not a droisoning, it is the opposite kind of claim.** A poisoned
Empath may be told anything, including the truth by accident, so a
poisoned reading constrains nothing. A Vortox'd Empath must be told
something that is *not* so, which constrains the world in the other
direction. Hence `INVERTED` — defined in `roles.py` since the beginning
and used nowhere until now.

It touches Townsfolk and nothing else, reads what a seat *is* rather than
what it thinks it is — so a Drunk holding a Townsfolk token is an
Outsider and stays arbitrary — and it neither protects nor droisons
anybody. Its text is that abilities *yield false information*, not that
they malfunction, and I had that wrong out loud once before being
corrected.

The win condition is the other half: evil wins on a day nobody is
executed, so a day that ended quietly with play carrying on says there
was no working Vortox **that day**. Per day, not per game, because a
Pit-Hag can bring one along later.

**And it broke the rows that say nothing.** A Savant, an Artist, and the
Mathematician on a script it cannot account for all answer "true" by
default — and under a Vortox "true" is a claim: it would mean the Vortox
was not working, and demand it had been droisoned. A row that says
nothing has to go on saying nothing, so rows now declare whether they are
weighed at all. The conformance corpus caught the JavaScript half of that
one board later.

One approximation, named rather than hidden: on a night mixing true and
false Townsfolk readings, the solver takes the Vortox as droisoned and
does not additionally charge the false ones for needing their own excuse.
Permissive, which is the direction to err in.

### The three Demons, and a starpass nobody had

**No Dashii** poisons its two nearest Townsfolk, all game. Nearest by
**team**, not by side — a Townsfolk can be evil, so this skips Outsiders
and Minions rather than skipping the evil, and it does not skip the dead
either. **Vigormortis** keeps the Minions it killed working and drunks a
Townsfolk beside each corpse. Both stop the moment their Demon does.

**Fang Gu** is a handover rather than a kill. The Outsider it chose
*lives*, turns evil and becomes the Fang Gu; the old one dies instead. So
the table sees exactly one body — the Demon's own seat — and the whole
thing drops into the heir machinery that already existed. Once per game,
so it is offered only while the star is still where it was dealt.

**Which is how a real bug surfaced.** Building it meant asking why the
Fang Gu was being offered a *starpass*, and the answer was that
everything was. The rule said "the Imp kills itself and a Minion takes
over" in its own docstring and then checked nothing — so a Zombuul or a
Pukka that fell to a Slayer or an Assassin could quietly pass to a Minion
and the game carried on, when good had actually won.

Only the Imp has it, and the list now says so. Three Bad Moon Rising
boards in the corpus moved, every one of them downward: 10,660 to 8,796,
10,344 to 8,354, 12,682 to 11,360. Worlds that should never have been
there.

### What the Demons did to every other reading

Adding them changed four Sects & Violets tests, and the change is the
script rather than a regression. A **No Dashii** always drunks its two
nearest Townsfolk and a **Vigormortis** drunks beside every Minion it
killed — neither is a choice and neither is lucky, so excusing a reading
from one of those seats costs **nothing at all**.

That makes a single reading on this script far weaker than the same
reading on Trouble Brewing, where a Poisoner has to have got lucky. An
Oracle saying one of the dead is evil used to name that seat at 100%; it
now moves the figure and no more, because "the Oracle was next to a No
Dashii" is free and "somebody evil died on night two" is priced at 0.05.

Both of those are true of the real game, so the tests now check the
*direction* a reading pushes rather than demanding certainty.

### The audit, before the difficult three

Taken at the seam where the risk changes shape rather than at the end:
the three characters left — Vortox, Pit-Hag, Snake Charmer — do not add
rules, they change machinery everything else already sits on. Auditing
afterwards would leave no way to tell "the Vortox broke it" from "it was
already broken".

`test_audit.py` asks one question of every reading the page offers: does
it do *anything*? Not what it does — each character has its own tests —
but that the row can be built, the solver accepts it, and the answer
moves. A reading that changes nothing is either broken or pointless, and
neither shows from outside.

Everything bites. Two that looked like they did not were the probe being
wrong, and both traps are worth keeping written down:

**A reading only bites when somebody claims its character.** A Courtier
row on a board where nobody claims Courtier fires only in the worlds
where some seat happens to hold it — a thin enough slice to look like
nothing at all. With the claim in place it moves the board from 9,894
worlds to 11,986 and drops the Chambermaid's evil reading from 20.5% to
12.4%.

**And "is this reading true" is a question about a world, not a board.**
The first version of that test compared board totals and expected them
equal. Across a whole board a reading is false in *some* worlds, so
excusing those moves the total — correctly. Asked of one world, the
numbers are exactly what they should be: a true reading costs nothing, a
false one costs 0.6 to excuse, and nothing at all once a Courtier
declared it.

The one reading that genuinely does nothing is the **Mathematician**, and
that is deliberate: four characters that droison are still unbuilt, so it
constrains nothing rather than being confidently wrong. A test asserts
that something is silencing it, so the day that stops being true is the
day it starts biting.

### The fourth batch: reaching a character from the other end

The **Witch** and the **Cerenovus** each make a hidden choice the board
never records — who was cursed, who was made mad — and no amount of
modelling gets at either. But each leaves something the table sees
plainly: a seat dropping dead as it nominates, and a seat executed for
breaking madness. Recording *that* says the character is in play, and on
a nine-player board with one Minion it names it outright. Both are new
seat statuses, and both demand the one who did it was working.

That is the whole handle either offers, and it is a good one.

**Evil Twin** — two seats that know each other, one of each side, one of
them it. A lot from a single row.

**Philosopher** — and this is the piece worth having built carefully,
because it is needed twice. It does not *become* the character it takes:
it keeps its own, and the chosen one may be sitting elsewhere at the same
time, which the world enumeration forbids two seats from doing. So it is
an **overlay** — from that night on, the seat also acts as the chosen
character — which is exactly the machinery a Pit-Hag will need from the
other direction, where "first night" has to mean the first night *since
arriving*.

Two things had to give. `ability_state` gained a fourth argument, so a
seat can be working two abilities at once from a phase onward. And the
**relaying rule had to learn an exception**: a row is normally handed to
the one seat claiming its source, which is right for somebody passing on
information and wrong for a Philosopher speaking its own — without that,
a Philosopher's Juggler reading was judged against the seat that actually
claimed Juggler.

It reads well. Guesses that cannot be right do not make the board
impossible; they make the seat **not the Philosopher**, which is the
cheaper story and the true one.

### Three states, not two

`modelled` was doing two jobs: *"not built yet"* and *"built as far as it
will ever be"*. Those look the same from outside and are completely
different things — and reporting them as one had me counting three
finished characters as a backlog.

A **Savant** is finished. Its pair of statements can be anything at all,
so the words are kept and shown and that is as far as it goes. Same for
the **Artist**. The **Mutant** is finished too: madness leaves no mark on
the board, so there is nothing to model. A **Vortox** is simply not
started. Putting all four in one list tells somebody the wrong thing
about every one of them.

So a character now says how far it is handled — *fully*, *partly*, or
*not* — and whether that is as far as it goes. The script panel says
three separate things instead of one, and the character list marks them
`*`, `°` and `–` with a key underneath.

`modelled` survives as a derived question, because a dozen places ask it
and all of them mean the same thing: can the solver be trusted about this
ability. Recording something without weighing it does not count.

The honest position for Sects & Violets is **15 of 25 finished, 10 left
to build**.

### The third batch, and a walk that went round for ever

**Sage** — killed by the Demon, shown two players, one of them the
killer. And **not** by registration, which is unlike almost every other
reading on this project: it sees *the Demon that killed it*, so a Recluse
being shown as the Demon cannot fill the pair. Easy to get wrong by
reflex, and I did until it was corrected.

**Sweetheart** — from the night it dies, one player is drunk for good.
Different in kind from a Poisoner: it never turns off, so every reading
that seat gives afterwards is arbitrary for the rest of the game.

**Klutz** — good loses on the spot if the seat it points at is evil, so a
board where play carried on says they were not. While it was *working*:
same shape as the Saint executed while poisoned, and a droisoned Klutz
makes the board expensive rather than impossible.

**Barber** — the Demon may swap two players' characters the night after
it dies. Characters only, sides unchanged, so a good player can end up
holding a Minion's character. That is the reason `Change` has kept its
two halves separate since the Ogre.

**And the Barber broke the lineage walk.** With two seats trading
characters, the star could be handed back to somebody who had already had
it, and the walk recursed until the stack ran out. It now refuses to go
backwards in time or to give the star to a seat twice.

The first fix was one comparison too strict — "no *later* than" instead
of "no *earlier* than" — which quietly ended some lineages early and
added worlds to two Bad Moon Rising boards. A Shabaloth kills twice in a
night, so a Demon and its heir can fall together and the star passes on
again. The corpus caught it.

**Mutant** stays unmodelled, and now says why: madness leaves no mark on
the board, and being executed for breaking it looks like any other
execution. If the table knows that is what happened, mark the seat as
confirmed.

### The second batch, and two that are kept rather than solved

**Oracle** — how many of the dead are evil, by registration, so a dead
Recluse may read either way. **Seamstress** — whether two players share a
side, once per game, which splits the table in one reading. **Juggler** —
guessed in daylight, answered that night, matched by registration.

**Savant and Artist are recorded and not weighed**, deliberately. A
Savant's pair can be anything from "the Demon sits beside an Outsider" to
"no Minion has yet chosen a man", and an Artist's question is whatever
the player thought to ask. Checking arbitrary claims about a board is a
different program from this one. So the words are kept and shown, the
script panel says they are not weighed, and the solver does not pretend.
They are not nothing: recording one is still somebody claiming to have
visited the Storyteller, so it argues for that character existing.

**Which forced a fix to the Mathematician.** Its guard read "constrain
nothing if *any* character on this script is unmodelled" — fine while
everything unmodelled was temporary. The Savant and Artist are permanent,
so that guard would have silenced the Mathematician on Sects & Violets
for good. Only a character that can **droison** matters to it, since its
number is the size of the impairment set, so there is now a list of the
fifteen that can, and the guard asks about those.

**And the generator was dropping the flag.** `tools/gen_characters.py`
leaves out any field at its default value, by way of a table of
defaults — and a field *missing* from that table is left out for every
character, default or not. So `impairs` never reached JavaScript, and the
corpus caught it one board later. The generator now refuses to run if the
table does not name every field, which was checked by removing one.

### Three checkboxes attached to nothing

They shipped. "Voted today", "nominated today" and "their information
might be wrong" were all added to the seat panel and never bound to a
handler, because the edit meant to attach them anchored on text that did
not exist and quietly did nothing. The suspect box had been dead for a
whole session before anybody clicked it.

Nothing in the solver could have noticed. A checkbox with no handler
looks exactly like a working one — it ticks, it looks right, and it
forgets the moment another seat is chosen. Every test passed, because
every test called the solver directly with data the page never managed to
produce.

`test_inspector.py` drives the page instead: it clicks a seat, ticks the
boxes, clicks away and back, and checks what survived and what the ledger
drew. Verified by removing a handler and watching it fail.

### A copy of the board reader, quietly drifting

Adding votes broke the conformance check, and the reason was worth more
than the feature. `dump_solve.mjs` had its **own copy** of the code that
turns a payload into a board — written before `api.mjs` existed. So the
page and the server learned to record votes and this did not, and the
corpus reported a difference between the two implementations that was not
there.

It goes through `api.solveBoard` now, and two things fell out. The
JavaScript was **refusing scripts Python merely complains about** — a
script short of a team is a complaint, not a wall — which nothing had
noticed because the check was running against the copy without that code
in it. And the long-standing gap where input validation lived only in the
server **closed by itself**: all eight refused boards now come back
refused, word for word, from both.

**One trap on this script, which cost an hour.** Sects & Violets has four
Outsiders and a nine-player bag wants two, so two Outsider claims fill it
*exactly* — those seats are pinned, nothing about them can vary, and a
reading aimed at one proves nothing. The first Dreamer test was aimed at
a pinned seat and looked broken when it was working perfectly. There is
now a test for the trap itself.

All twenty-five characters, and only one of them not reasoned about. It
shares nothing at all with Trouble Brewing — thirteen Townsfolk, four
Outsiders, four Minions and four Demons, none of them appearing on both.

Expect the solver to be **less certain here**, and expect that to be
right. Between the Sailor, the Innkeeper, the Courtier, the Goon and the
Minstrel there is nearly always somebody drunk that nobody can name, so a
contradiction is far cheaper to explain than on Trouble Brewing — two
contradictory readings in a single night are impossible there and
ordinary here. That is the game being harder to read, not the tool going
wrong.

### The Townsfolk

**Chambermaid.** Two living players, and how many woke tonight for their
*own* ability. This needed the one genuinely new piece of machinery in
the script, in `botc/waking.py`, because it asks a different question
from the wake table. That table is forgiving on purpose — it records what
somebody could honestly *claim*, and a Courtier's honest answer depends on
when it spent its ability. The Chambermaid needs the fact, and the fact
depends on the board: a Ravenkeeper wakes only on the night it dies, an
Undertaker only after an execution killed somebody, a Courtier only until
it has named a character, a Professor only until it has raised somebody.

Two details that are easy to get backwards. **Being impaired does not let
you sleep** — the Storyteller wakes you and makes an answer up — so
drunkenness never changes this count. And the Demon woken on the first
night is being shown its bluffs, which is not its own ability and does not
count.

The **Exorcist** makes the answer a range rather than a number. A Demon it
chose does not wake for itself, nobody writes down who it picked, so with
one in play the Demon's waking is genuinely open. The reading is checked
against every count it could have taken, the same way misregistration is
handled.

**Pacifist.** Some executed good players do not die, and it is the
Storyteller's choice each time — so an executed good player who *did* die
proves nothing. It only ever explains a survival.

**Tea Lady.** Both her living neighbours good and neither of them can
die, from any source. Whether they are good is exactly what is in
question, so this depends on the world being scored rather than on the
board. Always on rather than aimed, so a dead neighbour means she was not
working. Her neighbours are whoever is living beside her at the time, not
whoever started there.

**Fool.** Its first death does not take it, and that covers the gallows
as well as the night. Marked as aimed rather than always on, and the
reason is worth saying: a Fool's first would-be death leaves no record at
all, because nothing happened. So a Fool that *is* dead says nothing — the
free one was spent out of sight. What it can do is explain a survival.

That makes three reasons to walk away from an execution — a Sailor, a
Fool and a Pacifist — told apart by which seat had to be working. It is a
registry rather than a special case, and a Devil's Advocate will be the
fourth. It
counts who woke *for their own character* that night — so a Demon woken
because the Exorcist chose it does not count — and working that out for
every world is a piece of machinery that is not built yet.

**Expect the solver to be less certain on this script.** The Sailor and
the Innkeeper each float an impairment every night that nobody at the
table can pin down, so a contradiction is far cheaper to explain here
than on Trouble Brewing — two contradictory readings in a single night
are impossible there and ordinary here. That is the game being harder to
read, not the tool going wrong.

### The Outsiders

**Goon.** Whoever points at it first each night goes drunk, and the Goon
turns to their side. Only somebody whose ability actually *chooses a
player* triggers it — a Courtier names a character and never does, and a
Grandmother is shown somebody rather than picking them.

The side is not permanent and can go back and forth all game, and nobody
records who chose whom. So rather than tracking transitions, the Goon's
side is simply **open**: an Empath counting neighbours has to allow both.
That is a different thing from misregistration and the catalogue keeps
them apart — a Recluse is good and *reads* evil, while a Goon that turned
really is evil and counts for the team. Which is why the **Fortune Teller
says no to it**: that ability asks about the Demon specifically, not about
evil.

**Lunatic.** Thinks it is the Demon. The same machinery as the Drunk
pointed somewhere new — it is handed a Demon token rather than a Townsfolk
one — and it falls out that it *bluffs the way the Demon would*, because
as far as it knows it has every reason to. The only good player that lies
deliberately. Its choices never matter; the real Demon does the killing.

**Tinker.** May go at any time, at the Storyteller's whim, with no trigger
to wait for. Not the Demon's doing, which is why a Monk is no help — a Monk
guards against the Demon and the Storyteller is not the Demon. A Tea Lady
or an Innkeeper does stop it, because they guard against everything.

**Moonchild.** Its pick lands the night *after* it learns it died. A player
learns at dawn, or on the spot if it happened in daylight, and names
somebody there and then — but the rest resolves the following night. So a
Moonchild killed on night two reaches out on night three. Only a good
target dies, so it may fire rather than must.

### The Minions

**Godfather.** An Outsider lost in *daylight* and it kills tonight — an
Outsider taken in the night triggers nothing, which is a clean piece of
deduction for the table. Whether the seat that died was an Outsider is a
question about the world rather than about the board, so it fires in the
worlds where it holds and not in the others. Mandatory, but it can be
aimed at somebody already dead. Not the Demon's kill, so a grandchild
lost to it leaves the Grandmother standing.

Its setup is the first with a *choice*: one Outsider more or fewer, the
Storyteller's call. Composed with the Baron that gives six bags where
Trouble Brewing has two.

**Assassin.** Once per game, and **nothing stops it** — "dies even if
they could not" goes through every shield in the game. That needed
something genuinely new, since no cause had ever ignored a shield before.
The clean demonstration: a Tea Lady's neighbour cannot die while she is
working, and in worlds with nothing able to impair her that death is
flatly impossible — unless an Assassin did it, where it costs only the
Assassin's own penalty. A dead Sailor would *not* show this, because the
Sailor drunking itself is a cheaper story than either.

**Devil's Advocate.** The fourth way to walk away from the gallows, after
the Sailor, the Fool and the Pacifist. The gallows only, so a Tinker it
protected can still go of its own accord.

**Mastermind.** Mostly out of scope, and it says so: it moves the win
condition rather than the board. But the extra day it buys *is* modelled,
because that much is visible — when the Demon is executed and nobody
inherits, the lineage simply ends, and the nights that follow have no
Demon kill to explain. A quiet night after an execution is exactly that
shape.

The hint that goes with it started as a threshold and ended as a floor,
and the reason is worth recording. Waiting until the executed seat looked
like the Demon with any confidence turned out to fire on nothing: the town
executing the actual Demon is rare enough that even with every other seat
vouched for and a hard read on the one that went, the figure came to about
**8%**. So the situation is shown with the number attached instead —
"if that was the Demon, today is the extra day, and here is how likely
that is" — which is more use than a warning that never comes.

### The Demons

Four of them, and each kills differently — so exactly one of the four
rules answers for any given world.

**Zombuul.** Kills only if nobody died during the day before. *Any* death
stops it: an execution, a Slayer shot, a Tinker going of its own accord.
And it is dead on the board before it is dead in fact — the first time it
would die it does not, but it registers as dead, so the table crosses it
off while it carries on killing. It is only really gone the second time.
Nothing else in the game is recorded dead and alive at once.

**Pukka.** Poisons on one night, and that poison kills on the next. It
starts a night earlier than any other Demon: the first night is only the
poisoning. That needed the one extension the Demons asked for — a cause
that demands its victim was impaired on an *earlier* night, so the two
halves of it stay linked rather than floating free.

**Shabaloth.** Two a night, and it may bring one of them back. Either
kill can be aimed at somebody already dead, so the table may only ever
see one body — and a resurrection here is not the Professor's and is not
necessarily good, which is why nothing about coming back assumes the
character doing it is on your side.

**Po.** May choose nobody, and then takes three the next night. Whether
it declined is not written down, so a night with no bodies is read as it
possibly having done. That is permissive rather than exact — a Po that
sank a kill into a corpse also leaves no body — and it errs towards
keeping worlds rather than throwing them away.

## Part 4 – Using the grimoire

**Player count** sits in the top bar. The label shows what that count
produces, so `12 players — 7/2/2/1` means seven Townsfolk, two Outsiders,
two Minions, one Demon.

**Click any seat** to set the name, the claimed role, and whether that
player is alive, killed at night, executed, or died during the day some
other way. There is no "died night 1" option, because in Trouble Brewing
the Demon's first kill is night 2.

**Death is not permanent.** A Professor raises a dead Townsfolk, and it
is not the only character that can — nor are they all good, so nothing
here assumes the one coming back or the one doing it is on your side. A
seat's life is a run of events rather than a single death: it can go
down, come back, and go down again, and "were they standing then" is a
question about a moment.

**What happened** under each seat offers only the day the game has
actually reached, because recording a death on day five while the table
is on day two is a mis-entry rather than a choice — and a flat list of
thirty options invited exactly that. Everything already recorded for that
seat is listed underneath and can be removed, so a mistake on day two is
still fixable on day four. Nobody has to know what "N4" means.

Two conventions worth knowing, because every check that asks "who was
around then" depends on them. A death takes effect *after* its own
moment: somebody killed on night two was there during night two. A return
takes effect *at* its moment, because that is when they are back.

**Being executed and being killed are separate facts**, and the status
list keeps them apart:

| | |
|---|---|
| Died night N | the Demon |
| Executed day N, died | the town's vote, or a Virgin trigger |
| Executed day N, survived | the day still ended, but nothing died |
| Died day N, not executed | a Slayer shot |

Nothing on Trouble Brewing survives an execution, but plenty does
elsewhere — a Zombuul walks away from its first, a Devil's Advocate can
save somebody from theirs — and the two facts drive different rules, so
conflating them into one field was wrong even here.

Executing the Saint ends the game, so an execution *that killed* and was
followed by more play means that seat was not the Saint: in a 12-player
test the seat claiming Saint went from 43% evil to 100%. An execution
they survived proves nothing, because the Saint's condition is dying of
one. A Slayer shot proves nothing either, for the same reason.

**The Undertaker can only be pointed where it could have looked.** It
wakes on the night after an execution killed somebody, and learns about
that seat — so the ledger offers exactly that one seat and nothing else,
and says whose execution to record first if there isn't one. Who the town
executed is public, so a wrong target is never a lie worth modelling; it
is a mis-entry, and gets named as one.

I don't apply the mirror rule to the Demon, tempting as it is. Executing
the Imp normally ends the game too, but with five or more players alive
the Scarlet Woman becomes the Imp and play continues — and role changes
mid-game aren't modelled here, so an executed seat is left free to have
been the Demon. Seats run clockwise from
the top, and seat 1 sits next to the last seat — that adjacency is
exactly what the Empath and the Chef read, so get the seating right.

**How sure are you?** sits under the claim and has three settings:

- *Only their claim* — the default. They might be telling the truth, they
  might be the Drunk, they might be bluffing.
- *This seat is me* — marked **you** on the dial. You can see your own
  token, so you hold that role. The one thing you can't rule out is being
  the Drunk, because the Drunk never knows. Only one seat can be you.
- *Role is confirmed* — marked **sure**. The role is taken as certain and
  not the Drunk. This is for mechanical proof: a Virgin that triggered
  was the real sober Virgin, so nothing else fits that seat.
- *Might be hiding an Outsider* — also allows the good lie people
  actually tell: a Recluse, Saint or Butler claiming somebody else's role
  to stay alive. Cheap, and worth reaching for often.
- *Claim not trusted* — the claim is set aside and that seat may hold any
  role at all, including a Townsfolk falsely claiming a different
  Townsfolk. Use it when a claim smells wrong. It's the expensive one:
  each untrusted seat multiplies the search, so one or two at a time.

There is no global "good players may lie" switch, and that's a deliberate
retreat. Letting every seat hide takes a 12-player game from 15,120 legal
worlds to 2,928,960 — past any workable ceiling, and mostly worlds worth
almost nothing. Marking a single seat as hiding costs 30,672 instead, and
you almost always know which seat you doubt.

**What they said about waking** captures the soft claims people actually
open with — "my role doesn't wake", "only the first night", "every night".
It narrows the good roles without naming one:

| Said | Fits |
|---|---|
| Never wakes | Ravenkeeper, Virgin, Slayer, Soldier, Mayor, Recluse, Saint |
| Only the first night | Washerwoman, Librarian, Investigator, Chef |
| Every night | Empath, Fortune Teller, Undertaker, Monk, Butler |
| Every night but the first | Undertaker, Monk |
| Only sometimes | Undertaker, Ravenkeeper |

The table is deliberately forgiving, because ruling a role out wrongly is
far worse than ruling it out weakly. The Monk and Undertaker wake every
night after the first, so someone saying plainly "every night" is not
lying and both accept it — while "every night but the first" stays the
sharper statement. The Ravenkeeper wakes once and only on the night they
die, so their honest answer is "never" until then and "sometimes"
afterwards. And the Undertaker sleeps through any night following a day
with no execution, which is why "sometimes" fits them too. All of this
lives in `WAKE` in `botc/roles.py` — correct it to match how your table
talks. Pick a statement in the inspector and it lists the roles it could
mean, each with that seat's current odds of being it, so you can look up
what somebody might be without knowing the script by heart.

Evil is never held to this. They know what they are and will describe
whatever suits the bluff, so a wake statement prunes only the good roles.
The Drunk is judged on the token they were given, since the Storyteller
wakes them on that character's schedule.

Soft claims can be sharper than they look. In a 7-player test where four
seats had already claimed Washerwoman, Librarian, Investigator and Chef,
a fifth seat saying "only the first night" jumped straight to 51% evil —
every honest role that fits was already spoken for.

**Believe** on each ledger row is the same idea for the information
rather than the informant: how far you trust the reading itself,
separately from whoever announced it. It matters most for a reading
attributed to a role nobody has claimed, where there is no seat to have
an opinion about — and it is the setting that replaces the guess the
sensitivity pass shows doing the most work. With two Empath readings
nobody has claimed, moving it from *not at all* to *completely* takes the
odds an Empath exists at all from 14% to 98%, and flips the best guess
for a silent seat from Butler to Empath. Left alone it sits at the
default and behaves exactly as before.

**Your read** is a slider under each seat, running from *sure good* on the
green left to *sure evil* on the red right, with the current setting named
underneath it. It's your social
judgement, not a mechanical fact, so it never rules anything in or out —
each step doubles the odds that seat is evil, so ±3 shifts the odds by 8×
and no more. A read can make a suspicion visible without letting it
overrule the mechanics.

**"Said by"** on each ledger row is the person making the claim out loud.
A row says "this seat claims to be the Empath and to have seen one evil
neighbour" — so if they turn out to be evil or the Drunk in some world,
that row constrains nothing there.

New rows point themselves at whoever claims the matching role, so adding
Empath information picks the seat claiming Empath without you hunting for
it.

When the speaker claims something else, the row is read as a **relay** —
handing your information to someone else to share is ordinary play, not a
mistake. The row says whose information it is, and the solver treats it
accordingly: it binds to the seat that claims the role, and poison has to
land on *them*, since poisoning the messenger changes nothing.

The relay comes with its own escape, which is the point. A messenger who
turns out to be evil could have invented the whole thing, so any world
where the relayer is evil ignores the row entirely. That splits the
suspicion instead of concentrating it. In a 12-player test, an Empath
whose own two nights contradicted each other sat at 48% evil when she
spoke for herself; when a Washerwoman-claimer relayed the same two
readings, she dropped to 37% and the messenger rose from 19% to 37%.
Exactly where the doubt belongs when you can't tell which of the two
invented it.

If nobody claims the role at all, the row doesn't fall back to the
speaker — it floats. There may well be an Empath nobody has heard from
yet, so the statement is fitted onto whichever seat holds that role in
each world, including seats that have said nothing. Worlds where the role
simply isn't in play have to treat the whole thing as invented, and pay
for it (`FABRICATED_INFO_PENALTY`, 40%).

That's what makes an unclaimed role surface. In a 7-player test with five
claims and two silent seats, one call of "Empath 0" lifted the odds an
Empath exists at all from 16% to 21%; a second consistent night took it to
36%, and Empath became the most likely role for both silent seats. It can
still be a bluff — that's what the discount rather than a hard rule is
for — but the numbers now reflect that a called reading is evidence the
role exists.

**Seats that haven't claimed** show the solver's best guess instead of
"no claim" once you've solved: the most likely role for that seat with its
percentage, in brass italics so it's never mistaken for something the
player actually said.

Two rows are exceptions to all of this, because they aren't claims — they
are events the whole table watched. Both are handed to the search before
it starts rather than being checked afterwards, so they shrink the work
instead of generating worlds only to discard them. A Virgin trigger prunes
the search harder than marking that seat *Role is confirmed* by hand,
because it pins the nominator as well.

A **Virgin nomination** row records someone nominating the Virgin claim,
and both outcomes say something.

If the nominator died, it's a fact the table watched. A drunk or poisoned
Virgin doesn't trigger, so that seat is confirmed as the real, sober
Virgin and the nominator is confirmed to have registered as a Townsfolk —
an actual Townsfolk, or the Spy. In a 12-player test that took the Virgin
to 0% evil and left the nominator at 7%, exactly the Spy residue. Mark
the nominator's seat as **executed** that day; the card reminds you.

If nothing happened, it only bites in worlds where that seat really is
the Virgin — and then the nominator was no Townsfolk, or the Virgin was
poisoned. Same test, the nominator went from 21% evil to 34%. Only the
first nomination of a given Virgin carries this, since the ability fires
once; later quiet ones are ignored.

A **Slayer shot that killed someone** is not a claim either. A body hit the floor, and nothing but a real, sober,
healthy Slayer hitting the Demon can do that. So it binds in every world
— the target is the Imp or a Recluse registering as one, the shooter is
the Slayer, and every other possibility drops to zero. Poison can't excuse
either event, since a poisoned Slayer's shot does nothing and a poisoned
Virgin doesn't trigger.

**The ledger** sits down the left, beside the grimoire rather than below
it, because it's the thing you touch constantly. It runs one block per
night. Pick a type at the top, press **+ add** on the night it belongs
to, and the fields change to match: the Washerwoman gets two seats and a
Townsfolk, the Empath a number, the Fortune Teller two seats and a
yes/no. Day events are marked *(day)* and sit under the matching number.

**Hit Solve** — the natural moment is as the night falls, once the day's
talking is done and the grimoire is up to date. Every solve is kept as a
snapshot, so the **timeline** under the dial builds up a record of the
game: click any night to put the board back into that state, and the
inspector draws a small chart of how that seat's evil and lying odds have
moved across the whole game. Often the jump matters more than the number.
Editing anything after a solve marks the timeline *edited since the last
solve* rather than blanking the board, so stale figures stay readable
mid-conversation.

The centre of the dial shows how many worlds survive. Each
seat then carries two arcs: the **inner red ring** is how likely they are
to be evil, the **outer purple ring** how likely they are to be lying.
Blue means good throughout — a low evil reading, a confirmed seat, a read
pointing that way. Below each seat, a small ▲ or ▼ shows the change since
the previous solve.
Clicking a seat breaks it all down role by role in the side panel.

Those two rings usually match, because an evil player bluffing a role is
the ordinary reason to lie. They come apart when you mark a seat *Claim
not trusted*: in one test, an untrusted seat came out 41% lying but only
10% evil — probably lying, probably not your enemy. That gap is the point
of showing both.

The game is kept in your browser's local storage, so a refresh won't lose
it. *Clear game* wipes it.

## Part 5 – How the solver thinks

### When there are too many worlds to count

Early in a game, with three claims on the board, there can be tens of
billions of possible worlds. Counting them is hopeless, so past a ceiling
the solver stops counting and starts looking: tens of thousands of random
walks from the top of the search down to a finished world.

The walks are not uniform, and that matters. A seat claiming a Townsfolk
offers one honest option against five evil ones, so tossing a fair coin
over them makes a seat evil five times too often — the walks land in a
thin corner of the search and the correction needed to fix it explodes.
Instead each team is picked roughly in proportion to how many of its
slots are still unfilled. Each world then carries the reciprocal of the
probability the walk actually used, which is what keeps the estimate
unbiased; matching the shape only makes it steadier. In testing that one
change took the effective sample from 13 to 2,388 out of 4,000 walks.

**Sampled figures are labelled, always.** The seat readings carry a ±,
the dial says how many effective samples went into it, and the timeline
marks that snapshot with a tilde and a dashed border. Solve again later,
once claims have narrowed things, and you get an exact count instead — a
game's history never silently mixes the two.

Two things worth knowing:

- **The ± is the effective sample size, not the number of walks.**
  Uneven weights mean a thousand lopsided samples can carry the weight of
  a hundred even ones, and reporting the raw count would overstate the
  precision.
- **Sampling does not make the solver smarter early on.** With three
  claims recorded, the true answer really is close to uniform. You now
  get that answer instead of a refusal, which is better — but the
  flatness is the game not knowing yet, not the tool failing.

### When the Demon changes hands

A world is one starting assignment, and it stays that way. Who holds the
Demon *over time* is part of the explanation instead — searched lazily and
only when a death forces it, exactly like the poison schedule and the red
herring.

The timing is never a free choice. It is pinned by the deaths already on
the record: a Demon dead at night killed itself, and a Demon killed in
daylight ends the game unless the Scarlet Woman was standing by. Only the
recipient is ever open, and usually not even that — she takes priority
whenever her own condition holds, so most handovers have exactly one
story. Chains work without a special case, because a lineage is a list:
an heir who dies later hands it on again.

A starpass is not charged for on top. The Demon's own seat dying at night
is already discounted hard by the night-death prior, and billing it twice
would be double-counting.

This was measured before and after. The oracle deals games that perform
starpasses and takeovers, and before this landed **80–90% of them had the
real game discarded outright** — the solver saw the Demon's seat dead,
concluded nothing could have killed on a later night, and threw the world
away. It is now **zero**, at every starpass rate tried, and the seat
currently holding the Demon is the top suspect 26–45% of the time where
it used to be 8–25%.

### Adding characters that rewrite other characters

Trouble Brewing only ever moves the Demon between evil seats, so nothing
in it exercises the general case. The machinery underneath handles more
than that, and is arranged in three parts.

**A change is a record, not a rewrite.** `Change(phase, seat, role, side)`
says a seat became something else from that phase on. Either half may be
left alone: `role=None` moves only the side, which is what an Ogre or a
Politician does; `side=None` takes whichever side the new character
normally sits on, which covers a Minion catching the star. Both together
cover a Pit-Hag rewriting somebody into anything at all. A `Timeline` is a
world plus its changes, and the world underneath is never touched.

**Alignment is asked about a moment.** `alignment_at` and `evil_at` sit
beside `role_at`, because the two come apart — an Ogre turns evil without
changing character. This reaches the arithmetic, not just the
bookkeeping: the Empath's count and the Chef's pairs both read the side
at the night they were given.

**The trigger is fixed; the list of who can inherit is not.** That the
Demon dying means *something happened* is a rule of the game. Who catches
it is the part scripts keep adding to, so it lives in `HEIR_RULES` —
currently a Minion taking the star and the Scarlet Woman stepping up.
`tests/test_transitions.py` registers a third from outside the package:
the Fang Gu, whose victim becomes the Demon and turns evil. It is almost
the starpass — same trigger — but the star lands on a *good* seat, so it
only fits if the machinery understands changes that cross alignment. It
does, all the way through to the Empath reading one evil neighbour where
it read none, and to the report naming the new Demon rather than the dealt
one.

**Rules are anchored to something on the record.** A rule that could fire
on any night for no reason would multiply the search by seats times
nights, generating stories nothing is asking for. Every rule hangs off a
death or an execution, so a world with nothing to explain produces exactly
one story and costs nothing. Where a character really does act unprompted,
the way in is to record the event — the same way a Virgin trigger or a
Slayer shot gets in today. Positing a change only where a statement would
otherwise be false is the harder version, and is not built.

### What killed them

Trouble Brewing kills at night one way, so "died at night" and "died by
the Demon" were the same sentence and the solver never had to tell them
apart. They are not the same sentence. A Soldier cannot be killed by the
Demon and can be killed by a Gossip, an Assassin or a Godfather without
any trouble at all — so a death is attributed to a **cause**, and what a
character is safe from is a question about the cause rather than about
the night. `botc/deaths.py` holds the registry.

A cause carries three things beyond who it could reach. Its **kind**,
because the Soldier's protection reads "safe from the Demon" and turns on
that rather than on who is doing the killing. Whether it **must fire**,
because the Demon kills every night — so a night nobody died is a night
something stopped it — while a Gossip only kills when it said something
true, and owes a quiet night nothing. And what it **implies**, because a
Grandmother dies when her grandchild is killed *by the Demon*, and a
grandchild taken by a Gossip leaves her standing.

**One kill can leave two bodies.** Without that, a night where both the
grandchild and the Grandmother died would need two causes, and Trouble
Brewing has one — so the world would be thrown away. The dragged death
consumes no cause of its own.

The same link runs the other way, and that is where the deduction is: if
the grandchild died to the Demon and the Grandmother is still standing,
then either that seat was not the grandchild, or she was not working — and
something had to have impaired her, which costs. On a board with nothing
capable of impairing her, the world goes entirely.

What makes this awkward, and worth building before any character needs
it, is that the thing linking the two deaths is usually a **marker rather
than a character**. The grandchild is not a character anybody holds; it is
a token the Storyteller put on a seat when the Grandmother was shown it.
So an implication rule reads the board — including the readings on the
ledger — rather than reading the roles.

Protection is not a property of the night either. The Monk guards against
the Demon; the Innkeeper guards against everything, so a Grandmother's
grief and a Gambler's bad guess are stopped by one and not the other.

**A shield somebody aims implies nothing about a death.** This is the
distinction that matters most and the one I got wrong first: a Soldier is
safe every night whether anybody likes it or not, so a Soldier who died
must have been impaired — but a Monk picks one player a night, so a death
only ever means it guarded somebody else. Reading the Monk as an
always-on shield made every night death demand an impaired Monk, and the
oracle caught it immediately: eleven sweeps failed at once.

Quiet nights are no longer handled separately. "The Demon was stopped"
and "the Demon killed somebody" are the same question asked of the same
cause, so the bespoke logic for them is gone.

### What the deaths themselves rule out

Night deaths are no longer only a record of who is still alive. A body in
the morning means the Demon killed, and that alone rules a lot out:

- Only one seat can die per night, so two night deaths on the same night
  is not a world at all.
- The Demon has to have been alive to do it.
- A sober Soldier cannot be the victim. So if the seat that died holds
  the Soldier token, the Poisoner has to have been on them that night —
  which flows straight into the poison-luck accounting below. In a
  12-player test, killing the seat claiming Soldier pushed the odds a
  Poisoner is even in play from 67% to 87%, and left "they were actually
  the Drunk holding the Soldier token" carrying a third of the weight.
- If the Demon's own seat died at night, it killed itself and the star
  has to land on a living Minion. The Scarlet Woman takes it whenever her
  own condition holds — alive, with five or more players left — so in
  those worlds there is no choice about who inherits.
- If the Demon's seat died in the *day*, whether executed or shot, the
  game ended there unless the Scarlet Woman was present to take over. A
  death like that on the record means the handover happened. In a
  12-player test this took an executed seat's odds of having been the
  Demon from 7% down to 5%, and to zero once fewer than five players
  remained.

The Monk deliberately implies nothing here. Protection is a free choice
every night, so a death only ever means the Monk guarded somebody else.

### How much of an answer is guesswork

Every figure mixes two things. Some of it is rules — a landed Slayer shot
means the target was the Demon or the Recluse, which is checkable against
the rulebook and is tested against it. The rest rests on the constants
below, which I picked by judgement and which print in the same font as a
fact.

**How much is guesswork** in the top bar re-solves across the plausible
range of every one of them and shows each seat as a band rather than a
point, naming whichever guess moved it most. It is deliberately done by
sampling with a fixed seed, so the walks are identical across all the
settings and only the weights differ — what comes back is the effect of
the guess with no sampling noise mixed in.

The result is worth looking at, because the answer is not uniform. On a
12-player table with a contradictory Empath, an execution, a night kill
and a quiet night:

```
 seat   printed        range     driven by
    5     19.7%       7 – 37%    fabricated info penalty
   12     53.3%      51 – 56%    poison hit penalty
    9      1.0%       0 –  3%    night death evil penalty
```

Seat 12 the evidence decided. Seat 5 is almost entirely resting on one
number I invented — "19.7%" is not the honest answer there, "somewhere
between 7 and 37, depending on how sceptical you are of invented
readings" is.

Worth contrasting with the ± on a sampled solve. That one is
*statistical* — how far the random walks might be off, usually a point or
two. The band above is *modelling* uncertainty, and on that table it was
ten times larger and previously invisible.

### Whose ability was not working

Drunk and poisoned are one thing. A poisoned Soldier can be killed at
night, a drunk Empath's count is invented, a poisoned Monk guards nobody
— the cause differs and nothing downstream cares. So the solver talks
about a seat being **impaired** on a night, and leaves what did it to a
registry in `botc/impairment.py`.

Trouble Brewing has two sources, and they look nothing alike, which is
what makes the shape worth having. The Drunk is impaired every night of
the game for free, because that is simply what they are rather than a
piece of luck. The Poisoner impairs one seat a night and has to have
guessed right, which costs.

Nothing enumerates who was impaired. It works the other way round:
something came out wrong, so somebody must have been, and the question is
whether the sources in play could have managed it and what that costs.
The same lazy shape the poison schedule always had, generalised.

The plan takes demands in both directions. **Impaired** covers a reading
that came out false and an ability that did not fire — which is what the
Soldier case always was, and it stops being a special case here.
**Working** is the other half: a Monk that is the only explanation for a
quiet night was doing its job, so nothing can have stopped it, and the
plan has to satisfy that around every other night's failures.

Two of these went in for free, and four more are waiting: the Sailor
every night, the Innkeeper from the second, the Courtier for three
running, the Minstrel hitting everybody at once. `test_impairment.py`
registers one from outside the package and checks that two contradictions
in a single night — flatly impossible on Trouble Brewing — become
ordinary once a second source is in play.

**What it costs.** About 15% per solve against the single-source version
it replaced. I went after that twice, first by caching and then with a
fast path for the one-source case, and neither moved it: the cost is
building the sources per night rather than the planning. It is the price
of the registry and it is worth paying, but it is a real 15%.

### How the numbers are weighted

Worlds are not counted equally. Two things change a world's weight:

- **A good player who would have to be lying.** Evil players bluff
  constantly, so that costs a world nothing. A good player claiming a
  role they don't hold is rare, so those worlds are discounted heavily
  (by default to 5% — `GOOD_LIE_PENALTY` in `botc/solver.py`, worth
  tuning to your table).
- **Your reads**, as described above (`READ_ODDS_STEP`, default 2).
- **Whether a bluff collides with anything.** Evil is handed bluffs drawn
  from roles that are *not* in play, and the team knows each other. So a
  clean bluff collides with nothing: not with a role someone genuinely
  holds (a Drunk's token counts — the Storyteller put it on the board),
  and not with a teammate's bluff. Both collisions happen; a deliberate
  double-claim is a real tactic. But neither is the default, so each
  colliding bluff is discounted to 30%. With two seats claiming Empath,
  this pushes the odds that one of them really is the Empath from 93% to
  98%, and makes "they're both evil and picked the same bluff" the
  unlikely reading it should be (`BLUFF_COLLISION_PENALTY`).
- **How lucky the Poisoner had to be.** A world only survives a
  contradiction if the Poisoner hit exactly that seat on exactly that
  night. Treating that as free makes a clairvoyant Poisoner as plausible
  as an honest table, which is wrong. Each required hit now costs (35% of
  the weight by default), while repeat hits on a seat already being
  poisoned are cheap (70%), because staying on a target is what Poisoners
  actually do. The effect is that information which corroborates other
  information wins: worlds where several statements simply hold up carry
  full weight, and the more nights the Poisoner has to nail in a row, the
  further that world sinks (`POISON_HIT_PENALTY`, `POISON_REPEAT_PENALTY`).
- **Early night deaths.** The Demon kills good players. Killing your own
  Minion wastes a night, and the one real reason to do it — the Imp
  passing the star — happens late, once the Imp is cornered. So worlds
  where a night victim is evil are discounted, hardest on night 2 — the
  first night anyone can die — where they keep 5% of their weight, then
  easing off one night at a time until the factor reaches 1 and stops
  mattering. Executions carry no such prior: the town
  chose that death, so it says nothing on its own
  (`NIGHT_DEATH_EVIL_PENALTY`).

So the world count in the centre of the dial is a plain count, but every
percentage around it is a share of *weight*. The sample worlds listed
below the ledger are the most plausible ones, not the first ones found.

### What the solver will not do

Everything here rests on two assumptions: the bag is known, and the teams
are the usual size. A handful of characters take one of those away, and
they do not make the solver slightly less accurate — they make the whole
world set wrong while the output looks exactly as confident as ever. They
are named in `botc/limits.py` rather than half-supported, and the two
kinds are handled differently on purpose.

**Legion and Riot break the teams.** Most of the table is evil, so every
count the search prunes on is wrong from the first night — and nothing
about the board would look unusual. There is no signature to detect, so
if one is on the script the solver refuses before starting and says why.
A wrong answer delivered confidently is worse than no answer.

**The Atheist breaks the bag.** The Storyteller may break the rules and
there may be no evil at all, so no legal world exists to find. That one
*does* have a signature: the board fits nothing. So it isn't refused —
it's raised, and only when the evidence for it appears.

Neither is on Trouble Brewing, so neither fires today. The machinery and
its tests are there for the scripts that come next.

### The last thing the server did

The guesswork check re-solves the board a dozen times over, once with
each judgement call moved to the edge of the range I would defend, and
reports how far each seat travels and which constant moved it. It was the
last thing still asking a server, because it needs the sampler that
arrived a phase earlier.

Porting it meant collecting the priors first. They had been `const` in
three separate modules, and a value frozen into a `const` cannot be moved
— so they now live in one object that everything reads at the moment it
is needed. The conformance corpus is the check that the refactor changed
nothing: all ninety-two boards still match to four figures.

It cannot be compared number-for-number, because both sides sample and
they use different generators on purpose. What *can* be compared is the
thing the answer is for: **which guess is load-bearing for which seat**.
That is a fact about the board rather than about the walk, and the two
agree on it for every seat that moves at all. On a test board the seat
carrying a +2 social read swings twenty-five points on what a read is
worth, and the seat that died on night two barely moves — which is the
report doing exactly what it is for.

### Telling somebody what went wrong

A board that survives no world used to get a shrug from the JavaScript
side: zero, and nothing else. Python had named the culprit for a while,
and now both do — the same entry, in the same words.

`js/diagnose.mjs` removes one entry at a time and reports which removals
let a world through, asks first whether the *claims* are the problem
(which the entry-by-entry search cannot see), and raises a character like
the Atheist when no single entry accounts for it.

`js/limits.mjs` is the other half of the same idea: a script the solver
will not attempt at all. Legion and Riot break the team counts with no
signature — the board looks perfectly solvable and every number is wrong
— so they are refused before starting rather than half-supported. That
table is **generated** from `botc/limits.py`, because the wording is the
whole feature and two hand-written copies would drift.

Writing the test for it took three goes, and each failure was the board
rather than the code. The first "contradictory" board was *malformed* —
two Chef readings from one seat, which the input checking refuses before
the diagnosis ever runs. The second was merely awkward: the solver
excused one reading with a Poisoner and six worlds survived. The third
vouches for **every** seat, which leaves nobody to be the Poisoner and
makes the contradiction genuinely unfixable. A board has to fit nothing
before there is anything to diagnose.

### Sampling, and how you check a random walk

Above forty thousand worlds the solver stops counting and starts looking.
That was the last real gap in the port: JavaScript **truncated** instead,
handing back a partial count with no margins and no way to tell which
worlds were dropped. A twelve-seat Bad Moon Rising board now answers in
under three seconds — 438,775 worlds — with a margin on every seat.

It needed a seeded generator, because an unseeded sampler is untestable:
every run differs and there is no telling a regression from noise. It is
**not** Python's, and deliberately so. Matching the two streams
number-for-number sounds appealing and is the wrong goal — it would pin
the JavaScript to Python's arbitrary choice of generator forever, and it
is not what makes a sampler correct.

What makes it correct is that it converges on the right answer and is
honest about how far off it might be. So the check is coverage: run it
against boards small enough to solve exactly, and see whether the readings
land inside the margins it printed **as often as it claims they will**.

The first version of that test asked every seat to be inside on a single
seed — which demands a 95% interval be right 100% of the time, and it
failed exactly as often as it should have. Measured properly across sixty
seeds the coverage is **95.9% at two thousand walks and 96.3% at eight
thousand**, against the 95% that two standard errors claims. The margin is
honest rather than generous, and the test now says so in both directions:
too narrow to trust, or too wide to be useful.

### Why an update never arrived

The first change published after the app was installed did not show up,
and the upload was fine. A browser decides whether to reinstall a service
worker by comparing the bytes of `sw.js` with the copy it already has —
and everything that worker serves is cache-first. So a version string
that never changed meant a changed page was never fetched, never
installed and never activated. The old copy was served for ever, and the
update looked like it had failed to upload. It had not; it was never
asked for.

The worker is now stamped by the build with a fingerprint of everything
shipped, so any change to any file moves it. A test proves the stamp
moves by changing the page, rebuilding, and changing it back — a stamp
that does not move is exactly as useless as no stamp.

Two smaller things went in beside it. The page asks for an update on
every launch, because browsers check on their own schedule and that can
be a day. And when one arrives it is taken immediately rather than at
some later launch, because a fresh page paired with a stale solver module
is the one state worse than being out of date.

### A Demon with no rule of its own

Adding a third script found something that had been wrong since the
second. The generic Demon kill named the Imp — *"each Demon that kills
differently has its own rule below"* — which quietly meant that a Demon
with no rule at all could not kill either. Recording one night death on
Sects & Violets made **every world impossible**: an ordinary board reading
as a contradiction.

The default was backwards. An unmodelled Demon that cannot kill breaks
every board it appears on; an unmodelled Demon that kills once a night is
merely incomplete. So the four with special rules now register their
names, and everything else kills the ordinary way.

Worth noting what is *not* a bug: a quiet night on Sects & Violets is
genuinely impossible. The script has no protective character at all, so
with nobody yet dead the kill cannot be stopped and there is nowhere to
sink it.

### The ledger reading as the game happened

Each night's readings are framed by what actually occurred: the night's
deaths and returns above them, and the day that followed beneath — who
was executed, or a checkbox saying nobody was.

Neither line is new information. It is all on the seats already, one seat
at a time, and the night is when it matters together: a reading about
night three means something different once you can see who was not there
to hear it.

An execution ends a day, and so does the town deciding not to execute
anybody — which is how most days end. The board had no way to say the
second, and that left the page stuck: recording an execution on day two
advanced nothing, so the statuses on offer stayed day two's and there was
no way to reach day three without inventing a reading for night three
first. Both now move the game on.

It rules out no world by itself — the solver already assumes nobody was
executed unless somebody was. What it does is say the game *reached* that
day, which bounds how long a story can run. A Mastermind buys exactly one
more day after the Demon is executed, and recording that a second day
also finished is what says the game ran on too far for that.

### Which of a seat's readings hold up

The solver always knew, per world, which readings held and which had to
be excused — it just never said. It says now, weighed across every
surviving world, on each row of the ledger.

Four outcomes rather than true-or-false, because two of them are neither:

| | |
|---|---|
| **holds up** | the source was genuine and what they said was so |
| **would have to be wrong** | genuine and false, so something stopped them |
| **was never theirs** | they hold somebody else's token, so the Storyteller made the answer up |
| **nobody could have said it** | no possible source in that world at all |

The middle two are the speaker being wrong **without lying**, which is
the distinction the table cares about most and the one a single
probability cannot carry. An Empath calling two evil neighbours on night
one comes back as *3% holds up, 42% was never theirs, 30% would have to be
wrong, 25% nobody could have said it* — which is a far more useful thing
to read than "that seat is 25% evil".

**"Their information might be wrong"** is a checkbox on each seat, beside
the read slider and deliberately separate from it. It multiplies the odds
that the seat was handed somebody else's token, and it moves their evil
odds *down* — a suspected Drunk is a good player being wrong, which
competes with them lying rather than adding to it. On the board above,
marking the seat takes "was never theirs" from 42% to 68% and their evil
reading from 25% to 14%.

What it deliberately does **not** do is tilt towards poisoning, and the
reason is that it cannot: being poisoned is not a property of a world, it
is part of the story the solver tells about one. What the marker can move
is the case that lives in the world itself.

### The Saint being executed while poisoned

Executing the Saint ends the game — **while the Saint is working**. A
poisoned or drunk Saint is executed and play carries on, so an execution
that killed somebody does not rule the Saint out; it says something had
to have stopped them.

This used to be a flat rejection, which is the wrong direction to be
wrong in: a Poisoner going for the Saint on exactly the day the town is
minded to execute them is a real play, and the solver was insisting it
never happened. On a nine-seat board it threw away 126 worlds and
reported the executed seat as **100% evil**. It now reads 79%, with
"Saint" at 21% — which leans hard, because that Poisoner had to be lucky,
without claiming to have proved anything.

### The Mayor's kill going somewhere else

The Demon attacks the Mayor and the Storyteller may send it elsewhere.
Only one half of that needs modelling, and working out which took a
moment.

Bouncing onto a **living** player is invisible. "The Demon attacked the
Mayor and it landed on Cara" and "the Demon attacked Cara" leave exactly
the same board, and the solver never tracked who was aimed at in the
first place — only who fell. Nothing to add.

Bouncing into **somebody already dead** is a different thing entirely: a
night where the Demon fired and nobody fell. So the shield is offered
only when there is a corpse to bounce into, and it is marked *aimed*,
because the Storyteller chooses whether to move the kill — a Mayor that
died at night proves nothing about whether it was working.

It shows up as a real deduction. A quiet night after somebody has already
died costs **nothing** to explain with a real Mayor, against the sunk-kill
penalty without one — so that quiet night is evidence the Mayor is who
they say, and the seat goes to 77%.

### What "no Outsiders in play" actually means

The Librarian can be told **nobody**, and it is tempting to read that as
a claim about the bag. It is not: it is a claim about what the
Storyteller *showed*. A Recluse registers as a Minion or the Demon
whenever the Storyteller likes, so a Librarian can honestly be told
nobody with a Recluse sitting right there.

The first version checked the true team and threw those worlds away. At
eight players — the size that wants exactly one Outsider — that removed
126 perfectly ordinary worlds, and ruling out a game that happens is the
wrong direction to be wrong in. It now asks whether every Outsider in
play *could have shown as something else*: a Recluse can, and the Butler,
the Drunk and the Saint cannot.

### When nothing fits

**The claims are asked about first**, because they are a common cause and
one the entry-by-entry search below cannot see. Twelve seats all claiming
Townsfolk, when every bag for that table needs two Outsiders and only the
Drunk can sit behind a Townsfolk claim — removing a reading will never fix
that, so the shortlist comes back empty and says nothing useful.

The count has to be of Outsiders who could be there *at the same time*.
Every Townsfolk claim could individually be hiding the Drunk; only one of
them actually can, and counting them one at a time made this never fire.

A bag that cannot be filled is also exactly what an Atheist game looks
like, so on a script with one, both get said rather than the first
crowding out the second.

A board that survives no world used to say so and stop. It now tries
removing one entry at a time and reports which removals let a world
through, because that is where to look first.

- **One culprit** usually means a mis-entered reading, or somebody lying.
  In testing, a Virgin trigger naming a seat that had claimed Slayer came
  back as the single named entry.
- **No culprit at all** is the interesting case: removing any one entry
  still leaves nothing, so two things disagree rather than one being
  wrong. Only here, and only on a script containing one, does the Atheist
  get mentioned — as a possibility, not a diagnosis, since boards are
  contradictory in ordinary ways too.
- **An unfinished search** says so rather than presenting an empty
  shortlist as though it meant something.

Two messages worth knowing:

- **"No world fits."** A good player is lying, an entry is wrong, or a
  rule isn't modelled yet. Tick *Good players may lie* and try again.
- **A tilde and a ± beside the numbers.** The search was too big to walk
  in full, so it was sampled instead. See below.

---

### The shape of it, in four ideas

**1. A world is one complete role assignment.** Seat 1 = Washerwoman,
seat 2 = Imp, and so on. Every world that satisfies the bag: the right
count per team, whatever the setup-changing characters did, each
character used at most once. Somebody handed the wrong token — the Drunk,
the Marionette, the Lunatic — is the awkward case, because they consume
their own slot *and* the token they think they hold.

**2. Claims cut the search brutally.** Somebody claiming Empath is, in any
legal world, really the Empath, a believer holding the Empath token, or
evil and bluffing. That is a handful of options instead of the whole
script, and it is the only reason fifteen seats is tractable at all.
Without claims it explodes — which is not a bug but the truth: with no
claims you genuinely know nothing.

**3. Information constrains a world only when its source really holds
that character and was working.** Evil bluffs, so nothing they say
constrains anything. A believer answers honestly about a character they
do not have, so their reading is unchecked. Only a genuine, unimpaired
source has to have told the truth. Misregistration — a Recluse reading
evil, a Spy reading good — is handled inside each check.

**4. Nothing that is hidden gets enumerated.** Who was impaired, who the
red herring was, who caught the star when the Demon fell, what killed
each body: none of it is searched over up front. Each is posited only
when something on the board would otherwise be false, and priced by how
lucky it had to be. That is what keeps the search the size of the world
list rather than the world list times every hidden choice.

---

## Part 6 – Working in code instead

`example_game.py` does the same job without a browser. Seats are indexed
`0` to `n-1` in seating order, and role names are written without spaces
(`FortuneTeller`, `ScarletWoman`).

```python
state = GameState(
    n_players=12,
    names=["Ada", "Ben", ...],
    claims={0: "Washerwoman", 1: "Recluse", ...},
    deaths={4: "N2", 7: "D2"},                      # N = night, D = execution
    infos=[
        Washerwoman(night=1, player=0, a=3, b=5, role="Chef"),
        Librarian(night=1, player=1, a=None, b=None, role=""),  # "no Outsiders"
        Empath(night=1, player=4, count=1),
        Empath(night=2, player=4, count=2),
        FortuneTeller(night=1, player=5, a=0, b=6, yes=False),
        Undertaker(night=2, player=6, target=7, role="Imp"),
        Ravenkeeper(night=3, player=8, target=2, role="Spy"),
        SlayerShot(night=2, player=9, target=3, died=False),   # night = day number
    ],
)

all_worlds, valid = solve(state, allow_good_lies=False)
print_report(valid, state)
```

---

## Part 7 – Tests

```bash
python run_tests.py              # everything, about five minutes
python run_tests.py -v           # one line per test
python run_tests.py wakes        # only tests/test_wakes.py
python run_tests.py -k virgin    # only tests mentioning "virgin"
```

821 tests, standard library only, nothing to install. The runner prints
which files ate the time; `test_sampling` is the slow one, because
statistical claims need repeated runs to hold down.

| File | What it holds down |
|---|---|
| `tests/test_worlds.py` | Every world is a legal game: team counts, the Baron's mandatory two extra Outsiders, no token used twice, the Drunk consuming a Townsfolk. And that claims and certainty settings prune the way they promise. |
| `tests/test_info.py` | Each information type checked against hand-built worlds. Misregistration, the Chef wrapping around the circle, the Empath looking past the dead, the red herring, both outcomes of a Slayer shot and a Virgin nomination. |
| `tests/test_constraints.py` | What kills a world outright and what it costs to save one: poison accounting, the Demon killing once a night, a sober Soldier surviving, an executed Saint, a starpass needing a Minion. |
| `tests/test_weights.py` | The priors. Direction and monotonicity rather than exact figures — plus a table that sets every constant to a neutral value and insists the answer moves, so a prior that quietly stops being applied fails loudly. |
| `tests/test_wakes.py` | The wake table, including the forgiving cases: the Monk accepting a loose "every night", the Ravenkeeper honestly saying "never". |
| `tests/test_api.py` | The browser seam: payload round-trips, validation messages, and the response shape. |
| `tests/test_golden.py` | Seven fixed scenarios with recorded world counts and percentages. |
| `tests/test_oracle.py` | Games dealt at random and played out — including starpasses, Scarlet Woman takeovers and chains of both — checked against the truth. |
| `tests/test_sampling.py` | The sampler: unbiased counts, agreement with the exact answer where both fit, and margins that actually cover the error. |
| `tests/test_seams.py` | The three structural seams — phase-aware lookup, the ability predicate, and the bag as data. |
| `tests/test_transitions.py` | Registering a character the package has never heard of, and following it through to the arithmetic and the report. |
| `tests/test_sensitivity.py` | The guesswork bands, and the per-row trust setting that replaces the biggest guess. |
| `tests/test_limits.py` | What the solver refuses, what it merely flags, and the shortlist when a board fits nothing. |
| `tests/test_scripts.py` | The catalogue, scripts as selections, reading a real script file, and portable saves. |
| `tests/test_impairment.py` | Drunk and poisoned as one thing, and registering a source the solver has never heard of. |
| `tests/test_bmr.py` | All twenty-five Bad Moon Rising characters, one group at a time, on lineups chosen rather than convenient. |
| `tests/test_random_scripts.py` | Scripts nobody has played, built at random from everything known, and the things that have to hold on all of them. |
| `tests/test_conformance.py` | The corpus a second implementation will be held to, and the reference held to it meanwhile. |
| `tests/test_js_data.py` | The JavaScript data layer held against the Python one, field for field. Skipped without Node. |
| `tests/test_js_worlds.py` | The JavaScript enumeration held against the Python one, digested world set by world set. |
| `tests/test_js_info.py` | Every reading run against every world of a board, and the answers digested. |
| `tests/test_js_rules.py` | The impairment plan and the night accounting, against rules made up for the purpose. |
| `tests/test_js_characters.py` | All thirty-two character rules, asked about every world of twenty boards. |
| `tests/test_js_solve.py` | The whole JavaScript solver against the corpus, percentage by percentage. |
| `tests/test_js_sampling.py` | The JavaScript sampler: does it converge, and are its margins honest. |
| `tests/test_js_diagnose.py` | What the two say when a board fits nothing, and which scripts they refuse. |
| `tests/test_js_sensitivity.py` | The guesswork check: do both find the same load-bearing guess. |
| `tests/test_site.py` | The built folder: does it boot, solve, and ask nobody for anything. |
| `tests/test_ledger.py` | What the ledger actually draws around each night and day. |
| `tests/test_inspector.py` | The seat panel's checkboxes, clicked and clicked away from. |
| `tests/test_audit.py` | Does every reading the page offers actually do something. |
| `tests/test_runner.py` | The runner itself: a typo must not come back green. |
| `tests/test_round_trip.py` | A saved game, reopened: does anything go missing. |
| `tests/test_page_offline.py` | The page booting and solving with nothing behind it. |
| `tests/test_installable.py` | The manifest, the icons and the service worker, against what exists. |
| `tests/test_deaths.py` | Who inherits the Demon, how the lineage is searched, what an execution proves, what a quiet night proves, why the Mayor changes nothing, and coming back from the dead. |

### Random scripts

Every other file says what one character does. `test_random_scripts.py`
says what the machinery has to do *whatever* characters it is handed: it
builds scripts of the usual shape out of everything in the catalogue —
thirteen Townsfolk, four Outsiders, four Minions, two Demons — deals
boards on them and walks several thousand worlds looking for something
that does not hold.

The point is combinations. The two published scripts are two selections
out of an enormous number, and each only ever tests its own characters
against its own neighbours. A Tea Lady has never sat beside a Recluse; a
Goon has never been drunked by a Poisoner; a Pukka has never had to
explain a body next to a Soldier. Those pairings are where a rule that
quietly assumes its own script goes wrong.

Nothing there checks that an answer is *right* — that is the oracle's job
and the per-character files'. It checks that the machinery stays
coherent: every world a legal game, every rule returning seats that exist
and costs between nothing and one, every seat's role shares adding to a
hundred, every board's Demon odds adding to exactly one Demon, and every
fact recorded narrowing the world set rather than widening it.

A wider run of the same properties — a hundred random scripts, seventy
thousand worlds, plus a second sweep of four hundred deliberately awkward
boards with resurrections, double deaths and executions somebody walked
away from — turned up one further thing: a percentage reported as
`100.00000000000001`. Adding a few thousand floats and dividing lands
there often enough to matter, and a figure over a hundred is the sort of
thing somebody reasonably stops trusting the rest of the answer over. The
shares are clamped now.

It found a real bug on its first run. **A seat claiming to be the Drunk
was dealt a Drunk with no token behind it** — the confirmed-certainty
branch expanded believers into their tokens and the ordinary
Outsider-claim branch did not. Claiming to be the Drunk is a legal, if
odd, thing to say, and every world where somebody did was malformed:
a seat holding a character that consumes a Townsfolk token, consuming
nothing.

Two of the tests guard the guards. One checks that most generated boards
are actually games, because a generator producing unsolvable boards would
make every property above pass vacuously. The other checks that the
random scripts really do reach every character that has a rule — a sweep
that never puts a Pukka on a script proves nothing about the Pukka, and
would say so in silence.

### The oracle

`tests/simulate.py` deals a legal game, plays it out night by night, and
works out what each character honestly learned — re-deriving it from the
seating and the roles rather than calling the solver, so a shared
misreading of a rule cannot hide in both. Hand that to the solver and the
world that actually happened must still be standing at the end. A solver
that throws away the truth is wrong, and no tuning discussion changes it.

This found two real bugs the fixed scenarios missed completely:

- **The Empath was reading past the wrong people.** In Trouble Brewing
  the Demon kills before the Empath wakes, so tonight's victim is already
  gone. The solver still counted them as a neighbour, so any honest
  Empath reading on a night somebody died looked like a contradiction.
- **A relayed Empath reading counted the wrong seat's neighbours.** When
  somebody else announces the Empath's number, the count belongs to the
  Empath's seat. The solver used the speaker's.

Both are now regression tests in `test_oracle.py`. The golden suite stayed
green through both, which is the argument for having an oracle at all.

The oracle also checks the solver is *useful*, not merely correct — a
solver that keeps every world is sound and worthless. Across dealt games
the real Demon comes top of the suspect list about a quarter of the time
against a one-in-ten baseline, and lands in the top three three-quarters
of the time.

Two things worth knowing about how these are written.

**The golden numbers are anchors, not truths.** They came out of the code
itself, so they cannot tell you the solver is right — only that it has
stopped agreeing with the version that was reviewed. Each one is paired
with a plain-language assertion about what the scenario *means* (a
triggered Virgin is certain, a landed shot clears the shooter), so when a
figure moves you can tell a tuning decision from a broken rule.

**The suite was checked by breaking things on purpose.** Removing the
executed-Saint rule, disconnecting the social read, and dropping the
display-name mapping produced nine failures across four files, each
pointing at the thing that was actually broken. Putting the two Empath
bugs back produced three more, from the oracle. A test suite nobody has
tried to fool is just a green light.

---

## Part 8 – The seams, and why they are there

Three pieces of the solver are shaped for work that has not been done yet.
None of them changes an answer today, and each is a place where the next
script — or the next character that rewrites somebody mid-game — plugs in
instead of forcing a rewrite.

**Every question about a character carries a phase.** `role_at`,
`find_at`, `demon_at` and `team_at` on a `World` all take one and, for
now, ignore it: a world is a single starting assignment, so the answer is
the same all game. They exist so that a check which depends on *when* it
is asking says so. Asking `roles[seat]` directly is still right for
questions about the whole game — who claimed what, who is lying — and
wrong for anything a handover moves. The Demon is found by team rather
than by name, so a script whose Demon is not the Imp needs no change here.

**Knowing what you are is a different question from being good.** Three
places used to ask whether a seat was evil when what they meant was
whether its holder could be relied on to know their own character. In
Trouble Brewing the two never come apart, because the Drunk is the only
character handed the wrong token and it is good. The Marionette is evil
and equally in the dark, and it made the confusion visible: it was being
dealt with no token at all, freed from its own wake claim the way a
knowing bluffer is, and scored as a liar for naming the token it
sincerely believes. `knows_what_it_is` is now the predicate, and
`believed_tokens` says which tokens a character could have been handed —
the Drunk always a Townsfolk, the Marionette either kind of good
character.

**Whether an ability is working is three-valued, not a boolean.**
`ability_state` returns GENUINE, ARBITRARY or ABSENT. The distinction that
matters is the middle one: the Drunk is *running*, woken on their token's
schedule and handed a plausible answer, so there is nothing to check
against — which is a different thing from not being that character at all,
and only the second means somebody invented the information. A fourth
value, INVERTED, is defined and unused: Vortox makes Townsfolk information
actively false, and "guaranteed wrong" cuts the world set differently from
"not necessarily true". Poison is deliberately not decided here, since the
solver only posits a poisoning once a statement has turned out false.

**The bag is data.** `SETUP_MODIFIERS` maps a character to the ways it
shifts the distribution, and the search runs once per possible bag. The
Baron has exactly one shift, so Trouble Brewing gets two bags. Adding a
Godfather — plus or minus one Outsider — grows the search on its own, and
the combination that would need a fifth Outsider is dropped because there
isn't one. A character is in the bag if and only if its shift was applied,
so the two facts stay welded together in general and not just for the
Baron.

---

## Part 9 – Writing it again in JavaScript

**Done, and cut over.** The page imports `js/api.mjs` and calls it
directly; there is no `fetch` left in the grimoire except the one for the
guesswork check. What follows is how it was built and what it caught.

The solver is Python, and a phone will not run Python. Today the phone
borrows a laptop's, which works and means somebody has to keep a laptop
awake through the game. The way out is a second implementation that runs
in the browser itself.

**The contract is the corpus, not the code.** A port that is
ninety-eight percent right is worse than no port, because it looks like
it works and misleads somebody mid-game. So
`tests/fixtures/conformance.json` holds 92 boards paired with the answers
this solver gives, and both implementations are held to it. Python is the
reference; JavaScript has to agree.

The corpus covers both published scripts and a dozen custom ones, every
kind of reading, every kind of thing that can happen to a seat, the
Sentinel, and the awkward answers as well as the ordinary — boards that
fit nothing, and boards the solver refuses outright. `test_conformance.py`
checks the corpus is worth having (nothing sampled, since a random walk
could never be reproduced; every reading represented) and then holds
Python to it, so the reference cannot drift while the port is being
written.

    python tests/make_fixtures.py     # regenerate, then read the diff

Regenerating is deliberately a separate step. A change to the solver that
moves the corpus should be read as a diff, which is the moment to notice
you changed more than you meant to.

**The seam is already there.** The page talks to the solver over one
JSON call — a board goes in, an answer comes out — so a JavaScript solver
only has to offer the same function and the page need not change. The
shape of both is exactly what the corpus records.

**What to port, roughly in order.** `catalogue`, `scripts` and `roles`
first — done, see below. Then `worlds`, the enumeration — also done. `info`, `impairment`, `deaths` and `waking` are the
per-character rules, each small and independent. `solver` is the scoring
and the reporting, and is the largest piece.

### The data layer, and what is generated rather than written twice

The catalogue is fifty-six characters with a dozen fields each.
Transcribing that into a second language by hand is a way of introducing
mistakes rather than a way of porting — so `js/characters.mjs` is
**generated** from the Python catalogue by `tools/gen_characters.py`, and
only the logic is written twice.

That leaves `js/catalogue.mjs`, `js/scripts.mjs` and `js/roles.mjs` as the
part worth checking: the lookups, the derived facts, and the way a script
is built out of a selection. `js/dump_data.mjs` prints everything those
three derive, and `test_js_data.py` computes the same things in Python and
insists they match — every character field for field, every script's
lists and modifiers, the name lookups, misregistration, the wake table,
and a real script file read from JSON.

One guard is there because the rest would pass without it: if the
catalogue changes and nobody regenerates, every comparison above still
agrees — on stale data. So a test regenerates the file and fails if the
result differs from what is checked in.

### The enumeration, and why counting is not enough

`js/worlds.mjs` is the second half: candidate lists, the bag, the
backtracking search, and a timeline laid over a world.

Two implementations can produce **the same number of worlds and disagree
about which ones**, and that is the mistake that survives into a game and
misleads somebody. So `test_js_worlds.py` digests each board over its
whole sorted world set — every seat's character and every believer's
token — and the digests have to match. Altering one world out of 154,440
moves the digest while leaving the count alone, which is the property
worth having.

Thirty-five boards are compared: both scripts from five to fifteen seats,
Outsider claims, an openly evil claim, unclaimed seats, all four
certainty settings, good lies allowed, all five wake claims, characters
pinned by a watched event, the Sentinel both asked for and not, and two
custom scripts. Plus the bag shapes at every size, the candidate lists a
claim produces, and a Scarlet Woman inheriting the star.

It found a latent trap on the Python side straight away. An **empty**
claim reached the bottom of the candidate function and raised "  is not
on Trouble Brewing" — a confusing way to say "this seat said nothing".
The server never sends an empty claim, so nothing had ever hit it. An
empty claim is now no claim, on both sides.

### The readings, and boards that can tell one answer from another

`js/state.mjs` is what a board records and how to ask it about a moment;
`js/info.mjs` is every kind of reading and what makes each one true.

A reading is a function of a world and a board, so checking it against
*one* world proves close to nothing — a wrong implementation agrees with
a right one most of the time. So each reading is run against every world
of a board and digested over the whole sequence of trues and falses.
Twenty-nine readings agreed world for world on the first run.

What did not pass first time was the check on whether those cases are
worth anything. A reading that is true in every world, or false in every
world, matches trivially and tells the two implementations apart from
nothing — and ten of the twenty-nine were like that, mostly because the
*board* was wrong rather than the reading:

- A Virgin trigger was being checked on a table where nobody claimed
  Virgin, so it was false in all 630 worlds. On a table with a Virgin
  claim it is true in 7,616 of 15,120.
- The same for a Slayer shot.
- The red herring was inside the pair the Fortune Teller asked about,
  which forces the answer on its own. Moved outside it.
- "No Outsiders in play" was being checked at nine players, where the bag
  always wants two — impossible whatever anybody claims. Seven players is
  the only size that wants none. Even then it was true in every world
  until two seats claimed Outsiders, because a Baron's bag wants two and
  seven Townsfolk claims cannot fill it. It now separates 6 worlds
  from 106.

Five are still constant, and those are constant *by design* — a Courtier
naming a character constrains nothing, an Undertaker learns nothing from
an execution nobody died of. That they are constant is the thing being
checked.

`js/waking.mjs` came along with it, because the Chambermaid needs it and
leaving one reading throwing would have meant the layer was not really
finished. It is who *actually* woke for their own ability — a different
question from the wake table, which records what somebody could honestly
claim. Every conditional waker is compared on a board that makes its rule
bite: a Ravenkeeper only on the night it dies, a Courtier only until it
has spent, a Professor only until it has raised somebody, a Drunk on the
schedule of the token it holds rather than its own.

That check needed the same care as the readings. Five of the fourteen
cases first came back as "no such world" — a good character nobody claims
cannot be in any world, so the comparison was between two pieces of
nothing. Each case now carries claims that leave room for the character
it is testing, and a test fails if any of them stops having a world.

### The registries, tested with rules that do not exist

`js/impairment.mjs` and `js/deaths.mjs` are the two registries: who was
not working and what could have stopped them, and what killed somebody
rather than merely that they died.

The awkward part is that the *character* rules live in the solver, which
is the next phase — so at this point both registries are empty and there
is nothing to compare. What can be compared is the machinery they feed:
the impairment plan, which finds the cheapest arrangement of sources that
impairs exactly who a world needs, and the night accounting, which works
out how a night's deaths could have come about.

So both implementations register the **same made-up rules**: a poisoner
that reaches the living, a soldier that cannot be demon-killed, a monk
that guards somebody else, a gossip that need not fire, an assassin
nothing stops, and a grandmother whose grandchild drags her along. Made
up, but shaped exactly like the real ones, and between them they reach
every branch — capacity, per-seat pricing, repeats, free and unavoidable
sources, aimed against always-on shields, must-fire causes, implied
deaths, and a kill no shield touches.

Eighteen plans and thirteen nights, all agreeing. Five of the plans have
**no arrangement at all**, and a test insists on that: half the value is
in the ones that cannot be made, and a version that never returned
nothing would otherwise pass. Two of the nights have no account either —
two causes cannot leave three bodies.

Registering into the real registries would leave them dirty for every
test that ran afterwards, so the Python side swaps them out and puts them
back.

### The characters themselves

`js/characters.rules.mjs` holds all thirty-two rules that go into those
registries — eleven causes, eight shields, one implication, seven
impairment sources and four ways of walking away from your own execution.

Thirty-two small functions is too many to spot-check, so instead twenty
boards are walked world by world and night by night, and everything the
rules say — which causes were offered, which shields, which sources, what
each reaches and what it costs — is folded into one digest per board. A
digest matches only if the two agreed about every rule in every world.
Beside it sits a per-rule tally, because a digest says *that* something
differs and never *what*.

That tally earned itself immediately. Two Trouble Brewing boards came back
with Python offering 1,930 more shields than JavaScript, evenly across
every seat — which is the shape of one rule firing on a night the other
skipped. **The Monk had no night check.** It wakes every night but the
first, exactly like the Innkeeper and the Exorcist beside it, and both of
those said so while the Monk did not. Nothing ever turned on it, because
no cause fires on night one either, so the shield was never asked for —
and the conformance corpus is unchanged by the fix, which is the proof
that it was unreachable rather than merely rare.

### The scoring, and the whole thing against the corpus

`js/scoring.mjs` and `js/report.mjs` are the rest: explanation cost, the
impairment plan, the night accounts, demon lineages, the priors, and the
per-seat picture.

`test_js_solve.py` runs all ninety-two corpus boards through the
JavaScript solver end to end and holds every percentage to four figures.
**Eighty-seven of the ninety-two agreed on the first run.** Four of the
rest are boards Python refuses for *input* reasons — two seats executed
on one day, a night marked quiet with somebody dying in it — which is
server validation rather than solving, and is named in a test rather than
skipped so the gap stays visible.

The last one was a difference of eight thousand worlds on a twelve-seat
board, and it was my harness: the server passes its own ceiling rather
than the library default, so JavaScript was walking forty thousand worlds
against Python's forty-nine thousand. Comparing an exact answer against a
truncated one.

**Then the blame shares disagreed, and that one was real.** The server was
recomputing "what killed each body" from `result["samples"]` — the eight
*most plausible* worlds. That is not a sample of anything: it is the top
of the ranking, and the top of the ranking agrees with itself. On a board
where two bodies fell in one night it reported the Demon at 94% and never
mentioned the Gossip at all, where weighing every one of the ten thousand
surviving worlds gives Demon 76%, Gossip 19%, Assassin 5%. The solve
already computes it properly and the server was throwing that away.

### Making it installable

A manifest, three icons and a service worker. None of them affect a
single number, which is exactly why they rot: rename a solver module and
the offline copy becomes half an application with no way to tell. So
`test_installable.py` is mostly about drift — the worker's list of files
against the files on disk, the manifest's icons against the icons that
exist, the page against both. Adding a module and not listing it fails
the suite, which I checked by adding one.

The icons are **drawn by `tools/make_icons.py`** rather than checked in
as opaque bytes: a clock face in the grimoire's own palette, so the next
person can change the colour without a graphics editor. Two things came
out of looking at the first attempt rather than trusting it — the hands
were the same width and at midnight both point straight up, so they read
as one hand, and the background gradient had a dozen steps and showed as
rings.

**What this does not do is make it work offline over your wifi**, and the
reason is not fixable from here: a browser only registers a service
worker on a secure origin, and a LAN address over plain http is not one.
The registration is attempted and allowed to fail quietly, because the
browser's own answer is the accurate one and there is nothing worth
interrupting anybody over. Offline needs https.

### Cutting the page over

The page had always talked to the solver over one JSON call, which is
what made the swap possible without touching the grimoire. `js/api.mjs`
answers the same three shapes `app.py` did — the catalogue, a script, a
solve — including the input validation, so a board with two executions on
one day is refused the same way and with the same words.

`test_page_offline.py` pulls the module script straight out of
`ui/index.html`, gives it just enough DOM to get through boot, makes every
`fetch` fail while counting the attempts, and then solves a board. It is
not a substitute for opening the page — a stub DOM proves nothing about
layout — but it proves the three things that broke during the cutover and
that no test of the solver would have caught.

The sharpest was this: **`boot()` began running synchronously.** It used
to sit behind a `fetch`, which deferred it long enough for the rest of the
module to finish; with the answer arriving immediately it ran at once and
reached a `const` declared further down. The page died on load. The fetch
had been hiding it.

Two smaller things. The impairment sources were **registered in a
different order**, with the Poisoner second in Python and last in
JavaScript; registration order decides which arrangement a plan settles on
when two cost the same, so it is behaviour rather than a detail. And two
rules — the Godfather and the Courtier — were never reached by any board,
one because it sat past the world cap and one because it named a
character nobody held. Both now have a board aimed at them, and a test
insists every named cause and every named source fires somewhere.

**Measured before committing.** `spike/worlds_spike.mjs` is the
enumeration and nothing else, with the character data hardcoded — a day's
work to answer the question the whole port rests on. It counts the same
worlds as Python, exactly, on both scripts at nine, twelve and fifteen
seats.

| board | worlds | Python | Node | |
|---|---|---|---|---|
| Trouble Brewing, 15 | 154,440 | 2.05s | 0.85s | 2.4× |
| Bad Moon Rising, 12 | 427,680 | 3.57s | 2.02s | 1.8× |
| Bad Moon Rising, 15 | 9,087,936 | 70.0s | 34.3s | 2.0× |

**About twice as fast**, which settles it. The exact-solve ceiling is
40,000 worlds — above that the solver samples — and at these rates that
is 150 to 220ms of enumeration. A phone is perhaps a third to a half of
this machine, so call it 400ms for the worst exact solve. That is fine.

The spike also found a bug in itself worth recording, because it is the
kind of thing the corpus exists to catch. It first reported 535,392 worlds
for a fifteen-seat Bad Moon Rising board against Python's 9,087,936 — a
seventeenfold gap — because it had left out one candidate: a Lunatic
believes it is the Demon and therefore bluffs a good character, and being
an Outsider that is how an Outsider slot gets filled on a table where
every seat claims a Townsfolk. A port missing that would have looked
plausible and been wrong on every Bad Moon Rising board.

---

## Part 10 – Putting it on a phone for good

The app is static — the solver runs in the browser and `app.py` only
hands over files — so publishing it is arranging, not compiling.
`python tools/build_site.py` writes `docs/`, which GitHub Pages serves
straight from the main branch.

**Flat, with no subfolders**, which looks untidy and is the whole point:
GitHub's web uploader lets you choose *files* and not folders, and its
editor cannot create an empty folder either. One level means selecting
everything and uploading it, on any browser, with no command line.

Everything stays relative. A project site lives in a subdirectory, and an
absolute path would look at the domain root and find nothing.

**Why host at all, when the solver already runs on the device?** Because
a browser only registers a service worker on a secure origin — https or
localhost — and without one there is no offline copy. A laptop on your
wifi serves plain http at a LAN address, which is neither.

**What is not published:** nothing about your games. The host serves
files. Boards live in the phone's own storage and are never sent
anywhere.

---

## Part 11 – Where to take it next

Roughly in this order:

1. **Deaths as a constraint.** Right now deaths only feed "who is still
   alive". Much stronger: a night death means the Imp killed, so there
   was no Monk protection, the victim wasn't the Soldier, and the Imp was
   alive. No death at night means Monk, Soldier, or the Imp killed itself.
2. **Starpass.** When the Imp kills itself, a Minion becomes the Imp. That
   breaks the assumption that a world's roles are constant across the
   game — you'd model a world as a role *timeline* per night instead.
   This is the one genuinely hard piece.
3. **Nominations that didn't trigger.** A Virgin nominated by someone who
   *survived* is real information too — that nominator was not a sober
   Townsfolk — but the row only covers the trigger for now.
4. **More priors.** Weighting exists for good liars and for your reads.
   The same machinery could carry more: Storytellers rarely hand the
   Drunk token to a Virgin, bluffs follow patterns, and demons pick
   kills for reasons. Each is one more factor inside `world_weight`.
5. **Saving games.** Local storage holds one game at a time. Exporting to
   a file would let you keep a library of them.

## Files

Extract the folder and it is ready to run — nothing to move, nothing to
install, no build step.

```
botc-solver/
├── README.md              this file
├── app.py                 local web server: serves the page, runs the solver
├── example_game.py        the same thing without a browser, if you prefer code
├── run_tests.py           the test runner
│
├── ui/
│   ├── index.html         the grimoire itself: one file, no build step
│   ├── manifest.webmanifest  what a browser needs to install it
│   ├── sw.js              keeps a copy on the device
│   └── icons/             drawn by tools/make_icons.py
│
├── botc/                  the solver
│   ├── __init__.py
│   ├── catalogue.py       one record per character: team, when it wakes,
│   │                        how it misregisters, whether it takes a seat
│   ├── scripts.py         scripts, the built-in list, reading a script file
│   ├── roles.py           the standard bag, and the facts derived from
│   │                        the catalogue
│   ├── worlds.py          every legal role assignment, and the timeline
│   │                        laid over one
│   ├── info.py            the game state, and every kind of reading
│   ├── solver.py          scoring, reporting, and every character's rules
│   ├── impairment.py      who was not working, and what could have
│   │                        stopped them
│   ├── deaths.py          what killed somebody, of what kind, and what
│   │                        shields against it
│   ├── waking.py          who was actually woken on a night, as opposed
│   │                        to what they could claim
│   └── limits.py          characters the solver will not reason about
│
├── js/                    the JavaScript port, in progress
│   ├── characters.mjs     generated from the catalogue — do not hand-edit
│   ├── catalogue.mjs      character lookup
│   ├── scripts.mjs        scripts as selections
│   ├── roles.mjs          the facts derived from the catalogue
│   ├── phases.mjs         putting the moments of a game in order
│   ├── worlds.mjs         every legal assignment, and a timeline over one
│   ├── state.mjs          what a board records, and asking it about a moment
│   ├── info.mjs           every kind of reading
│   ├── waking.mjs         who woke for their own ability
│   ├── impairment.mjs     who was not working, and what stopped them
│   ├── deaths.mjs         what killed somebody, and what shields against it
│   ├── characters.rules.mjs  what each character does — 32 rules
│   ├── api.mjs            what the page calls — the old server contract
│   ├── scoring.mjs        what explaining a world costs
│   ├── report.mjs         weighing worlds into a picture of the table
│   ├── rng.mjs            a seeded generator, so sampling can be tested
│   ├── priors.mjs         the numbers that are judgement, in one place
│   ├── sensitivity.mjs    how much of the answer is guesswork
│   ├── diagnose.mjs       what would have to give when nothing fits
│   ├── limits.mjs         characters the solver refuses — generated
│   ├── dump_data.mjs      prints the data layer, for cross-checking
│   ├── dump_worlds.mjs    prints the enumeration, for cross-checking
│   ├── dump_info.mjs      prints the readings, for cross-checking
│   ├── dump_rules.mjs     prints the registry machinery, for cross-checking
│   ├── dump_characters.mjs   prints every rule's answers, for cross-checking
│   └── dump_solve.mjs     answers the corpus, for cross-checking
│
├── spike/worlds_spike.mjs  the enumeration timing spike
├── tools/gen_characters.py regenerates js/characters.mjs
├── tools/make_icons.py     draws the app icons
├── tools/gen_limits.py     regenerates js/limits.mjs
├── tools/build_site.py     assembles docs/ for a static host
│
├── docs/                  built by the above — what a host serves
│
└── tests/                 821 tests, standard library only
    ├── helpers.py         shared assertions and board builders
    ├── simulate.py        the oracle: deals games and plays them out
    ├── test_worlds.py     setup legality, claims, pruning
    ├── test_info.py       each kind of reading, on its own
    ├── test_constraints.py  poison, deaths, pinned events
    ├── test_weights.py    the priors: direction, monotonicity, wiring
    ├── test_wakes.py      the wake-pattern table
    ├── test_deaths.py     lineage, executions, quiet nights, resurrection
    ├── test_impairment.py drunk and poisoned as one thing
    ├── test_seams.py      phase-aware lookup, ability state, the bag as data
    ├── test_transitions.py  registering a character the package never knew
    ├── test_scripts.py    the catalogue, script files, portable saves
    ├── test_bmr.py        Bad Moon Rising, character by character
    ├── test_random_scripts.py  scripts nobody has played, built at random
    ├── test_conformance.py     the corpus a JavaScript port must match
    ├── make_fixtures.py        regenerates that corpus
    ├── fixtures/               92 boards with their answers
    ├── test_js_data.py         the JavaScript data layer, cross-checked
    ├── test_js_worlds.py       the JavaScript enumeration, cross-checked
    ├── test_js_info.py         the JavaScript readings, cross-checked
    ├── test_js_rules.py        the JavaScript registries, cross-checked
    ├── test_js_characters.py   the JavaScript character rules, cross-checked
    ├── test_js_solve.py        the whole JavaScript solver, cross-checked
    ├── test_js_sampling.py     the JavaScript sampler, checked by coverage
    ├── test_js_diagnose.py     the JavaScript diagnosis, cross-checked
    ├── test_js_sensitivity.py  the guesswork check, cross-checked
    ├── test_page_offline.py    the page, with no server running
    └── harness/page_boot.mjs   loads the page the way a browser would
    ├── test_limits.py     what is refused, and what a dead board says
    ├── test_sensitivity.py  the guesswork bands, and per-row trust
    ├── test_sampling.py   the sampler: unbiased, convergent, honest margins
    ├── test_golden.py     fixed boards with recorded answers
    ├── test_api.py        the HTTP layer
    └── test_oracle.py     dealt games checked against the truth
```

Two files carry most of the character work. `catalogue.py` says what each
character *is* — facts that do not depend on any script. `solver.py` holds
the rules that say what each one *does*, registered into the death,
impairment, shield and transition registries at import time. Adding a
character is usually an entry in the first and a rule in the second.
