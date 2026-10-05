# Handover: Clocktower-Solver, Stand 05.10.2026

Für einen neuen Chat, der genau hier weitermacht. Zuerst diese Datei lesen, dann `ROADMAP.md`.

**Die nächste Aufgabe:** experimentelle Charaktere in den Solver bringen, einzeln und in Batches von fünf. Siehe Abschnitt 9.

## 1 · Wo alles liegt

| Was | Wo |
|---|---|
| Code, Tests, Website, Messskripte, Rohdaten | GitHub `angerprints/clocktower-solver`, Zweig `main` |
| Website | GitHub Pages aus `docs/`, angerprints.github.io/clocktower-solver |
| Berichte für Patrick (deutsch) | Projekt „BOTC Addons and Companions“, Dokumente unter `claude/…` |
| Roadmap | `ROADMAP.md` im Repo, Kopie im Projekt als `claude/solver-roadmap-neubewertung.md` |
| Offizielles deutsches Wording | Projektdokumente `claude/stilguide-deutsche-faehigkeiten.md` und `claude/deutsche-charaktertexte-referenz.md` |
| Messskripte und Rohdaten | `messung/` im Repo, erklärt in `messung/README.md` |
| Anleitung für eine echte Partie | `ANLEITUNG-ECHTE-PARTIE.md` |

**Nur lesen:** Die Engine des Einzelspieler-Spiels unter `J:\dev\clocktower` gehört einem anderen Chat. Abweichungen gehen als Handover-Dokument dorthin, geändert wird von hier aus nichts.

## 2 · Wie Patrick arbeiten will

- Antworten auf Deutsch, in ganzen Sätzen, das Ergebnis zuerst.
- Schritt für Schritt, von null. Er hat keine eigene Entwicklungsumgebung. Wenn etwas bei ihm lokal laufen soll: Anleitung für Windows und für Mac.
- **Erst messen, dann ändern.** Entscheidungen gehören ihm. Er antwortet meist kurz („Weg 1“), deshalb jede Entscheidung als benannte Wege anbieten, mit einer Empfehlung.
- Fertiges wird gepackt und gepusht.
- Am Ende jeder Antwort der nächste Schritt.
- **Das offizielle deutsche Wording der botc.app benutzen,** in Antworten, Berichten und der Roadmap. Es heißt Besessenheit (nicht Wahnsinn), Charakter (nicht Rolle), Bürger, Außenseiter, Scherge, Dämon, Erzähler, Fraktion. Namen wie in der Referenz: Liebchen, Grubenweib, Schlangenbeschwörer, Schneiderin, Marktschreier, Blumenmädchen, Poe, Schläger, Strippenzieher. Die Website selbst ist englisch und bleibt es.
- **Dieses Handover nicht nach jedem Schritt nachziehen.** Es wird nur geschrieben, wenn Patrick eines verlangt. Die Roadmap wird nach jedem Schritt nachgezogen, und ihre Kopie im Projekt auch.
- Commits als „Claude <noreply@anthropic.com>“, mit den beiden Zeilen `Co-Authored-By` und `Claude-Session`. Vor dem Push `git fetch origin main`.
- Zu jedem abgeschlossenen Schritt ein Bericht als Projektdokument `claude/<thema>.md`, kurz und mit Tabellen.

## 3 · Tisch-Entscheidungen, die gelten

- **Eine Fähigkeit endet mit dem Tod ihres Trägers.** Wer wiederbelebt oder neu erschaffen wird, ist eine neue Instanz und wählt neu (03.10.2026).
- **Schläger:** Der Erste, der ihn wählt, ist sofort betrunken, also schlägt schon diese Wahl fehl.
- **Barbier:** Ein Tausch wird nur erwogen, wenn ein gemeldeter Barbier gestorben ist. Ein versteckter Barbier ist Schuld des Dorfs, der Solver verliert dort die wahre Welt mit Absicht.
- **Ziel des Solvers:** den richtigen Spieler als Dämon benennen.
- **Stille Nächte:** Nichts wird bepreist (04.10.2026, am 05.10.2026 direkt gemessen und bestätigt). Die strenge Lesart ist zurückgestellt.
- **Grenze 400** für die Erzählungen der Nächte bleibt.
- **Zwei auf dem Brett, und die Partie läuft** (04.10.2026): Dann leben wirklich mindestens drei, der Dämon ist also ein Zombuul unter den Toten. Gilt nur, wenn ein Zombuul auf dem Skript steht. Die Website hat dafür den Haken „the game is over“.
- **Dämon-Typ auf der Website: nur Fakten** (05.10.2026). Der Kasten „Night pattern“ zählt die Nächte und nennt die Regel, ohne Prozentzahl und ohne Eingriff in den Solver.
- **Das Dorf im Simulator bleibt, wie es ist** (05.10.2026). Es richtet fast jeden Tag hin, das passt zu Patricks Tisch.
- **Pukka:** läuft nach dem Ablaufplan von Not_Quite_Vertical.
- Alle weiteren stehen in `ROADMAP.md`.

