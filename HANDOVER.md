# Handover: Clocktower-Solver, Stand 11.10.2026

Für einen neuen Chat, der genau hier weitermacht. Zuerst diese Datei lesen, dann `ROADMAP.md` (Abschnitte „Als Nächstes“ und „Offene Stellen“ am Ende).

**Die nächste Aufgabe:** Batch 8 der experimentellen Charaktere. Vorgeschlagen sind Kopfgeldjäger, Kultführer, Mezepheles, Leviathan und Yaggababble. Zuerst die Lesarten vorlegen, erst nach Patricks Antwort bauen. Siehe Abschnitt 9.

## 1 · Wo alles liegt

| Was | Wo |
|---|---|
| Code, Tests, Website, Messskripte | GitHub `angerprints/clocktower-solver`, Zweig `main` |
| Website | GitHub Pages aus `docs/`, angerprints.github.io/clocktower-solver |
| Berichte für Patrick (deutsch) | Projekt „BOTC Addons and Companions“, Dokumente unter `claude/…`, je Schritt einer |
| Roadmap | `ROADMAP.md` im Repo, Kopie im Projekt als `claude/solver-roadmap-neubewertung.md` |
| **Offizielle deutsche Übersetzung aller Charaktere** | Projektdokument `claude/deutsche-charaktertexte-referenz.md`, dazu `claude/botc-app-de.json.md` und `claude/stilguide-deutsche-faehigkeiten.md`. Siehe Abschnitt 2. |
| Messskripte | `messung/` im Repo, erklärt in `messung/README.md` |
| Anleitung für eine echte Partie | `ANLEITUNG-ECHTE-PARTIE.md` |

**Nur lesen:** Die Engine des Einzelspieler-Spiels unter `J:\dev\clocktower` gehört einem anderen Chat. Abweichungen gehen als Handover-Dokument dorthin (Muster: `claude/handover-hoefling-schlaeger.md`), geändert wird von hier aus nichts.

## 2 · Wie Patrick arbeiten will

- Antworten auf Deutsch, in ganzen Sätzen, das Ergebnis zuerst.
- Schritt für Schritt, von null. Er hat keine eigene Entwicklungsumgebung. Wenn etwas bei ihm lokal laufen soll: Anleitung für Windows und für Mac.
- **Erst messen, dann ändern.** Entscheidungen gehören ihm. Er antwortet meist kurz („Weg 1“, „J: …, Rest passt“). Deshalb jede Entscheidung als benannte Wege oder als Lesarten mit Buchstaben anbieten, mit einer Empfehlung.
- **Lesarten vor dem Bau.** Für jeden neuen Charakter zuerst die Stellen zeigen, an denen eine Regel zu wählen ist, und erst nach seiner Antwort bauen.
- Am Ende jeder Antwort steht der nächste Schritt.
- **Dieses Handover nicht nach jedem Schritt nachziehen.** Es wird nur geschrieben, wenn Patrick eines verlangt. Die Roadmap wird nach jedem Schritt nachgezogen, ihre Kopie im Projekt auch.
- Zu jedem abgeschlossenen Schritt ein Bericht als Projektdokument `claude/<thema>.md`, kurz und mit Tabellen. Die lokalen Kopien liegen in `.projdoc/` (nicht im Git).
- Commits als „Claude <noreply@anthropic.com>“, mit den Zeilen `Co-Authored-By` und `Claude-Session` am Ende. Vor dem Push `git fetch origin main`.

### Die offizielle deutsche Übersetzung ist Pflicht

**Für alle Charaktere gibt es in diesem Projekt bereits eine offizielle deutsche Übersetzung, und sie ist zu benutzen.** Sie steht in `claude/deutsche-charaktertexte-referenz.md`. Das ist der Text der botc.app v3.57.3 in der deutschen Spielübersetzung: alle 185 Charaktere mit Name und Fähigkeit, dazu die Erinnerungsmarker und die Jinxes. Vor jedem deutschen Charakternamen in Antworten, Berichten und der Roadmap dort nachsehen. Nie einen Namen selbst übersetzen.

In Roadmap und Berichten standen bis zum 11.10.2026 einige selbst übersetzte Namen. Sie sind korrigiert, und sie zeigen, wo die Falle liegt:

