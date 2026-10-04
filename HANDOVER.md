# Handover: Clocktower-Solver, Stand 04.10.2026

Für einen neuen Chat, der genau hier weitermacht. Zuerst diese Datei lesen, dann `ROADMAP.md`.

## 1 · Wo alles liegt

| Was | Wo |
|---|---|
| Code, Tests, Website, Messskripte, Rohdaten | GitHub `angerprints/clocktower-solver`, Zweig `main` |
| Berichte für Patrick (deutsch) | Projekt „BOTC Addons and Companions“, Dokumente unter `claude/…` |
| Regelwerk des Spiels, Tisch-Entscheidungen | Projektdokument `claude/v3-1-bad-moon-rising-regelwerk.md` und `ROADMAP.md` |
| Roadmap | `ROADMAP.md` im Repo, Kopie im Projekt als `claude/solver-roadmap-neubewertung.md` |
| Messskripte und Rohdaten | `messung/` im Repo, erklärt in `messung/README.md` |

Der Arbeitsordner des alten Chats ist weg. Was dort lag und gebraucht wird, steht jetzt in `messung/`.

**Nur lesen:** Die Engine des Einzelspieler-Spiels unter `J:\dev\clocktower` gehört einem anderen Chat. Abweichungen gehen als Handover-Dokument dorthin, geändert wird von hier aus nichts.

## 2 · Wie Patrick arbeiten will

- Antworten auf Deutsch, in ganzen Sätzen, das Ergebnis zuerst.
- Schritt für Schritt, von null. Er hat keine eigene Entwicklungsumgebung. Wenn etwas bei ihm lokal laufen soll: Anleitung für Windows und für Mac.
- **Erst messen, dann ändern.** Entscheidungen gehören ihm. Fertiges wird gepackt und gepusht.
- Am Ende jeder Antwort der nächste Schritt.
- Commits als „Claude <noreply@anthropic.com>“, mit den beiden Zeilen `Co-Authored-By` und `Claude-Session`. Vor dem Push `git fetch origin main`.

## 3 · Tisch-Entscheidungen, die gelten

- **Eine Fähigkeit endet mit dem Tod ihres Trägers.** Wer wiederbelebt oder neu erschaffen wird, ist eine neue Instanz und wählt neu (03.10.2026). Höfling: Trunkenheit endet sofort, nach der Rückkehr neue Wahl, wieder drei Tage. Großmutter: neues Enkelkind.
- **Schläger:** Der Erste, der ihn wählt, ist sofort betrunken, also schlägt schon diese Wahl fehl. Ein Dämon, der ihn zuerst wählt, tötet in der Nacht niemanden mehr.
- **Barbier:** Ein Tausch wird nur erwogen, wenn ein gemeldeter Barbier gestorben ist. Ein versteckter Barbier ist Schuld des Dorfs. Der Solver verliert dort die wahre Welt mit Absicht (41 von 6.000 Partien Sects & Violets bei vier Nächten).
- **Ziel des Solvers:** den richtigen Spieler als Dämon benennen.
- **Stille Nächte (04.10.2026):** Nur die fehlende Erklärung „der Dämon selbst wurde gestoppt“ wird gebaut, keine Erklärung wird weggenommen und nichts bepreist. Die strenge Lesart ist zurückgestellt.
- **Grenze 400** für die Erzählungen der Nächte bleibt (04.10.2026).
- **Pukka:** läuft nach dem Ablaufplan von Not_Quite_Vertical. Eine gestörte Pukka greift nicht an, ihr Gift ruht.
- Alle weiteren stehen in `ROADMAP.md` (Abschnitte „Regelabgleich“ und „Regelprüfung“).

## 4 · Aufbau in Kürze