## 4 · Aufbau in Kürze

- Zwei Solver für dieselben Regeln: Python in `botc/`, JavaScript in `js/`. **Jede Regeländerung in beiden.**
- `python3 tools/build_site.py` baut die Website aus `ui/` und `js/` nach `docs/`.
- `tests/fixtures/conformance.json` ist der Korpus (194 Bretter), auf dem Python und JavaScript übereinstimmen müssen. Neu schreiben mit `python3 tests/make_fixtures.py` (etwa 3 Minuten), immer nach einer Regeländerung.
- `tests/simulate.py` spielt ganze Partien, `tests/claims.py` macht daraus, was der Tisch sagt, `tests/nightwalk.py` spielt jede Nacht unabhängig ein zweites Mal nach.
- Tests: `python3 run_tests.py` (alles, 1.149 Tests), mit `1/2` und `2/2` in zwei Hälften nebeneinander etwa 22 Minuten. `python3 run_tests.py bmr` läuft einen Filter in Sekunden.
- Die ganze Suite immer auf einer Kopie laufen lassen (`git ls-files` in einen Arbeitsordner kopieren), damit sich der Code nicht unter ihr ändert.

**Reihenfolge nach einer Regeländerung:** Python ändern, JavaScript spiegeln, Messlauf (`messung/sim5.py`), Tests dazu, Korpus neu, Website bauen, ganze Suite, Roadmap und Bericht, Commit und Push.

## 5 · Was am 04. und 05.10.2026 passiert ist

| Commit | Inhalt |
|---|---|
| cc2aa45 | Simulator beendet die Partie, wenn Böse gewonnen hat |
| be39613, 91aae55 | Gespielte Partien tragen stille Nächte ein; Dämon-Messung am letzten offenen Morgen |
| e2d215e, df17b6c | Solver: „der Dämon selbst wurde gestoppt“; Solver schneller |
| c139b3e | Messung: der Zombuul, der als tot gilt |
| 0ea4bc4 | Solver: zwei auf dem Brett und die Partie läuft, also leben wirklich drei |
| 11f36ad | Website: Haken „the game is over“ |
| e9f31ae | Messung: der Zombuul, der als tot gilt, bei drei oder mehr Lebenden |
| 01fb5d4 | Website: Kasten „Night pattern“; Messung des Dorfs im Simulator |
| 45cb34c | Roadmap: das Dorf bleibt, als Nächstes die experimentellen Charaktere |
| 6072a2e, 0bc515f | Night-Walk repariert (Sects & Violets 60 → 0 abweichende Nächte) |
| danach | Simulator ordnet die Nacht nach dem aktuellen Charakter; dieses Handover |

Berichte im Projekt aus diesen zwei Tagen: `claude/simulator-spielende.md`, `claude/stille-naechte-eingetragen-und-letzter-morgen.md`, `claude/stille-nacht-daemon-gestoppt.md`, `claude/messung-zombuul-gilt-als-tot.md`, `claude/zwei-auf-dem-brett-und-die-partie-laeuft.md`, `claude/messung-zombuul-tot-drei-lebende.md`, `claude/dorf-im-simulator-und-nachtmuster.md`, `claude/sv-simulator-gegen-night-walk.md`.

## 6 · Der Stand der Messungen

**Wahre Welt gehalten** (verwirft der Solver die Welt, die gespielt wurde?):