| Englisch | Richtig | Nicht |
|---|---|---|
| Gossip | **Schwätzer** | Lästerschwester |
| Sailor | **Segler** | Seemann |
| Sweetheart | **Liebchen** | Süße |
| Farmer | **Farmer** | Bauer |
| Sage | **Weise** | Weiser |
| Washerwoman | **Waschweib** | Wäscherin |
| Librarian | **Bibliothekar** | Bibliothekarin |
| Investigator | **Detektiv** | Ermittler |
| Tea Lady | **Teedame** | Teefrau |
| mad, madness | **besessen, Besessenheit** | Wahn, wahnsinnig |
| faux paw (Werwolf) | **Falsche Pfote** | – |

Weitere feste Regeln zum Wording:
- Es heißt **registrieren**, nicht „erscheinen“, wenn ein Charakter für eine Fähigkeit anders gilt (Spion, Einsiedler, Falsche Pfote). Die App selbst schreibt „erscheint“, Patrick will „registriert“.
- Charakter (nicht Rolle), Bürger, Außenseiter, Scherge, Dämon, Erzähler, Fraktion.
- Die Website selbst ist englisch und bleibt es.
- In älteren Abschnitten der Roadmap können noch abweichende Namen stehen (Sweetheart, Näherin, Pit-Hag). Neue Texte benutzen nur die Namen der Referenz.

## 3 · Tisch-Entscheidungen, die gelten

Allgemein:
- **Eine Fähigkeit endet mit dem Tod ihres Trägers.** Wer wiederbelebt oder neu erschaffen wird, ist eine neue Instanz und wählt neu (03.10.2026).
- **Jede Störung ruht, solange ihre Quelle gestört ist** (02.10.2026).
- **Schläger:** Der Erste, der ihn wählt, ist sofort betrunken, also schlägt schon diese Wahl fehl. Ein Höfling, der den Schläger nennt, wählt ihn (08.10.2026).
- **Barbier:** Ein Tausch wird nur erwogen, wenn ein gemeldeter Barbier gestorben ist. Ein versteckter Barbier ist Schuld des Dorfs.
- **Ziel des Solvers:** den richtigen Spieler als Dämon benennen.
- **Vortox und Registrieren:** Die Wirklichkeit zählt, auch bei der Adligen (07.10.2026).
- **Stille Nächte:** nichts bepreisen. **Grenze 400** für die Erzählungen der Nächte bleibt.
- **Zwei auf dem Brett, und die Partie läuft:** Dann leben wirklich mindestens drei. Gilt nur mit einem Zombuul auf dem Skript.
- **Dämon-Typ auf der Website:** nur Fakten. **Das Dorf im Simulator** bleibt, wie es ist.
- **Pukka:** nach dem Ablaufplan von Not_Quite_Vertical.

Die Entscheidungen zu den Batches 1 bis 7 stehen je in `claude/experimentelle-charaktere-batch-N.md` (Batch 1 im Bericht `claude/experimentelle-charaktere-batch-1.md`) und gekürzt in der Roadmap. Die jüngsten, Batch 7 vom 11.10.2026:

| Charakter | Entscheidung |
|---|---|
| Feenkind | Gezeigt wird ein Bürger im Spiel, oder ein Spion registriert als er. Ihn zu behaupten heißt, besessen zu sein, und kostet nichts. Die Fähigkeit kommt ab der Nacht nach dem Tod des Halters, wenn das Feenkind lebt, arbeitet und besessen ist. Der Erzähler darf sie verweigern (kostet 0,35). |
| Dorftrottel | 1 bis 3, ab zwei ist einer das ganze Spiel betrunken. Liest nach Registrieren. Mehrere Dorftrottel-Claims sind keine Lüge. Der Jinx mit dem Grubenweib ist nicht gebaut. |
| Werwolf | Ab Nacht 2: Ein guter Gewählter stirbt, und der Dämon tötet niemanden, auch das alte Gift der Pukka nicht. Kein Dämon-Kill (Mönch und Soldat schützen nicht). **Die Falsche Pfote darf auch der Werwolf selbst sein** (Patricks Korrektur). Sie registriert sicher als böse, solange der Werwolf lebt und arbeitet. |
| Harpyie | Sagt der Besessene es, lebt eine Harpyie. Regel 24 des Cerenovus gilt. Sie tötet nie den Dämon. |
| Lleech | Der Wirt ist vergiftet, solange der Lleech lebt; das ruht, solange der Lleech gestört ist. Der Lleech stirbt nur mit dem Wirt, gestört erst, wenn er wieder arbeitet. Jinx mit Dämonenjäger und Strippenzieher gebaut, mit Ketzer nicht. |

