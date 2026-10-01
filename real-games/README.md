# Echte Partien

Partien von echten Tischen als gespeicherte Bretter der Seite, mit der Auflösung aus dem Grimoire. Jede lässt sich auf der Seite öffnen (**…** → **Open a file**) oder hier auswerten:

    node tools/review_game.mjs real-games/<datei>.json

Bewertet wird nach dem Maßstab des Tisches: Stand der wahre Dämon an jedem Morgen vorn?

---

## 2026-10-01-tb-marionette-stream.json

**Quelle:** ein gestreamtes Online-Spiel „Trouble Brewing with a Marionette“, 12 Spieler, Storyteller Avery. Abgeschrieben aus einem automatischen Transkript ohne Sprecherangaben. Der Gastgeber des Streams ist Ben, der im Spiel auch „Alfred“ genannt wird.

**Grimoire:** Sam Imp (Saint-Claim) · Cosmo Marionette (glaubte Fortune Teller) · Ekken Poisoner (Monk-, dann Undertaker-Claim) · Mullabuck Drunk (glaubte Empath) · Ben Butler · Chiz Chef · Patters Ravenkeeper · Naya Slayer · Chris Investigator · Jackie Monk · Alejo Virgin · Emily Mayor. Gutes Team gewinnt an Tag 6 durch die Hinrichtung von Sam.

**Verlauf:**

| | Tod | Angaben |
|---|---|---|
| Nacht 1 | – | Chef 1 · Investigator: Ekken oder Patters ist Poisoner · Empath 0 · FT Emily+Jackie ja |
| Tag 1 | Chiz hingerichtet | |
| Nacht 2 | Naya | Empath 0 · Undertaker: Chiz war Chef · FT Ekken+Chris nein |
| Tag 2 | Patters hingerichtet | |
| Nacht 3 | Mullabuck | Undertaker: Patters war Poisoner · FT Mullabuck+Alejo ja |
| Tag 3 | Ekken hingerichtet | Ekken nominiert die Virgin Alejo, nichts passiert |
| Nacht 4 | Chris | FT Jackie+Chris nein |
| Tag 4 | Emily hingerichtet | |
| Nacht 5 | Alejo | FT Jackie+Ben ja |
| Tag 5 | keine Hinrichtung | |
| Nacht 6 | Jackie | FT Ben+Chris ja |

**Unsicher:**

- **Sitzordnung:** Im Transkript belegt sind nur die Nachbarschaften Jackie–Emily, Mullabuck–Ekken, Ekken–Ben, Ben–Chris und Chris–Alejo. Dass Cosmo neben Sam saß, folgt aus der Marionette. Die übrigen fünf Plätze sind geraten. Vier verschiedene Anordnungen geben dasselbe Bild (siehe unten).
- **Claims:** Pro Sitz steht der letzte öffentliche Claim. Emily bleibt beim Mayor, obwohl sie an Tag 1 öffentlich als Slayer auf Sam geschossen hat. Alejos Spaßschuss auf Naya ist weggelassen, Naya hat nie geclaimt. Die Seite kennt nur einen Claim pro Sitz, also sieht der Rückblick jeden Claim schon am ersten Morgen.
- **FT Nacht 2:** „Ekken und jemand, nein“. Der zweite Sitz ist Chris, weil Cosmo Chris später „ein früheres Nein“ nennt.
- **Nicht eingetragen:** die Wahl des Mönchs, die Wahl des Butlers und die Stimmen. Bei Trouble Brewing rechnet der Solver mit keiner davon.

**Ergebnis (01.10.2026):**

- **Regelprüfung bestanden:** Die wahre Welt ist an allen sechs Morgen gültig. Ihr Gewicht ist 1,0, nach den beiden erfundenen Undertaker-Angaben von Ekken 0,4 × 0,4 = 0,16.
- **Tischprüfung aus Bens Sicht:** Das Transkript ist aus Bens Sicht, er hat das Butler-Token selbst gezogen. Deshalb steht sein Sitz auf **This seat is me**: Butler, außer er wäre die Marionette.

  | Morgen | Sams Platz | Sam | vorn |
  |---|---|---|---|
  | 1 | 1 | 24–27 % | Sam |
  | 2 | 1 | 29–35 % | Sam |
  | 3 | 2–3 | 23–28 % | Emily 34–37 % |
  | 4 | 2–3 | 14–28 % | Emily 43–64 % |
  | 5 | 1 | 93–97 % | Sam |
  | 6 | 1 | 97–99 % | Sam |

  Die Bereiche umfassen mehrere Läufe, denn die Zahlen kommen aus einer Stichprobe. Mit **Role is confirmed** statt **This seat is me** ändert sich praktisch nichts. In vier Sitzordnungen ist Sam am letzten Morgen 97–99 % vorn.
- **Ohne Bens Token** (nur sein Claim): Sam stand auf Platz 2 bis 3, nie vorn. Vorn lag Ben, am letzten Morgen mit 50–80 %.
- **Warum Ben ohne sein Token vorn lag:** Ohne Bauchgefühl gibt es eine billigere Welt als die wahre. Ben ist Imp mit Butler-Bluff, Cosmo ist ein nüchterner Fortune Teller, dessen Ja-Ergebnisse auf Ben in Nacht 5 und 6 stimmen. Patters ist der Poisoner, das deckt der Investigator. Ekken ist der Drunk, dann sind seine Undertaker-Angaben kostenlos, und die Virgin löst bei einem Outsider ohnehin nicht aus. Die wahre Welt muss dagegen zwei erfundene Angaben bezahlen. Dieselbe Lesart hatte Cosmo am Tisch selbst: „Wenn ich gut bin, ist es Ben.“ Der Tisch entschied nach Bauchgefühl (Bens Butler-Witz kam, bevor er die Bluffs kennen konnte). Als Lesart −2 eingetragen, liegt auch dann Sam vorn mit 65 %.
- **Rollen teils falsch, Dämon richtig:** Am Ende hält der Solver Patters (57 %) statt Ekken für den Poisoner, weil Ekkens erfundene Undertaker-Angaben Gewicht kosten.