| Skript | verloren | Anmerkung |
|---|---|---|
| Bad Moon Rising | 0 von 60.000 | 4 bis 6 Nächte |
| Trouble Brewing, Oster-Skript | je 0 von 12.000 | 4 und 6 Nächte |
| Sects & Violets, 4 Nächte | 43 von 6.000 | 40 mit verstecktem Barbier (gewollt) |
| Sects & Violets, 6 Nächte | 69 von 6.000 | 64 mit verstecktem Barbier (gewollt) |

**Simulator gegen Night-Walk:** 0 Abweichungen auf allen vier Skripten (Sects & Violets 0 von 16.641 und 0 von 9.456 Nächten). Jede neue Abweichung ist also ein echter Hinweis.

**Dämon gefunden** (steht der wahre Dämon an der Spitze?), 400 Partien je Skript, am letzten Morgen, an dem die Partie noch offen ist:

| | vorn | unter den ersten drei |
|---|---|---|
| Bad Moon Rising | 228 von 400 (57 %) | 375 (94 %) |
| Pukka / Poe / Shabaloth / Zombuul | 70 von 105 / 59 von 102 / 60 von 103 / 39 von 90 | |
| Sects & Violets | 65 % | 98 % |

Die Zahl für Sects & Violets ist vom 04.10.2026. Seit der Reparatur der Nachtreihenfolge laufen etwa 5 % der Partien anders, sie ist nicht neu gemessen.

**Der Zombuul, der als tot gilt:** Zeigt das Brett zwei Lebende, steht er in 9 von 22 Partien vorn. Zeigt es drei oder mehr, in 0 von 22. Das ist eine bekannte Grenze (offene Stelle 33): Keine Regel fehlt, und ein Preis auf stille Nächte kostet über alle 400 Partien mehr, als er findet (218 bis 225 statt 228).

## 7 · Was offen ist

Die vollständige Liste steht in `ROADMAP.md` unter „Offene Stellen“. Für die nächsten Schritte wichtig:

| Nr. | Was |
|---|---|
| 14 | Experimentelle Charaktere, die nächste Aufgabe |
| 36 | Sects & Violets: Wer früh in der Nacht handelt und in derselben Nacht vom Grubenweib verwandelt wird, dessen Wahl verwirft der Solver. 1 von 6.000 Partien (Seed 1078). Gefunden, nicht gebaut. |
| — | Der Simulator spielt die Hinrichtung wegen Besessenheit (Cerenovus) nicht. |
| 33 | Zombuul, der als tot gilt, bei drei oder mehr Lebenden: bekannte Grenze |

Zurzeit ist nichts zu entscheiden außer dem ersten Batch.

## 8 · Die Roadmap ist ein Tagebuch

`ROADMAP.md` hat über 650 Zeilen. Der aktuelle Stand steht in den Abschnitten „Als Nächstes“ und „Offene Stellen“ am Ende. In älteren Abschnitten stehen noch englische oder abweichende Charakternamen (Sweetheart, Näherin, Pit-Hag). Sie sind nicht umgeschrieben. Neue Abschnitte benutzen die Namen der App.

## 9 · Die nächste Aufgabe: experimentelle Charaktere

Patricks Entscheidung vom 05.10.2026: **Die Charaktere kommen einzeln dazu, ohne ein zugehöriges Skript, in Batches von fünf.**

**Stand des Katalogs** (`botc/catalogue.py`, `js/catalogue.mjs`): 83 Charaktere.

| | Anzahl | Stand |
|---|---|---|
| Die drei Grundskripte | 72 | modelliert, nur der Künstler ist „aufgezeichnet“ |
| Weitere, modelliert | 8 | Akrobatin, Alsaahir, Ballonfahrer, Farmer, Marionette, Adlige, Oger, Wächter |
| Weitere, nicht modelliert | 3 | Atheist, Legion, Riot |
| Fehlen ganz | 56 | nach Zählung 24 Bürger, 10 Außenseiter, 14 Schergen, 8 Dämonen; vor dem ersten Batch gegen die App-Referenz prüfen |

**Vorschlag für den ersten Batch, nicht entschieden:** Gutsverwalter, Ritter, Shugenja, Dorftrottel, Nachtwächter. Alle fünf geben nur Information und ändern nichts am Ablauf der Nacht.

**Das Tor, durch das jeder Charakter muss** (aus `README.md` und `NEXT.md`, dort „standing gate“):

