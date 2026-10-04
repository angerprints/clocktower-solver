# Messläufe

Skripte und Rohdaten der Messungen vom 03. und 04.10.2026. Bis dahin lagen
sie nur im Arbeitsordner einer Sitzung und wären mit ihr verschwunden.

Alle Skripte werden **aus dem Hauptordner des Repos** gestartet, zum Beispiel
`python3 messung/sim5.py BMR 3000 4`. Sie ändern nichts am Code. Nichts hier
gehört zu den Tests oder zur Website.

Zwei Dinge, die jede Messung über mehrere Nächte betreffen (ROADMAP, offene
Stellen 26 und 27):

- Seit dem 04.10.2026 beendet der Simulator eine Partie, wenn Böse gewonnen
  hat. Eine Partie kann also kürzer sein als verlangt: `deal.ended_at` nennt
  den Moment (`None` heißt offen), `deal.game_ends_after` die letzte
  gespielte Nacht. Vorher lief sie weiter, und entschiedene Partien mussten
  herausgefiltert werden.
- Seit dem 04.10.2026 trägt `deal.record()` die stillen Nächte und die Tage
  ein, nach denen die Partie weiterging (`quiet_nights`, `days_done`). Jeder
  Lauf, der sein Brett aus `record()` baut, sagt dem Solver also beides.
  `record(told=False)` lässt beides weg. Die Skripte der Messungen vom 03.
  und 04.10. (`dmeas.py`, `dtype.py`, `dcond.py`, `quiet.py`, `attr.py`,
  `sim6.py`) benutzen das, damit ihre Rohdaten nachstellbar bleiben.

## Wahre Welt gehalten

| Skript | Aufruf | Was es misst |
|---|---|---|
| `sim5.py` | `SKRIPT N NÄCHTE [START]` | Wie oft der Solver die Welt verwirft, die wirklich gespielt wurde. Zählt mit, was in den Partien vorkam (Schläger, Meuchelmörder, …). `SKRIPT` ist `TB`, `BMR`, `SV` oder `EASTER`. |
| `sim6.py` | `SKRIPT N NÄCHTE [START]` | Dasselbe, einmal ohne und einmal mit eingetragenen stillen Nächten. |
| `svclass.py` | `N NÄCHTE` | Sects & Violets: verworfene Partien nach Barbier-Tausch sortiert. |
| `sim4c.py` | `SKRIPT NÄCHTE SEED…` | Eine Partie im Detail: Rollen, Tode, welche Zeile die Welt kostet. |
| `sim4d.py` | `SKRIPT NÄCHTE SEED` | Dieselbe Partie von innen: Ursachen und Störquellen je Nacht. |
| `cap.py` | `NÄCHTE SEED…` | Hält die wahre Welt bei verschiedenen Grenzen für die Erzählungen der Nächte? |
| `benchcap.py` | `GRENZE NÄCHTE SEED…` | Rechenzeit und Ergebnis einer vollen Auswertung bei einer Grenze. |

## Simulator gegen Night-Walk

| Skript | Aufruf | Was es misst |
|---|---|---|
| `nw2.py` | `SKRIPT N NÄCHTE` | Nacht für Nacht: Stimmen Simulator und Night-Walk bei den Toten überein? |
| `nw3.py` | `SKRIPT NÄCHTE SEED…` | Eine abweichende Nacht im Detail. |
| `tbhash.py` | – | Prüfsumme über 600 Partien je Skript (ohne Bad Moon Rising). Gleiche Prüfsumme vor und nach einer Änderung heißt: Der Simulator spielt dort Zeichen für Zeichen dasselbe. |
| `find5.py` | `[SEED…]` | Sucht Partien mit 7 Spielern, in denen ein bestimmter Fall vorkommt. So wurden die benannten Bretter in `tests/make_fixtures.py` ausgesucht. |

## Python gegen JavaScript