- Zwei Solver für dieselben Regeln: Python in `botc/`, JavaScript in `js/`. **Jede Regeländerung in beiden.**
- `python3 tools/build_site.py` baut die Website nach `docs/`.
- `tests/fixtures/conformance.json` ist der Korpus (190 Bretter), auf dem Python und JavaScript übereinstimmen müssen. Neu schreiben mit `python3 tests/make_fixtures.py` (etwa 2,5 Minuten), immer nach einer Regeländerung.
- `tests/simulate.py` spielt ganze Partien und hört auf, wenn Böse gewonnen hat. Dann steht in `deal.ended_at` der Moment (`N4`, `D3`, `E3`), in `deal.ended_why` der Grund (`two alive` oder `vortox`) und in `deal.game_ends_after` die letzte gespielte Nacht. Den Zusatztag des Strippenziehers liefert `deal.mastermind_day`. `deal.record()` gibt dem Solver Tode, Rückkehrer, Hinrichtungen und seit dem 04.10.2026 auch die stillen Nächte und die Tage, nach denen die Partie weiterging. `record(told=False)` lässt die beiden letzten weg. `tests/nightwalk.py` erzählt dieselbe Nacht ein zweites Mal, unabhängig. `tests/claims.py` macht aus einer Partie, was der Tisch sagt.
- Tests: `python3 run_tests.py` (alles, etwa 31 Minuten, 1.120 Tests, mit `1/2` und `2/2` in zwei Hälften nebeneinander etwa 22 Minuten), `python3 run_tests.py bmr` (ein Filter, Sekunden).

**Reihenfolge nach einer Regeländerung:** Python ändern, JavaScript spiegeln, Messlauf (`messung/sim5.py`), Tests dazu, Korpus neu, Website bauen, ganze Suite, Roadmap und Bericht, Commit und Push.

## 5 · Was am 03. und 04.10.2026 passiert ist

| Commit | Inhalt |
|---|---|
| 0a43516 | Regelprüfung Bad Moon Rising und Sects & Violets |
| de89cc0 | Simulator spielt überlebte Hinrichtung, Wiederbelebung, Mondkind nachts, Hexen-Tod; neun Solver-Fehler behoben |
| 605d1d4 | Simulator spielt Schläger, Meuchelmörder, Pate, Schwätzer; Regel „neue Instanz“; sechs Solver-Fehler behoben; Grenze der Erzählungen 96 → 400 |
| a560877 | Roadmap: Messung „Dämon gefunden“ |
| 2d75583 | Roadmap: Messung „stille Nächte“ und Berichtigung |
| ed5ea39 | `messung/` und diese Datei |
| cc2aa45 | Simulator beendet die Partie, wenn Böse gewonnen hat (zwei Lebende, oder ein Tag ohne Hinrichtung unter einem Vortox) |
| 34421be | ein Kommentar berichtigt |
| be39613 | Gespielte Partien tragen stille Nächte und Tage ohne Hinrichtung ein; `messung/dmorgen.py` |
| 91aae55 | Dämon-Messung am letzten offenen Morgen, Rohdaten, Roadmap, diese Datei |
| e2d215e | Solver: „der Dämon selbst wurde gestoppt“ als Erklärung für eine stille Nacht (Zombuul, Pukka, Shabaloth); ausgeschlossene Erzählungen fallen vor der Grenze 400 weg |
| danach | Solver schneller, ohne Einfluss auf das Ergebnis; Roadmap, diese Datei |

Berichte im Projekt: `claude/regelpruefung-bmr-und-snv.md`, `claude/simulator-vier-dinge.md`, `claude/simulator-schlaeger-und-drei-kills.md`, `claude/messung-daemon-gefunden.md`, `claude/messung-stille-naechte.md`, `claude/simulator-spielende.md`, `claude/stille-naechte-eingetragen-und-letzter-morgen.md`, `claude/stille-nacht-daemon-gestoppt.md`.

## 6 · Der Stand der Messungen

**Wahre Welt gehalten** (verwirft der Solver die Welt, die gespielt wurde?):

Stand vom 04.10.2026: Der Simulator beendet die Partie, wenn Böse gewonnen hat, und jede Partie trägt ihre stillen Nächte und Tage ein.