1. Solver in Python und in JavaScript.
2. Simulator: Er spielt den Charakter, auch betrunken und vergiftet.
3. Night-Walk: Er spielt die Nacht mit dem Charakter nach, 0 Abweichungen.
4. Vierzig gemischte Partien mit `tools/play_games.py`, kein unmögliches Brett.
5. Eintragbar auf der Website. Ein Prüftest vergleicht die Felder der Seite mit den Zeilen, die der Solver kennt.
6. Korpus neu, ganze Suite, Roadmap, Bericht, Commit und Push.

**So fängt der neue Chat an:**

1. Die sechs Proben aus Abschnitt 11 ausführen.
2. Die fehlenden Charaktere gegen `claude/deutsche-charaktertexte-referenz.md` auszählen und Patrick die Liste zeigen, nach Charaktertyp und mit einer Einschätzung, wie aufwendig jeder ist.
3. Patrick wählt die ersten fünf.
4. Für jeden der fünf zuerst die Regel aus dem offiziellen Wiki lesen und Patrick die Stellen zeigen, an denen eine Lesart zu wählen ist. Erst danach bauen.

## 10 · Stolpersteine

- **Während die ganze Testsuite läuft, nichts am Code ändern.** JavaScript und Korpus werden zur Laufzeit gelesen. Deshalb die Kopie aus Abschnitt 4.
- Ein Befehl läuft höchstens 10 Minuten. Lange Läufe mit `nohup … &` starten und später nachsehen.
- `pgrep -f` und `pkill -f` treffen die eigene Shell. Stattdessen `ps -eo pid,args | awk …`.
- Textersetzungen in Dateien immer mit Prüfung, dass die Stelle genau einmal vorkommt.
- Ein Seed benennt eine Partie nur, bis der Simulator etwas Neues lernt. Danach ergibt derselbe Seed eine andere Partie.
- `messung/tbhash.py` zeigt, ob eine Änderung am Simulator die Partien von Trouble Brewing, Oster-Skript und Sects & Violets unberührt lässt. Stand jetzt: `TB 8f3c25a3d4262fc9`, `EASTER 79c371afe11a183f`, `SV 9834d5c76e3efb60`.
- **„Am Ende der Nacht“ ist keine Antwort auf „in diesem Moment“.** Dreimal hat ein Stand vom Ende der Nacht einen früheren Platz verfälscht (Night-Walk, 05.10.2026). Und sechsmal wurde der ausgeteilte Charakter mit dem aktuellen verwechselt (`deal.roles[sitz]` statt `deal.role_at(sitz, phase)`).
- Der Solver rechnet in ganzen Nächten. Was innerhalb einer Nacht nacheinander passiert, sieht er nur dort, wo es eigens gebaut ist (offene Stellen 20 und 36).
- CSS-Klassen der Website vor dem Benutzen suchen: `.rule` war schon vergeben.
- Rechenzeit vor und nach einer Solver-Änderung vergleichen: `git worktree add ORDNER COMMIT`, dann in beiden Ständen `python3 messung/dmorgen.py BMR aus.jsonl 0 48` und die Spalte `t` summieren. Ein Prozess je Kern.
- Eine gespielte Partie kann kürzer sein als die verlangten Nächte. Schleifen über die Nächte hören bei `deal.game_ends_after` auf.
- Die Live-Seite auf GitHub Pages lässt sich aus dem Container nicht aufrufen. Geprüft wird die gebaute Seite lokal mit Playwright (`python3 -m http.server` in `docs/`).

## 11 · Probe: Ist der neue Chat wirklich am selben Punkt?

Der neue Chat führt diese sechs Befehle im Repo aus. Stimmen alle sechs, ist nichts verloren.

| Befehl | Muss ergeben |
|---|---|
| `git log --oneline -1` | den Commit „Simulator: die Nacht nach dem aktuellen Charakter; Handover“ |
| `git status --short` | nichts |
| `python3 run_tests.py bmr` | 214 Tests, „all good“ |
| `python3 messung/nw2.py SV 6000 4` | erste Zeile: `{'all': '0 von 16641'}` |
| `python3 messung/sim5.py SV 6000 4` | beginnt mit `SV: 6000 Partien ab 0, 4 Nächte, verworfen 43` |
| `python3 messung/preis_vergleich.py 0.5` | erste Zeile beginnt mit `price 0.5: 400 games; first 228 -> 225` |
