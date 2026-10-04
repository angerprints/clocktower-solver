# Clocktower-Solver — Roadmap, neu bewertet

**Stand:** 04.10.2026 (Neubewertung vom 29.09.2026, seither fortgeschrieben)
**Projekt:** botc-solver (Tischhilfe, gehostet auf angerprints.github.io/clocktower-solver)
**Ausgangslage:** 959 Tests grün, 0 unmögliche Bretter auf Trouble Brewing, Bad Moon Rising, Sects & Violets und in allen fünf Charakter-Gates. solver.py nach dem Aufräumen 3.596 Zeilen.

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
| Sects & Violets | Artist (nur aufgezeichnet) |

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

### Phase 0 — Zuhause und Auslieferung · *erledigt am 28.09.2026*

Der komplette Quellcode liegt jetzt im GitHub-Repo `angerprints/clocktower-solver`, nicht mehr nur in einem Container. GitHub Pages liefert die Seite aus `docs/` aus.

So wird ab jetzt veröffentlicht:

```
python tools/build_site.py      # baut docs/ neu
git add -A && git commit        # Quellcode und Seite zusammen
git push                        # nach ein bis zwei Minuten ist die Seite aktuell
```

Kein ZIP mehr, kein Hochladen von Hand. Ein Container-Reset kostet nichts mehr, weil alles auf GitHub liegt.

### Phase 1 — Der unabhängige Schiedsrichter · *erledigt am 28.09.2026*

`tools/engine_bridge.py` macht aus jeder Partie der Engine in `J:\dev\clocktower` ein Brett und aus ihrer Austeilung die wahre Welt. Die Engine wird dabei nur gelesen, nie verändert.

Zwei Modi: **grimoire** (jeder Sitz ehrlich, auch gestörte Information) prüft die Regeln, **tisch** (nur öffentliche Behauptungen, Böse bluffen) prüft das Werkzeug so, wie man es benutzt.

```
Ergebnis nach den Korrekturen:
  grimoire   300 Partien, 5 bis 9 Spieler, alle Komplexitäten   0 verworfen
  tisch      140 Partien mit bluffenden Bots                    0 verworfen
```

**Vier Regelfehler im Solver gefunden**, alle in Python und JavaScript behoben:

1. **Ein vergifteter Dämon tötet niemanden.** Eine ruhige Nacht konnte der Solver nur mit einem Schild vor dem Opfer erklären. Ein Giftmischer, der den eigenen Imp trifft, machte das Brett unmöglich. Jetzt trägt der Kill des Dämons seinen Täter. Gewichtet mit 0,05, weil das an deinem Tisch selten vorkommt. Damit bleibt ein behaupteter Mönch nach einer ruhigen Nacht zu 99,5 % echt statt vorher zu 100 %.
2. **Hat der Dämon getötet, muss er funktioniert haben.** Die Gegenrichtung von 1.
3. **Die Wahrsagerin bekommt auch für einen toten Dämon ein Nicken.** Der Solver fragte, wer in dieser Nacht als Dämon handelt. Nach einer Übernahme durch die Scharlachrote Frau war ein wahres „Ja" auf den hingerichteten Imp für ihn unmöglich.
4. **Eine Sweetheart macht *einen* Spieler betrunken, nicht alle.** Die Planung der Störungen behandelte jede kostenlose Quelle so, als träfe sie jeden, den sie erreichen kann. Das stimmt für den Trunkenbold und den Minnesänger. Sweetheart, Vigormortis und Goon wählen aber genau einen. Nach dem Tod einer Sweetheart galt deshalb die ganze Stadt als betrunken, und „der Dämon hat funktioniert" (Punkt 2) war unmöglich. Aufgefallen ist das an vier S&V-Partien des eigenen Simulators, nicht an der Engine. Punkt 2 hat den alten Fehler nur sichtbar gemacht. Das Brett, das im ersten Commit von 268 auf 76 Welten fiel, hat wieder 268. Die 76 waren dieser Fehler, keine Erkenntnis.

Dazu ein Fehler, den ich beim Beheben selbst eingebaut und wieder entfernt habe: Die neue Erklärung für ruhige Nächte ohne Giftquelle verdrängte in der auf 24 Kombinationen begrenzten Suche die echte Geschichte.

**Offene Designfrage:** Der Solver nimmt an, dass das Spiel weiterläuft. Stirbt der Dämon ohne Nachfolger oder wird eine funktionierende Heilige hingerichtet, ist das Brett für ihn unmöglich, obwohl das Spiel einfach vorbei ist. Während einer Partie stimmt die Annahme. Wer ein fertiges Spiel nachträglich eingibt, bekommt „unmöglich". Die Brücke schneidet deshalb das Spielende ab.

**Gegenrichtung noch offen:** Ob die Engine Regelfehler hat, die der Solver findet. In 440 Partien hat keine einzige Abweichung auf einen Fehler der Engine gezeigt. Alle Treffer lagen beim Solver oder in der Brücke.

### Phase 2 — Deine Skripte vollständig · *erledigt am 29.09.2026*

1. **Ogre** und **Marionette** · *erledigt am 28.09.2026.* Easter Trouble ist bis auf den Artist vollständig.
2. **Mastermind** · *erledigt am 29.09.2026.* Bad Moon Rising ist vollständig.
3. **Sects & Violets:** die 22 von 1000 Simulator-Partien, die der Solver verwarf, und **Mutant**, **Cerenovus**, **Savant** · *erledigt am 29.09.2026.* Alle drei Grundskripte sind komplett, nur der Artist bleibt „aufgezeichnet".
4. Artist bleibt „aufgezeichnet": Seine Frage ist frei formuliert und lässt sich nicht als Regel prüfen.

**Sects & Violets aufgeräumt.** Die 22 Fehlfälle waren kein einzelner Fehler, sondern ein Muster: Mehrere Charaktere verändern in derselben Partie, wer was ist (Schlangenbeschwörer, Pit-Hag, Barbier, Fang Gu, Farmer, Ogre), und der Solver hat alle Nächte auf einmal betrachtet. Ein Barbier-Tausch in Nacht 3 sah dann nicht, dass der Schlangenbeschwörer in Nacht 2 schon getauscht hatte. Neu: Sind zwei oder mehr dieser Charaktere im Spiel, baut der Solver die Geschichte **Nacht für Nacht** auf. Jede Regel sieht dabei, was die anderen vor ihr getan haben, aber nicht ihre eigenen früheren Änderungen. Aussortiert wird erst ganz am Ende. Mit nur einem solchen Charakter läuft der alte, schnellere Weg.

Dabei gefunden und in Python und JavaScript behoben:

- *Solver:* Der Mathematiker zählt nur **lebende** gestörte Spieler. Zwei Schlangenbeschwörer-Tausche hintereinander sehen einander. Ein Barbier, den die Pit-Hag erschaffen hat, zählt als Barbier. Ein getauschter Dämon behält beim Barbier-Tausch seine böse Seite. Die Vigormortis vergiftet nur für Schergen, die sie **selbst getötet** hat. In der Nacht, in der eine Sweetheart stirbt, muss der Dämon nicht getötet haben. Ein wahres Ergebnis unter dem Vortox ist erklärt, wenn der Vortox aus ist **oder** die Quelle gestört war (vorher nur das Erste). Die Geschichten einer Welt waren nicht nach Zeit sortiert, eine spätere Änderung konnte eine frühere überschreiben.
- *Simulator:* Tötet der Fang Gu einen Außenseiter, springt er (vorher fehlte das ganz). Der Barbier tauscht nur Lebende, auch bei einem Tod in der Nacht. Der Philosoph handelt ab Nacht 2 an der Stelle seines neuen Charakters. Die Pit-Hag macht keinen Dämon zu etwas anderem. Tote bekommen keine gestörten Informationen mehr.

Geprüft: 2000 S&V-Partien mit 7 bis 11 Spielern und 4 Nächten, keine verwirft die Wahrheit, der Fang Gu springt dabei über 10-mal. TB, BMR und Easter: je 0 von 2000, auch mit 5 Nächten. Engine: 300 Grimoire-Partien und 70 Tisch-Partien mit Bot-Hirn, 0 verworfen. Sieben gespielte Partien liegen jetzt als feste Bretter im Korpus, Python und JavaScript stimmen auf allen 783 Welten überein. **Offen:** Mit 5 Nächten verwirft der Solver genau eine von 2000 S&V-Partien (Seed 181), noch nicht untersucht.

**Mutant, Cerenovus, Savant.** Alle drei waren bisher „nicht modelliert" oder „nur aufgezeichnet". Jetzt:

- **Mutant:** Er darf nicht sagen, dass er ein Außenseiter ist, sonst wird er vielleicht hingerichtet. Also steht er **immer hinter einem Townsfolk-Claim**, und das kostet die Welt nichts. Vorher baute der Solver eine Welt mit Mutant nur, wenn jemand „Mutant" behauptete, also genau dann, wenn der Mutant es nie tut. Gemessen an 60 S&V-Partien mit 7 bis 9 Spielern: Auf dem Sitz des echten Mutanten stieg die Wahrscheinlichkeit „Mutant" von 0 % (17 von 18 Partien) auf 17 % im Mittel, und kein Brett ist mehr ohne Welten (vorher 6 von 60). Der Dämon steht im Median auf Rang 1 statt 2. **Preis:** Viele S&V-Bretter haben jetzt mehr legale Welten, eines 7.320 statt 1.104. Das Lösen dauert im Mittel 6,8 statt 2,9 Sekunden, einzelne Bretter über 40 Sekunden.
- **Savant:** Die zwei Sätze bleiben Freitext. Zusätzlich kann jeder Satz in einer von neun prüfbaren Formen eingegeben werden: „X ist böse", „X ist gut", „X und Y sind auf derselben Seite", „auf verschiedenen Seiten", „X ist der C", „C ist im Spiel", „C ist nicht im Spiel", „es gibt N Außenseiter", „der Dämon ist einer von …". Sind beide Sätze so eingegeben, wird das Paar gewogen: Genau einer war wahr, unter dem Vortox beide falsch, ein gestörter Savant kann alles hören. Fehlregistrierung (Einsiedler, Spion) ist erlaubt. Der Simulator lässt den Savant jetzt jeden Tag fragen: 538 gewogene Paare in 1000 Partien, keines verwirft die Wahrheit. Zur Gegenprobe wurde je ein Paar in zwei gleiche Sätze verfälscht, dann verwirft der Solver 120 von 201 Brettern (der Rest ist mit Gift oder Vortox erklärbar).
- **Cerenovus:** Der Wahnsinn selbst hinterlässt keine Spur. Drei Dinge sieht der Tisch aber: eine Hinrichtung wegen gebrochenem Wahnsinn (gab es schon), die neue Zeile **„wurde verrückt gemacht als X"**, die der Gewählte selbst sagt und die einen lebenden Cerenovus in jener Nacht belegt, und einen guten Spieler, der etwas Falsches behauptet. Diese Lüge kostet in einer Welt mit lebendem Cerenovus 0,25 statt 0,02, höchstens eine pro Nacht. Das wirkt, wenn der Sitz als „unsicher" markiert ist.

**Offen:** Zwei seltene S&V-Partien verwirft der Solver noch, beide mit einem Philosophen, der den Schlangenbeschwörer nahm und tauschte, während der echte Beschwörer in derselben Nacht auch tauschte (Seed 836 bei 4 Nächten, vermutlich auch Seed 181 bei 5 Nächten). Die Regeln sind dort selbst unklar: Endet die Trunkenheit des echten Beschwörers, sobald der Philosoph kein Philosoph mehr ist?

**S&V schneller (29.09.2026).** Gemessen an 30 gespielten S&V-Brettern mit 7 bis 11 Spielern, so wie die Seite sie im Browser rechnet: **98,6 → 65,3 Sekunden** gesamt. Die schwersten Bretter: 30 → 19 bis 21 s, 21 → 11 s, 13 → 6 s. Kein Ergebnis hat sich verändert, geprüft Brett für Brett im Korpus und an allen exakt gerechneten Messbrettern.

- *Nacht für Nacht nur, wo es nötig ist:* Ob die langsame Nacht-für-Nacht-Rechnung läuft, entschied das Skript. Auf S&V also jede Welt. Jetzt entscheidet die einzelne Welt: nur wenn in ihr zwei Arten von Tausch wirklich passieren können.
- *Die Zeitleiste merkt sich, welcher Sitz sich ändert:* Die Frage „wer war wann was" lief jedes Mal durch alle Änderungen und las jede Phase neu, 14 Millionen Mal auf einem Brett.
- *Der Barbier kostet am meisten:* Stirbt er, entsteht für jedes Sitzpaar eine eigene Geschichte, bei zehn Spielern 45 bis 55. Seine Angebote und die Todeserklärungen der Nächte vor dem Tausch werden jetzt einmal pro Welt berechnet statt einmal pro Geschichte. Unnötige Vergleiche beim Zusammenführen der Geschichten fallen weg.

Beim Messen gefunden: Die Testhilfe für gespielte Bretter schrieb Stimmen und Nominierungen an eine Stelle, die weder Seite noch Server lesen. Die sieben gespielten Bretter im Korpus liefen deshalb ohne Stimmen. Behoben. Über den Weg der Seite halten jetzt 300 von 300 S&V-Partien die Wahrheit.

**Rechnung im Hintergrund (30.09.2026).** Die Seite löst jetzt in einem Web Worker, einem eigenen Thread neben der Seite. Sie friert bei langen Brettern nicht mehr ein und zeigt den Fortschritt in Prozent in der Mitte. Der Knopf „Solve" wird während der Rechnung zu „Stop". Die Empfindlichkeitsprüfung zeigt ebenfalls Prozent. Kann ein Browser keinen Modul-Worker starten, rechnet die Seite wie bisher direkt. Geprüft in Chromium auf dem schwersten Messbrett (22 s): 447 von 448 Zeittakten der Seite liefen während der Rechnung weiter, 147 Fortschrittsmeldungen, dasselbe Ergebnis wie direkt gerechnet. Stopp, erneutes Lösen, Empfindlichkeitsprüfung und der Rückfall ohne Worker funktionieren. An der Rechenzeit selbst ändert sich nichts.

**Tischregel Barbier (29.09.2026, deine Entscheidung):** Ein Barbier-Tausch wird nur noch betrachtet, wenn ein Sitz gestorben ist, der Barbier behauptet hat. Das gilt als Claim oder in einer Zeile „wurde/war Barbier". Gemessen an denselben 30 Brettern: **65,3 → 52,3 Sekunden**, zusammen mit dem Obigen also 98,6 → 52,3. Bretter mit einem offen genannten toten Barbier bleiben so langsam wie vorher (bis etwa 20 s). **Preis:** Von 2000 S&V-Partien mit 4 Nächten erklärt der Solver jetzt 10 nicht mehr, etwa eine von 200. In allen zehn hatte sich der Barbier versteckt (anderer Claim oder nur „ich wache nie auf"), starb, und der Dämon tauschte wirklich.

