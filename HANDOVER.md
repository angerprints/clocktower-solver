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
- **Barbier:** Ein Tausch wird nur erwogen, wenn ein gemeldeter Barbier gestorben ist. Ein versteckter Barbier ist Schuld des Dorfs. Der Solver verliert dort die wahre Welt mit Absicht (47 von 6.000 Partien Sects & Violets).
- **Ziel des Solvers:** den richtigen Spieler als Dämon benennen.
- **Pukka:** läuft nach dem Ablaufplan von Not_Quite_Vertical. Eine gestörte Pukka greift nicht an, ihr Gift ruht.
- Alle weiteren stehen in `ROADMAP.md` (Abschnitte „Regelabgleich“ und „Regelprüfung“).

## 4 · Aufbau in Kürze

- Zwei Solver für dieselben Regeln: Python in `botc/`, JavaScript in `js/`. **Jede Regeländerung in beiden.**
- `python3 tools/build_site.py` baut die Website nach `docs/`.
- `tests/fixtures/conformance.json` ist der Korpus (190 Bretter), auf dem Python und JavaScript übereinstimmen müssen. Neu schreiben mit `python3 tests/make_fixtures.py` (etwa 2,5 Minuten), immer nach einer Regeländerung.
- `tests/simulate.py` spielt ganze Partien. `tests/nightwalk.py` erzählt dieselbe Nacht ein zweites Mal, unabhängig. `tests/claims.py` macht aus einer Partie, was der Tisch sagt.
- Tests: `python3 run_tests.py` (alles, etwa 31 Minuten, 1.091 Tests), `python3 run_tests.py bmr` (ein Filter, Sekunden).

**Reihenfolge nach einer Regeländerung:** Python ändern, JavaScript spiegeln, Messlauf (`messung/sim5.py`), Tests dazu, Korpus neu, Website bauen, ganze Suite, Roadmap und Bericht, Commit und Push.

## 5 · Was am 03. und 04.10.2026 passiert ist

| Commit | Inhalt |
|---|---|
| 0a43516 | Regelprüfung Bad Moon Rising und Sects & Violets |
| de89cc0 | Simulator spielt überlebte Hinrichtung, Wiederbelebung, Mondkind nachts, Hexen-Tod; neun Solver-Fehler behoben |
| 605d1d4 | Simulator spielt Schläger, Meuchelmörder, Pate, Schwätzer; Regel „neue Instanz“; sechs Solver-Fehler behoben; Grenze der Erzählungen 96 → 400 |
| a560877 | Roadmap: Messung „Dämon gefunden“ |
| 2d75583 | Roadmap: Messung „stille Nächte“ und Berichtigung |
| danach | `messung/` und diese Datei |

Berichte im Projekt: `claude/regelpruefung-bmr-und-snv.md`, `claude/simulator-vier-dinge.md`, `claude/simulator-schlaeger-und-drei-kills.md`, `claude/messung-daemon-gefunden.md`, `claude/messung-stille-naechte.md`.

## 6 · Der Stand der Messungen

**Wahre Welt gehalten** (verwirft der Solver die Welt, die gespielt wurde?):

- Bad Moon Rising: 0 von 60.000 (4 bis 6 Nächte). Trouble Brewing und Oster-Skript: je 0 von 6.000.
- Sects & Violets: 49 von 6.000, alle mit Barbier-Tausch, 47 mit verstecktem Barbier.
- Mit eingetragenen stillen Nächten: 0 von 3.000 (Bad Moon Rising) und 0 von 3.000 (Trouble Brewing). Mehr ist dazu nicht gemessen.
- Simulator gegen Night-Walk, Bad Moon Rising mit Schläger: 0 von 52.565 Nächten.

**Dämon gefunden** (steht der wahre Dämon an der Spitze?), 400 Partien je Skript, 7 bis 10 Spieler, Stand nach vier Nächten, **nur offene Partien**:

| | offene Partien | vorn |
|---|---|---|
| Bad Moon Rising | 274 | 52 % |
| Shabaloth / Poe / Pukka / Zombuul | 41 / 63 / 81 / 89 | 61 / 57 / 62 / **36** % |
| Sects & Violets | 200 | 68 % |
| Fang Gu / Vigormortis / No Dashii / Vortox | 48 / 52 / 50 / 50 | 73 / 73 / 64 / 64 % |

Raten unter den Lebenden träfe zu 23 % und 30 %. Jede Zahl schwankt um 6 bis 7 Punkte.