Nicht gebaute Jinxes, mit Patricks Einverständnis: Magierin–Geist, Angstmacher–Wesir, Dorftrottel–Grubenweib, Lleech–Ketzer, Werwolf–Oger.

## 4 · Aufbau in Kürze

- Zwei Solver für dieselben Regeln: Python in `botc/`, JavaScript in `js/`. **Jede Regeländerung in beiden.**
- `botc/catalogue.py` ist die Quelle für die Charakterdaten. `python3 tools/gen_characters.py` schreibt daraus `js/characters.mjs`. Ein neues Feld im Katalog muss auch in `DEFAULTS` von `tools/gen_characters.py` und `js/catalogue.mjs` stehen.
- Nachtplätze, die in der Datei im Repo fehlen, stehen von Hand in `_NOT_IN_THE_FILE` im Katalog.
- `python3 tools/build_site.py` baut die Website aus `ui/` und `js/` nach `docs/`.
- `tests/fixtures/conformance.json` ist der Korpus (331 Bretter). Neu schreiben mit `python3 tests/make_fixtures.py` (etwa 17 Minuten), immer nach einer Regeländerung, danach die Bretter mit Namen gegen den alten Stand vergleichen.
- `tests/simulate.py` spielt ganze Partien, `tests/claims.py` macht daraus, was der Tisch sagt, `tests/nightwalk.py` spielt jede Nacht unabhängig nach.
- **Verdeckte Wahlen** (seit Batch 7): Was nirgends auf dem Brett steht, etwa die Falsche Pfote oder der Wirt des Lleech, erzählt der Solver für jede mögliche Wahl einmal (`_hidden_choices` in `botc/solver.py`, `hiddenChoices` in `js/scoring.mjs`). Die Memo-Schlüssel enthalten die Wahl.
- **Mehrfache Charaktere** (seit Batch 7): Feld `copies` im Katalog, der Dorftrottel hat 3.

**Reihenfolge nach einer Regeländerung:** Python ändern, JavaScript spiegeln, Messlauf, Tests dazu, Korpus neu, Website bauen, ganze Suite, Roadmap und Bericht, Commit und Push.

**Das Tor für einen Batch** (so seit Batch 2):

| Nr. | Schritt | Werkzeug |
|---|---|---|
| 1 | Solver in Python und JavaScript, gleiche Ergebnisse | `tests/test_experimental_N.py`, Korpus, `test_js_solve` |
| 2 | Simulator spielt alle, auch gestört | `tests/simulate.py` |
| 3 | Night-Walk spielt die Nächte nach | `messung/nw2.py XNAME 3000 4`, einzelne Seeds mit `messung/nw3.py` |
| 4 | Gemischte Partien: keine wahre Welt verloren wegen der neuen Zeilen | `messung/tor.py 3000 4 0 Name1 Name2 …` (auch mit 6 Nächten und ohne Namen) |
| 5 | Eintragbar auf der Website, im Browser geprüft | Playwright gegen `python3 -m http.server` in `docs/` |
| 6 | Korpus, Suite, Roadmap, Bericht, Commit, Push | |

Für jeden Batch gibt es zwei eigene Skripte in `tests/test_experimental_N.py` (eines wie Trouble Brewing, eines wie Bad Moon Rising). `messung/sim5.py` und `nw2.py` kennen sie als `XSEVEN`, `XSEVENB` usw.

## 5 · Was seit dem 05.10.2026 passiert ist

