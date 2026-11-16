# Handover: Clocktower-Solver, Stand 16.11.2026

Für einen neuen Chat, der genau hier weitermacht. Zuerst diese Datei ganz lesen, dann in `ROADMAP.md` die Abschnitte „Als Nächstes“ und „Offene Stellen“ am Ende. Die Kopie im Projekt heißt `claude/handover-solver-2026-11-16.md`.

**Die nächste Aufgabe:** Das Hauptziel geht weiter: Der Solver soll den Dämon öfter zuerst nennen. Der nächste Hebel ist eine Frage an Patrick, **wie die Bösen an seinen Tischen bluffen**. Siehe Abschnitt 9. Erst die Lesarten vorlegen, erst nach seiner Antwort bauen.

---

## 0 · Das Wichtigste vorweg: Sprache

**Mit Patrick wird immer Deutsch geschrieben.** Das gilt für jede Antwort, jede Zwischenmeldung, jede Frage und jeden Bericht. Englisch schleicht sich nach langen Arbeitsstrecken mit englischem Code und englischen Commit-Texten ein. Patrick hat das am 16.11.2026 ausdrücklich bemängelt („du fängst schon wieder an auf englisch zu schreiben“).

Englisch bleibt nur im Code, in Code-Kommentaren, in Commit-Texten und auf der Website, die englisch ist und bleibt.

## 1 · Wo alles liegt

| Was | Wo |
|---|---|
| Code, Tests, Website, Messskripte | GitHub `angerprints/clocktower-solver`, Zweig `main`, Stand **47b76b9** |
| Website | GitHub Pages aus `docs/`, angerprints.github.io/clocktower-solver |
| Berichte für Patrick (deutsch) | Projekt „BOTC Addons and Companions“, Dokumente unter `claude/…`, je Schritt einer |
| Roadmap | `ROADMAP.md` im Repo, Kopie im Projekt als `claude/solver-roadmap-neubewertung.md` |
| Offizielle deutsche Namen und Texte | Projektdokument `claude/deutsche-charaktertexte-referenz.md`, dazu `claude/botc-app-de.json.md`, `claude/stilguide-deutsche-faehigkeiten.md` |
| Prüfung der Namen | `python3 tools/check_wording.py DATEI` im Repo |
| Nachtreihenfolge (verbindlich) | Projektdokument `claude/nachtreihenfolge.md` |
| Messskripte | `messung/`, erklärt in `messung/README.md`; fürs Hauptziel `messung/hauptziel/README.md` |
| Grundmessungen fürs Hauptziel | `messung/daten/hauptziel/` (siehe Abschnitt 6) |
| Aufteilung der Testreihe in zwei Hälften | `messung/suite_A.txt`, `messung/suite_B.txt` |
| Anleitung für eine echte Partie | `ANLEITUNG-ECHTE-PARTIE.md` |
| Sitzungsprotokolle | `~/.claude/session-logs/JJJJ-MM-TT.md` (Patricks Vorgabe, siehe Abschnitt 2) |

**Nur lesen:** Das Einzelspieler-Spiel (`angerprints/clocktower_singleplayer`, lokal `J:\dev\clocktower`) gehört einem anderen Chat. Dessen Berichte liegen ebenfalls im Projekt, etwa `claude/rueckmeldungen-2026-11-15.md` (B73–B75, v6.0.35). Von hier aus wird dort nichts geändert. Abweichungen gehen als Handover-Dokument dorthin (Muster: `claude/handover-hoefling-schlaeger.md`).

**Die Arbeitsumgebung ist flüchtig.** Der Container wird nach einer Pause abgeräumt, und alles außerhalb von GitHub und dem Projekt ist dann weg: Arbeitsordner, lokale Zweige und die lokalen Berichtskopien in `.projdoc/`. Deshalb liegen seit diesem Handover die Auswerte-Skripte und Grundmessungen fürs Hauptziel im Repo.

## 2 · Wie Patrick arbeiten will