**Stille Nächte:** Der Solver erklärt sie nur mit „das Ziel konnte nicht sterben“, gratis auf fünf Arten (Segler, Gastwirt, Narr, Teedame, Exorzist). In Wahrheit wurde beim Shabaloth in 85 % der Dämon selbst gestoppt. Eine Erklärung zu streichen ändert fast nichts, alle zu streichen schiebt den Glauben zum Poe und findet den Zombuul nicht öfter. Folgerung: Bepreisen hilft nicht beim Finden.

## 7 · Zwei Mängel im Messaufbau (nicht behoben)

1. **Der Simulator beendet eine Partie nicht, wenn Böse gewonnen hat.** Mit zwei Lebenden wird weitergespielt. Jede Messung über mehrere Nächte muss solche Partien herausfiltern (`alive > 2`).
2. **Stille Nächte werden dem Solver nirgends eingetragen.** `deal.record()` liefert Tode, Rückkehrer und Hinrichtungen, aber kein `quiet_nights`. Kein Test mit gespielten Partien prüft deshalb, was der Solver mit einer Nacht ohne Toten macht.

## 8 · Was Patrick noch entscheiden muss

Aus `claude/messung-stille-naechte.md`, Abschnitt 6. Er hat sich noch nicht geäußert.

| | Was | Empfehlung |
|---|---|---|
| A | Stille Nächte in Messläufe und Tests eintragen | ja, zuerst |
| B | Strenge Lesart für stille Nächte einbauen (gestörter Dämon als eigene Erklärung, zwei Erklärungen für zwei Shabaloth-Kills, das Ziel der Pukka schützt sich nicht selbst). Liegt als Variante `logic` in `messung/quiet.py`, nicht im Solver. | danach, erst nach einem großen Lauf |
| C | Stille Nächte bepreisen | nein |
| D | Dämon-Messung wiederholen, am letzten Morgen mit offener Partie statt nach festen vier Nächten | ja, zuerst |

Außerdem offen: **die Grenze 400** für die Erzählungen der Nächte (statt 96). Sie kostet bei langen Partien bis zum Doppelten an Rechenzeit, im Schnitt 17 %. Patrick hat sie noch nicht bestätigt. Im Browser ist die Rechenzeit nicht gemessen.

## 9 · Der nächste Schritt

Wenn Patrick A und D bestätigt:

1. In `tests/simulate.py` die Partie enden lassen, wenn Böse gewonnen hat, **oder** im Messaufbau filtern. Das Erste ändert alle gespielten Partien (benannte Seeds in `tests/make_fixtures.py` prüfen, `messung/find5.py`), das Zweite nichts.
2. `quiet_nights` und `days_done` aus der gespielten Partie ableiten und in `deal.record()` oder daneben anbieten. Dann `tests/test_simulator_plays.py` und die Messläufe damit laufen lassen.
3. `messung/dmeas.py` so umbauen, dass das Brett am letzten offenen Morgen ausgewertet wird (`deal.record(upto=…)`, Auskünfte und Abstimmungen bis dahin).
4. Neu messen, Bericht, Roadmap.

## 10 · Stolpersteine

- **Während die ganze Testsuite läuft, nichts am Code ändern.** JavaScript und Korpus werden zur Laufzeit gelesen.
- Ein Befehl läuft höchstens 10 Minuten. Lange Läufe mit `nohup … &` starten und später nachsehen.
- `pgrep -f` und `pkill -f` treffen die eigene Shell. Stattdessen `ps -eo pid,args | awk …`.
- Textersetzungen in Dateien immer mit Prüfung, dass die Stelle genau einmal vorkommt.
- Ein Seed benennt eine Partie nur, bis der Simulator etwas Neues lernt. Danach ergibt derselbe Seed eine andere Partie.
- `messung/tbhash.py` zeigt, ob eine Änderung am Simulator die Partien von Trouble Brewing, Oster-Skript und Sects & Violets unberührt lässt.
- Kein ungeschütztes `rm` mit Variablen.

## 11 · Probe: Ist der neue Chat wirklich am selben Punkt?

Der neue Chat führt diese fünf Befehle im Repo aus. Stimmen alle fünf, ist nichts verloren.

| Befehl | Muss ergeben |
|---|---|
| `git log --oneline -1` | den Commit „Messskripte, Rohdaten und Handover“ |
| `git status --short` | nichts |
| `python3 run_tests.py bmr` | 195 Tests, OK |
| `python3 messung/dana.py messung/daten/dm_bmr.jsonl kind offen` | erste Zeile: `n= 274 vorn  143 (  52%)` |
| `python3 messung/sim6.py BMR 60 4` | in jeder Zeile „verworfen wegen stiller Nacht 0“ |