| Skript | Aufruf | Was es misst |
|---|---|---|
| `dumpworlds.py` | `BRETTNAME aus.json` | Alle Welten eines Korpus-Bretts mit ihrem Preis in Python. |
| `cmp2.mjs` | `aus.json` | Dieselben Welten in JavaScript, mit Abweichungen. Aus `messung/` starten. |

## Wie oft wird der Dämon gefunden (03.10.2026)

| Skript | Aufruf | Was es tut |
|---|---|---|
| `dmeas.py` | `SKRIPT aus.jsonl ERSTER LETZTER NÄCHTE` | Spielt Partien (7 bis 10 Spieler), wertet jedes Brett voll aus und schreibt je Partie eine Zeile: Rang des wahren Dämons, Dämon-Werte aller Sitze, Rollen, Tode. Etwa 4 Sekunden je Partie. |
| `dana.py` | `datei.jsonl [SCHLÜSSEL] [offen]` | Tabelle daraus. `SCHLÜSSEL` ist ein Feld (`kind`, `n`, `sampled`, …). Mit `offen` nur Partien, die nach vier Nächten noch offen sind. **Ohne `offen` sind die Zahlen geschönt.** |
| `dtype.py` | `aus.jsonl ERSTER LETZTER` | Bad Moon Rising: an welchen Dämon-Typ der Solver glaubt. |
| `dcond.py` | `ORDNER TEIL` | Rang des wahren Dämons, wenn der Typ bekannt wäre. Liest `dt_a.jsonl` und `dt_b.jsonl` aus `ORDNER`. |

## Stille Nächte (04.10.2026)

| Skript | Aufruf | Was es tut |
|---|---|---|
| `whyquiet.py` | `N` | Warum Nächte im Simulator wirklich still waren, je Dämon. Ohne Solver. |
| `attr.py` | `SEED…` | Welt für Welt: welche Erklärungen der Solver für eine stille Nacht im Angebot hat. Nur Bretter, die exakt gezählt werden. |
| `quiet.py` | `aus.jsonl TEIL VARIANTEN [all]` | Der Versuch: tauscht **im Speicher** den Schritt aus, mit dem `deaths._account_for` eine stille Nacht erklärt, und wertet jede Partie je Variante aus. `TEIL` ist 0 oder 1 (jede zweite Partie, für zwei Prozesse). Ohne `all` nur Partien mit zwei oder drei stillen Nächten. |
| `qana2.py` | `ORDNER` | Tabellen aus den Läufen von `quiet.py`, nur offene Partien. |

Varianten von `quiet.py`: `base` (der Solver, wie er ist, mit eingetragenen
stillen Nächten), `no_dead`, `no_tealady`, `no_fool`, `no_sailor`,
`no_innkeeper`, `no_exorcist` (je eine Erklärung gestrichen), `no_free` (alle
fünf Gratis-Erklärungen gestrichen), `logic` (strenge Lesart: gestörter Dämon
als eigene Erklärung, zwei Erklärungen für zwei Shabaloth-Kills, das Ziel der
Pukka schützt sich nicht selbst).

`quiet.py` findet seine Stelle über den Quelltext von `_account_for`. Ändert
sich diese Funktion, bricht das Skript mit einer Meldung ab, statt falsch zu
messen.

## Stille Nächte eingetragen, Dämon am letzten offenen Morgen (04.10.2026)

| Skript | Aufruf | Was es tut |
|---|---|---|
| `sim5.py` | wie oben | Seit dem 04.10. mit eingetragenen stillen Nächten und Tagen. |
| `quietwhy.py` | `NÄCHTE N` | Bad Moon Rising: sortiert die Partien, in denen eine eingetragene stille Nacht die wahre Welt kostet, nach dem wahren Grund der Nacht. |
| `quietsweep.py` | `NÄCHTE N VARIANTEN` | Dieselbe Frage für `base`, `source` (dazu die Erklärung „der Dämon selbst wurde gestoppt“) und `logic` (strenge Lesart), im Speicher wie `quiet.py`. |
| `dmorgen.py` | `SKRIPT aus.jsonl ERSTER LETZTER [NÄCHTE] [untold]` | Spielt jede Partie bis zu ihrem Ende (höchstens 6 Nächte) und wertet das Brett am letzten Morgen aus, an dem sie noch offen ist. Stille Nächte und Tage sind eingetragen. Eine Zeile je Partie, lesbar mit `dana.py` (ohne `offen`, Schlüssel zum Beispiel `kind`, `morning`, `how`, `n`). |