**Tischregel Barbier-Gewichtung (30.09.2026, deine Entscheidung):** An deinem Tisch tauscht der Dämon nach einem Barbier-Tod meistens, oft mit einem eigenen Schergen. Der Tod ist laut, der Tausch leise. Deshalb sind jetzt zwei Fragen getrennt. *Welt gegen Welt:* Ein Tausch Dämon ↔ Scherge kostet nichts, jeder andere Tausch 0,15. *Innerhalb einer Welt* („wer ist jetzt was"): „kein Tausch" bekommt 25 %, die Dämon-Scherge-Paare teilen sich 37,5 %, alle übrigen Paare die anderen 37,5 %, egal wie viele es sind. Vorher bekamen 45 Paare à 0,15 fast neun Zehntel und der übliche Tausch fast nichts. Beide Anteile stehen in der Empfindlichkeitsprüfung.

Gemessen an 129 simulierten S&V-Partien mit genanntem totem Barbier (7 bis 9 Spieler, 4 Nächte). Der Simulator tauscht dabei wie dein Tisch: in 75 % der Fälle, und wenn noch ein Scherge lebt, zur Hälfte mit ihm.

| Fall | Partien | echter Dämon oben | P(echter Dämon) |
|---|---|---|---|
| Tausch Dämon ↔ Scherge | 26 | 16 → 18 | 52,1 → 57,8 % |
| kein Tausch | 40 | 28 → 27 | 60,1 → 59,0 % |
| anderer Tausch | 63 | 28 → 27 | 41,1 → 40,6 % |
| alle | 129 | 72 → 72 | 49,2 → 49,7 % |

**Ausprobiert und verworfen:** Ein zweiter Auslöser sollte Barbier-Tausche auch dann öffnen, wenn jemand einen Rollenwechsel meldet, den nichts erklärt. Dazu gehörte, dass der Solver einen Sitz mit „wurde X, vorher Y" aus Y heraus durchrechnet. Gemessen: Von 14 Partien, die ein versteckter Barbier kostet, rettete das keine einzige. In keiner hatte jemand gemeldet. In den 8 Partien mit Meldung fiel der echte Dämon im Schnitt von 54 auf 34 %. Grund: Ein Tausch betrifft zwei Sitze, meist meldet nur einer. Der Code liegt auf dem Zweig `barber-trigger-experiment`.

**Dabei gefunden, noch offen:** Die Zeile „wurde X" wird nur aufgeschrieben, für die Suche zählt der aktuelle Claim. Ein guter Spieler, dessen Rolle sich geändert hat und der die neue nennt (nach Pit-Hag oder Barbier), wird nie mit seiner wahren Anfangsrolle durchgerechnet. Eine Lösung müsste beide Sitze eines Tauschs zusammen denken.

**Mastermind.** Die Grundidee war schon da: Nach der Hinrichtung des Dämons darf das Spiel einen Tag weiterlaufen. Gefehlt haben drei Bedingungen aus dem Wiki. Nur eine **Hinrichtung** zählt, auch der Nominierende einer Jungfrau und eine Wahnsinns-Hinrichtung, aber kein Schuss des Dämonenjägers. Der Mastermind muss **funktionieren**. Und eine Scharlachrote Frau, die übernehmen könnte, **hat Vorrang**. Die Mastermind-Geschichte ist jetzt markiert und wird zu Forderungen an den Störungsplan: Mastermind nicht gestört, Scharlachrote Frau gestört. Vorher standen beide Geschichten kostenlos nebeneinander.

**Der breitere Test hat mehr gefunden als den Mastermind.** Der bisherige BMR-Test spielte 6 Partien mit 9 Spielern. 300 Partien mit 7 bis 11 Spielern und 4 Nächten verwarfen die Wahrheit **32-mal** – schon vor dem Mastermind. Behoben, jetzt 0 von 1000:

- *Solver:* Ein Aliasing-Fehler in `_night_accounts` (nur Python; JavaScript war richtig): Beim Kombinieren der Nächte teilten sich alle Varianten dieselben Mengen, und die Forderungen verschiedener Erklärungen häuften sich, bis kein einzelner Pukka sie erfüllen konnte.
- *Solver:* Ein Zombuul, der zum ersten Mal hingerichtet wird, stirbt nicht. Der Solver hielt das für einen echten Tod, fand keinen Erben und verwarf jedes solche Brett.
- *Solver:* Ein Glücksspieler, der falsch rät und lebt, war immer „gestört". Eine Teedame neben ihm oder eine aufgezeichnete Wahl des Gastwirts hält ihn aber auch am Leben.
- *Solver:* Der Assassine wacht in Nacht 1 nicht für seine Fähigkeit auf („at night*").
- *Simulator:* Die Trunkenheit des Höflings fehlte (die sechste fehlende Störquelle in seiner Liste). Ein nüchterner Seemann, ein Narr beim ersten Tod und die Nachbarn einer Teedame starben bei Hinrichtungen. Das Gift des Pukka tötete durch jeden Schutz hindurch. Der Assassine wurde nur in Nacht 1 gezählt.

Der Simulator darf jetzt den Dämon hinrichten: Ein Zombuul überlebt das beim ersten Mal, ein funktionierender Mastermind verlängert um einen Tag, danach endet das Spiel. In 1000 Partien: 60 Zusatztage, 75 überlebende Zombuuls, und bei jedem Zusatztag ist die Mastermind-Geschichte die beste Erklärung. Ein dauerhafter Test spielt 200 solche Partien.

**Ogre.** Er wählt in der ersten Nacht einen Spieler und bekommt dessen wahre Gesinnung, auch betrunken oder vergiftet, ohne es zu erfahren. Spion und Einsiedler zählen für ihn als böse (Jinx). Er handelt spät in der Nacht, also sehen Empath, Adliger und Großmutter ihn in Nacht 1 noch als gut. Ab Tag 1 zählt die neue Seite. Neue Protokollzeile „Ogre wählte X": Dann steht seine Seite fest, sofern der Sprecher wirklich der Ogre ist. Ohne diese Zeile wiegt „böse geworden" so viel wie das Verhältnis böser zu guten Sitzen.

**Marionette.** Die Technik für „glaubt, jemand anderes zu sein" war schon allgemein, der Hinweis im Katalog war veraltet. Gefehlt hat nur die Aufbauregel „sitzt neben dem Dämon". Sie steht jetzt als Feld `beside` im Katalog und wird in der Suche und in der Stichprobe geprüft.

**Nebenbei zwei Verbesserungen, die mehr als den Ogre betreffen:**

- *Jede passende Geschichte zählt anteilig.* Bisher bekam die beste Geschichte einer Welt das ganze Gewicht. Ein Ogre, der böse geworden sein könnte, stand dadurch als gut da, sobald „gut geblieben" nichts kostete. Jetzt wird das Gewicht einer Welt nach dem Gewicht ihrer Geschichten aufgeteilt. Das Gewicht der Welt selbst bleibt gleich. Im Korpus ändern sich 11 von 142 Brettern: alle Ogre-Sitze (das leere Easter-Brett 40 → 55 % böse), der Barbier-Tausch, und ein Brett, auf dem Mastermind und Scharlachrote Frau gleich gut passten. Dort gewann vorher zufällig die erste Geschichte.
- *Adliger und Näherin lesen die aktuelle Seite*, wie Empath und Koch schon vorher. Ein guter Giftmischer vom Pit-Hag las sich für sie noch als böse.

Geprüft mit dem eigenen Simulator, der beide Charaktere nach seiner eigenen Lesart der Regeln spielt: 500 Easter-Partien, keine verwirft die Wahrheit. In 34 der 66 Partien mit bösem Ogre ist „Ogre böse" die beste Geschichte, die neue Regel wird also wirklich gebraucht. Die Engine deines Spiels kennt nur Trouble Brewing und kann hier nicht mitprüfen.

### Phase 3 — Gemeinsames Regelwissen für das Spiel

Wenn das Spiel bei v2 ankommt (vorher kommen dort M9 bis M13): kein Solver-Neubau, sondern das Charakterwissen von botc-solver als Grundlage für BMR und S&V in der Engine. Die Schnittstelle wird entschieden, wenn es so weit ist, nicht jetzt.

Das ist auch der Grund, warum botc-solver zweisprachig bleiben sollte. Die Python-Hälfte ist genau die, die das Spiel nutzen kann.

### Phase 4 — Eine echte Partie · *Werkzeug fertig am 30.09.2026, erste Partie ausgewertet am 01.10.2026*

Bleibt wertvoll, auch neben Phase 1: ein gespeichertes Brett aus einer echten Runde, und der Vergleich, was das Werkzeug sagt und was passiert ist. Die Engine-Partien prüfen die Regeln, eine echte Partie prüft, ob das Werkzeug am Tisch hilft.

**Gebaut:** Auf der Seite gibt es unter **…** → **After the game…** die Auflösung. Du trägst ein, wer was war, vorbelegt mit den Claims. **Look back** rechnet jeden Morgen der Partie neu, mit genau dem Wissen, das der Tisch damals hatte: Nacht-Ereignisse bis zu dieser Nacht, Tages-Ereignisse bis zum Vortag. Bewertet wird nach deinem Maßstab, also wo der echte Dämon stand, mit wie viel Prozent, und ob er klarer Hauptverdacht war. Gleichstände werden angezeigt. Die Auflösung wird mit der Partie gespeichert. `tools/review_game.mjs` liefert dieselbe Auswertung für eine Datei, die du mir schickst. Die Anleitung für den Spieleabend steht in `ANLEITUNG-ECHTE-PARTIE.md`.

**Erste Partie (01.10.2026):** ein gestreamtes „Trouble Brewing with a Marionette“ mit 12 Spielern, abgeschrieben aus einem Transkript. Die Datei liegt unter `real-games/`, die Einzelheiten stehen in `real-games/README.md`.

- **Regelprüfung bestanden:** Die wahre Welt ist an allen sechs Morgen gültig. `tests/test_real_games.py` hält das fest.
- **Tischprüfung aus Bens Sicht bestanden:** Das Transkript stammt von Ben, und er kennt sein eigenes Token. Sein Sitz steht deshalb auf **This seat is me**: Butler, außer der Erzähler hat ihn zur Marionette gemacht. Damit liegt Sam an vier von sechs Morgen klar vorn, am Ende mit 96–99 %. An den Morgen 3 und 4 ist es ein Dreikampf mit Emily und Alejo, Sam liegt dort auf Platz 2 bis 3.
- **Ohne Bens eigenes Token** lag Sam nie vorn. Es gibt eine billigere Welt mit Ben als Imp und Butler-Bluff, Cosmo als nüchternem Fortune Teller und Ekken als Drunk. Wer am Tisch mitschreibt, sollte also immer seinen eigenen Sitz markieren.
- **Rollen teils falsch, Dämon richtig:** Am Ende hält der Solver Patters für den wahrscheinlicheren Poisoner (57 %) und Ekken eher für den Drunk. Der Grund ist, dass Ekkens erfundene Undertaker-Angaben Gewicht kosten. Nach dem Maßstab des Tisches ist der Job trotzdem getan.
- **Offene Ideen, nicht gebaut:**
  - Ein Info-Claim, der lange öffentlich bekannt ist und nie stirbt, deutet auf Drunk, Marionette oder böse.
  - Ein Verlauf der Claims pro Sitz. In dieser Partie haben allerdings drei Gute ihren Claim gewechselt, das Signal hätte also in die Irre geführt.

**Als Nächstes:** weitere Partien, am besten selbst am Tisch mitgeschrieben, mit gesicherter Sitzordnung.

### Regelabgleich Bad Moon Rising mit dem Spiel · *erledigt am 02.10.2026*

Der Chat, der das Einzelspieler-Spiel baut, hat alle 25 Charaktere von Bad Moon Rising gegen Wiki, Pukka-Flowchart und diesen Code gelesen und sechs Abweichungen übergeben (`claude/handover-web-solver-bmr-regeln.md`). Alle sechs sind abgearbeitet, in Python und JavaScript, mit Tests.

| Nr. | Stelle | Jetzt |
|---|---|---|
| 1 | Kammerzofe, Dämon in Nacht 1 | **Weg B, duldsam** (deine Entscheidung): Die Dämon-Info ist nicht die Fähigkeit des Dämons, aber beide Zahlen bleiben erlaubt. Nur die Pukka zählt sicher. Der Simulator spielt deinen Tisch und zählt nicht. |
| 2 | Kammerzofe, Verrückte | Zählt, nach dem Plan des Dämons, für den sie sich hält. |
| 3 | Kammerzofe, Professor | Zählt ab Nacht 2, bis jemand wiederbelebt wurde. Ist ein Shabaloth im Spiel, bleibt es danach offen. |
| 4 | Kammerzofe, Pate | Nacht 1, danach nur nach einem Tag, an dem ein Außenseiter starb. |
| 5 | Gift der Pukka | Vergiftet bis zum nächsten Zug der Pukka, getrennt vom Gift des Giftmischers, und es ruht, solange die Pukka selbst gestört ist. |
| 6 | Exorzist und Pukka | Der Exorzist verhindert die Wahl, nicht den Tod: Das Opfer von gestern stirbt, die Nacht danach ist die ruhige. Im Simulator und im Solver. |

**Was dabei zusätzlich herauskam:**

- **Jeder Kill der Pukka kostete ihre Welt 0,35.** Das Gift auf dem späteren Opfer wurde bepreist wie ein Treffer des Giftmischers, als wäre es Glück. Die wahre Welt einer Pukka-Partie wog dadurch im Mittel 0,17, bei den anderen Dämonen 0,78 bis 0,86. Jetzt ist das Gift auf dem, der in der Nacht darauf stirbt, kostenlos: 0,76.
- **Ein Glücksspieler, der richtig rät und in derselben Nacht vom Dämon getötet wird, war unmöglich.** Der Solver las „tot, also falsch geraten“. Gefunden, sobald der Simulator den Glücksspieler vor dem Dämon handeln ließ. Das hätte an einem echten Tisch die wahre Welt gekostet.
- **Der Night-Walk hat einen Fehler im neuen Simulator gefunden:** Das neue Gift liegt, bevor das alte fällig wird. Eine heute vergiftete Teedame schützt den gestern Vergifteten also nicht.
- **Im JavaScript fehlte der Zeitplan des Philosophen** für die Kammerzofe. Python hatte ihn.
- Die Aussage der Übergabe, das Gift ende schon in der Nacht der Wahl, stimmte nur halb: Nacht und folgender Tag teilen sich hier eine Spanne, der Tag war also gedeckt. Es fehlte die Todesnacht.

**Messung:**

- Wahrheit gehalten: 1.500 BMR-Partien über 4 Nächte, 0 verworfen, auf beiden Wegen (direkt und über das Brett der Seite). Schiedsrichter: 440 Engine-Partien, 0 verworfen. 994 Tests grün.
- Simulator gegen Night-Walk, Pukka-Nächte: vorher 14 von 620 verschieden, jetzt 5 von 1.248, und das sind alles die bekannten Fälle „Bastler stirbt in Nacht 1“.
- **Dämon gefunden, alter gegen neuen Giftpreis, 152 Partien:** praktisch unverändert (Pukka: 23 → 22 von 41 vorn, mittlere Sicherheit 35,1 → 36,3 %). Der Preis traf alle Pukka-Welten gleich, deshalb verschiebt er vor allem, *welcher* Dämon es ist, kaum *wer*.
- Das Korpus: 9 von 153 Brettern geben andere Zahlen, alle Bad Moon Rising.

**Nachtrag am selben Tag, deine Entscheidung zur Marionette:** Die Kammerzofe bekommt die Zahl, die das Token der Marionette ergibt, genau wie beim Trunkenbold. Der Solver hatte sie gar nicht gezählt, der Simulator schon immer nach ihrem Token. Kein Skript in den Messläufen hatte beide Charaktere, deshalb fiel es nie auf. Auf einem gemischten Skript mit beiden verwarf der Solver vorher die wahre Welt in 115 von 532 Partien, jetzt in 0.

### Regelprüfung Bad Moon Rising und Sects & Violets · *erledigt am 02.10.2026*

Die Frage war: Sind die Regeln beider Skripte noch richtig umgesetzt? Alle 50 Charaktere wurden gegen das Regelwerk des Spiels, das Pukka-Flowchart und das offizielle Wiki gelesen, mit rund 130 Probebrettern mit bekannter Wahrheit. Der volle Bericht steht in `claude/regelpruefung-bmr-und-snv.md`.

**Regeln, die fehlten (die wahre Welt ging verloren), alle behoben:**

| Skript | Charakter | Was fehlte |
|---|---|---|
| BMR | Teedame | Sie schützte nachts, aber nicht vor der Hinrichtung. |
| BMR | Teedame und Shabaloth | Tötet der Shabaloth erst sie und dann ihren Nachbarn, sterben beide. |
| BMR | Shabaloth | Das Hochwürgen fehlte ganz. |
| BMR | Höfling | Die Trunkenheit lief weiter, wenn der Höfling tot oder beim Wählen selbst gestört war. |
| BMR | Minnesänger | Er löste auch aus, wenn der hingerichtete Scherge überlebte. |
| BMR | Überlebte Hinrichtung | Standen zwei mögliche Retter auf dem Brett, mussten beide funktioniert haben. |
| S&V | **Vigormortis** | **„[−1 Außenseiter]“ fehlte ganz.** Der wahre Beutel kam in der Suche nicht vor. Der wichtigste Fund. |
| S&V | Vigormortis und Schergen | Eine vom Vigormortis getötete Hexe oder ein Cerenovus wirkte nicht weiter. |
| S&V | No Dashii | Ein Nachbar, der nachts die Rolle wechselt, war vorher in derselben Nacht noch vergiftet. |
| S&V | Philosoph | Dasselbe für die Nacht, in der er aufhört oder stirbt, und: beim Wählen gestört, macht er niemanden betrunken. |

**Stellen, die zu viel durchließen, jetzt strenger:** Teedame (Nachbar wird gehängt), Poe (höchstens ein Toter in Nacht 2), Gastwirt (eingetragenes Paar bindet), Exorzist (nennt er den Dämon, tötet der nicht), Mondkind (ein gewählter Guter stirbt), Teufelsadvokat (nicht zweimal hintereinander derselbe), Narr (nur einmal), Vortox (auch ein gestörter Bürger sagt nichts Wahres, nach dem Wiki), Böser Zwilling (guter Zwilling gehängt heißt Spielende), Hexe (keine Fähigkeit bei drei Lebenden).

**Berichtigung zum 29.09.2026:** Damals hatte ich beim Vortox das Gegenteil eingebaut, weil der Simulator ein betrunkenes Orakel die Wahrheit sagen ließ. Solver und Simulator hatten denselben Fehler. Beide folgen jetzt dem Wiki.

**Nebenbei gefunden:** Die alte lokale Python-App speicherte den Tag bei Hexen-Tod und Wahnsinns-Hinrichtung als Text statt als Zahl. Die Seite war richtig.

**Messung:**

- Wahrheit gehalten: Bad Moon Rising, Trouble Brewing und das Oster-Skript je 3.000 Partien, 0 verworfen.
- Sects & Violets, 3.000 Partien: 22 verworfen (0,7 %, vorher 1,3 %). Alle 22 haben einen Barbier-Tausch, in 21 hat sich der Barbier nie gemeldet. Das ist nach deiner Regel Sache des Dorfs.
- Python und JavaScript stimmen auf allen 171 Brettern des Korpus überein, darunter 18 neue für diese Regeln. 1.034 Tests grün.

### Der Simulator spielt die vier fehlenden Dinge · *erledigt am 03.10.2026*

Der Simulator spielt jetzt, was die Regelprüfung nur an Einzelbrettern prüfen konnte. Der volle Bericht steht in `claude/simulator-vier-dinge.md`.

| Was | Wie oft in 6.000 Partien Bad Moon Rising (4 Nächte) |
|---|---|
| Überlebte Hinrichtung | Pazifist 1.529, Narr 667, Teedame 575, Teufelsadvokat 506, Segler 436 |
| Wiederbelebung | Professor 769, Shabaloth 603 |
| Mondkind stirbt nachts und wählt am Morgen | 275 Wahlen, davon 139 mit Totem |
| Nominierender fällt durch die Hexe tot um | 836 von 6.000 Partien Sects & Violets |

**Die neuen Partien haben neun Fehler im Solver gefunden,** alle behoben, in Python und JavaScript:

| Nr. | Fehler | Jetzt |
|---|---|---|
| 1 | **Die Erzählungen der Nächte wurden bei 24 abgeschnitten,** unsortiert und mit Doppelten. Ab der vierten Nacht lag die wahre Erzählung oft dahinter, und die wahre Welt flog raus. | Eine Erzählung je Forderung, die beste zuerst, bis 96. |
| 2 | **Ein Professor kann seine Fähigkeit unsichtbar verbrauchen** (auf einen Nicht-Bürger, oder betrunken). Der Solver hielt ihn danach weiter für geweckt. | Nacht 2 sicher geweckt, danach offen. |
| 3 | **Eine Rückkehr ist auf eine Nacht datiert, und eine Nacht hat siebzig Plätze.** Wer in Nacht 3 zurückkam, galt die ganze Nacht als lebend: Teedame, Großmutter, Höfling, Minnesänger und Pukka-Gift waren dadurch falsch. | Was vom Lebendsein abhängt, wird nur verlangt, wenn es in beiden Lesarten gilt. Segler, Gastwirt und Exorzist handeln in der Nacht ihrer Rückkehr nicht. |
| 4 | **Ein Narr, der tot war und zurückkam,** überlebt wieder einmal. | Abgebildet. |
| 5 | **Eine betrunkene Pukka greift nicht an, ihr Gift ruht,** und das Opfer stirbt eine Nacht später. | Der Kill darf eine oder zwei Nächte später kommen. |
| 6 | **Schläger:** War nur noch ein Wähler am Leben, galt er jede Nacht als betrunken. | Die Trunkenheit ist ein Angebot, kein Zwang. |
| 7 | **Großmutter:** Trauer ist ein Tod wie jeder andere. Neben einer Teedame oder im Paar des Gastwirts stirbt sie nicht. | Abgebildet. |
| 8 | **Teedame:** Ist nur noch ein Spieler neben ihr am Leben, ist er ihr Nachbar auf beiden Seiten. | Abgebildet. |
| 9 | **Python und JavaScript waren bei Gleichstand uneins,** welche Störung sie wählen. | Gleiche Reihenfolge. |

**Der Night-Walk hat dabei sechs Fehler im Simulator gefunden,** die schon vorher da waren: mehrere Kills einer Nacht liefen nicht nacheinander ab, der Dämon wählte jemanden, der in derselben Nacht schon tot war, die Großmutter starb trotz Teedame, beim Mondkind zählte der falsche Zeitpunkt, ein wiederbelebter Minnesänger machte rückwirkend alle betrunken, und ein Shabaloth wählte denselben Spieler zweimal. Umgekehrt fehlten dem Night-Walk der Segler und der Gastwirt bei anderen Toden als dem des Dämons.

**Messung:**

- Wahrheit gehalten, Bad Moon Rising: 0 von 6.000 (4 Nächte), 0 von 20.000 (5 Nächte), 0 von 26.000 (6 Nächte).
- Trouble Brewing und das Oster-Skript: je 0 von 6.000 (5 Nächte).
- Sects & Violets: 49 von 6.000 (4 Nächte), alle mit Barbier-Tausch, 47 davon mit verstecktem Barbier. Am Morgen waren es 45. Die Hexen-Tode bringen keine neue Klasse.
- Simulator gegen Night-Walk, Bad Moon Rising: ohne Schläger stimmen alle 13.016 Nächte überein, mit Schläger weichen 39 von 4.639 ab. Am Morgen waren es 37 von 5.857 über alles. Trouble Brewing: 0 von 6.000. Sects & Violets: 21 von 6.000, am Morgen 14 von 3.000.
- Korpus: 181 Bretter, 10 davon neue gespielte Partien. Python und JavaScript stimmen überein. 1.066 Tests grün.

### Schläger, die drei fehlenden Kills und „neue Instanz“ · *erledigt am 03.10.2026*

Der volle Bericht steht in `claude/simulator-schlaeger-und-drei-kills.md`.

**Deine Regel vom 03.10.2026:** Die Fähigkeit eines Charakters endet immer mit seinem Tod. Wer wiederbelebt oder neu erschaffen wird, ist eine neue Instanz und wählt neu. Für den Höfling: Die Trunkenheit endet sofort mit seinem Tod. Kommt er zurück, darf er neu wählen, und die neue Trunkenheit hält wieder drei Tage. Für die Großmutter: Sie bekommt bei der Rückkehr ein neues Enkelkind, das alte bedeutet ihr nichts mehr. Simulator, Night-Walk und beide Solver spielen das jetzt so.

**Was der Simulator neu spielt,** in 20.000 Partien Bad Moon Rising (4 Nächte):

| Was | Wie oft |
|---|---|
| Schläger wird als Erster gewählt (Wähler betrunken) | Dämon 1.405, Kammerzofe 834, Gastwirt 781, Segler 741, Exorzist 393, Glücksspieler 346, Verrückte 241, Teufelsadvokat 166, Pate 61, Meuchelmörder 54 |
| Schläger wird böse | 1.618 Partien |
| Meuchelmörder schlägt zu | 2.767 mit Totem, 576 ohne Wirkung |
| Pate tötet nach einem bei Tag gestorbenen Außenseiter | 1.130 mit Totem, 522 ohne |
| Schwätzer hatte recht | 2.954 Partien |
| Höfling wählt in einem neuen Leben noch einmal | 211 |
| Großmutter bekommt ein neues Enkelkind | 369 |

**Die neuen Partien haben sechs Fehler im Solver gefunden,** alle behoben, in Python und JavaScript:

| Nr. | Fehler | Jetzt |
|---|---|---|
| 1 | **Teedame neben einem Schläger:** Der Solver hielt den Schläger immer für gut. War er böse geworden und ihr anderer Nachbar starb, musste die Teedame „gestört“ gewesen sein, und nichts konnte das erklären. | Neben einem Schläger kann ihr Schutz ein Überleben erklären, ein Tod neben ihr beweist nichts. |
| 2 | **Mondkind wählt den Schläger,** und der lebt weiter: gleiche Ursache. | Die Wahl kann töten, muss aber nicht. |
| 3 | **Meuchelmörder und Kammerzofe:** Er wird geweckt, bis er zugeschlagen hat. Schlägt er betrunken zu, sieht das niemand. Der Solver hielt ihn weiter für geweckt (alte offene Stelle 17). | Nacht 2 sicher geweckt, danach offen, außer der Schlag ist eingetragen. |
| 4 | **Pate:** Ein betrunkener Pate tötet nicht. Der Solver kannte dafür nur „er hat auf einen Toten gezielt“. | Der Kill kann an der Quelle gestoppt sein. |
| 5 | **Pukka-Gift auf jemandem, der überlebt:** Das Gift bleibt bis zum Zug der Pukka in der nächsten Nacht. Ein vergifteter Gastwirt, den eine Teedame am Leben hält, wählt also ohne Fähigkeit. Der Solver kannte das Gift nur auf dem, der stirbt. | Das Gift kann auch auf einem Überlebenden liegen (als Vermutung bepreist). |
| 6 | **Die Erzählungen der Nächte wurden bei 96 abgeschnitten.** Mit Meuchelmörder und Schwätzer im Spiel lag in sechs Nächten die wahre Erzählung 3-mal in 20.000 Partien dahinter. | Erst fallen Erzählungen weg, die mehr verlangen und nicht billiger sind (verlustfrei, nachgemessen). Dann Grenze 400. |

**Preis von Nr. 6:** 13 Partien mit sechs Nächten brauchen zusammen 178 statt 152 Sekunden (plus 17 %), die langsamste einzelne 56 statt 29 Sekunden. Dafür zählt der Solver bei 6 der 13 Partien mehr gültige Welten als vorher (bis zu 11 % mehr), die Grenze 96 hat also auch sonst Welten verloren. Bei vier und fünf Nächten ist der Unterschied klein (plus 12 % Zeit). Wenn dir das zu teuer ist, lässt sich die Grenze mit einer Zahl zurückstellen.

**Ein Fehler im Simulator, der schon vorher da war:** Ein Segler oder Gastwirt, der noch das Gift der Pukka vom Vortag trägt, wählte ohne Fähigkeit, aber wenn er die Nacht überlebte, machte seine Wahl am Ende doch jemanden betrunken. Der Night-Walk hatte es richtig.

**Messung:**

- Wahrheit gehalten, Bad Moon Rising: 0 von 20.000 (4 Nächte), 0 von 16.000 (5 Nächte), 0 von 24.000 (6 Nächte).
- Trouble Brewing und das Oster-Skript: je 0 von 6.000 (4 Nächte). Die gespielten Partien dieser beiden Skripte und von Sects & Violets sind Zeichen für Zeichen dieselben wie vorher.
- Sects & Violets: unverändert 49 von 6.000, alle mit Barbier-Tausch, 47 davon mit verstecktem Barbier.
- Simulator gegen Night-Walk, Bad Moon Rising, jetzt mit Schläger: 0 von 23.544 Nächten (4 Nächte), 0 von 29.021 (6 Nächte). Vorher wichen mit Schläger 39 von 4.639 ab.
- Korpus: 190 Bretter, 9 davon neue gespielte Partien. Python und JavaScript stimmen überein. 1.091 Tests grün.

### Messung: Wie oft findet der Solver den Dämon? · *gemessen am 03.10.2026, berichtigt am 04.10.2026*

Berichte: `claude/messung-daemon-gefunden.md` und `claude/messung-stille-naechte.md`. Am Solver wurde dafür nichts geändert.

Je Skript 400 gespielte Partien, 7 bis 10 Spieler, Stand nach vier Nächten. „Vorn“ heißt: Kein anderer Sitz hat einen höheren Dämon-Wert als der wahre Dämon. Gezählt sind nur **offene Partien** (mindestens drei Spieler am Leben). Unter den Lebenden zu raten träfe zu etwa 23 % (Bad Moon Rising) und 30 % (Sects & Violets). Jede Zahl schwankt um 6 bis 7 Punkte.

| Bad Moon Rising | offene Partien | vorn | unter den ersten drei |
|---|---|---|---|
| Shabaloth | 41 | 61 % | 100 % |
| Poe | 63 | 57 % | 95 % |
| Pukka | 81 | 62 % | 94 % |
| **Zombuul** | 89 | **36 %** | 73 % |
| alle | 274 | 52 % | 88 % |

| Sects & Violets | offene Partien | vorn | unter den ersten drei |
|---|---|---|---|
| Fang Gu | 48 | 73 % | 98 % |
| Vigormortis | 52 | 73 % | 100 % |
| No Dashii | 50 | 64 % | 96 % |
| Vortox | 50 | 64 % | 100 % |
| alle | 200 | 68 % | 98 % |

**Berichtigung:** Die zuerst gemeldeten Zahlen (63 % und 79 %) enthielten Partien, die längst entschieden waren. Der Simulator spielt weiter, wenn nur noch zwei Spieler leben, und dort ist der Dämon leicht zu finden. Bei Sects & Violets mit 7 und 8 Spielern sind nach vier Nächten 193 von 200 Partien entschieden, für diese Größen gibt es also noch keine brauchbare Messung.

**Warum der Zombuul schwach ist:**

1. **Er tötet im Simulator fast nie.** Das Dorf richtet fast jeden Tag hin, in 55 von 90 Partien hat er kein einziges Mal getötet. Es wird kaum jemand entlastet.
2. **Ein scheintoter Zombuul** (hingerichtet, spielt weiter) sieht aus wie ein toter Guter: 2 von 23 vorn.
3. Dass der Solver den Zombuul nicht an stillen Nächten erkennt, stimmt, ist aber **nicht** der Grund (siehe nächster Abschnitt).

### Messung: stille Nächte bei Shabaloth und Pukka · *gemessen am 04.10.2026*

Der volle Bericht steht in `claude/messung-stille-naechte.md`. Kein Code geändert.

- **Der Messaufbau hat dem Solver stille Nächte nie eingetragen.** Kein Messlauf hat bisher geprüft, was der Solver mit einer Nacht ohne Toten macht. Nachgeholt an je 3.000 Partien Bad Moon Rising und Trouble Brewing: Die wahre Welt geht nie verloren.
- **Warum Nächte wirklich still sind** (6.000 Partien): Beim Shabaloth wurde in 85 % der stillen Nächte der Dämon selbst gestoppt (Exorzist, betrunken durch Gastwirt, Segler, Schläger, Höfling), nur in 15 % waren beide Ziele geschützt. Bei der Pukka wurde in 38 % der Vergiftete vorher hingerichtet. Still sind beim Shabaloth 19 % der Nächte, bei der Pukka 32 %, beim Poe 38 %, beim Zombuul 65 %.
- **Womit der Solver sie erklärt:** nur mit „das Ziel konnte nicht sterben“, und das ist gratis (Segler, Gastwirt, Narr, Teedame, Exorzist). In 98 % des Gewichts der Shabaloth-Welten hat jede stille Nacht eine Gratis-Erklärung. Beim Shabaloth reicht eine für beide Kills.
- **Wegnehmen im Versuch** (71 offene Partien mit zwei oder drei stillen Nächten): Eine einzelne Erklärung zu streichen ändert fast nichts. Alle fünf zu streichen drückt Shabaloth und Pukka auf 6 % und 9 %, der Glaube wandert aber vor allem zum Poe, **der Zombuul steht nicht öfter vorn** (15 von 42), und in 10 von 71 Partien geht die wahre Welt verloren.
- **Strenge Lesart** (gestörter Dämon als eigene Erklärung, zwei Erklärungen für zwei Shabaloth-Kills, das Ziel der Pukka schützt sich nicht selbst): verliert in 382 Partien keine wahre Welt, findet den Dämon nicht öfter, kostet 20 % Rechenzeit.

**Folgerung:** Stille Nächte zu bepreisen hilft nicht, den Dämon zu finden.

### Der Simulator beendet die Partie, wenn Böse gewonnen hat · *erledigt am 04.10.2026*

Der volle Bericht steht in `claude/simulator-spielende.md`. Am Solver und an der Website wurde nichts geändert.

**Deine Entscheidungen vom 04.10.2026:** Stille Nächte in Messläufe und Tests eintragen: ja, zuerst. Strenge Lesart für stille Nächte: erst nach einem großen Lauf. Stille Nächte bepreisen: nein. Dämon-Messung am letzten offenen Morgen wiederholen: ja. Den Simulator reparieren, statt nur im Messaufbau zu filtern.

**Wie groß der Mangel war** (je 6.000 Partien, 7 bis 11 Spieler, vor der Reparatur). „Entschieden“ heißt: Böse hatte nach den Regeln schon gewonnen. „Lief weiter“ heißt: Der Simulator hat danach noch mindestens einen Tag oder eine Nacht gespielt.

| Skript | 4 Nächte: entschieden / lief weiter | 5 Nächte | 6 Nächte |
|---|---|---|---|
| Trouble Brewing | 1.885 / 822 | 4.053 / 3.061 | 5.608 / 5.147 |
| Oster-Skript | 2.175 / 1.014 | 4.447 / 3.328 | 5.848 / 5.514 |
| Sects & Violets | 2.464 / 1.233 | 4.927 / 3.782 | 5.948 / 5.826 |
| Bad Moon Rising | 1.356 / 705 | 2.588 / 1.991 | 3.616 / 3.208 |

Die Läufe über sechs Nächte („0 von 24.000“) haben also zum größten Teil Partien geprüft, die es am Tisch nicht gibt.

**Was der Simulator jetzt tut:**

- **Zwei Lebende:** Leben nur noch zwei Spieler und einer ist der Dämon, endet die Partie. Geprüft wird am Morgen, nach einem Hexen-Tod am Tag und nach der Hinrichtung. Die letzte Nacht wird zu Ende gespielt, damit ihr Protokoll vollständig ist.
- **Zombuul:** Ein Zombuul, der als tot gilt, zählt als lebend. Die Partie läuft mit ihm und zwei anderen weiter (Regelwerk, Teil 2).
- **Strippenzieher:** Der Zusatztag läuft, egal wie wenige noch leben (Regelwerk, Teil 6, Punkt 7).
- **Niemand kommt in eine entschiedene Partie zurück:** Sind vor dem Zug des Professors nur noch zwei am Leben, belebt er niemanden. Dasselbe gilt für das Hochwürgen des Shabaloth. Zusammen kam das in 2 von 6.000 Partien vor.
- **Vortox:** Ein Tag ohne Hinrichtung unter einem funktionierenden Vortox beendet die Partie. Der Solver kennt diese Regel und liest einen solchen Tag als Beweis gegen einen Vortox. Das betraf 75 von 6.000 Partien Sects & Violets und wäre beim Eintragen der Tage ohne Hinrichtung als falscher Alarm aufgefallen.

Neu an einer gespielten Partie: `ended_at` (der Moment, zum Beispiel `N4` oder `E3`), `ended_why` (`two alive` oder `vortox`), `mastermind_day` (der Zusatztag). `game_ends_after` ist jetzt in jedem Fall die letzte gespielte Nacht.

**Was sich an den Partien ändert,** Partie für Partie verglichen, 72.000 Partien (vier Skripte, 4 bis 6 Nächte, je 6.000):

- Jede Partie, die offen bleibt, ist Zeichen für Zeichen dieselbe wie vorher, mit Claims.
- Jede Partie, die endet, ist bis zu ihrem Ende dieselbe wie vorher. Ausnahme sind die 2 Partien, in denen der Professor jemanden in eine entschiedene Partie zurückgeholt hätte.
- Weil die Claims nach dem Spielen gewürfelt werden, bekommt eine verkürzte Partie andere Claims als vorher.

**Korpus:** 8 von 190 Brettern ändern sich. Sieben sind dieselbe Partie, nur kürzer. `bmr-played-regurgitated` hat einen neuen Seed (94 statt 1), weil das Hochwürgen bei Seed 1 in einer Nacht lag, die es nicht mehr gibt. Python und JavaScript stimmen auf allen 190 überein.

**Messung nach der Reparatur:**

- Wahrheit gehalten, Bad Moon Rising: 0 von 20.000 (4 Nächte), 0 von 16.000 (5 Nächte), 0 von 24.000 (6 Nächte).
- Trouble Brewing und Oster-Skript: je 0 von 6.000 (4 Nächte).
- Sects & Violets: 43 von 6.000 (vorher 49), alle mit Barbier-Tausch, 41 mit verstecktem Barbier.
- Mit eingetragenen stillen Nächten: 0 von 3.000 (Bad Moon Rising), 0 von 3.000 (Trouble Brewing).
- Simulator gegen Night-Walk: Bad Moon Rising 0 von 22.558 Nächten (4 Nächte) und 0 von 23.093 (6 Nächte), Trouble Brewing 0 von 17.178. Sects & Violets 60 von 16.641. Vor der Reparatur waren es dort 61 von 18.000, die Abweichung ist also alt.
- Die Dämon-Messung vom 03.10.2026 gilt weiter, weil sie nur offene Partien zählt und die sich nicht geändert haben.
- 1.100 Tests grün, davon 9 neue für das Spielende. Die Website ist unverändert.

### Stille Nächte eingetragen, Dämon am letzten offenen Morgen · *erledigt am 04.10.2026*

Der volle Bericht steht in `claude/stille-naechte-eingetragen-und-letzter-morgen.md`. Am Solver und an der Website wurde nichts geändert.

**Was neu ist:** Eine gespielte Partie gibt dem Solver jetzt auch, was nicht passiert ist: die Nächte ohne Toten (ab Nacht 2) und die Tage, nach denen die Partie weiterging. Das gilt für alle Tests und Messläufe mit gespielten Partien und für die 26 gespielten Bretter im Korpus.

**Der große Lauf mit eingetragenen stillen Nächten** (wahre Welt gehalten):

| Skript | Partien | verworfen |
|---|---|---|
| Bad Moon Rising, 4 Nächte | 20.000 | 16 |
| Bad Moon Rising, 5 Nächte | 16.000 | 19 |
| Bad Moon Rising, 6 Nächte | 24.000 | 48 |
| Trouble Brewing, 4 und 6 Nächte | je 6.000 | 0 |
| Oster-Skript, 4 und 6 Nächte | je 6.000 | 0 |
| Sects & Violets, 4 Nächte | 6.000 | 43, alle Barbier-Tausch, wie ohne Eintrag |
| Sects & Violets, 6 Nächte | 6.000 | 72, alle Barbier-Tausch |

**Befund: 83 von 60.000 Partien Bad Moon Rising gehen verloren,** ohne eingetragene stille Nächte waren es 0. In allen 83 war die Nacht still, weil der **Dämon selbst gestoppt** wurde, und es gab keinen Schutz, mit dem der Solver die Nacht sonst erklären konnte. Bei vier Nächten hatte der Dämon in 15 von 16 Fällen den Schläger zuerst gewählt (in dieser Nacht, oder die Pukka in der Nacht davor). Bei sechs Nächten war er in 32 von 48 Fällen durch den Schläger gestoppt, in 16 anders betrunken oder vergiftet. Das ist die offene Stelle 1.

Wie oft das überhaupt vorkommt: In 6.000 Partien gab es 6.609 stille Nächte, in 1.907 davon war der Dämon selbst gestoppt. Fast immer findet der Solver trotzdem eine andere, falsche Erklärung (einen Schutz auf dem Opfer). Deshalb fiel es bisher nicht auf.

**Versuch im Speicher** (nichts im Solver geändert), verworfen von 20.000 / 16.000 / 24.000 Partien bei 4 / 5 / 6 Nächten:

| Variante | 4 Nächte | 5 Nächte | 6 Nächte |
|---|---|---|---|
| Solver, wie er ist | 16 | 19 | 48 |
| dazu nur die Erklärung „der Dämon selbst wurde gestoppt“ | 0 | 1 | 12 |
| strenge Lesart (Variante `logic`) | 2 | 3 | 6 |

Keine der beiden Varianten ist fertig. Die einfache lässt bei sechs Nächten 12 übrig und verliert dabei auch Partien, die der Solver heute hält. Die strenge verliert andere Partien als der Solver heute. Beides ist nicht untersucht.

**Dämon gefunden am letzten offenen Morgen** (400 Partien je Skript, 7 bis 10 Spieler, höchstens sechs Nächte, stille Nächte eingetragen). Das Brett ist das, was der Tisch am letzten Morgen hat, bevor die Partie entschieden ist. Jede Partie zählt, nicht mehr nur die nach vier Nächten offenen.

| Bad Moon Rising | Partien | vorn | unter den ersten drei |
|---|---|---|---|
| Pukka | 105 | 65 % | 96 % |
| Poe | 102 | 58 % | 97 % |
| Shabaloth | 103 | 58 % | 99 % |
| **Zombuul** | 90 | **34 %** | 78 % |
| alle | 400 | 54 % | 93 % |

| Sects & Violets | Partien | vorn | unter den ersten drei |
|---|---|---|---|
| No Dashii | 99 | 69 % | 98 % |
| Vigormortis | 105 | 67 % | 100 % |
| Vortox | 92 | 63 % | 98 % |
| Fang Gu | 104 | 62 % | 97 % |
| alle | 400 | 65 % | 98 % |

Raten unter den Lebenden träfe zu 28 % und 29 %. Jede Zahl für ein ganzes Skript schwankt um etwa 5 Punkte, für einen einzelnen Dämon um etwa 10.

- **Das Bild ist dasselbe wie nach festen vier Nächten** (52 % und 68 %). Der andere Zeitpunkt ändert das Ergebnis nicht über die Schwankung hinaus.
- **Der Zombuul ist nur schwach, solange er als tot gilt:** 3 von 44 vorn. Ist er sichtbar am Leben, steht er in 28 von 46 Partien vorn (61 %), so oft wie die anderen Dämonen.
- **Lange Partien sind schwerer:** Bad Moon Rising, nach sechs Nächten noch offen: 48 % vorn (111 Partien). Am dritten und vierten Morgen: 60 % und 62 %.
- Sects & Violets endet im Simulator fast immer am dritten oder vierten Tag (372 von 400).
- In 4 Partien Sects & Violets geht die wahre Welt verloren (Barbier-Tausch). Der richtige Spieler steht in allen vier trotzdem vorn.

1.108 Tests grün, davon 8 neue. Korpus: Alle 26 gespielten Bretter tragen die neuen Angaben, bei 2 ändert sich die Zahl der Welten.

### Stille Nacht: der Dämon selbst wurde gestoppt · *erledigt am 04.10.2026*

Der volle Bericht steht in `claude/stille-nacht-daemon-gestoppt.md`.

**Deine Entscheidungen vom 04.10.2026:** Die Grenze 400 für die Erzählungen der Nächte bleibt. Zu B: Weg 1, also nur die fehlende Erklärung bauen und keine wegnehmen.

**Gebaut, in Python und JavaScript:**

- **Zombuul, Pukka und Shabaloth** können eine stille Nacht jetzt damit erklären, dass der Dämon selbst betrunken oder vergiftet war. Angeboten wird das nur, wenn ihn in dieser Nacht etwas erreichen kann (Schläger, Segler, Gastwirt, Höfling, Minnesänger, Gift). Es kostet nichts extra: Die Störquelle kostet, was sie immer kostet, und der Schläger ist gratis.
- **Pukka:** War sie in der Nacht davor gestört, hat sie niemanden vergiftet. Dann ist in dieser Nacht nichts fällig (von Nacht 1 auf Nacht 2), oder die Marke aus der Nacht davor wird fällig, und deren Träger konnte nicht sterben.
- **Der Poe** braucht nichts davon, er darf ohnehin niemanden wählen.
- **Nichts weggenommen:** Ein Kill sagt bei diesen Dämonen weiterhin nichts darüber, ob der Dämon nüchtern war.

**Die letzten zwei Partien gingen an der Grenze 400 verloren, nicht an einer Regel.** Mit mehr Erklärungen je Nacht waren alle 400 Plätze mit Erzählungen belegt, die das Brett ohnehin ausschließt (ein Sitz soll gestört sein, den eine Auskunft arbeitend braucht, oder umgekehrt). Diese fallen jetzt weg, bevor die Plätze vergeben werden. Das verliert nichts, weil der Plan jede davon abgelehnt hätte. Die Grenze selbst bleibt bei 400. Beide Partien gehen jetzt sogar mit der alten Grenze 96 auf.

**Messung, wahre Welt gehalten, stille Nächte eingetragen:**

| Skript | Partien | vorher | jetzt |
|---|---|---|---|
| Bad Moon Rising, 4 / 5 / 6 Nächte | 20.000 / 16.000 / 24.000 | 16 / 19 / 48 | **0 / 0 / 0** |
| Trouble Brewing, Oster-Skript | je 12.000 | 0 | 0 |
| Sects & Violets, 4 / 6 Nächte | je 6.000 | 43 / 72 | 43 / 72, alle Barbier-Tausch |

**Dämon gefunden** (Bad Moon Rising, dieselben 400 Partien wie am Mittag): 222 statt 218 vorn, also 56 % statt 54 %. In 391 von 400 Partien hat der Dämon denselben Rang wie vorher, in 6 einen besseren, in 3 einen schlechteren. Der Zombuul, der als tot gilt, steht weiter in 3 von 44 Partien vorn. Die Erklärung rettet also Welten, den Dämon findet der Solver dadurch nicht öfter. So war es erwartet.

**Rechenzeit.** Die neue Erklärung hätte lange Bretter mit stillen Nächten um die Hälfte langsamer gemacht. Zwei Änderungen ohne Einfluss auf das Ergebnis gleichen das aus:

| 48 Bretter Bad Moon Rising | vor der Änderung | mit der Erklärung allein | jetzt |
|---|---|---|---|
| Python | 316 s | 497 s | 329 s |
| JavaScript (die Website) | 138 s | etwa 207 s | 134 s |

- Der Solver rechnet den Störungsplan einer Erzählung nicht mehr aus, wenn sie nicht mehr gewinnen kann.
- Beim Kombinieren der Nächte werden die Mengen geteilt statt jedes Mal kopiert, und eine Erzählung, die schon geschlagen ist, wird gar nicht erst gebaut.

Geprüft: Der Korpus ist nach beiden Änderungen Zeichen für Zeichen derselbe.

**Korpus:** 10 von 190 Brettern geben andere Zahlen, alle zehn haben eine stille Nacht. Die übrigen 180 sind unverändert. Python und JavaScript stimmen auf allen 190 überein. 1.120 Tests grün, davon 12 neue.

### Als Nächstes

**1 · Der Zombuul, der als tot gilt.** Hier liegt die ganze Schwäche beim Zombuul (3 von 44 vorn). Sichtbar am Leben wird er so oft gefunden wie die anderen Dämonen.

**2 · Das Dorf im Simulator.** Es richtet an 2,3 von 3 Tagen hin.

**3 · Strenge Lesart für stille Nächte** (zurückgestellt): zwei Erklärungen für zwei Shabaloth-Kills, das Ziel der Pukka schützt sich nicht selbst. Im Versuch verlor sie 11 von 60.000 Partien, die der Solver hält.

**4 · Was der Simulator weiter nicht spielt:** die **Hinrichtung wegen Wahnsinn** (Cerenovus) in Sects & Violets.

**5 · Die Regeln an das Spiel zurückgeben.** Mehrere Funde (Teedame, Höfling, Glücksspieler, Vortox, Rückkehr mitten in der Nacht, Pukka eine Nacht später, Teedame neben dem Schläger, Gift auf einem Überlebenden) betreffen auch das Regelwerk des Einzelspieler-Spiels.

### Offene Stellen

| Nr. | Bereich | Was offen ist |
|---|---|---|
| 1 | Bad Moon Rising | *Erledigt am 04.10.2026:* Gestörter Dämon als Erklärung für eine ruhige Nacht, jetzt auch bei Zombuul, Pukka und Shabaloth. Mit eingetragenen stillen Nächten gingen 83 von 60.000 Partien verloren, jetzt 0. |
| 2 | Bad Moon Rising | **„Jede Störung ruht, wenn ihre Quelle gestört ist“** (deine Entscheidung vom 02.10.2026). Abgebildet für Höfling und Philosoph (Tod, und Störung beim Wählen) und für die Pukka, seit dem 03.10. auch mit dem Kill, der dadurch später kommt. Nicht allgemein für eine Quelle, die erst später gestört wird. |
| 3 | Bad Moon Rising | **Poe und Meuchelmörder bleiben locker:** drei Tote in zwei Nächten hintereinander, und ein Meuchelmörder ohne eingetragene Zeile kann in mehreren Nächten zuschlagen (jeder Schlag kostet 0,25). |
| 4 | Sects & Violets | **Barbier-Tausch ohne gemeldeten Barbier** verliert die wahre Welt, in 47 von 6.000 Partien. Nach deiner Regel gewollt. |
| 5 | Sects & Violets | **Sitze, deren Rolle gewechselt hat,** werden nicht von ihrer ursprünglichen Rolle aus gesucht (halber Barbier-Tausch). 2 von 6.000 Partien. |
| 6 | Sects & Violets | **Mathematiker unter einem Vortox:** Seine Zahl wird als Bereich geprüft, deshalb bleibt hier die alte, lockere Regel. |
| 7 | Sects & Violets | **Barbier-Bretter brauchen im Browser etwa 20 Sekunden.** Die Seite friert dabei nicht mehr ein. |
| 8 | Echte Partien | **Ein Info-Claim, den alle kennen und der nie nachts stirbt,** deutet auf Trunkenbold, Marionette oder böse. Idee aus der ersten echten Partie, nicht gebaut. |
| 9 | Echte Partien | **Claims haben keinen Zeitpunkt.** Die Seite kennt einen Claim pro Sitz, der Rückblick sieht ihn schon am ersten Morgen. Ein Verlauf der Claims ist nicht gebaut. |
| 10 | Echte Partien | **Mehr Partien.** Eine ausgewertete Partie ist ein Anfang, belastbar wird es mit drei bis fünf weiteren. |
| 11 | Werkzeug | **Die alte lokale Python-App lehnt einen Tod in Nacht 1 ab,** die Seite nicht. Ein Bastler kann in Nacht 1 sterben. Der Night-Walk kennt den Fall auch nicht. |
| 12 | Werkzeug | **Exakte Zählung früher Bretter auf der Website.** Der Barbier-Multiplikator und der Aufbau der Zeitleisten sind die Hauptkosten. |
| 13 | Werkzeug | **NEXT.md** in eine kurze Roadmap und ein Archiv aufteilen. |
| 14 | Nach Bedarf | Weitere experimentelle Charaktere. |
| 15 | Bad Moon Rising | *Erledigt am 03.10.2026:* Höfling nach einer Wiederbelebung. Deine Regel: Die Fähigkeit endet mit dem Tod, der Wiederbelebte ist eine neue Instanz. |
| 16 | Bad Moon Rising | **Kammerzofe und wer in derselben Nacht stirbt.** Simulator und Solver zählen einen Sitz als geweckt, auch wenn er vor seinem Platz in der Nacht getötet wurde (Professor an Platz 43, Dämon an 27). Beide machen es gleich, deshalb sieht es kein Messlauf. |
| 17 | Bad Moon Rising | *Erledigt am 03.10.2026:* Meuchelmörder, der seine Fähigkeit unsichtbar verbraucht. Gemessen und behoben. |
| 18 | Solver | **Der Plan der Störungen geht Nacht für Nacht vor** und nimmt bei Gleichstand die erste Lösung. Über mehrere Nächte gesehen kann eine andere besser sein. Das kostet Gewicht, keine Welten. |
| 19 | Simulator | **Der Mönch schützt in manchen Nächten zwei Spieler:** ein alter Münzwurf neben der eingetragenen Wahl. Ihn zu entfernen würde alle Trouble-Brewing-Partien neu austeilen, die Tests beim Namen nennen. Der Solver ist davon nicht betroffen. |
| 20 | Solver | **Der Solver rechnet in ganzen Nächten.** Das Pukka-Gift auf einem Überlebenden gilt bei ihm für die ganze Nacht und den Tag danach, am Tisch nur bis zum Zug der Pukka. Das hält zu viele Welten, verliert aber keine. |
| 21 | Simulator | **Ein Seitenwechsel des Schlägers gilt für die ganze Nacht,** nicht erst ab dem Platz, an dem er gewählt wurde. Simulator und Night-Walk machen es gleich. |
| 22 | Solver | **Grenze 400 für die Erzählungen der Nächte** bleibt eine Grenze (von dir bestätigt am 04.10.2026). Seit demselben Tag fallen Erzählungen, die das Brett ausschließt, vor dem Schnitt weg. In 60.000 Partien ging keine wahre Welt verloren, ausgeschlossen ist es bei sieben und mehr Nächten nicht. Sauber wäre, die Nächte einzeln statt als Produkt zu führen. |
| 23 | Solver | **Der Dämon-Typ wird aus stillen Nächten kaum erkannt.** Nach drei stillen Nächten ist es in 65 % ein Zombuul, der Solver sagt 38 %. Gemessen am 04.10.2026: Das zu ändern findet den Dämon nicht öfter. |
| 24 | Messung | **Nicht gemessen:** wie früh der Solver den Dämon findet (nur der Stand nach vier Nächten), und ob ein Dämon am Morgen vor seiner Hinrichtung vorn stand. Der Solver weiß nicht, dass eine Partie zu Ende ist. |
| 25 | Messung | **Kleine Tische:** Bei 7 und 8 Spielern sind nach vier Nächten fast alle Partien entschieden. Die frühere Auffälligkeit „9 Spieler“ bei Sects & Violets war ein Artefakt davon. |
| 26 | Simulator | *Erledigt am 04.10.2026:* Die Partie endet, wenn Böse gewonnen hat (zwei Lebende, Tag ohne Hinrichtung unter einem Vortox). |
| 27 | Messung | *Erledigt am 04.10.2026:* Stille Nächte und Tage ohne Hinrichtung sind in jedem Messlauf und Test mit gespielten Partien eingetragen. |
| 31 | Messung | **Die Dämon-Messung zeigt keinen Verlauf.** Sie wertet einen Morgen je Partie aus. Wie sich der Rang des Dämons von Morgen zu Morgen entwickelt, ist nicht gemessen. |
| 28 | Simulator | **Das Dorf gewinnt im Simulator nie.** Es richtet den Dämon nur hin, wenn die Partie danach weitergeht (Scharlachrote Frau, Zombuul, Strippenzieher, Teufelsadvokat). Das ist Absicht, heißt aber: Alle gespielten Partien sind solche, in denen der Dämon überlebt. |
| 29 | Korpus | **`sv-played-1063` heißt „zwei Tausche hintereinander“ und enthält nur noch einen.** Der Seed ergab schon vor dem 04.10.2026 eine andere Partie als bei seiner Auswahl. Seed 183 hätte zwei. |
| 30 | Simulator gegen Night-Walk | **Sects & Violets weicht in 60 von 16.641 Nächten ab.** Nicht untersucht, älter als die Reparatur. |

**Berichtigt:** Die frühere Stelle 6 („der direkte Messlauf verwirft 20 von 1.500, der Lauf über das Brett nicht“) war falsch. Beide Wege verwerfen etwa gleich viel, und es ist die Barbier-Klasse aus Stelle 4. Die frühere Stelle 4 (Philosoph und Schlangenbeschwörer, Seeds 836 und 181) lässt sich nicht mehr nachstellen, weil der Simulator seither anders spielt. Im neuen Lauf über 3.000 Partien gibt es keine verworfene Partie ohne Barbier-Tausch.

---

## Was gestrichen ist

- **Night-Walk als Filter:** gemessen und abgeschlossen. 3.580 verworfene Geschichten, keine einzige Zahl bewegt, elfmal langsamer. Er bleibt als zweite unabhängige Umsetzung der Nacht.
- **Preacher, Nightwatchman, Poppy Grower** als nächste Charaktere: auf keinem deiner Skripte.
- **„43 Charaktere übrig":** falsch gezählt, siehe Befund 3.