- Bad Moon Rising: 0 von 60.000 (4 bis 6 Nächte). Vor dem Einbau der Erklärung „der Dämon selbst wurde gestoppt“ waren es 83.
- Trouble Brewing und Oster-Skript: je 0 von 12.000 (4 und 6 Nächte).
- Sects & Violets: 43 von 6.000 (4 Nächte) und 72 von 6.000 (6 Nächte), alle mit Barbier-Tausch, 41 und 68 mit verstecktem Barbier.
- Simulator gegen Night-Walk: Bad Moon Rising 0 von 45.651 Nächten, Trouble Brewing 0 von 17.178. Sects & Violets 60 von 16.641, das war vorher schon so (61 von 18.000).

**Dämon gefunden** (steht der wahre Dämon an der Spitze?), 400 Partien je Skript, 7 bis 10 Spieler, **am letzten Morgen, an dem die Partie noch offen ist** (höchstens sechs Nächte), stille Nächte eingetragen:

| | Partien | vorn | unter den ersten drei |
|---|---|---|---|
| Bad Moon Rising | 400 | 54 % | 93 % |
| Pukka / Poe / Shabaloth / Zombuul | 105 / 102 / 103 / 90 | 65 / 58 / 58 / **34** % | 96 / 97 / 99 / 78 % |
| Sects & Violets | 400 | 65 % | 98 % |
| No Dashii / Vigormortis / Vortox / Fang Gu | 99 / 105 / 92 / 104 | 69 / 67 / 63 / 62 % | 98 / 100 / 98 / 97 % |

Raten unter den Lebenden träfe zu 28 % und 29 %. Ein ganzes Skript schwankt um etwa 5 Punkte, ein einzelner Dämon um etwa 10.

Diese Tabelle ist vom Mittag des 04.10., vor dem Einbau der neuen Erklärung. Danach neu gemessen ist nur Bad Moon Rising: 56 % vorn (222 statt 218 von 400), in 391 Partien derselbe Rang (`messung/daten/morgen/dm_bmr_weg1.jsonl`).

Der Zombuul ist nur schwach, solange er als tot gilt (3 von 44 vorn). Sichtbar am Leben steht er in 28 von 46 Partien vorn.

Die ältere Messung nach festen vier Nächten, nur offene Partien, ergab 52 % (274 Partien) und 68 % (200 Partien). Ihre Rohdaten liegen weiter in `messung/daten/`, Probe 4 unten rechnet sie nach.

**Stille Nächte:** Der Solver erklärt sie nur mit „das Ziel konnte nicht sterben“, gratis auf fünf Arten (Segler, Gastwirt, Narr, Teedame, Exorzist). In Wahrheit wurde beim Shabaloth in 85 % der Dämon selbst gestoppt. Eine Erklärung zu streichen ändert fast nichts, alle zu streichen schiebt den Glauben zum Poe und findet den Zombuul nicht öfter. Folgerung: Bepreisen hilft nicht beim Finden.

## 7 · Zwei Mängel im Messaufbau (beide behoben)

1. *Behoben am 04.10.2026:* Der Simulator beendete eine Partie nicht, wenn Böse gewonnen hatte. Jetzt endet sie bei zwei Lebenden und an einem Tag ohne Hinrichtung unter einem Vortox. Wer nur offene Partien messen will, fragt `deal.ended_at is None`.
2. *Behoben am 04.10.2026:* Stille Nächte wurden dem Solver nirgends eingetragen. Jetzt liefert `deal.record()` sie mit, zusammen mit den Tagen, nach denen die Partie weiterging.

## 8 · Was Patrick entschieden hat, und was noch offen ist

Aus `claude/messung-stille-naechte.md`, Abschnitt 6. Entschieden am 04.10.2026:

| | Was | Entscheidung |
|---|---|---|
| A | Stille Nächte in Messläufe und Tests eintragen | ja, zuerst |
| B | Strenge Lesart für stille Nächte einbauen (gestörter Dämon als eigene Erklärung, zwei Erklärungen für zwei Shabaloth-Kills, das Ziel der Pukka schützt sich nicht selbst). Liegt als Variante `logic` in `messung/quiet.py`, nicht im Solver. | erst nach einem großen Lauf |
| C | Stille Nächte bepreisen | nein |
| D | Dämon-Messung wiederholen, am letzten Morgen mit offener Partie statt nach festen vier Nächten | ja |
| | Simulator reparieren oder nur im Messaufbau filtern | reparieren (erledigt) |

Zu B entschieden am 04.10.2026: Weg 1, nur die fehlende Erklärung. Gebaut und gemessen, siehe Abschnitt 6. Die Grenze 400 ist bestätigt.

Zurzeit ist nichts zu entscheiden.

## 9 · Der nächste Schritt

A, D und B (Weg 1) sind erledigt (04.10.2026). Der nächste Fund aus der Messung ist der Zombuul, der als tot gilt: 3 von 44 vorn, sichtbar am Leben 28 von 46.

1. Zuerst messen, warum: An welcher Stelle steht er in diesen 44 Partien, und wer steht vor ihm? `messung/daten/morgen/dm_bmr_weg1.jsonl` hat je Partie die Dämon-Werte aller Sitze (`pcts`), den Sitz des Dämons (`demon`) und ob er auf dem Brett lebt (`demon_alive`).
2. Erst mit dem Befund entscheidet Patrick, ob und was gebaut wird.

## 10 · Stolpersteine

- **Während die ganze Testsuite läuft, nichts am Code ändern.** JavaScript und Korpus werden zur Laufzeit gelesen.
- Ein Befehl läuft höchstens 10 Minuten. Lange Läufe mit `nohup … &` starten und später nachsehen.
- `pgrep -f` und `pkill -f` treffen die eigene Shell. Stattdessen `ps -eo pid,args | awk …`.
- Textersetzungen in Dateien immer mit Prüfung, dass die Stelle genau einmal vorkommt.
- Ein Seed benennt eine Partie nur, bis der Simulator etwas Neues lernt. Danach ergibt derselbe Seed eine andere Partie.
- `messung/tbhash.py` zeigt, ob eine Änderung am Simulator die Partien von Trouble Brewing, Oster-Skript und Sects & Violets unberührt lässt.
- Kein ungeschütztes `rm` mit Variablen.
- Rechenzeit vor und nach einer Solver-Änderung vergleichen: `git worktree add ORDNER COMMIT`, dann in beiden Ständen `python3 messung/dmorgen.py BMR aus.jsonl 0 48` und die Spalte `t` summieren. Ein Prozess je Kern, sonst sind die Zeiten nicht vergleichbar.
- Wer wissen will, was eine Änderung am Simulator an den Partien ändert: das Repo ein zweites Mal klonen, dieselben Seeds mit beiden Ständen spielen und Partie für Partie vergleichen. So ist die Reparatur vom 04.10.2026 geprüft.
- Eine gespielte Partie kann kürzer sein als die verlangten Nächte. Schleifen über die Nächte hören bei `deal.game_ends_after` auf.

## 11 · Probe: Ist der neue Chat wirklich am selben Punkt?

Der neue Chat führt diese sechs Befehle im Repo aus. Stimmen alle sechs, ist nichts verloren.

| Befehl | Muss ergeben |
|---|---|
| `git log --oneline -1` | den Commit „Solver schneller, Ergebnis unverändert“ |
| `git status --short` | nichts |
| `python3 run_tests.py bmr` | 206 Tests, OK |
| `python3 messung/dana.py messung/daten/dm_bmr.jsonl kind offen` | erste Zeile: `n= 274 vorn  143 (  52%)` |
| `python3 messung/sim6.py BMR 60 4` | in jeder Zeile „verworfen wegen stiller Nacht 0“ |
| `python3 messung/dana.py messung/daten/morgen/dm_bmr.jsonl kind` | erste Zeile: `n= 400 vorn  218 (  54%)` |