Rohdaten dazu in `daten/morgen/`: `dm_bmr.jsonl` und `dm_sv.jsonl`, je 400
Partien, Seeds 0 bis 399, Spielerzahl `[7, 8, 9, 10][seed % 4]`, gemessen mit
dem Stand von Commit be39613.

`dmorgen_regel.py` ist `dmorgen.py` mit einer Regel, die nur im Speicher
ausprobiert wird: Die Partie läuft, also leben wirklich mindestens drei.
`dm_zombuul_basis.jsonl` und `dm_zombuul_regel.jsonl` sind die 90
Zombuul-Partien ohne und mit dieser Regel (Stand Commit df17b6c).

`dm_bmr_weg1.jsonl` sind dieselben 400 Partien Bad Moon Rising nach dem
Einbau der Erklärung „der Dämon selbst wurde gestoppt“ (Commit e2d215e). Die
Rechenzeiten in dieser Datei stammen von vor den beiden Beschleunigungen und
sind zu hoch, die Ergebnisse gelten.

    python3 messung/dana.py messung/daten/morgen/dm_bmr.jsonl kind
    python3 messung/dana.py messung/daten/morgen/dm_sv.jsonl kind

## Rohdaten in `daten/`

Alle mit dem Code von Commit 605d1d4 (Solver) gemessen, je 400 Partien,
Seeds 0 bis 399, Spielerzahl `[7, 8, 9, 10][seed % 4]`, vier Nächte.

Gemessen mit dem Simulator **vor** der Reparatur vom 04.10.2026. Die Zeilen
der offenen Partien gelten weiter, denn die spielt der Simulator Zeichen für
Zeichen wie vorher. Die Zeilen der entschiedenen Partien (`alive` höchstens 2)
lassen sich nicht mehr nachstellen: Dort endet die Partie jetzt früher und
bekommt andere Claims.

| Datei | Woraus | Inhalt |
|---|---|---|
| `dm_bmr.jsonl`, `dm_sv.jsonl` | `dmeas.py` | Rang des Dämons, stille Nächte **nicht** eingetragen. |
| `dt_a.jsonl`, `dt_b.jsonl` | `dtype.py` | Geglaubter Dämon-Typ, 382 laufende Partien Bad Moon Rising. |
| `dc_0.jsonl`, `dc_1.jsonl` | `dcond.py` | Rang bei bekanntem Typ. |
| `told/all0.jsonl`, `told/all1.jsonl` | `quiet.py … base,logic all` | Alle 382 Partien, stille Nächte eingetragen. |
| `told/ab0.jsonl`, `told/ab1.jsonl` | `quiet.py … no_…` | Die sieben Streich-Varianten. **Abgebrochen bei 74 von 130 Partien.** |
| `attr_z.log`, `zseeds.txt` | `attr.py` | Zählung über 33 kleine Zombuul-Partien und deren Seeds. |

Die Tabellen der Berichte lassen sich daraus ohne neue Rechnung herstellen:

    python3 messung/dana.py messung/daten/dm_bmr.jsonl kind offen
    python3 messung/dana.py messung/daten/dm_sv.jsonl kind offen
    python3 messung/qana2.py messung/daten

**Ändert sich der Simulator, ergeben dieselben Seeds andere Partien,** und die
Rohdaten passen nicht mehr zu neuen Läufen. Dann alles neu messen, nicht
mischen.