- **Deutsch**, in ganzen Sätzen, **das Ergebnis zuerst**, und **am Ende der nächste Schritt**.
- Schritt für Schritt, von null. Er hat keine eigene Entwicklungsumgebung. Soll bei ihm etwas lokal laufen: Anleitung für Windows (Projekte unter `J:\dev\`) und für den Mac.
- **Erst messen, dann ändern.** Entscheidungen gehören ihm. Er antwortet meist kurz („Weg 1“, „alle A“).
- **Lesarten vor dem Bau:** Jede Stelle, an der eine Regel oder ein Wert zu wählen ist, wird zuerst als Projektdokument `claude/<thema>-lesarten.md` vorgelegt, mit Buchstaben und Wegen und mit einer Empfehlung. Dann die Fragen mit dem Fragewerkzeug stellen: höchstens 4 Fragen, die empfohlene Antwort zuerst und mit „(Recommended)“ markiert. Jede Frage muss für sich allein verständlich sein. Seine Antworten unten im Lesarten-Dokument eintragen und das Dokument neu hochladen.
- Was ich selbst entschieden habe, steht im Bericht unter **„Was ich zusätzlich entschieden habe – bitte prüfen“**, als Tabelle mit Begründung.
- Zu jedem abgeschlossenen Schritt ein **Bericht** als Projektdokument `claude/<thema>.md`, kurz und mit Tabellen, hochgeladen mit `present_to_user: true`. Lokale Kopien in `.projdoc/` (nicht im Git).
- Nach jedem Schritt die **Roadmap** nachziehen (Abschnitt „Als Nächstes“) und ihre Kopie im Projekt neu hochladen.
- **Dieses Handover nur schreiben, wenn Patrick eines verlangt.**
- **Sitzungsprotokoll (Patricks feste Vorgabe):** Zu Beginn jeder Sitzung die neueste Datei in `~/.claude/session-logs/` lesen. In die Datei des heutigen Tages schreiben (Ordner und Datei anlegen, wenn sie fehlen), und zwar nach jedem fertigen Arbeitsstück, nach jeder Entscheidung und bei jedem Themenwechsel, nicht erst am Ende. Jeder Eintrag hat vier Überschriften: *What was done*, *Decisions made*, *Open threads*, *Errors*. Weil der Container flüchtig ist, gehen ältere Protokolle verloren. Das Projekt und dieses Handover sind das Gedächtnis.

### Die offizielle deutsche Übersetzung ist Pflicht

Für alle Charaktere gibt es eine offizielle deutsche Übersetzung (botc.app), und sie ist zu benutzen. Vor jedem deutschen Charakternamen in `claude/deutsche-charaktertexte-referenz.md` nachsehen, nie selbst übersetzen, und jeden Bericht mit `tools/check_wording.py` prüfen.

Fallen, in die schon getreten wurde:

| Englisch | Richtig | Englisch | Richtig |
|---|---|---|---|
| Goon | Schläger | Gossip | Schwätzer |
| Recluse | Einsiedler | Sailor | Segler |
| Pixie | Feenkind | Sweetheart | Liebchen |
| Puzzlemaster | Puzzlemeister | Sage | Weise |
| Preacher | Prediger | Washerwoman | Waschweib |
| Boomdandy | Bombenleger | Librarian | Bibliothekar |
| Village Idiot | Dorftrottel | Investigator | Detektiv |
| Godfather | Pate | Tea Lady | Teedame |
| Balloonist | Ballonfahrer | Huntsman | Jäger |
| Witch | Hexe | Slayer | Dämonenjäger |
| Assassin | Meuchelmörder | Pit-Hag | Grubenweib |
| Boffin | Laborratte | Lycanthrope | Werwolf |
| Fortune Teller | **Wahrsagerin** (nie „Wahrsager“) | Sentinel | Wächter |
| Savant, Shugenja, Xaan, Kazali, Lord of Typhon | bleiben so | Moonchild | Mondkind |

Weitere Regeln: **registrieren** statt „erscheinen“; Charakter (nicht Rolle), Bürger, Außenseiter, Scherge, Dämon, Erzähler, Fraktion; „besessen, Besessenheit“ (nicht Wahn).

## 3 · Tisch-Entscheidungen, die gelten

Die Liste aus dem Handover vom 11.10.2026 gilt weiter: Eine Fähigkeit endet mit dem Tod ihres Trägers. Jede Störung ruht, solange ihre Quelle gestört ist. Ziel des Solvers ist, den richtigen Spieler als Dämon zu benennen. Stille Nächte werden nicht bepreist. Beim Vortox zählt die Wirklichkeit. Die Entscheidungen zu jedem Charakter stehen in dessen Lesarten-Dokument und gekürzt in der Roadmap.

Neu seit dem 13.11.2026, alle zum Hauptziel:

| Datum | Entscheidung | Dokument |
|---|---|---|
| 13.11. | Jede Welt wird mit der Wahrscheinlichkeit gewichtet, genau ihre Tasche zu ziehen, für jedes Skript (A). Jede Aufbau-Möglichkeit des Erzählers gleich wahrscheinlich (B). Überall, Korpus neu (C). | `claude/hauptziel-tasche-lesarten.md` |
| 15.11. | Grundlose Lügen guter Spieler im Simulator: Rate bleibt etwa 1 von 10 (A). Messung immer getrennt nach Partien ohne und mit Chaos-Lüge (B). Versuch „ein grundloser Lügner“ (C). Nur Aufbau-Möglichkeiten zählen, die bei Spielerzahl und Skript gehen (D). | `claude/hauptziel-chaos-lesarten.md` |
| 15.11. | Ein grundloser Lügner erfindet passend oder schweigt (E, gebaut als „schweigt“). Versuch C erst nach E entscheiden (F); gemessen, bringt dann nichts, nicht gebaut. Lügen-Strafe 0,1 nur zusammen mit C (G), bleibt also 0,02. | `claude/hauptziel-ein-luegner-lesarten.md` |

## 4 · Aufbau in Kürze

- Zwei Solver für dieselben Regeln: Python in `botc/`, JavaScript in `js/`. **Jede Regeländerung in beiden**, mit einem Test, der beide vergleicht.
- `botc/catalogue.py` ist die Quelle der Charakterdaten (137 Einträge). `python3 tools/gen_characters.py` schreibt daraus `js/characters.mjs`.
- `python3 tools/build_site.py` baut die Website nach `docs/`. Das macht auch `tests/test_site` während der Testreihe. Die neu gebauten Dateien danach aus dem Prüfordner in den Arbeitszweig kopieren und mit committen.
- **Korpus:** `tests/fixtures/conformance.json`, 772 Bretter. Neu schreiben mit `python3 tests/make_fixtures.py` (25 bis 60 Minuten, im Hintergrund), immer nach einer Änderung an Solver oder Prioren. Vorher die alte Datei sichern, danach mit `python3 messung/hauptziel/kv.py ALT NEU` vergleichen und die größten Verschiebungen erklären.
- **Simulator:** `tests/simulate.py` spielt Partien, `tests/claims.py` macht daraus, was der Tisch sagt (`claims_for`) und was er hört (`heard_by_table`, seit 15.11.), `tests/nightwalk.py` spielt jede Nacht unabhängig nach.
- **Prioren:** `botc/solver.py` (`prior_weight`, `PRIOR_RANGES`) und `js/priors.mjs`. Seit dem 14.11. gehört das Taschen-Gewicht dazu: `bag_weight`, `BAG_PRIOR_POWER` (0 schaltet es aus), `setup_choices`, in JavaScript `bagWeight`, `setupChoices`.

**Reihenfolge nach einer Regeländerung:** Python ändern, JavaScript spiegeln, Tests dazu, Messlauf, Korpus neu, Testreihe in zwei Hälften (die Website wird dabei gebaut), Bericht, Roadmap, Squash nach main, Hochladen, Protokoll, Abschlussnachricht.

**Das Tor für einen Charakter:** Solver in Python und JavaScript, Simulator, Night-Walk (`messung/nw2.py`), gemischte Partien ohne verlorene wahre Welt (`messung/tor.py N NÄCHTE START NAME…`), eintragbar auf der Website.

### Arbeitsweise mit Zweigen und Ordnern (bewährt)

- Im Repo-Ordner nur `main`. Gearbeitet wird in eigenen Worktrees: **ein Bearbeitungsordner** (`git worktree add … -b wip/<thema> origin/main`) und **zwei eingefrorene Prüfordner** (`git worktree add --detach …`), in denen Messungen und Testreihe auf einem festen Commit laufen.
- **Nie Code ändern, während in demselben Ordner eine Messung oder Testreihe läuft.** JavaScript und Korpus werden zur Laufzeit gelesen.
- Höchstens **zwei schwere Läufe** gleichzeitig.
- Lange Läufe im Hintergrund, mit `timeout 7000` (Grenze 2 Stunden). Abbrechen nur über das Werkzeug zum Stoppen von Hintergrundaufgaben, **nie `pkill -f`** (trifft die eigene Shell).
- Auf das Ende warten, bevor die Antwort endet: Ein Hintergrundlauf wird sonst kurz nach Ende der Antwort gestoppt.
- **Testreihe in zwei Hälften** (zusammen 1 bis 2 Stunden), in den beiden Prüfordnern gleichzeitig:
  `bash messung/suite_haelfte.sh OUT_A $(cat messung/suite_A.txt)` und dasselbe mit `suite_B.txt`. Jede Zeile: Datei | Sekunden | Ergebnis, am Ende `FINISHED`. Langsam sind die Korpus-Abgleiche in `test_conformance` und `test_claims`.
- **Squash nach main:**
  `git fetch -q origin main wip/<thema> && git merge-base --is-ancestor origin/main origin/wip/<thema> && git checkout -q main && git reset -q --hard origin/main && git merge --squash -q origin/wip/<thema> && git commit && git push -q origin main`. Danach `git diff --stat origin/main origin/wip/<thema>` muss leer sein. Force-Push ist gesperrt.
- Commits enden mit den Zeilen `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` und `Claude-Session: <Sitzungs-Link>`.

## 5 · Was seit dem 11.10.2026 passiert ist

87 Commits. Die Einzelheiten stehen in der Roadmap und den Berichten im Projekt.

| Zeitraum | Inhalt | Berichte (Auswahl) |
|---|---|---|
| 12.–19.10. | Batch 8 und 9 (u. a. Hohepriesterin, General, Fischer), Falsche Pfote, Philosoph mit genommener Fähigkeit (Stelle 56), Stellen 52–60 | `claude/experimentelle-charaktere-batch-*.md` |
| 20.–30.10. | Die großen Charaktere: Lord of Typhon, Kazali, Al-Hadikhia, Lil' Monsta, Beschwörer, Hutmacher (3 Stufen, neue Nachtreihenfolge), Ingenieur, Laborratte, Pestdoktor | je ein Bericht |
| 30.10.–05.11. | Stellen-Pakete 1–5, Stellen 4, 5, 53, 83, 100–117 | `claude/stelle-*.md` |
| 04.–06.11. | Alchemist in Gruppen 1–5b | `claude/alchemist*.md` |
| 07.–12.11. | Eremit, Stufen 1, 2, 2b | `claude/eremit-*.md` |
| 12.–13.11. | Kannibale, Stufen 1, 2, 2b | `claude/kannibale-*.md` |
| 14.11. | **Hauptziel: Taschen-Gewicht** (9114cfc) | `claude/hauptziel-tasche.md` |
| 15.11. | **Taschen-Gewicht Stufe 2 und getrennte Messung** (de350b0) | `claude/hauptziel-tasche-2.md` |
| 15.11. | **Simulator: grundloser Lügner schweigt**; Versuch C verworfen (47b76b9) | `claude/hauptziel-ein-luegner.md` |
| 16.11. | Dieses Handover, Auswerte-Skripte und Grundmessungen ins Repo | |

**Stand des Katalogs:** 137 Einträge. Von den 138 Spielercharakteren der App fehlen nur die Vergessliche und der Zauberer; beide lassen sich nicht modellieren. Die Arbeit an den Charakteren ist damit abgeschlossen. Seit dem 13.11. geht es ums Hauptziel.

## 6 · Der Stand beim Hauptziel

**Messung:** `python3 messung/dmeas.py SKRIPT OUT.jsonl ERSTE LETZTE 4`, ab Seed 0, 7 bis 10 Spieler, 4 Nächte. Gemessen wird am letzten Morgen, an dem die Partie noch offen ist. Auswertung **immer** mit `python3 messung/dmeas_bericht.py OUT.jsonl [GRUNDMESSUNG.jsonl]` (Patricks Vorgabe B: alle, ohne und mit Chaos-Lüge).

**Dämon vorn, aktueller Stand:**

| Skript | Partien | Dämon vorn | ohne Chaos-Lüge | mit Chaos-Lüge | Grundmessung |
|---|---|---|---|---|---|
| Trouble Brewing | 600 | 405 (68 %) | 275 von 375 (73 %) | 130 von 225 (58 %) | `TB_600_47b76b9.jsonl` (main heute) |
| Trouble Brewing | 1.500 | 994 (66 %) | – | – | `TB_1500_9114cfc.jsonl` (vor „Lügner schweigt“) |
| Bad Moon Rising | 450 | 269 (60 %) | 183 von 278 (66 %) | 86 von 172 (50 %) | `BMR_450_de350b0.jsonl` |
| Sects & Violets | 150 | 108 (72 %) | 68 von 92 | 40 von 58 | `SV_150_9114cfc.jsonl` |

Vor dem Taschen-Gewicht (main 0b9c7a1) waren es 943 von 1.500, 259 von 450 und 106 von 150.

**Was gebaut ist:** das Taschen-Gewicht (eine Tasche mit weniger Bürgern hat weniger Alternativen und ist deshalb je Welt wahrscheinlicher; Aufbau-Möglichkeiten gleich verteilt, nur mögliche zählen). Der Simulator lässt einen grundlosen Lügner schweigen.

**Was versucht und verworfen ist (nicht wiederholen):**

| Versuch | Ergebnis |
|---|---|
| Gute Lügen zulassen (`allow_good_lies`) | schlechter: BMR 78 statt 88 von 150; TB 60 Partien: 6 neu, 9–10 verloren, 3,5-mal so langsam. Der Schalter nimmt nur versteckte Außenseiter auf. |
| Erfundene Zeilen nur einmal je Spieler bepreisen | schlechter: TB 351 statt 376 von 600 |
| Ab der zweiten erfundenen Zeile 0,7 bzw. 0,55 statt 0,4 | schlechter: 0 neu, 7 bzw. 3 verloren |
| Höchstens ein grundloser Lügner je Welt, allgemein | trifft, aber 10- bis 75-mal so langsam |
| … schmal (nur Charaktere, zu denen seine Zeilen passen) | +21 in TB, aber nur weil der Lügner damals seine wahren Zeilen verriet. Mit schweigendem Lügner: 405 = 405 |

Die Versuchszweige (`exp/erfunden`, `exp/ein-luegner`, `exp/ein-luegner-2`) lagen nur lokal und sind mit dem Container weg. Die Berichte beschreiben, wie sie gebaut waren.

**Wo der Dämon verfehlt wird (Trouble Brewing):**
- Die meisten Fehler: Der Dämon behauptet einen Charakter ohne Information, und ein anderer solcher Sitz steht vorn (rund 190 von 500 Fehlern auf 1.500 Partien).
- Partien mit Chaos-Lüge: 58 % statt 73 %. In 147 Partien lag der Vorderste mehr als 30 Punkte vor dem Dämon; 103 davon waren Chaos-Partien.
- Kalibrierung insgesamt gut. Ab Tag 3 sind Dämonen, die die Wahrsagerin, den Empath oder den Totengräber behaupten, rund 40 % häufiger, als der Solver erwartet. Der Heilige wird zu oft verdächtigt (Verhältnis 0,73 nach dem Taschen-Gewicht, vorher 0,63).

## 7 · Der Simulator in Zahlen, die man kennen muss

- Jeder gute Spieler lügt mit 10 % (`GOOD_LIE_CHANCE`, `tests/claims.py`). Ein Außenseiter versteckt sich dabei meist, ein Bürger lügt immer „chaotisch“, also grundlos. In Trouble Brewing hat rund jede dritte Partie eine Chaos-Lüge.
- Seit 47b76b9 behält ein Chaos-Lügner seine Zeilen für sich (`heard_by_table`). Öffentliche Zeilen bleiben (`row.hard()`). Genutzt in `messung/dmeas.py` und `messung/tor.py`, **nicht** in `tests/make_fixtures.py`: Die Korpus-Bretter sind feste Fälle.
- **Böse Bluffer melden nie eine Zeile.** In 40 Partien hatte kein böser Sitz eine. Das ist der Ansatz für die nächste Aufgabe.
- Der Solver rechnet für einen Bürger, der einen anderen Bürger behauptet, mit 0,02 (`TOWNSFOLK_LIE_PENALTY`) und zählt solche Welten normalerweise gar nicht auf.
- Jede Zeile eines Spielers, der in einer Welt böse ist, kostet diese Welt den Faktor 0,4 (`FABRICATED_INFO_PENALTY`, `invention_cost`).

**Prüfsummen** (`python3 messung/tbhash.py`, Stand 47b76b9): `TB de6314604a57ccf7`, `EASTER 7a5f428cbbc77d24`, `SV fb4894c3ac4bb783`. Ändern sie sich, spielt der Simulator anders.

## 8 · Was offen ist

- `ROADMAP.md`, „Offene Stellen“ (Nummern 1 bis 119, die meisten erledigt). Noch offen sind unter anderem 2, 3, 6–9, 19, 36, 48, 52, 54, 82, 99, 102.
- „Als Nächstes“, Punkte 2 bis 4: zwei kleine Stellen in Sects & Violets (darunter: der Simulator spielt die Hinrichtung wegen Besessenheit nicht), die strenge Lesart für stille Nächte (zurückgestellt), die Regeln ans Einzelspieler-Spiel zurückgeben (gehört dem anderen Chat).
- Für Bad Moon Rising und Sects & Violets gibt es noch keine Grundmessung mit schweigendem Lügner.

## 9 · Die nächste Aufgabe: Wie bluffen die Bösen?

**Befund:** Im Simulator nennt ein böser Spieler, der zum Beispiel die Wahrsagerin vorspielt, nie eine Information. Eine echte Wahrsagerin meldet jede Nacht etwas, und jede ihrer Zeilen macht Welten teurer, in denen sie böse ist. Der Dämon, der sie nur vorspielt, meldet nichts und zahlt nichts. Das erklärt, warum solche Dämonen ab Tag 3 zu selten verdächtigt werden. An einem echten Tisch erfindet ein Bluffer Informationen.

**So fängt der neue Chat an:**

1. Die Proben aus Abschnitt 11 ausführen.
2. Ansehen, wie `tests/claims.py` die Behauptungen der Bösen wählt und warum sie keine Zeilen bekommen (`table_view` und `claims_for`).
3. Patrick ein Lesarten-Dokument `claude/hauptziel-bluff-lesarten.md` vorlegen. Die Fragen, die sich abzeichnen:
   - Erfinden Böse an seinen Tischen Informationen zum vorgespielten Charakter? Immer, meistens, selten?
   - Wenn ja: Wie erfindet der Simulator sie? Zufällig, passend zur eigenen Geschichte (etwa ein Empath, der seine Nachbarn als gut meldet), oder so, dass sie einen Guten belasten?
   - Soll der Solver einen Spieler, der einen Info-Charakter behauptet, aber nie etwas meldet, verdächtiger finden? Am echten Tisch kann es auch heißen, dass die Information nicht eingetragen wurde.
   - Die Simulator-Änderung zuerst allein messen (wie viel schwerer wird das Hauptziel?), dann erst den Solver anpassen?
4. Messen wie in Abschnitt 6, immer getrennt nach Chaos-Lüge und gegen die Grundmessungen.

Weitere mögliche Hebel, noch nicht vorgelegt: Unter den Sitzen, die einen Charakter ohne Information behaupten, unterscheidet der Solver den Dämon kaum (die größte Fehlergruppe). Und es gibt Partien, in denen gar keine Welt übrig bleibt und der Dämon trotzdem als „vorn“ zählt (Beispiel: Bad Moon Rising Seed 405).

## 10 · Stolpersteine

- **Deutsch schreiben** (Abschnitt 0). Charakternamen immer in der Referenz nachsehen.
- `dmeas.py` braucht je nach Last 25 bis 60 Minuten für 600 Partien Trouble Brewing, Bad Moon Rising mit 450 Partien über eine Stunde. Ein dritter schwerer Lauf daneben macht alles langsamer.
- In Bad Moon Rising zählt der Solver jede dritte Partie nicht vollständig durch, sondern schätzt (`sampled`). Schätzungen schwanken, und Verbesserungen an der Aufzählung erreichen sie nicht.
- Eine Partie mit 0 gültigen Welten zählt in `dmeas.py` als „vorn“, wenn alle Prozente 0 sind. Bei Vergleichen darauf achten.
- `iter_worlds` zählt Welten mit guten Lügen nicht auf. In Chaos-Partien fehlt die wahre Welt deshalb meist, ohne dass das Tor es sieht (`explanation_cost` der wahren Welt ist trotzdem nicht `None`).
- Ein Wartebefehl im Vordergrund darf höchstens 10 Minuten laufen. Für längeres Warten mehrere kurze Wartebefehle hintereinander.
- Textersetzungen in Dateien immer mit Prüfung, dass die Stelle genau einmal vorkommt.
- Ein Seed benennt eine Partie nur, bis der Simulator etwas Neues lernt.
- Ausgeteilter und aktueller Charakter: `deal.role_at(sitz, phase)`, nicht `deal.roles[sitz]`.
- Die Live-Seite auf GitHub Pages lässt sich aus dem Container nicht aufrufen. Geprüft wird die gebaute Seite lokal.
- Nach einer Änderung am Taschen-Gewicht oder an den Prioren erwarten `test_golden` (feste Prozente) und einige Tests in `test_sv` (Strafen einer Welt) andere Zahlen. Am 14.11. angepasst: Diese Tests rechnen das Taschen-Gewicht heraus.

## 11 · Probe: Ist der neue Chat am selben Punkt?

Im Repo ausführen. Stimmt alles, ist nichts verloren.

| Befehl | Muss ergeben |
|---|---|
| `git log --oneline -1` | den Commit „Handover 16.11.2026 …“ |
| `git status --short` | nichts |
| `python3 messung/tbhash.py` | `TB de6314604a57ccf7`, `EASTER 7a5f428cbbc77d24`, `SV fb4894c3ac4bb783` |
| `python3 messung/dmeas_bericht.py messung/daten/hauptziel/TB_600_47b76b9.jsonl` | `alle 600 Partien, Dämon vorn 405 (68 %)` |
| `cd tests && python3 -m unittest test_tasche test_schweigen` | 9 Tests, grün |
| `python3 -c "import json; print(len(json.load(open('tests/fixtures/conformance.json'))['cases']))"` | `772` |
| Projekt: `claude/hauptziel-ein-luegner.md` | vorhanden, Stand 15.11.2026 |
