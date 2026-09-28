# Clocktower-Solver — Roadmap, neu bewertet

**Stand:** 28.09.2026
**Projekt:** botc-solver (Tischhilfe, gehostet auf angerprints.github.io/clocktower-solver)
**Ausgangslage:** 893 Tests grün, 0 unmögliche Bretter auf Trouble Brewing, Bad Moon Rising, Sects & Violets und in allen fünf Charakter-Gates. solver.py nach dem Aufräumen 3.596 Zeilen.

Diese Neubewertung schaut über das Solver-Repo hinaus auf das ganze Projekt. Daraus kommt die größte Verschiebung.

---

## Sechs Befunde

### 1 · Es gibt zwei Solver für dasselbe Spiel

| | botc-solver (dieses Repo) | Solver im Einzelspieler-Spiel (`J:\dev\clocktower`) |
|---|---|---|
| Zweck | Hilfe für echte Partien am Tisch | Gehirn der Bots |
| Sprache | Python + JavaScript | Python |
| Skripte | TB, BMR, S&V + 5 experimentelle | nur TB |
| Spieler | 5–15, Stichproben vorhanden | 5–9, volle Aufzählung |
| Tiefe | Zeitleisten, Gift-/Trunkenheitsquellen, Charakterwechsel | Skelett-Welten (2.610 bei 7 Spielern) |
| Tempo | 127 ms Median auf voll geclaimten TB-Brettern, Sekunden auf frühen | 20 ms |

Die Roadmap des Spiels plant für v2: *„Zwei Schergen machen einen Solver-Umbau nötig: Stichproben statt vollständiger Aufzählung. Danach Bad Moon Rising und Sects & Violets."* Genau das kann botc-solver schon.

**Aber:** botc-solver ist kein Ersatz für das Bot-Gehirn. Die Bots fragen den Solver bei fast jeder Entscheidung, tausende Partien lang. Mit 127 ms und mehr pro Aufruf wäre der Selbstspiel-Harness um ein Vielfaches langsamer. Teilen lohnt sich beim **Regelwissen** (Charaktere, Nachtreihenfolge, Registrierung, Giftquellen), nicht beim Gehirn.

### 2 · Der Zirkelschluss lässt sich jetzt billig brechen

Alles an botc-solver wird gegen den eigenen Simulator geprüft, und der wurde zusammen mit dem Solver geschrieben. Mehrere Fehler dieser Sitzungen gab es nur, weil beide Seiten dieselbe falsche Annahme hatten.

Die Engine des Einzelspieler-Spiels ist eine **unabhängige** Trouble-Brewing-Umsetzung, zweimal auditiert (M8.4), 14 Testdateien. Jede Partie dort liefert die volle Wahrheit und das öffentliche Protokoll. Daraus wird ein Brett für botc-solver, und der muss die wahre Welt behalten.

Das sind tausende unabhängig gespielte Partien, ohne dass jemand etwas eintippt. Und es wirkt in beide Richtungen: Wo die beiden sich widersprechen, hat einer von beiden einen Regelfehler. Welcher, entscheidet das Lesen des Bretts, und das ist deine Stärke.

### 3 · Die Abdeckung war falsch eingeschätzt

Ich hatte „43 Charaktere übrig" gesagt. Gemessen:

```
Katalog:        83 Charaktere, 73 modelliert, 10 nicht
außerhalb:      mindestens 56 offizielle Charaktere gar nicht im Katalog
```

Wichtiger ist, was **auf deinen Skripten** fehlt:

| Skript | fehlt |
|---|---|
| Easter Trouble (AnqeR & Shellynax) | Ogre, Marionette, Artist (nur aufgezeichnet) |
| Bad Moon Rising | Mastermind |
| Sects & Violets | Mutant, Cerenovus, Savant, Artist |

Preacher, Nightwatchman und Poppy Grower, die ich zuletzt vorgeschlagen hatte, stehen auf keinem deiner Skripte außer Whale Buffet.

### 4 · Der Solver hat kein Zuhause auf deinem Rechner

Unter `J:\dev` liegt nur `clocktower`, das Spiel. botc-solver existiert nur in diesem Container und als ZIP, das du von Hand auf GitHub hochlädst.

