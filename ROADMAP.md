# Clocktower-Solver — Roadmap, neu bewertet

**Stand:** 02.10.2026 (Neubewertung vom 29.09.2026, seither fortgeschrieben)
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

### Als Nächstes

**1 · Der Simulator spielt die neuen Regeln nicht.** Sie sind durch Einzeltests und Korpus-Bretter gedeckt, aber kein Messlauf erzeugt sie:

- eine überlebte Hinrichtung (Teufelsadvokat, Pazifist, Narr, Segler, Teedame)
- das Hochwürgen des Shabaloth und den Professor
- ein Mondkind, das nachts stirbt und am Morgen wählt
- einen Nominierenden, der durch die Hexe tot umfällt

Erst wenn der Simulator das spielt, prüfen die Messläufe diese Regeln mit.

**2 · Wie gut findet der Solver den Dämon?** Die zweite Hälfte der Neubewertung, jetzt wo die Regeln stimmen: getrennt nach Dämon, für beide Skripte. Der erste Blick bei Bad Moon Rising: Shabaloth 38 von 40 vorn, Poe 22 von 34, Pukka 22 von 41, **Zombuul 10 von 37**. Warum der Zombuul so schwach ist, ist die erste Frage.

**3 · Die Regeln an das Spiel zurückgeben.** Mehrere Funde (Teedame, Höfling, Glücksspieler, Vortox) betreffen auch das Regelwerk des Einzelspieler-Spiels.

### Offene Stellen

| Nr. | Bereich | Was offen ist |
|---|---|---|
| 1 | Bad Moon Rising | **Gestörter Dämon als Erklärung für eine ruhige Nacht.** Das gibt es nur beim allgemeinen Dämon, nicht bei Zombuul, Pukka, Shabaloth und Poe. Die Bretter gehen trotzdem auf, über einen Schutz auf dem Opfer. |
| 2 | Bad Moon Rising | **„Jede Störung ruht, wenn ihre Quelle gestört ist“** (deine Entscheidung vom 02.10.2026). Abgebildet für Höfling und Philosoph (Tod, und Störung beim Wählen) und für die Pukka. Nicht allgemein für eine Quelle, die erst später gestört wird. |
| 3 | Bad Moon Rising | **Poe und Meuchelmörder bleiben locker:** drei Tote in zwei Nächten hintereinander, und ein Meuchelmörder ohne eingetragene Zeile kann in mehreren Nächten zuschlagen (jeder Schlag kostet 0,25). |
| 4 | Sects & Violets | **Barbier-Tausch ohne gemeldeten Barbier** verliert die wahre Welt, in 21 von 3.000 Partien. Nach deiner Regel gewollt. |
| 5 | Sects & Violets | **Sitze, deren Rolle gewechselt hat,** werden nicht von ihrer ursprünglichen Rolle aus gesucht (halber Barbier-Tausch). 1 von 3.000 Partien. |
| 6 | Sects & Violets | **Mathematiker unter einem Vortox:** Seine Zahl wird als Bereich geprüft, deshalb bleibt hier die alte, lockere Regel. |
| 7 | Sects & Violets | **Barbier-Bretter brauchen im Browser etwa 20 Sekunden.** Die Seite friert dabei nicht mehr ein. |
| 8 | Echte Partien | **Ein Info-Claim, den alle kennen und der nie nachts stirbt,** deutet auf Trunkenbold, Marionette oder böse. Idee aus der ersten echten Partie, nicht gebaut. |
| 9 | Echte Partien | **Claims haben keinen Zeitpunkt.** Die Seite kennt einen Claim pro Sitz, der Rückblick sieht ihn schon am ersten Morgen. Ein Verlauf der Claims ist nicht gebaut. |
| 10 | Echte Partien | **Mehr Partien.** Eine ausgewertete Partie ist ein Anfang, belastbar wird es mit drei bis fünf weiteren. |
| 11 | Werkzeug | **Die alte lokale Python-App lehnt einen Tod in Nacht 1 ab,** die Seite nicht. Ein Bastler kann in Nacht 1 sterben. Der Night-Walk kennt den Fall auch nicht. |
| 12 | Werkzeug | **Exakte Zählung früher Bretter auf der Website.** Der Barbier-Multiplikator und der Aufbau der Zeitleisten sind die Hauptkosten. |
| 13 | Werkzeug | **NEXT.md** in eine kurze Roadmap und ein Archiv aufteilen. |
| 14 | Nach Bedarf | Weitere experimentelle Charaktere. |

**Berichtigt:** Die frühere Stelle 6 („der direkte Messlauf verwirft 20 von 1.500, der Lauf über das Brett nicht“) war falsch. Beide Wege verwerfen etwa gleich viel, und es ist die Barbier-Klasse aus Stelle 4. Die frühere Stelle 4 (Philosoph und Schlangenbeschwörer, Seeds 836 und 181) lässt sich nicht mehr nachstellen, weil der Simulator seither anders spielt. Im neuen Lauf über 3.000 Partien gibt es keine verworfene Partie ohne Barbier-Tausch.

---

## Was gestrichen ist

- **Night-Walk als Filter:** gemessen und abgeschlossen. 3.580 verworfene Geschichten, keine einzige Zahl bewegt, elfmal langsamer. Er bleibt als zweite unabhängige Umsetzung der Nacht.
- **Preacher, Nightwatchman, Poppy Grower** als nächste Charaktere: auf keinem deiner Skripte.
- **„43 Charaktere übrig":** falsch gezählt, siehe Befund 3.