| Commit | Inhalt |
|---|---|
| 5f6860d | Batch 1: Gutsverwalter, Ritter, Shugenja, Nachtwächter, König |
| ce22d6a | Gemischte Skripte aufgeräumt (96 → 16 von 3.000 verloren) |
| 1a1ed20 | Vortox und Registrieren |
| 2255bf2, 8415139 | Batch 2: Banshee, Eiferer, Ketzer, Goblin, Ojo, und Patricks Antworten dazu |
| 38932a7, f605ea4 | Batch 3: Magierin, Mohnzüchter, Politiker, Petze, Geist, und Antworten |
| 9c8737b | Batch 4: Unschuld, Angstmacher, Wesir, Drehorgelspieler |
| af5a930 | Batch 5: Chorknabe, Prinzessin, Golem, Psychopath, Witwe |
| e15c88b | Batch 6: Prediger, Jäger, Puzzlemeister, Xaan, Bombenleger |
| 0559e3d | Batch 7: Feenkind, Dorftrottel, Werwolf, Harpyie, Lleech |
| danach | Offizielle Namen in Roadmap und Berichten nachgezogen; dieses Handover |

## 6 · Der Stand der Messungen

**Wahre Welt gehalten** (verwirft der Solver die Welt, die gespielt wurde?), 4 Nächte:

| Skript | verloren | Anmerkung |
|---|---|---|
| Bad Moon Rising | 0 von 6.000 | |
| Sects & Violets | 37 von 6.000 | fast alle versteckter Barbier, gewollt |
| Eigene Skripte von Batch 1 bis 7 | je 0 von 3.000 | auch bei 6 Nächten |
| Gemischte Partien mit den fünf aus Batch 7 | 9 von 3.000 | Barbier-Klasse, Stelle 6, Stelle 48 a |
| Gemischte Partien ohne Pflicht-Charaktere | 5 von 3.000 | Barbier-Klasse, Stellen 41, 42, 48 e |

**Prüfsummen** (`python3 messung/tbhash.py`): `TB 4ff5ece3d7c1f8a7`, `EASTER b58eb3f2d8074508`, `SV fc480a8d2311d52b`. Ändern sie sich, spielt der Simulator Trouble Brewing, Oster-Skript oder Sects & Violets anders.

**Simulator gegen Night-Walk:** Bad Moon Rising 0 von 8.467 Nächten, Sects & Violets 0 von 8.324. Auf den Skripten von Batch 7: 3 von 15.526 (Stelle 47). Gemischt: 6 von 7.509 mit den fünf und 6 von 7.862 ohne Pflicht, alle bekannte Stellen (40, 41, 44, 49).

**Suite:** 1.449 Tests, alle grün, 2 übersprungen.

## 7 · Was offen ist

Die vollständige Liste steht in `ROADMAP.md` unter „Offene Stellen“ (Nummern 1 bis 50). Für die nächsten Schritte wichtig:

| Nr. | Was |
|---|---|
| 14 | Experimentelle Charaktere, die laufende Aufgabe |
| 4 | Barbier-Tausch ohne gemeldeten Barbier verliert die wahre Welt, gewollt |
| 6 | Mathematiker unter einem Vortox, lockere Regel |
| 36 | Wer früh in der Nacht handelt und in derselben Nacht verwandelt wird |
| 40 | Der Schläger antwortet im Simulator nicht auf verdeckte Wahlen (Giftmischer, Mönch, Hexe, Grubenweib, Schlangenbeschwörer) |
| 41 | Regelfrage: Gastwirt schützt einen Fang Gu, der springt |
| 47 | Gift der Pukka aus der Vornacht, und die Pukka wählt den Schläger |
| 48 | Kleine Klassen aus den Toren, je 1 von 3.000 |
| 49 | Der Night-Walk ändert Störungen aus Gründen in der Nacht erst am Platz des Liebchens |

Zu entscheiden ist zurzeit nur Batch 8.

## 8 · Die Roadmap ist ein Tagebuch

`ROADMAP.md` hat über 1.100 Zeilen. Der aktuelle Stand steht in „Als Nächstes“ und „Offene Stellen“ am Ende. Jeder Batch hat dort einen kurzen Abschnitt, der volle Bericht liegt im Projekt.

## 9 · Die nächste Aufgabe: Batch 8

**Stand des Katalogs:** 117 Charaktere. Von den 138 Spielercharakteren der App sind 116 im Katalog, dazu der Wächter (ein Fabled). 22 fehlen:

| Einschätzung | Charaktere |
|---|---|
| mittel (der Vorschlag für Batch 8) | Kopfgeldjäger, Kultführer, Mezepheles, Leviathan, Yaggababble |
| groß | Alchemist, Kannibale, Ingenieur, Hutmacher, Eremit, Pestdoktor, Laborratte, Beschwörer, Al-Hadikhia, Kazali, Lil' Monsta, Lord of Typhon |
| nur aufzeichnen | Hohepriesterin, General, Fischer |
| nicht modellierbar | Vergessliche, Zauberer |

**So fängt der neue Chat an:**

1. Die Proben aus Abschnitt 11 ausführen.
2. Für jeden der fünf die Regel im offiziellen Wiki und die Jinxes in der Referenz lesen.
3. Patrick die Lesarten vorlegen, mit Buchstaben, je Charakter: welche Zeile auf der Website, was der Solver daraus schließt, was kostet, welche Jinxes gebaut werden, wie der Simulator ihn spielt.
4. Erst nach seiner Antwort bauen, dann durch das Tor aus Abschnitt 4.

## 10 · Stolpersteine

- **Charakternamen immer in der Referenz nachsehen** (Abschnitt 2).
- **Während die ganze Suite läuft, nichts am Code ändern.** JavaScript und Korpus werden zur Laufzeit gelesen.
- **Die ganze Suite dauert über eine Stunde** und wurde am 11.10.2026 von einer Zeitgrenze von 3.500 Sekunden abgebrochen. Besser jede Testdatei einzeln laufen lassen, in zwei Hälften nebeneinander: `PYTHONPATH=tests python3 -m unittest -q test_NAME`. Die langsamsten sind `test_conformance` (23 min), `test_claims` (15 min) und `test_oracle` (6 min).
- Ein Befehl läuft höchstens 10 Minuten. Lange Läufe im Hintergrund starten und später nachsehen.
- `pgrep -f` und `pkill -f` treffen die eigene Shell. Stattdessen `ps -eo pid,args | awk …`.
- Textersetzungen in Dateien immer mit Prüfung, dass die Stelle genau einmal vorkommt.
- Ein Seed benennt eine Partie nur, bis der Simulator etwas Neues lernt.
- **„Am Ende der Nacht“ ist keine Antwort auf „in diesem Moment“.** `simulate.droisoned_at` ist der Stand am Ende der Nacht. Der Night-Walk bekommt Änderungen innerhalb der Nacht erst am Platz des Liebchens (Stelle 49), außer wo es eigens gebaut ist.
- Ausgeteilter und aktueller Charakter: `deal.role_at(sitz, phase)`, nicht `deal.roles[sitz]`.
- Der Solver rechnet in ganzen Nächten. Was in einer Nacht nacheinander passiert, sieht er nur, wo es eigens gebaut ist.
- Eine gespielte Partie kann kürzer sein als die verlangten Nächte. Schleifen hören bei `deal.game_ends_after` auf.
- Die Live-Seite auf GitHub Pages lässt sich aus dem Container nicht aufrufen. Geprüft wird die gebaute Seite lokal mit Playwright.
- Eine Änderung am Simulator ändert oft gespielte Bretter im Korpus. Nach `make_fixtures.py` die Bretter mit Namen gegen den alten Stand vergleichen und jede Änderung erklären (Beispiel: Batch 7, zwei Bretter mit mehr Welten, weil die Scharlachrote Frau jetzt auch nachts übernimmt).

## 11 · Probe: Ist der neue Chat wirklich am selben Punkt?

Der neue Chat führt diese Befehle im Repo aus. Stimmen alle, ist nichts verloren.

| Befehl | Muss ergeben |
|---|---|
| `git log --oneline -1` | den Commit „Handover 11.10.2026; offizielle deutsche Namen“ |
| `git status --short` | nichts |
| `python3 run_tests.py bmr` | 214 Tests, alle grün |
| `python3 messung/tbhash.py` | `TB 4ff5ece3d7c1f8a7`, `EASTER b58eb3f2d8074508`, `SV fc480a8d2311d52b` |
| `python3 messung/sim5.py SV 6000 4` | beginnt mit `SV: 6000 Partien ab 0, 4 Nächte, verworfen 37` |
| `python3 messung/sim5.py XSEVEN 3000 4` | beginnt mit `XSEVEN: 3000 Partien ab 0, 4 Nächte, verworfen 0` |
| `python3 messung/nw2.py SV 3000 4` | erste Zeile `{'all': '0 von 8324'}` |
