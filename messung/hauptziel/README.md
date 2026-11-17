# Auswerte-Skripte für das Hauptziel (Dämon finden)

Alle Skripte lesen die Ausgabe von `messung/dmeas.py` (eine JSON-Zeile je Partie). Aufruf immer aus dem Repo-Wurzelordner.

| Skript | Aufruf | Zeigt |
|---|---|---|
| `messung/dmeas_bericht.py` | `python3 messung/dmeas_bericht.py NEU.jsonl [ALT.jsonl]` | **Die Standard-Auswertung** (Patrick, 15.11.2026): alle Partien, ohne und mit Chaos-Lüge; mit zweiter Datei auch neu vorn / nicht mehr vorn |
| `ana.py` | `python3 messung/hauptziel/ana.py DATEI` | Dämon vorn, unter den ersten 2/3, Durchschnitt, warum verfehlt |
| `cmp.py` | `python3 messung/hauptziel/cmp.py ALT NEU` | Vergleich zweier Läufe, Partie für Partie (kürzere Länge zählt) |
| `cal.py` | `python3 messung/hauptziel/cal.py DATEI` | Kalibrierung: erwartete gegen wirkliche Dämonen, nach Prozent-Stufe und nach Behauptung |
| `byinfo.py` | `python3 messung/hauptziel/byinfo.py DATEI` | Kalibrierung nach Behauptungsgruppe (nachts / erste Nacht / ohne Info) und Partielänge. Gruppen nur für Trouble Brewing eingetragen |
| `miss.py` | `python3 messung/hauptziel/miss.py DATEI` | Wo der Dämon verfehlt wird: Gruppe des Dämons gegen Gruppe des Vordersten. Gruppen nur für Trouble Brewing eingetragen |
| `lies.py` | `python3 messung/hauptziel/lies.py SKRIPT DATEI` | Spielt die Partien nach und ordnet jede nach den Lügen der Guten (keine, versteckt, Chaos); schreibt `DATEI.kinds.json`. Nur für alte Dateien ohne Feld `lie` nötig |
| `kv.py` | `python3 messung/hauptziel/kv.py ALT.json NEU.json` | Korpus-Vergleich: Weltenzahl, geänderte Prozente, anderer Sitz vorn, größte Verschiebungen |
| `why2.py` | `python3 messung/hauptziel/why2.py BRETT…` | Für Korpus-Bretter: Welten gruppiert nach Dämon, Außenseiter-Zahl und Schergen, mit und ohne Taschen-Gewicht |

## Grundmessungen in `messung/daten/hauptziel/`

Gegen diese Dateien vergleichen, statt neu zu messen. Der Dateiname nennt Skript, Zahl der Partien (ab Seed 0, 7–10 Spieler, 4 Nächte) und den Commit.

| Datei | Stand | Dämon vorn |
|---|---|---|
| `TB_600_b67f464.jsonl` | **main heute: Preis nach der Behauptungswelt** (17.11.2026) | 375 von 600 |
| `BMR_450_b67f464.jsonl` | dito | 238 von 450 |
| `SV_150_f2edd2f.jsonl` | dito (Stand f2edd2f; TB und BMR dort in Stichproben von 80 und 50 Partien gleich wie b67f464) | 98 von 150 |
| `TB_600_d0a36ac.jsonl` | böse Bluffer melden Zeilen (16.11.2026) | 344 von 600 |
| `BMR_450_d0a36ac.jsonl` | dito | 215 von 450 |
| `SV_150_d0a36ac.jsonl` | dito | 98 von 150 |
| `TB_600_47b76b9.jsonl` | Lügner schweigt, Bluffer stumm | 405 von 600 |
| `BMR_450_3fb6236.jsonl` | Lügner schweigt, Bluffer stumm | 270 von 450 |
| `SV_150_3fb6236.jsonl` | Lügner schweigt, Bluffer stumm | 106 von 150 |
| `TB_1500_9114cfc.jsonl` | Taschen-Gewicht, Lügner verrät noch seine Zeilen | 994 von 1.500 |
| `BMR_450_de350b0.jsonl` | Taschen-Gewicht Stufe 2 | 269 von 450 |
| `SV_150_9114cfc.jsonl` | Taschen-Gewicht | 108 von 150 |

Seit 47b76b9 schweigt der grundlose Lügner. Seit d0a36ac melden böse Bluffer, was ihr behaupteter Charakter in der Welt der Behauptungen erführe (`tests/claims.py`, `told_table`); `dmeas.py` schreibt die Zahl dieser Zeilen ins Feld `bluffed`. Seit b67f464 kostet eine erfundene Zeile 0,7, wenn sie zu den Behauptungen am Tisch passt, sonst 0,2; Entscheidungen kosten nichts, außer „wurde zu X“ und „war besessen“ (seit f2edd2f). Neue Solver-Änderungen gegen die b67f464-Dateien messen. Die Versuche zum Preis liegen in `versuche/` (`variante.py`, `vergleich.py`; sie stammen von vor b67f464).

Ein Lauf: `python3 messung/dmeas.py TB OUT.jsonl 0 600 4` (etwa 25 bis 60 Minuten, im Hintergrund starten).