Der Container wurde in diesen Sitzungen zweimal zurückgesetzt, einmal gingen drei fertige Fehlerbehebungen verloren. Das ZIP-Hochladen hat die Verwirrung um den „fehlenden" Balloonist verursacht. Und du hast für das Spiel schon festgelegt, dass Dateien direkt in den Projektordner sollen statt als ZIP.

### 5 · Die Dokumentation ist ein Tagebuch

Im Projekt steht zum Solver kein einziges Dokument. Alles steckt in NEXT.md (2.454 Zeilen Sitzungsprotokoll) und README.md (4.606 Zeilen). Das Spiel dagegen hat saubere m-Dokumente. Dieses Dokument ist der erste Schritt dagegen.

### 6 · Die Website zählt frühe Bretter nicht exakt

Dein gespeichertes Farmer-Brett wurde per Stichprobe beantwortet: 417.546 Welten, Fehlermarge ±2 Punkte. Die Seite zählt nur bis 40.000 Welten exakt. Zum Spielen reicht das. Dringend ist es nicht.

---

## Die neue Reihenfolge

### Phase 0 — Zuhause und Auslieferung · *als Nächstes*

Eine von zwei Möglichkeiten, deine Entscheidung:

- **A.** Ein eigener Ordner `J:\dev\botc-solver` mit git. Ich lege die Dateien direkt dort ab, du lädst per `git push` hoch.
- **B.** Ich bekomme Schreibzugriff auf das GitHub-Repo und committe direkt. Die Seite aktualisiert sich ohne dein Zutun.

Beides beendet das ZIP-Hochladen und den Datenverlust durch Container-Resets. B ist bequemer, A lässt dich jeden Schritt sehen.

### Phase 1 — Der unabhängige Schiedsrichter

Eine Brücke: Partien aus der Engine des Spiels werden zu Brettern für botc-solver.

```
Messung:   N Engine-Partien, TB, 5 bis 9 Spieler
Frage:     Wie oft verwirft botc-solver die wahre Welt?
Jeder Treffer ist ein Regelfehler in einem der beiden Projekte.
```

Einmal pro Partie gerechnet, also 127 ms pro Partie, kein Tempo-Problem.

### Phase 2 — Deine Skripte vollständig

1. **Ogre** und **Marionette**, weil sie auf deinem eigenen Skript stehen.
2. **Mastermind** (BMR), dann **Mutant**, **Cerenovus**, **Savant** (S&V). Danach sind alle drei Grundskripte komplett.
3. Artist bleibt „aufgezeichnet": Seine Frage ist frei formuliert und lässt sich nicht als Regel prüfen.

### Phase 3 — Gemeinsames Regelwissen für das Spiel

Wenn das Spiel bei v2 ankommt (vorher kommen dort M9 bis M13): kein Solver-Neubau, sondern das Charakterwissen von botc-solver als Grundlage für BMR und S&V in der Engine. Die Schnittstelle wird entschieden, wenn es so weit ist, nicht jetzt.

Das ist auch der Grund, warum botc-solver zweisprachig bleiben sollte. Die Python-Hälfte ist genau die, die das Spiel nutzen kann.

### Phase 4 — Eine echte Partie

Bleibt wertvoll, auch neben Phase 1: ein gespeichertes Brett aus einer echten Runde, und der Vergleich, was das Werkzeug sagt und was passiert ist. Die Engine-Partien prüfen die Regeln, eine echte Partie prüft, ob das Werkzeug am Tisch hilft.

### Später

- Exakte Zählung früher Bretter auf der Website (Tempo: der Barbier-Multiplikator und der Aufbau der Zeitleisten sind die Hauptkosten)
- weitere experimentelle Charaktere nach Bedarf
- NEXT.md in eine kurze Roadmap und ein Archiv aufteilen

---

## Was gestrichen ist

- **Night-Walk als Filter:** gemessen und abgeschlossen. 3.580 verworfene Geschichten, keine einzige Zahl bewegt, elfmal langsamer. Er bleibt als zweite unabhängige Umsetzung der Nacht.
- **Preacher, Nightwatchman, Poppy Grower** als nächste Charaktere: auf keinem deiner Skripte.
- **„43 Charaktere übrig":** falsch gezählt, siehe Befund 3.
