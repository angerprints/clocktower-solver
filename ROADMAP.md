# Clocktower-Solver — Roadmap, neu bewertet

**Stand:** 21.10.2026 (Neubewertung vom 29.09.2026, seither fortgeschrieben)
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
| Easter Trouble (AnqeR & Shellynax) | Oger, Marionette, Artist (nur aufgezeichnet) |
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
4. **Ein Liebchen macht *einen* Spieler betrunken, nicht alle.** Die Planung der Störungen behandelte jede kostenlose Quelle so, als träfe sie jeden, den sie erreichen kann. Das stimmt für den Trunkenbold und den Minnesänger. Liebchen, Vigormortis und Schläger wählen aber genau einen. Nach dem Tod eines Liebchens galt deshalb die ganze Stadt als betrunken, und „der Dämon hat funktioniert" (Punkt 2) war unmöglich. Aufgefallen ist das an vier S&V-Partien des eigenen Simulators, nicht an der Engine. Punkt 2 hat den alten Fehler nur sichtbar gemacht. Das Brett, das im ersten Commit von 268 auf 76 Welten fiel, hat wieder 268. Die 76 waren dieser Fehler, keine Erkenntnis.

Dazu ein Fehler, den ich beim Beheben selbst eingebaut und wieder entfernt habe: Die neue Erklärung für ruhige Nächte ohne Giftquelle verdrängte in der auf 24 Kombinationen begrenzten Suche die echte Geschichte.

**Offene Designfrage:** Der Solver nimmt an, dass das Spiel weiterläuft. Stirbt der Dämon ohne Nachfolger oder wird eine funktionierende Heilige hingerichtet, ist das Brett für ihn unmöglich, obwohl das Spiel einfach vorbei ist. Während einer Partie stimmt die Annahme. Wer ein fertiges Spiel nachträglich eingibt, bekommt „unmöglich". Die Brücke schneidet deshalb das Spielende ab.

**Gegenrichtung noch offen:** Ob die Engine Regelfehler hat, die der Solver findet. In 440 Partien hat keine einzige Abweichung auf einen Fehler der Engine gezeigt. Alle Treffer lagen beim Solver oder in der Brücke.

### Phase 2 — Deine Skripte vollständig · *erledigt am 29.09.2026*

1. **Oger** und **Marionette** · *erledigt am 28.09.2026.* Easter Trouble ist bis auf den Artist vollständig.
2. **Mastermind** · *erledigt am 29.09.2026.* Bad Moon Rising ist vollständig.
3. **Sects & Violets:** die 22 von 1000 Simulator-Partien, die der Solver verwarf, und **Mutant**, **Cerenovus**, **Savant** · *erledigt am 29.09.2026.* Alle drei Grundskripte sind komplett, nur der Artist bleibt „aufgezeichnet".
4. Artist bleibt „aufgezeichnet": Seine Frage ist frei formuliert und lässt sich nicht als Regel prüfen.

**Sects & Violets aufgeräumt.** Die 22 Fehlfälle waren kein einzelner Fehler, sondern ein Muster: Mehrere Charaktere verändern in derselben Partie, wer was ist (Schlangenbeschwörer, Grubenweib, Barbier, Fang Gu, Farmer, Oger), und der Solver hat alle Nächte auf einmal betrachtet. Ein Barbier-Tausch in Nacht 3 sah dann nicht, dass der Schlangenbeschwörer in Nacht 2 schon getauscht hatte. Neu: Sind zwei oder mehr dieser Charaktere im Spiel, baut der Solver die Geschichte **Nacht für Nacht** auf. Jede Regel sieht dabei, was die anderen vor ihr getan haben, aber nicht ihre eigenen früheren Änderungen. Aussortiert wird erst ganz am Ende. Mit nur einem solchen Charakter läuft der alte, schnellere Weg.

Dabei gefunden und in Python und JavaScript behoben:

- *Solver:* Der Mathematiker zählt nur **lebende** gestörte Spieler. Zwei Schlangenbeschwörer-Tausche hintereinander sehen einander. Ein Barbier, den das Grubenweib erschaffen hat, zählt als Barbier. Ein getauschter Dämon behält beim Barbier-Tausch seine böse Seite. Die Vigormortis vergiftet nur für Schergen, die sie **selbst getötet** hat. In der Nacht, in der ein Liebchen stirbt, muss der Dämon nicht getötet haben. Ein wahres Ergebnis unter dem Vortox ist erklärt, wenn der Vortox aus ist **oder** die Quelle gestört war (vorher nur das Erste). Die Geschichten einer Welt waren nicht nach Zeit sortiert, eine spätere Änderung konnte eine frühere überschreiben.
- *Simulator:* Tötet der Fang Gu einen Außenseiter, springt er (vorher fehlte das ganz). Der Barbier tauscht nur Lebende, auch bei einem Tod in der Nacht. Der Philosoph handelt ab Nacht 2 an der Stelle seines neuen Charakters. Das Grubenweib macht keinen Dämon zu etwas anderem. Tote bekommen keine gestörten Informationen mehr.

Geprüft: 2000 S&V-Partien mit 7 bis 11 Spielern und 4 Nächten, keine verwirft die Wahrheit, der Fang Gu springt dabei über 10-mal. TB, BMR und Easter: je 0 von 2000, auch mit 5 Nächten. Engine: 300 Grimoire-Partien und 70 Tisch-Partien mit Bot-Hirn, 0 verworfen. Sieben gespielte Partien liegen jetzt als feste Bretter im Korpus, Python und JavaScript stimmen auf allen 783 Welten überein. **Offen:** Mit 5 Nächten verwirft der Solver genau eine von 2000 S&V-Partien (Seed 181), noch nicht untersucht.

**Mutant, Cerenovus, Savant.** Alle drei waren bisher „nicht modelliert" oder „nur aufgezeichnet". Jetzt:

- **Mutant:** Er darf nicht sagen, dass er ein Außenseiter ist, sonst wird er vielleicht hingerichtet. Also steht er **immer hinter einem Townsfolk-Claim**, und das kostet die Welt nichts. Vorher baute der Solver eine Welt mit Mutant nur, wenn jemand „Mutant" behauptete, also genau dann, wenn der Mutant es nie tut. Gemessen an 60 S&V-Partien mit 7 bis 9 Spielern: Auf dem Sitz des echten Mutanten stieg die Wahrscheinlichkeit „Mutant" von 0 % (17 von 18 Partien) auf 17 % im Mittel, und kein Brett ist mehr ohne Welten (vorher 6 von 60). Der Dämon steht im Median auf Rang 1 statt 2. **Preis:** Viele S&V-Bretter haben jetzt mehr legale Welten, eines 7.320 statt 1.104. Das Lösen dauert im Mittel 6,8 statt 2,9 Sekunden, einzelne Bretter über 40 Sekunden.
- **Savant:** Die zwei Sätze bleiben Freitext. Zusätzlich kann jeder Satz in einer von neun prüfbaren Formen eingegeben werden: „X ist böse", „X ist gut", „X und Y sind auf derselben Seite", „auf verschiedenen Seiten", „X ist der C", „C ist im Spiel", „C ist nicht im Spiel", „es gibt N Außenseiter", „der Dämon ist einer von …". Sind beide Sätze so eingegeben, wird das Paar gewogen: Genau einer war wahr, unter dem Vortox beide falsch, ein gestörter Savant kann alles hören. Fehlregistrierung (Einsiedler, Spion) ist erlaubt. Der Simulator lässt den Savant jetzt jeden Tag fragen: 538 gewogene Paare in 1000 Partien, keines verwirft die Wahrheit. Zur Gegenprobe wurde je ein Paar in zwei gleiche Sätze verfälscht, dann verwirft der Solver 120 von 201 Brettern (der Rest ist mit Gift oder Vortox erklärbar).
- **Cerenovus:** Die Besessenheit selbst hinterlässt keine Spur. Drei Dinge sieht der Tisch aber: eine Hinrichtung wegen gebrochener Besessenheit (gab es schon), die neue Zeile **„war besessen davon, X zu sein"**, die der Gewählte selbst sagt und die einen lebenden Cerenovus in jener Nacht belegt, und einen guten Spieler, der etwas Falsches behauptet. Diese Lüge kostet in einer Welt mit lebendem Cerenovus 0,25 statt 0,02, höchstens eine pro Nacht. Das wirkt, wenn der Sitz als „unsicher" markiert ist.

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

**Dabei gefunden, noch offen:** Die Zeile „wurde X" wird nur aufgeschrieben, für die Suche zählt der aktuelle Claim. Ein guter Spieler, dessen Rolle sich geändert hat und der die neue nennt (nach Grubenweib oder Barbier), wird nie mit seiner wahren Anfangsrolle durchgerechnet. Eine Lösung müsste beide Sitze eines Tauschs zusammen denken.

**Mastermind.** Die Grundidee war schon da: Nach der Hinrichtung des Dämons darf das Spiel einen Tag weiterlaufen. Gefehlt haben drei Bedingungen aus dem Wiki. Nur eine **Hinrichtung** zählt, auch der Nominierende einer Jungfrau und eine Hinrichtung wegen Besessenheit, aber kein Schuss des Dämonenjägers. Der Mastermind muss **funktionieren**. Und eine Scharlachrote Frau, die übernehmen könnte, **hat Vorrang**. Die Mastermind-Geschichte ist jetzt markiert und wird zu Forderungen an den Störungsplan: Mastermind nicht gestört, Scharlachrote Frau gestört. Vorher standen beide Geschichten kostenlos nebeneinander.

**Der breitere Test hat mehr gefunden als den Mastermind.** Der bisherige BMR-Test spielte 6 Partien mit 9 Spielern. 300 Partien mit 7 bis 11 Spielern und 4 Nächten verwarfen die Wahrheit **32-mal** – schon vor dem Mastermind. Behoben, jetzt 0 von 1000:

- *Solver:* Ein Aliasing-Fehler in `_night_accounts` (nur Python; JavaScript war richtig): Beim Kombinieren der Nächte teilten sich alle Varianten dieselben Mengen, und die Forderungen verschiedener Erklärungen häuften sich, bis kein einzelner Pukka sie erfüllen konnte.
- *Solver:* Ein Zombuul, der zum ersten Mal hingerichtet wird, stirbt nicht. Der Solver hielt das für einen echten Tod, fand keinen Erben und verwarf jedes solche Brett.
- *Solver:* Ein Glücksspieler, der falsch rät und lebt, war immer „gestört". Eine Teedame neben ihm oder eine aufgezeichnete Wahl des Gastwirts hält ihn aber auch am Leben.
- *Solver:* Der Assassine wacht in Nacht 1 nicht für seine Fähigkeit auf („at night*").
- *Simulator:* Die Trunkenheit des Höflings fehlte (die sechste fehlende Störquelle in seiner Liste). Ein nüchterner Segler, ein Narr beim ersten Tod und die Nachbarn einer Teedame starben bei Hinrichtungen. Das Gift des Pukka tötete durch jeden Schutz hindurch. Der Assassine wurde nur in Nacht 1 gezählt.

Der Simulator darf jetzt den Dämon hinrichten: Ein Zombuul überlebt das beim ersten Mal, ein funktionierender Mastermind verlängert um einen Tag, danach endet das Spiel. In 1000 Partien: 60 Zusatztage, 75 überlebende Zombuuls, und bei jedem Zusatztag ist die Mastermind-Geschichte die beste Erklärung. Ein dauerhafter Test spielt 200 solche Partien.

**Oger.** Er wählt in der ersten Nacht einen Spieler und bekommt dessen wahre Gesinnung, auch betrunken oder vergiftet, ohne es zu erfahren. Spion und Einsiedler zählen für ihn als böse (Jinx). Er handelt spät in der Nacht, also sehen Empath, Adlige und Großmutter ihn in Nacht 1 noch als gut. Ab Tag 1 zählt die neue Seite. Neue Protokollzeile „Oger wählte X": Dann steht seine Seite fest, sofern der Sprecher wirklich der Oger ist. Ohne diese Zeile wiegt „böse geworden" so viel wie das Verhältnis böser zu guten Sitzen.

**Marionette.** Die Technik für „glaubt, jemand anderes zu sein" war schon allgemein, der Hinweis im Katalog war veraltet. Gefehlt hat nur die Aufbauregel „sitzt neben dem Dämon". Sie steht jetzt als Feld `beside` im Katalog und wird in der Suche und in der Stichprobe geprüft.

**Nebenbei zwei Verbesserungen, die mehr als den Oger betreffen:**

- *Jede passende Geschichte zählt anteilig.* Bisher bekam die beste Geschichte einer Welt das ganze Gewicht. Ein Oger, der böse geworden sein könnte, stand dadurch als gut da, sobald „gut geblieben" nichts kostete. Jetzt wird das Gewicht einer Welt nach dem Gewicht ihrer Geschichten aufgeteilt. Das Gewicht der Welt selbst bleibt gleich. Im Korpus ändern sich 11 von 142 Brettern: alle Oger-Sitze (das leere Easter-Brett 40 → 55 % böse), der Barbier-Tausch, und ein Brett, auf dem Mastermind und Scharlachrote Frau gleich gut passten. Dort gewann vorher zufällig die erste Geschichte.
- *Adlige und Schneiderin lesen die aktuelle Seite*, wie Empath und Koch schon vorher. Ein guter Giftmischer vom Grubenweib las sich für sie noch als böse.

Geprüft mit dem eigenen Simulator, der beide Charaktere nach seiner eigenen Lesart der Regeln spielt: 500 Easter-Partien, keine verwirft die Wahrheit. In 34 der 66 Partien mit bösem Oger ist „Oger böse" die beste Geschichte, die neue Regel wird also wirklich gebraucht. Die Engine deines Spiels kennt nur Trouble Brewing und kann hier nicht mitprüfen.

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

**Nebenbei gefunden:** Die alte lokale Python-App speicherte den Tag bei Hexen-Tod und Hinrichtung wegen Besessenheit als Text statt als Zahl. Die Seite war richtig.

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

### Messung: der Zombuul, der als tot gilt · *gemessen am 04.10.2026*

Der volle Bericht steht in `claude/messung-zombuul-gilt-als-tot.md`. Kein Code am Solver geändert.

- **Wo er steht** (44 Partien, letzter offener Morgen): meist auf Rang 3 oder 4, mit im Mittel 13 %. Vor ihm liegt fast immer ein lebender Spieler (35 von 41 Partien) mit im Mittel 56 %.
- **Ursache 1, eine fehlende Regel (22 der 44 Partien):** Das Brett zeigt nur noch zwei Lebende, und die Partie läuft. Das geht nur, wenn einer der Toten in Wahrheit lebt, also ein Zombuul ist. Der Solver kennt „Böse gewinnt bei zwei Lebenden“ nicht und gibt den toten Sitzen zusammen 45 % statt fast alles.
- **Versuch im Speicher** mit der Regel „die Partie läuft, also leben wirklich mindestens drei“: In diesen 22 Partien glaubt der Solver zu 95 % statt 52 % an einen Zombuul, der wahre Sitz steht in 9 statt 3 vorn und in 21 statt 16 unter den ersten drei. Über alle 400 Partien Bad Moon Rising: 228 statt 222 vorn. Keine wahre Welt geht verloren, und keine der 310 Partien ohne Zombuul ändert sich.
- **Ursache 2, keine Regel greift (die anderen 22 Partien):** Das Brett zeigt drei oder mehr Lebende. Der Solver glaubt dort zu etwa einem Drittel an einen Zombuul, der wahre Sitz hat im Mittel 9 %. Hier fehlt kein Regelwissen, sondern ein Hinweis: Der Zombuul tötet im Simulator fast nie, weil das Dorf fast jeden Tag hinrichtet.
- **Was auch mit der Regel bleibt:** Welcher der Hingerichteten der Zombuul ist. In den 22 Partien gibt es im Mittel 5,7 Tote, der wahre steht unter ihnen in 9 Partien an erster und in 8 an zweiter Stelle.

### Die Partie läuft, also leben wirklich mindestens drei · *erledigt am 04.10.2026*

Der volle Bericht steht in `claude/zwei-auf-dem-brett-und-die-partie-laeuft.md`.

**Deine Entscheidung vom 04.10.2026:** Weg 1. Die Regel gilt nur, wenn ein Zombuul auf dem Skript steht.

**Gebaut, in Python und JavaScript:** Zeigt das Brett zu einem Zeitpunkt, an dem die Partie lief, nur noch zwei Lebende, dann gilt für jede Welt:

- Ein Zombuul, der einmal gestorben ist, zählt als dritter. Die Welt bleibt.
- Jeder andere Dämon, der noch lebt, hätte gewonnen. Die Welt fällt weg. Das gilt auch für einen Zombuul, der nie gestorben ist.
- Ein Dämon, der wirklich tot ist, lässt nur den Zusatztag des Strippenziehers. Das prüft der Solver wie bisher.

„Die Partie lief“ heißt: zu Beginn jeder Nacht und jedes Tages, den das Brett erreicht, und jetzt. Auf Skripten ohne Zombuul ändert sich nichts.

**Neu: ein Brett kann sagen, dass die Partie vorbei ist** (`game_over`). Dann gilt die Regel nicht für „jetzt“, nur für die Zeitpunkte davor. Gespielte Partien des Simulators setzen das selbst. Der Rückblick „After the game“ der Website setzt es für seinen letzten Morgen. Die Seite selbst hat dafür noch keinen Schalter.

**Vorher geprüft, was ein Brett nach Spielende bekommt** (40 beendete Partien je Skript, zwei Lebende, kein Zombuul):

| | als beendet markiert | nicht markiert |
|---|---|---|
| Bad Moon Rising: Dämon vorn | 32 | 1 |
| Bad Moon Rising: ein Toter vorn | 2 | 33 |
| Trouble Brewing: Dämon vorn | 20 | 20 |

Wer auf Bad Moon Rising nach dem Ende einer Partie weiterrechnet, ohne dass das Brett es weiß, wird also auf die Toten verwiesen. Das ist der Preis von Weg 1.

**Messung:**

- Wahrheit gehalten, stille Nächte eingetragen: Bad Moon Rising 0 von 60.000, Trouble Brewing und Oster-Skript je 0 von 6.000, Sects & Violets unverändert 43 und 72 von je 6.000 (alle Barbier-Tausch).
- **Dämon gefunden, Bad Moon Rising, 400 Partien: 228 statt 222 vorn (57 %).** Zombuul, der als tot gilt: 9 statt 3 von 44 vorn, 30 statt 25 unter den ersten drei. Alle anderen Partien unverändert. Die gebaute Regel gibt in allen 90 Zombuul-Partien genau die Zahlen des Versuchs.
- Korpus: 194 Bretter, 4 neue für diese Regel. Kein altes Brett gibt eine andere Antwort. Python und JavaScript stimmen überein. 1.133 Tests grün, davon 13 neue.

**Was bleibt:** In den 22 Partien, in denen das Brett drei oder mehr Lebende zeigt, greift die Regel nicht (0 von 22 vorn). Und unter den Toten ist weiter offen, welcher der Zombuul ist.

**Schalter „the game is over“ auf der Website** (deine Entscheidung vom 04.10.2026, gebaut am selben Tag): Er steht als letzte Zeile unter **Information**, wird mit der Partie gespeichert und geht bei **Solve** und **How much is guesswork?** an den Solver. Der Rückblick braucht ihn nicht. Im Browser geprüft an einem Brett mit zwei Lebenden auf Bad Moon Rising: ohne Haken 555 Welten und kein Lebender als Dämon, mit Haken 1.419 Welten und die beiden Lebenden mit je 30 %. Die Anleitung für den Spieleabend nennt den Haken.

### Messung: der Zombuul, der als tot gilt, bei drei oder mehr Lebenden · *gemessen am 05.10.2026*

Der volle Bericht steht in `claude/messung-zombuul-tot-drei-lebende.md`. Kein Code am Solver geändert.

- **Woran man ihn erkennen könnte:** nur am Muster der Nächte. Ein Zombuul tötet nur nach einem Tag ohne Toten. In 4.000 gespielten Partien ist die Nacht nach einem Tag mit einem Toten beim Zombuul in 81 % still, beim Poe in 40 %, bei der Pukka in 39 %, beim Shabaloth in 24 %. Nach vier solchen stillen Nächten und keiner lauten ist es in 93 % ein Zombuul.
- **Ob der Solver es sieht:** nein. In den 22 Partien sagt das Muster allein im Mittel 70 % Zombuul, der Solver sagt 32 % und verteilt den Rest gleichmäßig auf Poe, Pukka und Shabaloth (24, 24, 20 %). Grund: Jede stille Nacht ist bei den anderen Dämonen gratis erklärbar (das Ziel konnte nicht sterben, der Dämon wurde gestoppt, der Poe wählte niemanden). Das ist nach den Regeln richtig, also fehlt keine Regel.
- **Preis im Versuch** (nur im Speicher, 400 Partien): Eine stille Nacht kostet jede Welt, deren Dämon hätte töten können, den Faktor 0,5 oder 0,25. In den 22 Partien steht der Zombuul dann in 3 oder 7 statt 0 vorn und in 17 oder 18 statt 9 unter den ersten drei. Über alle 400 Partien wird es aber schlechter: 225 oder 218 statt 228 vorn. Der Glaube an den Zombuul fließt auch dann zu den Toten, wenn der Zombuul lebt (dort 26 oder 21 statt 30 vorn). Keine wahre Welt geht verloren.
- **Was auch mit dem richtigen Typ bleibt:** welcher der Toten es ist. In 13 der 22 Partien steht der wahre Sitz unter den Toten vorn, vor ihm liegen dann nur lebende Sitze.

**Folgerung:** Deine Entscheidung „stille Nächte nicht bepreisen“ ist jetzt direkt gemessen und bestätigt. Die Stelle bleibt offen und hängt am Dorf im Simulator: Es richtet fast jeden Tag hin, deshalb tötet der Zombuul fast nie und hinterlässt kaum Spuren.

### Messung: das Dorf im Simulator · *gemessen am 05.10.2026*

Der volle Bericht steht in `claude/dorf-im-simulator-und-nachtmuster.md`. Am Simulator ist nichts geändert. Je 4.000 Partien mit `messung/dorf.py`.

- **Es richtet fast jeden Tag hin:** an 97 bis 99 % der Tage. In Bad Moon Rising überlebt der Hingerichtete an 21 % der Tage (Teufelsadvokat, Pazifist, Teedame, Narr, Segler), tot ist am Ende an 78 % der Tage jemand.
- **Es stimmt nicht ab wie ein Tisch.** Wer die meisten Stimmen hat, geht, auch mit einer einzigen. Nur 54 bis 59 % der Hinrichtungen hatten die halbe Zahl der Lebenden hinter sich, bei 6 bis 12 % hatte niemand gestimmt und ein Sitz wurde gezogen. Nach der Tischregel (meiste Stimmen, mindestens die Hälfte der Lebenden, kein Gleichstand) gäbe es an etwa 55 % der Tage eine Hinrichtung.
- **Es weiß nichts.** Nominiert wird ein gezogener Sitz, jeder Lebende stimmt mit 45 % zu, Böse für Böse mit 20 %. Der Dämon ist ausgenommen, solange die Partie mit ihm enden würde: 0 % der Hinrichtungen in Trouble Brewing und Sects & Violets, 6 % in Bad Moon Rising.
- **Folge für den Zombuul:** Er darf nur in 22 % seiner Nächte töten.

**Deine Entscheidung vom 05.10.2026:** Der Simulator bleibt, wie er ist. An deinem Tisch wird fast jeden Tag hingerichtet, die Rate passt also. Die Tischregel beim Abstimmen wird nicht gebaut, und keine Partie wird neu ausgeteilt.

### Website: das Muster der Nächte · *erledigt am 05.10.2026*

Unter den Nächten steht ein Kasten „Night pattern“, wenn ein Zombuul auf dem Skript ist. Er zählt die Nächte, getrennt nach dem Tag davor: nach einem Tag mit einem Toten und nach einem Tag ohne Toten, jeweils still oder mit Toten. Darunter steht die Regel „A Zombuul kills only after a day with no death“ und, je nach Zählung, „This pattern fits one“ oder „If the Demon is a Zombuul, something else killed on N nights“.

Der Kasten zählt nur, was auf dem Brett steht. Er ändert keine Zahl, und der Solver bleibt, wie er ist (deine Entscheidung „nur Fakten“ vom 05.10.2026). Geprüft in `tests/test_night_pattern.py` und im Browser.

### Sects & Violets: Simulator gegen Night-Walk · *untersucht und Night-Walk repariert am 05.10.2026*

Der volle Bericht steht in `claude/sv-simulator-gegen-night-walk.md`. Am Solver und am Simulator ist nichts geändert.

- **Ergebnis:** Alle 60 abweichenden Nächte (von 16.641) waren Lücken des Night-Walk, kein Regelfehler in Simulator oder Solver.
- **Lücke 1 (53 Nächte):** Der Night-Walk bekam gesagt, wer am **Ende** der Nacht betrunken oder vergiftet ist, und las das schon am Anfang. Tötet der Dämon das Liebchen und wird dadurch selbst betrunken, galt er schon vor dem Kill als betrunken. Dasselbe nach einem Barbier-Tausch, der den No Dashii und sein Gift erst nach dem Kill versetzt. Jetzt bekommt er drei Dinge gesagt: wer zu Beginn der Nacht gestört war, wer es im Lauf der Nacht wurde und wer es nicht mehr ist.
- **Lücke 2 (7 Nächte):** Ein Philosoph mit der Fähigkeit des Schlangenbeschwörers tauschte im Night-Walk nie. Jetzt wählt er an der Stelle des Schlangenbeschwörers, und zwei Schlangenbeschwörer in einer Nacht haben je ihr eigenes Ziel.
- **Nachher:** 0 von 16.641 Nächten (4 Nächte), 1 von 9.458 (6 Nächte, vorher 35). Bad Moon Rising, Trouble Brewing und das Oster-Skript bleiben bei 0.
- **Die eine verbliebene Nacht ist ein Fehler im Simulator** (offene Stelle 35): Er ordnet die Nacht nach dem Charakter, den ein Sitz **ausgeteilt** bekam, nicht nach dem, den er jetzt hat. Ein Sitz, den das Grubenweib zum Schlangenbeschwörer gemacht hat, handelt deshalb zu spät. Im Versuch (nur im Speicher) behebt die richtige Reihenfolge auch diese Nacht. Sie ändert 283 von 6.000 Partien Sects & Violets, keine auf den anderen Skripten und keines der sechs Bretter im Korpus.
- **Der Solver** hält in 57 der 60 betroffenen Partien die wahre Welt. Die 3 anderen sind Barbier-Tausche ohne gemeldeten Barbier (offene Stelle 4).

### Der Simulator ordnet die Nacht nach dem aktuellen Charakter · *erledigt am 05.10.2026*

Deine Entscheidung „Weg 1“. Eine Zeile in `tests/simulate.py`: Die Reihenfolge der Nacht liest den Charakter, den ein Sitz in dieser Nacht hat, nicht den ausgeteilten.

- **Night-Walk:** jetzt 0 Abweichungen auf allen Skripten, auch bei sechs Nächten (Sects & Violets 0 von 9.456).
- **Was sich ändert:** 283 von 6.000 Partien Sects & Violets laufen anders. Bad Moon Rising, Trouble Brewing, das Oster-Skript und alle Bretter im Korpus sind unverändert.
- **Wahre Welt gehalten, Sects & Violets neu gemessen:** 43 von 6.000 verloren (4 Nächte, wie vorher) und 69 von 6.000 (6 Nächte, vorher 72). Davon mit verstecktem Barbier 40 und 64.
- **Ein neuer Fund im Solver** (offene Stelle 36): In einer der neu gespielten Partien (Seed 1078) wählt ein Schlangenbeschwörer an Platz 11 und wird in derselben Nacht vom Grubenweib an Platz 16 zum Uhrmacher gemacht. Der Solver rechnet in ganzen Nächten, hält den Sitz in dieser Nacht für einen Uhrmacher und verwirft seine Wahl als Schlangenbeschwörer. Damit geht die wahre Welt verloren, in 1 von 6.000 Partien.
- **Nicht neu gemessen:** „Dämon gefunden“ für Sects & Violets (65 %, 400 Partien). Etwa 5 % der Partien sind neu, der Wert kann sich um wenige Punkte verschieben.
- 1.149 Tests, drei davon neu.

### Die ersten fünf experimentellen Charaktere · *erledigt am 05.10.2026*

Der volle Bericht steht in `claude/experimentelle-charaktere-batch-1.md`.

**Deine Entscheidungen vom 05.10.2026:** Der erste Batch ist Gutsverwalter, Ritter, Shugenja, Nachtwächter und König. Der Dorftrottel aus dem Vorschlag ist nicht dabei: Sein Aufbau bringt denselben Charakter bis zu dreimal ins Spiel, und die Suche lässt jeden Charakter nur einmal zu. Dazu fünfmal Weg 1:

| | Entscheidung |
|---|---|
| A | Der Shugenja liest nach dem, wie ein Spieler registriert, wie Koch und Empath. |
| B | Beim Nachtwächter zählt nur die Zeile des Gewählten. Was der Nachtwächter selbst sagt, wird aufgezeichnet. |
| C | Der König zählt an seinem Platz in der Nacht, also mit den Toten dieser Nacht. |
| D | Ein Zombuul, der als tot gilt, zählt für den König als lebend. |
| E | Die drei Plätze, die die Nachtreihenfolge im Repo nicht kennt, sind von Hand eingetragen. |

**Gebaut, in Python und JavaScript:**

| Charakter | Zeile auf der Website | Was der Solver prüft |
|---|---|---|
| Gutsverwalter | „X ist gut“ | X registriert als gut. Ein Spion darf es sein, dann war er in dieser Nacht nicht gestört. Unter einem Vortox ist X böse. |
| Ritter | „X und Y sind nicht der Dämon“ | Keiner der beiden hält in dieser Nacht einen Dämon. Schergen sind erlaubt und können später Dämon werden. Unter einem Vortox ist der Dämon dabei. |
| Shugenja | „im Uhrzeigersinn“ oder „gegen den Uhrzeigersinn“ | Der nächste Sitz, der dort als böse registrieren kann, ist nicht weiter weg als der nächste auf der anderen Seite, der es muss. Bei gleicher Entfernung passt beides, auch unter einem Vortox. |
| Nachtwächter | „wählte X“, gesagt vom Nachtwächter | Aufgezeichnet. Datiert die Wahl: Bis zu dieser Nacht wird er geweckt, danach nicht mehr (Kammerzofe). |
| | „wurde geweckt: Y ist der Nachtwächter“, gesagt vom Gewählten | Y ist der Nachtwächter, lebte an seinem Platz in der Nacht und war nicht gestört. Ein falscher Name lässt sich nicht mit Gift erklären, denn ein gestörter Nachtwächter weckt niemanden. Ein Trunkenbold mit dem Plättchen auch nicht. Unter einem Vortox wird ein falscher Spieler gezeigt. |
| König | „Charakter C lebt“ | Es gibt mindestens so viele Tote wie Lebende, und ein Lebender registriert als C. Unter einem Vortox hält kein Lebender C. |
| | „erfuhr nichts“ | Es gibt weniger Tote als Lebende. Zeigt das Brett es anders, lebt einer der Toten: ein Zombuul. |

**Das Tor:**

| Nr. | Schritt | Ergebnis |
|---|---|---|
| 1 | Solver in Python und JavaScript | 20 neue Bretter im Korpus, beide stimmen überein. |
| 2 | Simulator | Spielt alle fünf, auch betrunken, vergiftet und unter einem Vortox. |
| 3 | Night-Walk | 0 von 17.593 und 0 von 16.203 Nächten weichen ab (zwei eigene Skripte). |
| 4 | Vierzig gemischte Partien | 1 von 40 verliert die wahre Welt, nicht wegen der fünf (siehe Befund). |
| 5 | Website | Sechs Zeilen eintragbar, der Prüftest ist grün, im Browser geprüft. |
| 6 | Korpus und Suite | 214 Bretter, 1.210 Tests grün (61 neue). |

**Messung:**

- **Zwei eigene Skripte**, weil die fünf kein Skript haben (`tests/test_experimental.py`): eines mit Spion, Einsiedler und Zombuul, eines mit Vortox. Wahre Welt gehalten: 0 von 24.000 verloren (je 6.000 Partien über 4 und 6 Nächte).
- **Auskünfte, Night-Walk gegen Simulator:** 1 von 4.254 weicht ab. Dort wählt das Grubenweib den Schläger, und der Simulator fragt den Schläger nicht.
- **Grundskripte unverändert:** Trouble Brewing, Oster-Skript und Sects & Violets spielen Zeichen für Zeichen dieselben Partien (Prüfsummen gleich). Bad Moon Rising, Trouble Brewing und Oster-Skript: je 0 von 6.000 verloren. Sects & Violets: 43 von 6.000, wie vorher.
- **Korpus:** 134 alte Bretter geben dieselbe Antwort. Die 60 Zufallsbretter sind neu gezogen, weil ihr Vorrat an Charakteren um fünf gewachsen ist.

**Befund: Die gemischten Skripte waren schon vorher nicht sauber** (offene Stelle 37). `messung/tor.py` spielt gemischte Partien, einmal mit den fünf auf jedem Skript und einmal mit dem alten Stand ohne sie:

| 3.000 gemischte Partien, 4 Nächte | wahre Welt verloren | Night-Walk weicht ab |
|---|---|---|
| alter Stand, nichts Neues | 107 (3,6 %) | 129 von 8.456 Nächten |
| mit den fünf auf jedem Skript | 50 (1,7 %) | 45 von 8.367 Nächten |

Keine der 45 Nächte hängt am Nachtwächter, dem einzigen der fünf, der jemanden wählt. Von den 50 Partien bleiben 48 verloren, wenn man die Zeilen der fünf wegnimmt. Die anderen 2 haben ihre Ursache ebenfalls anderswo (Philosoph neben Kammerzofe, Barbier-Tausch mit einem Philosophen). Mit den fünf sind es weniger, weil sie auf jedem Skript fünf Plätze belegen, auf denen sonst etwas Schwieriges stünde.

Die Ursachen sind Paarungen, die es auf keinem Grundskript gibt:

| Paarung | Wo der Fehler sitzt |
|---|---|
| Vortox neben Rabenhüter oder Totengräber | Simulator: Der Rabenhüter bekommt unter einem Vortox die Wahrheit, beim Totengräber geht der Sitz verloren. |
| Vortox neben Koch, Empath, Orakel oder Schneiderin, mit Spion, Einsiedler oder Schläger | Solver: Eine falsche Auskunft, die durch Registrieren legal wäre, gilt ihm als wahr. Hier ist eine Lesart zu wählen. |
| Kammerzofe neben Schlangenbeschwörer | Simulator: Die Kammerzofe zählt nach dem ausgeteilten Charakter, nicht nach dem aktuellen. |
| Kammerzofe neben Philosoph | Solver: In der Nacht seiner Wahl gilt der Philosoph nicht als geweckt. Simulator: Danach weckt er ihn nie mehr. |
| Grubenweib wählt den Schläger | Simulator: Der Schläger antwortet nicht. |

### Die gemischten Skripte aufgeräumt · *erledigt am 07.10.2026*

Der volle Bericht steht in `claude/gemischte-skripte-aufgeraeumt.md`.

**Deine Entscheidung vom 07.10.2026:** erst die gemischten Skripte aufräumen, dann Batch 2.

**Ergebnis:** `messung/tor.py` spielt gemischte Partien auf Skripten, die Charaktere zusammenbringen, die sich auf keinem Grundskript begegnen.

| 3.000 gemischte Partien | wahre Welt verloren, vorher | jetzt | Night-Walk weicht ab, vorher | jetzt |
|---|---|---|---|---|
| 4 Nächte, nichts Neues | 96 (3,2 %) | 16 (0,5 %) | 32 von 8.325 Nächten | 25 von 8.316 |
| 4 Nächte, mit den fünf aus Batch 1 | 50 (1,7 %) | 14 (0,5 %) | 12 von 8.301 | 9 von 8.284 |
| 6 Nächte, nichts Neues | 106 (3,5 %) | 20 (0,7 %) | 39 von 10.461 | 30 von 10.451 |

„Vorher“ ist der Stand nach Batch 1. Vor Batch 1 waren es 107, seitdem werden die Skripte aus einem um fünf Charaktere größeren Vorrat gezogen.

**Berichtigung zum 05.10.2026:** Die Zahl „Night-Walk weicht in 129 von 8.456 Nächten ab“ war zum größten Teil ein Fehler in meinem Messskript. Es lief Nächte nach, die nie gespielt wurden, wenn ein Alsaahir die Partie beendet hatte. Richtig gemessen waren es 32 von 8.325. Die Zahl der verlorenen wahren Welten war davon nicht betroffen.

**Was falsch war, im Simulator** (er las die ausgeteilten Charaktere, wo er die von heute Nacht meinte, oder spielte etwas nicht):

| Paarung | Fehler | Behoben |
|---|---|---|
| Vortox neben Totengräber | Die falsche Auskunft verlor ihren Sitz und sprach immer von Sitz 1. Das galt auch für einen vergifteten Totengräber in Trouble Brewing. | Der Sitz bleibt, nur der Charakter ist falsch. |
| Vortox neben Rabenhüter | Er bekam immer die Wahrheit, auch vergiftet. | Er bekommt jetzt etwas Falsches. |
| Kammerzofe neben Schlangenbeschwörer oder Grubenweib | Sie zählte nach dem ausgeteilten Charakter. | Sie zählt nach dem Charakter von heute Nacht. |
| Kammerzofe neben Philosoph | Nach seiner Wahl wurde er nie mehr geweckt. | Er wird geweckt wie der Charakter, den er genommen hat. |
| Kammerzofe neben Charakteren, die ihre Fähigkeit einmal nutzen | Die Nacht, in der sie sie nutzen, zählte nicht (Schneiderin in Nacht 1). | Sie zählt. |
| Waschweib, Bibliothekar, Koch nach einem Tausch in Nacht 1 | Sie lasen die Charaktere vor dem Tausch. | Sie lesen den Stand an ihrem Platz in der Nacht. |
| Baron neben Fang Gu | Beide konnten im selben Beutel liegen, der nur für einen gezählt war. Diese Welt ist nicht legal. | Höchstens ein Charakter, der den Aufbau ändert. |
| Fang Gu springt in den Trunkenbold | Der neue Fang Gu galt für den Rest der Partie als betrunken und tötete nie. | Das falsche Plättchen endet, wenn der Sitz einen anderen Charakter bekommt. |
| Giftmischer neben Grubenweib | Der ausgeteilte Sitz vergiftete weiter, nachdem er verwandelt war, und ein neu erschaffener Giftmischer vergiftete nie. | Es vergiftet, wer den Charakter heute Nacht hält. Wird er in derselben Nacht verwandelt, endet das Gift. |
| Gestörter Sitz nach einem Tausch | Er hörte Auskünfte für den Charakter, den er abgegeben hatte. | Er hört, was zu seinem heutigen Charakter passt. |

**Was falsch war, im Solver** (Python und JavaScript):

| Paarung | Fehler | Behoben |
|---|---|---|
| Kammerzofe neben Philosoph | In der Nacht seiner Wahl galt er nur als geweckt, wenn der genommene Charakter aufwacht. | Er ist in dieser Nacht wach, weil er wählt. |
| Wahrsagerin unter einem Vortox | Ein „Nein“ auf zwei gute Spieler galt als wahr. Liegt der rote Hering im Paar, ist es falsch. | Der rote Hering wird auch unter einem Vortox gesucht. |
| Kammerzofe unter einem Vortox | Eine Zahl galt als wahr, sobald sie möglich war, auch wenn eine zweite genauso möglich war. | Wahr ist sie nur, wenn keine andere möglich ist. |
| Glücksspieler neben Schlangenbeschwörer, Grubenweib oder Barbier | Der Tipp wurde am Stand nach der Nacht geprüft. Der Glücksspieler rät aber an Platz 10, vor allen, die Charaktere bewegen. | Geprüft wird der Stand vor der Nacht. Stirbt er und wird danach verwandelt, bleibt sein Tod erklärt. |
| Philosoph mit der Fähigkeit des Glücksspielers | Sein falscher Tipp tötete ihn nicht, weil die Regel nur den echten Glücksspieler kannte. | Jeder, der die Fähigkeit hat, riskiert seinen eigenen Tipp. Auch im Night-Walk. |
| Exorzist neben Fang Gu | Nannte er den Außenseiter, in den der Fang Gu gleich danach sprang, galt der Dämon als gestoppt. | Es zählt der Dämon, den es an Platz 21 gab. |
| Fang Gu springt in den Trunkenbold | Das falsche Plättchen störte den Sitz weiter. | Es endet mit dem Charakter, wie im Simulator. |
| Philosoph nimmt die Verrückte | Zwei Regeln riefen sich endlos gegenseitig auf, der Solver stürzte ab. | Er wacht dafür nicht auf. |

**Drei Fehler der Website,** die erst die gemischten Bretter gezeigt haben:

| Fehler | Folge | Behoben |
|---|---|---|
| Die Regel für den Tod der Akrobatin rief in JavaScript einen Namen auf, den es nicht gab. | Jedes Brett mit einer eingetragenen Wahl der Akrobatin brach auf der Website mit einem Fehler ab. Python war nicht betroffen. | Ja. |
| Die Zeile einer Akrobatin, die in derselben Nacht stirbt, wurde abgelehnt („wurde getötet und ist nie aufgewacht“). | Etwa jedes 25. gemischte Brett ließ sich nicht eintragen. Sie stirbt aber gerade wegen ihrer Wahl, wie der Glücksspieler. | Ja, in Python und JavaScript. |
| Die Zeile des Ballonfahrers galt in JavaScript unter einem Vortox als gewogene Auskunft. | JavaScript verwarf jede Welt mit einem arbeitenden Vortox neben einem Ballonfahrer, Python nicht. | Ja. |

**Messung:**

- **Python gegen JavaScript:** Die wahre Welt von 4.446 gemischten Partien kostet in beiden Sprachen dasselbe (vorher brach JavaScript bei 82 von 1.421 ab). Im Korpus stehen 9 gemischte Bretter, je eines pro behobener Klasse.
- **Grundskripte:** Trouble Brewing, Bad Moon Rising, Oster-Skript und die zwei eigenen Skripte aus Batch 1 verlieren weiter 0 von je 6.000 Partien (4 und 6 Nächte). Sects & Violets: 62 von 6.000, vorher ebenfalls 62, davon 58 die Barbier-Klasse aus Stelle 4. Night-Walk: 0 abweichende Nächte auf allen sechs Skripten.
- **Der Simulator spielt einige Partien anders als vorher.** Bad Moon Rising: keine. Trouble Brewing und Oster-Skript: 4 % der Partien haben eine berichtigte Totengräber-Zeile, 0,4 % verlaufen anders (wegen des Rabenhüters). Sects & Violets: 8 % verlaufen anders, weil ein vergifteter Sitz nach einem Tausch jetzt zu seinem neuen Charakter befragt wird. Die Prüfsummen in `messung/tbhash.py` sind deshalb neu.
- **Tests:** 1.232 grün, davon 22 neue in `tests/test_mixed_scripts.py`. Der letzte davon spielt 600 gemischte Partien je Lauf und lässt nur die Seeds durch, die mit Grund auf der Liste stehen.
- **Korpus:** 223 Bretter. 212 alte geben dieselbe Antwort. `sv-played-672` ist eine der Partien, die jetzt anders verlaufen. `random-58` behält 150 statt 141 Welten: Dort kann der Fang Gu in eine Verrückte springen, die danach wirklich tötet.

**Was noch verloren geht** (16 von 3.000 ohne die fünf, 14 von 3.000 mit ihnen):

| Klasse | ohne die fünf | mit den fünf | Stand |
|---|---|---|---|
| Barbier-Tausch, den niemand gemeldet hat | 10 | 6 | Offene Stelle 4, nach deiner Regel gewollt. |
| Vortox und Registrieren (Koch, Empath, Orakel, Schneiderin, Wahrsagerin) | 5 | 3 | *Behoben am selben Tag,* siehe unten. Danach sind es 11 und 11. |
| Gastwirt schützt einen Fang Gu, der springt | 0 | 2 | Offene Stelle 41, Regelfrage. |
| Mathematiker unter einem Vortox | 0 | 1 | Offene Stelle 6. |
| Eine Auskunft stimmt nur durch Registrieren, in einer Nacht, in der alle betrunken sind | 1 | 0 | Offene Stelle 42. |
| Einzelfälle | 0 | 2 | Einer ist die offene Stelle 36 (Gastwirt wählt und wird in derselben Nacht verwandelt). Den anderen habe ich nicht zugeordnet (Seed 461: Trunkenbold mit dem Plättchen des Schlangenbeschwörers neben einem Philosophen, der dieselbe Fähigkeit nahm). |

**Vortox und Registrieren · *entschieden und gebaut am 07.10.2026*** (frühere offene Stelle 38). Unter einem Vortox muss die Auskunft eines Bürgers falsch sein. **Deine Entscheidung: Weg 1, die Wirklichkeit zählt, und die Adlige auch.** Beispiel: Ein Koch sitzt an einem Tisch ohne böses Paar, neben dem Dämon sitzt ein Einsiedler. Sagt der Erzähler „1“, ist das falsch, weil es in Wirklichkeit kein böses Paar gibt. Dass der Einsiedler als böse registrieren dürfte, macht die Zahl nicht wahr.

| Charakter | Unter einem Vortox gilt als wahr (und kann deshalb nicht gesagt worden sein) |
|---|---|
| Koch | Die Zahl der Paare, die wirklich böse sind. |
| Empath | Die Zahl der Nachbarn, die wirklich böse sind. |
| Orakel | Die Zahl der Toten, die wirklich böse sind. |
| Schneiderin | Ob die zwei wirklich auf derselben Seite stehen. |
| Wahrsagerin | „Ja“, wenn ein Dämon oder der rote Hering im Paar ist. Ein „Ja“ auf einen Einsiedler ist falsch. |
| Jongleur | Die Zahl der Tipps, die den wirklichen Charakter treffen. |
| Großmutter | Der wirkliche Charakter eines wirklich guten Spielers. |
| Adlige | Genau einer der drei ist wirklich böse. Vorher las der Code hier als einziger streng: falsch war nur, was auch mit Registrieren nicht „genau einer“ ergeben konnte. Der Simulator verfälscht jetzt ebenfalls nach der Wirklichkeit. |

Ohne Vortox ändert sich nichts: Eine ehrliche Auskunft muss weiter nur legal sein, also mit Registrieren stimmen können. Waschweib, Bibliothekar, Detektiv, Träumer, Totengräber, Rabenhüter, Gutsverwalter und König rechneten schon so.

| 3.000 gemischte Partien | wahre Welt verloren, vor der Entscheidung | danach |
|---|---|---|
| 4 Nächte, nichts Neues | 16 | 11 (0,4 %) |
| 4 Nächte, mit den fünf aus Batch 1 | 14 | 11 (0,4 %) |
| 6 Nächte, nichts Neues | 20 | 15 (0,5 %) |

Die Grundskripte verlieren dieselben Partien wie vorher (Sects & Violets 23 und 39 von je 3.000, alle anderen 0). Das Oster-Skript spielt einige Partien anders, weil eine vergiftete Adlige jetzt eine andere falsche Auskunft hört. Neue Prüfsumme: `EASTER b58eb3f2d8074508`. Python und JavaScript kosten die wahre Welt von 4.446 gemischten Partien gleich. Im Korpus stehen 5 neue Bretter für diese Regel (228 insgesamt, alle 223 alten geben dieselbe Antwort). 1.239 Tests sind grün.

### Die zweiten fünf experimentellen Charaktere · *erledigt am 07.10.2026*

Der volle Bericht steht in `claude/experimentelle-charaktere-batch-2.md`.

**Dein Auftrag vom 07.10.2026:** „Such fünf kleine aus und mach direkt weiter.“ Ausgesucht: **Banshee, Eiferer, Ketzer, Goblin und Ojo**, also ein Bürger, zwei Außenseiter, ein Scherge und ein Dämon. Keiner von ihnen liest etwas, nur der Ojo handelt nachts. Die Regeln sind aus dem Wiki gelesen.

**Sechs Lesarten habe ich selbst gewählt,** weil du nicht gefragt werden wolltest. Jede lässt sich umdrehen:

| | Was ich gewählt habe | Warum |
|---|---|---|
| A | Die Ansage der Banshee ist eine Tatsache ohne Sitz: „Heute Nacht starb die Banshee.“ Welcher der Toten sie war, sagt die Welt. | Das Wiki lässt den Erzähler nur ansagen, dass sie starb. |
| B | Geprüft wird, dass eine Banshee in dieser Nacht starb und nicht gestört war. Nicht geprüft wird, dass der Dämon sie getötet hat. | Was einen Sitz getötet hat, kann eine Zeile den Solver nicht fragen. Das lässt eher zu viel durch als zu wenig. |
| C | Ein Eiferer, der nicht abgestimmt hat, kostet die Welt den Faktor 0,1. Er macht sie nicht unmöglich. | Nach dem Wiki wäre es Betrug. Am Tisch ist eine nicht eingetragene Stimme aber wahrscheinlicher, und eine fehlende Stimme darf die wahre Welt nicht kosten. |
| D | Der Goblin wird nur geprüft, wenn der Sprecher hingerichtet wurde, daran starb und die Partie weiterging. Wurde er hingerichtet und überlebte, sagt das Brett nichts. | Ob „hingerichtet“ ohne Tod für den Sieg reicht, steht nicht im Wiki. |
| E | Nennt der Ojo den Charakter des Schlägers, gilt der Schläger als gewählt. | Das Wiki zum Schläger nennt als Beispiel einen Höfling, der den Schläger wählt (siehe offene Stelle 45). |
| F | Der Platz des Ojo in der Nacht ist von Hand eingetragen (nach der Vigormortis). | Die Nachtreihenfolge im Repo kennt ihn nicht (offene Stelle 39). |

**Gebaut, in Python und JavaScript:**

| Charakter | Zeile auf der Website | Was der Solver prüft |
|---|---|---|
| Banshee | „Banshee announced“ (Nacht) | Eine Banshee starb in dieser Nacht und war nicht gestört. Eine Welt ohne solche Banshee ist unmöglich. Ein Trunkenbold mit dem Plättchen zählt nicht, ein Philosoph mit der Fähigkeit schon. Ein Vortox ändert nichts (ihr Jinx). |
| Eiferer | keine | An einem Tag mit eingetragenen Stimmen, einer Nominierung und fünf oder mehr Lebenden hat der Eiferer abgestimmt. Sonst kostet die Welt den Faktor 0,1 je Tag. |
| Ketzer | keine | Nichts. Die Partie endet im selben Moment, nur der Sieger ist vertauscht. |
| Goblin | „Goblin claim“ (Tag) | Wer das sagt, hingerichtet wird und stirbt, während die Partie weitergeht, war kein arbeitender Goblin. War er der Goblin, muss er an diesem Tag gestört gewesen sein. Jeder darf es sagen. |
| Ojo | keine | Tötet wie jeder Dämon einen Spieler je Nacht. Er gibt den Stern nicht weiter, wenn er nachts stirbt. |

Der Simulator spielt alle fünf: Der Eiferer stimmt immer ab, der Goblin sagt es in 70 % der Fälle, wenn er hingerichtet wird, und beendet damit die Partie, wenn er nicht gestört ist. In 6 % der Hinrichtungen sagt es jemand anderes.

**Das Tor:**

| Nr. | Schritt | Ergebnis |
|---|---|---|
| 1 | Solver in Python und JavaScript | 15 neue Bretter im Korpus, beide stimmen überein. Die wahre Welt von 4.453 gemischten Partien kostet in beiden gleich. |
| 2 | Simulator | Spielt alle fünf. 3.000 gemischte Partien: 305 Ansagen der Banshee, 687 Goblin-Sätze, etwa 220 Partien, die ein Goblin gewinnt. |
| 3 | Night-Walk | Alle 305 Ansagen der Banshee passen zum Night-Walk. Auf den zwei eigenen Skripten weicht 1 von 16.360 Nächten ab (offene Stelle 46). |
| 4 | Gemischte Partien mit den fünf | 6 von 3.000 verlieren die wahre Welt (4 Nächte), 11 von 3.000 bei 6 Nächten. Keine wegen der Zeilen der fünf. |
| 5 | Website | Zwei neue Zeilen eintragbar, im Browser geprüft. |
| 6 | Korpus und Suite | 243 Bretter, 1.280 Tests grün (41 neue). |

**Messung:**

- **Zwei eigene Skripte** (`tests/test_experimental_2.py`), eines wie Trouble Brewing und eines wie Bad Moon Rising. Wahre Welt gehalten: 1 von 12.000 verloren. Diese eine Partie (Seed 2118, 6 Nächte) geht an der Grenze von 400 Erzählungen verloren, nicht an den fünf: Mit einer höheren Grenze hält der Solver sie. Das ist das erste Mal, dass die Grenze messbar eine wahre Welt kostet (offene Stelle 22).
- **Grundskripte:** Trouble Brewing, Bad Moon Rising, Oster-Skript und die zwei Skripte aus Batch 1 verlieren 0 von je 6.000. Sects & Violets 62 von 6.000 wie vorher.
- **Gemischte Partien ohne Pflicht-Charaktere:** 15 von 3.000 (0,5 %). Das ist nicht mit den 11 von vorher zu vergleichen: Die Skripte werden jetzt aus 93 statt 88 Charakteren gezogen, es sind andere Partien. Von den 15 sind 10 die Barbier-Klasse, 2 die offene Stelle 41, 2 der Mathematiker unter einem Vortox (Stelle 6) und 1 ein Philosoph mit der Fähigkeit des Höflings.
- **Korpus:** 168 alte Bretter geben dieselbe Antwort. Die 60 Zufallsbretter sind neu gezogen, weil ihr Vorrat um fünf gewachsen ist.
- **Benannte gemischte Partien bleiben stabil:** Tests und Korpus ziehen ihre gemischten Skripte aus dem Vorrat vom 07.10.2026 (88 Charaktere), damit „Seed 1250“ nach jedem Batch dieselbe Partie bleibt (`an_awkward_script(as_named=True)`). Das Tor zieht aus allem.

**Nebenbei gefunden und behoben:**

| Wo | Fehler | Folge |
|---|---|---|
| Website | Hielt eine feste Tatsache in einer Welt nicht (ein Schuss, der tötete, eine Nominierung, die den Nominierenden tötete) und stand danach noch eine erfundene Zeile auf dem Brett, zählte JavaScript die Welt als möglich mit Gewicht null. Python verwarf sie. | Die Zahl „worlds remain“ konnte auf der Website zu hoch sein. Die Prozente stimmten. |
| Simulator | Ein gestörter Spion oder Einsiedler wurde Waschweib, Bibliothekar und Detektiv trotzdem als etwas anderes gezeigt. Deine Regel sagt: Wer gestört ist, registriert nicht anders. | Trouble Brewing spielt deshalb einige Partien anders (neue Prüfsumme `TB 4ff5ece3d7c1f8a7`). Verloren ging dort nichts. |
| Simulator | Das Dorf richtete den Dämon hin und spielte den Extratag des Strippenziehers, obwohl eine Scharlachrote Frau bereitstand. Sie übernimmt zuerst. | Nur auf gemischten Skripten. |
| Solver | Meine Regel für den Exorzisten vom selben Tag griff zu weit: Tauschte ein Schlangenbeschwörer vorher mit dem Dämon und tötete der neue Dämon den alten, galt der alte als genannt. | Jetzt zählt der alte Dämon nur, wenn er als Dämon starb (Sprung, Stern). |

### Deine Antworten zu Batch 2 und der Höfling · *erledigt am 08.10.2026*

Der Nachtrag steht im Bericht `claude/experimentelle-charaktere-batch-2.md`.

**Deine Antworten vom 08.10.2026:** A, E und F bleiben. B, C und D sind umgedreht. Beim Höfling gilt Weg 1, wie im Wiki.

| | Deine Regel | Was der Solver jetzt tut |
|---|---|---|
| B | Die Banshee wird nur angesagt, wenn der Dämon sie getötet hat. Auch ihre Fähigkeit im Tod gilt nur dann. | Steht „Banshee announced“ auf dem Brett, muss die Banshee in dieser Nacht durch den Dämon gestorben sein. Eine Welt, in der sie anders starb (Attentäter, Klatschbase, Pate), ist unmöglich. Gebaut in der Todes-Mechanik: Jede andere Ursache prallt an ihr ab. |
| C | Ein Eiferer, der nicht abstimmt, ist kein Eiferer. | An einem Tag mit eingetragenen Stimmen, einer Nominierung und fünf oder mehr Lebenden ist eine Welt unmöglich, in der der Eiferer nicht abgestimmt hat. Der Faktor 0,1 ist weg. Eine Vergiftung entschuldigt das nicht, weil ein Eiferer seine Fähigkeit nicht nutzt, sondern einhalten muss. |
| D | Ein Goblin, der hingerichtet wird und nicht stirbt, beendet die Partie trotzdem. | Geprüft wird jetzt jeder hingerichtete Sprecher, nicht nur einer, der daran starb. Ging die Partie danach weiter, war er kein arbeitender Goblin. Im Simulator gewinnt ein hingerichteter Goblin auch, wenn er überlebt. |
| Höfling | Nennt der Höfling den Schläger, zählt das als Wahl des Schlägers. | Ist der Höfling in dieser Nacht der Erste, wird er betrunken, und der Schläger bleibt nüchtern. Solver, Simulator und Night-Walk rechnen so. Die Abweichung für das Einzelspieler-Spiel steht in `claude/handover-hoefling-schlaeger.md`. |

**Messung:**

| Was | Ergebnis |
|---|---|
| Bad Moon Rising | 0 von 6.000 verloren, Night-Walk 0 von 8.467 Nächten abweichend. Die Partien sind etwas anders, weil der Höfling eine Wahl mehr hat. |
| Zwei eigene Skripte aus Batch 2 | 1 von 12.000 verloren (Seed 1073, 6 Nächte). Wie vorher an der Grenze von 400 Erzählungen: Mit 2.000 hält der Solver sie. Seed 2118 ist jetzt eine andere Partie und wird gehalten. |
| Andere Grundskripte | Trouble Brewing, Oster-Skript, Sects & Violets: Prüfsummen unverändert. Sects & Violets 62 von 6.000 wie vorher, die anderen 0. |
| Gemischte Partien mit den fünf | 7 von 3.000 bei 4 Nächten, 11 von 3.000 bei 6 Nächten. Keine wegen der Zeilen der fünf. Neu verloren ist Seed 304: Weil der Höfling jetzt auch den Schläger nennen kann, verläuft die Partie anders und landet in der bekannten Klasse „Philosoph mit der Fähigkeit des Höflings“. |
| Gemischte Partien ohne Pflicht-Charaktere | 16 von 3.000. Neu ist Seed 1576, aus demselben Grund eine andere Partie, und sie gehört zur Barbier-Klasse. |
| Banshee, Simulator gegen Night-Walk | 316 Ansagen, 0 abweichend. |
| Python gegen JavaScript | Die wahre Welt von 2.972 gemischten Partien kostet in beiden gleich. |
| Korpus | 237 von 243 Brettern geben dieselbe Antwort. Zwei Bad-Moon-Rising-Partien sind neu gespielt (Höfling). Vier Bretter auf dem eigenen Skript mit Banshee geben andere Prozente, weil ihr Tod jetzt dem Dämon gehören muss. |
| Suite | 1.287 Tests grün, 4 davon neu (der Höfling, der den Schläger nennt). |


### Die dritten fünf experimentellen Charaktere · *erledigt am 08.10.2026*

Der volle Bericht steht in `claude/experimentelle-charaktere-batch-3.md`.

**Dein Auftrag vom 08.10.2026:** „Such aus.“ Ausgesucht habe ich die fünf kleinsten, die noch übrig waren: **Magierin, Mohnzüchter, Politiker, Petze und Geist**. Das sind zwei Bürger, zwei Außenseiter und ein Scherge. Vier von ihnen ändern nur, was das böse Team weiß oder wer am Ende gewinnt. Das zeigt kein Brett. Der Geist ändert, wer nachts wach ist, und das sieht die Kammerzofe.

| Charakter | Was der Solver daraus macht |
|---|---|
| Magierin | Nichts. Sie wacht nie für sich auf. |
| Mohnzüchter | Nichts. Wenn das böse Team in der Nacht seines Todes geweckt wird, ist das nicht ihre eigene Fähigkeit. Die Kammerzofe zählt es nicht. |
| Politiker | Nichts. Ob er die Seite wechselt, entscheidet sich erst nach der Partie. |
| Petze | Nichts. Die Schergen bekommen ihre Bluffs, ohne dass das als Aufwachen durch ihre eigene Fähigkeit zählt. |
| Geist | Er wacht in jeder Nacht auf, in der ein anderer böser Spieler durch seine eigene Fähigkeit aufwacht. Die Kammerzofe zählt ihn. Ist das Aufwachen des anderen Bösen offen (der Dämon in Nacht 1, der Exorzist), ist es auch beim Geist offen. |

**Vier Lesarten hatte ich selbst gewählt:**

| | Was ich gewählt habe | Warum |
|---|---|---|
| A | Der Geist zählt für die Kammerzofe als durch seine eigene Fähigkeit geweckt. | Der Erzähler weckt ihn nur wegen seiner Fähigkeit. Das Wiki sagt zur Kammerzofe nichts. |
| B | Geweckt wird er nur, wenn ein anderer Böser durch seine eigene Fähigkeit aufwacht. Schergen- und Dämonen-Info in Nacht 1 zählen nicht. Ein Spion, der das Grimoire sieht, zählt. Ein Böser Zwilling nur in Nacht 1. | Deine Regel vom 02.10.2026: Der Dämon in Nacht 1 zählt nicht für die Kammerzofe. Der Spion öffnet die Augen, auch wenn er nur etwas gezeigt bekommt. |
| C | Ein betrunkener oder vergifteter Geist zählt trotzdem. | Er wird geweckt, um zu erfahren, dass er nicht schauen darf. So rechnet der Solver bei jedem gestörten Charakter. |
| D | Lebt ein Mohnzüchter, ist offen, ob der Spion das Grimoire gesehen hat. | Ihr Jinx: Hat der Mohnzüchter seine Fähigkeit, sieht der Spion das Grimoire nicht. Ob er sie hat, weiß der Solver an dieser Stelle nicht. |

Nicht gebaut: der Jinx von Magierin und Geist. Nach jeder Hinrichtung darf eine lebende Magierin öffentlich raten, wer der Geist ist. Liegt sie richtig, muss der Dämon in dieser Nacht den Geist wählen.

**Deine Antworten vom 08.10.2026:** A und B sind richtig. C und D sind umgedreht, und das ist gebaut:

| | Deine Regel | Was der Solver jetzt tut |
|---|---|---|
| C | Ein betrunkener oder vergifteter Geist wacht nicht auf. | Die Kammerzofe zählt ihn dann nicht. Braucht ihre Zahl einen wachen Geist, muss er nüchtern gewesen sein. Braucht sie einen schlafenden, muss er gestört gewesen sein. In beiden Fällen darf stattdessen die Kammerzofe selbst gestört gewesen sein. Der Solver probiert beide Wege. |
| D | Der Spion sieht das Grimoire nicht, solange der Mohnzüchter lebt. | Ob der Mohnzüchter dabei gestört ist, spielt keine Rolle. Ein Spion neben einem lebenden Mohnzüchter weckt den Geist nicht. |

Dass der Jinx von Magierin und Geist nicht gebaut ist, passt für dich.

Für C kann eine Zeile jetzt sagen: „entweder die Kammerzofe war gestört oder der Geist“. Der Solver probiert beide Wege, so wie beim Vortox mit dem Mathematiker. Gemessen: Auf dem Skript wie Bad Moon Rising fragte die Kammerzofe 324-mal nach einem Geist, 70-mal war er gestört, und 0 von 6.000 Partien verlieren die wahre Welt. Die gemischten Partien verlieren dieselben 6 von 3.000 wie vorher, Python und JavaScript stimmen auf 2.984 Partien überein. Im Korpus stehen zwei neue Bretter mit einem Höfling, der den Geist nennt (255 insgesamt). 1.311 Tests sind grün.

**Das Tor:**

| Nr. | Schritt | Ergebnis |
|---|---|---|
| 1 | Solver in Python und JavaScript | 10 neue Bretter im Korpus, beide stimmen überein. Die wahre Welt von 2.984 gemischten Partien kostet in beiden gleich. |
| 2 | Simulator | Spielt alle fünf. Die Kammerzofe zählt den Geist nach derselben Regel. In 3.000 gemischten Partien fragte sie 50-mal nach einem Geist. |
| 3 | Night-Walk | Keiner der fünf handelt nachts. Auf den zwei eigenen Skripten weicht 1 von 17.222 Nächten ab, nicht wegen der fünf (offene Stelle 47). |
| 4 | Gemischte Partien mit den fünf | 6 von 3.000 verlieren die wahre Welt bei 4 Nächten, 8 bei 6 Nächten. Keine wegen der fünf. |
| 5 | Website | Ein Brett mit Geist-Skript und Kammerzofe im Browser gelöst. |
| 6 | Korpus und Suite | 253 Bretter, 1.308 Tests grün (21 neue). |

**Messung:**

| Was | Ergebnis |
|---|---|
| Zwei eigene Skripte (eines wie Trouble Brewing, eines wie Bad Moon Rising mit Kammerzofe und Spion) | 0 von 12.000 Partien verlieren die wahre Welt. |
| Grundskripte | Prüfsummen von Trouble Brewing, Oster-Skript und Sects & Violets unverändert. Bad Moon Rising 0 von 6.000, Sects & Violets 62 von 6.000 wie vorher. |
| Gemischte Partien mit den fünf | 6 von 3.000: 3 Barbier-Klasse, 1 Mathematiker unter einem Vortox (Stelle 6), 1 Philosoph und ein Trunkenbold mit demselben Plättchen (Stelle 43), 1 Fang Gu springt in einen Schläger, den vorher in derselben Nacht ein Glücksspieler gewählt hat (Stelle 36). Bei 6 Nächten sind es 8, dieselben Klassen, davon 5 Barbier-Klasse. |
| Gemischte Partien ohne Pflicht-Charaktere | 11 von 3.000. Wieder andere Partien als bei Batch 2, weil der Vorrat um fünf gewachsen ist. |
| Korpus | 183 alte Bretter geben dieselbe Antwort. Die 60 Zufallsbretter sind neu gezogen, weil ihr Vorrat gewachsen ist. |

**Nebenbei gefunden und behoben:** Der Simulator weckte den Geist neben einem Bösen Zwilling in jeder Nacht. Der Böse Zwilling sieht seinen Zwilling aber nur in Nacht 1. Gefunden am Tor (Seed 1623), bevor etwas gemessen war.

### Die vierten vier experimentellen Charaktere · *erledigt am 10.10.2026*

Der volle Bericht steht in `claude/experimentelle-charaktere-batch-4.md`.

**Dein Auftrag vom 08.10.2026:** „Diese vier alleine, sag mir aber vorher deine Interpretation.“ Ich habe die Lesarten A bis M vorgelegt. Deine Antworten vom 10.10.2026: alles wie vorgeschlagen, mit zwei Klarstellungen. Der Angstmacher wird nur angesagt, wenn er wirklich einen **neuen** Spieler wählt. Ein Wesir, der an seinem ersten Tag vergiftet ist, hat keine Fähigkeit und wird **gar nicht** angesagt. Gebaut ist genau das, umbauen musste ich nichts.

| Charakter | Zeile auf der Website | Was der Solver daraus macht |
|---|---|---|
| Unschuld | „Damsel guess“ (Tag) | Nur der erste öffentliche Tipp eines Schergen zählt. Trifft er die lebende Unschuld und geht die Partie weiter, war sie gestört. Ein gestörter Scherge gewinnt trotzdem. Spion im Spiel, jetzt oder früher: Unschuld vergiftet (Jinx). |
| Angstmacher | „Fearmonger chose“ (Nacht) | Tatsache: ein lebender Angstmacher hat einen neuen Spieler gewählt, auch gestört. Fehlende Ansage sagt nichts. Das Spielende spielt nur der Simulator. |
| Wesir | „Vizier announced“ (Tag), mit Sitz | Tatsache: dieser Sitz ist an seinem ersten Tag der Wesir und arbeitet. Tagsüber kann er nicht sterben; gestört schon, außer ein Höfling hat ihn betrunken gemacht (Jinx). Wacht mit dem Angstmacher auf. |
| Drehorgelspieler | „Blind vote“ (Tag) | Tatsache: ein lebender, arbeitender Drehorgelspieler an diesem Tag. Ein Tag mit Stimmen hatte keinen arbeitenden. Selbst betrunken kostet nichts, der Mathematiker zählt es nicht. |

Daraus folgt auch: Das Blumenmädchen wird an einem blinden Tag nicht gewertet, weil keine Stimmen auf dem Brett stehen. Angstmacher und Drehorgelspieler wachen jede Nacht auf, die Kammerzofe zählt sie, und sie wecken den Geist.

**Das Tor:**

| Nr. | Schritt | Ergebnis |
|---|---|---|
| 1 | Solver in Python und JavaScript | 17 neue Bretter, beide stimmen überein. 1.488 gemischte Partien mit den vier kosten die wahre Welt in beiden gleich. |
| 2 | Simulator | Spielt alle vier. In 3.000 gemischten Partien: 1.702 Tipps auf die Unschuld, 1.921 Ansagen des Angstmachers, 639 des Wesirs, 1.443 blinde Tage. |
| 3 | Night-Walk | Kennt die Wahl des Angstmachers. Auf den eigenen Skripten 1 von 15.483 Nächten abweichend (offene Stelle 47). |
| 4 | Gemischte Partien mit den vier | 11 von 3.000 bei 4 Nächten, 9 bei 6 Nächten. Keine wegen der vier. |
| 5 | Website | Vier neue Zeilen, im Browser geprüft. |
| 6 | Korpus und Suite | 272 Bretter, 1.342 Tests grün (31 neue). |

**Messung:** Die zwei eigenen Skripte verlieren 0 von 12.000 Partien. Grundskripte unverändert (Prüfsummen gleich, Bad Moon Rising 0, Sects & Violets 62 von 6.000). Die 11 gemischten Partien: 4 Barbier-Klasse, 1 Stelle 43, 1 Stelle 41, 1 Stelle 6, und 4 in drei kleinen Klassen, die neu sind und nichts mit den vier zu tun haben (offene Stelle 48).

**Nebenbei gefunden und behoben:** Im Simulator wählte ein Angstmacher, den das Grubenweib in derselben Nacht vorher verwandelt hatte (Platz 16 vor 17). Der Night-Walk meldete einen Charakter als „nicht gesagt bekommen“, obwohl der Sitz in dieser Nacht vorher zu etwas anderem gemacht worden war. Ohne die vier weicht er jetzt in 15 statt 19 von gut 8.000 gemischten Nächten ab.

### Die fünften fünf experimentellen Charaktere · *erledigt am 10.10.2026*

Der volle Bericht steht in `claude/experimentelle-charaktere-batch-5.md`.

**Dein Auftrag vom 10.10.2026:** „such aus“. Ich habe Chorknabe, Prinzessin, Golem, Psychopath und Witwe mit den Lesarten A bis P vorgelegt. Deine Antworten: alles wie vorgeschlagen. Dazu zwei Hinweise: Ein Skript mit Chorknabe und ohne König ist falsch gebaut. Und wer bei der Hinrichtung Schere-Stein-Papier spielen muss, ist zu 100 % der Psychopath. Ein Tagestod durch den Yaggababble kommt erst, wenn dieser Dämon gebaut ist.

| Charakter | Zeile auf der Website | Was der Solver daraus macht |
|---|---|---|
| Chorknabe | „Choirboy“ (Nacht) | Nie ohne König. Starb in der Nacht ein König, ist der Gezeigte der Dämon oder ein Einsiedler. Arbeitet der Chorknabe, hat der Dämon den König getötet. Wacht nur in dieser Nacht. |
| Prinzessin | „Princess nominated“ (Tag) | Erster Tag als Prinzessin, Nominierter hingerichtet: In der Nacht danach tötet der Dämon niemanden, wenn sie lebt und arbeitet. Auch das alte Gift der Pukka tötet nicht. |
| Golem | „Golem nomination“ (Tag), mit „died“ | Tot: arbeitender Golem, erste Nominierung, kein Dämon. Überlebt: registriert als Dämon, konnte nicht sterben, oder der Golem war gestört. Einmal pro Spiel, auch gestört. |
| Psychopath | „Psychopath kill“ (Tag), mit „died“; „Roshambo at the execution“ (Tag) | Tot: lebender, arbeitender Psychopath. Schere-Stein-Papier heißt sicher Psychopath, arbeitend. Eine überlebte Hinrichtung kostet nichts. |
| Witwe | „Widow known“ (Nacht) | Wahr nur in ihrer ersten Nacht, wenn sie arbeitete. Ihr Gift darf auf jedem liegen, solange sie lebt, kostenlos. Vergiftet die Unschuld (Jinx). Die Kammerzofe zählt sie in der ersten Nacht. |

Daraus folgt auch: Vergiftet die Pukka oder nennt der Höfling die Witwe nach ihrem Zug in derselben Nacht, hatte sie trotzdem schon gewählt. Bei der Hinrichtung sind die Nachbarn der Teedame die, die dann noch leben.

**Das Tor:**

| Nr. | Schritt | Ergebnis |
|---|---|---|
| 1 | Solver in Python und JavaScript | 20 neue Bretter, beide stimmen überein. 1.490 gemischte Partien mit den fünf kosten die wahre Welt in beiden gleich. |
| 2 | Simulator | Spielt alle fünf. In 3.000 gemischten Partien: 202 Auskünfte des Chorknaben, 730 Nominierungen der Prinzessin, 345 des Golems, 762 Tötungen des Psychopathen, 348-mal Schere-Stein-Papier, 1.083 Hinweise der Witwe. |
| 3 | Night-Walk | Kennt die Wahl der Witwe und die Prinzessin. Auf den eigenen Skripten 0 von 16.899 Nächten abweichend. |
| 4 | Gemischte Partien mit den fünf | 1 von 3.000 bei 4 Nächten, 5 bei 6 Nächten. Keine wegen der fünf. |
| 5 | Website | Sechs neue Zeilen, im Browser geprüft. |
| 6 | Korpus und Suite | 292 Bretter, 1.380 Tests grün (38 neue). |

**Messung:** Die zwei eigenen Skripte verlieren 0 von 12.000 Partien. Grundskripte unverändert (Prüfsummen gleich, Bad Moon Rising 0, Sects & Violets 62 von 6.000). Gemischte Partien ohne Pflicht: 10 von 3.000, davon 6 Barbier-Klasse, 1 Stelle 6, 1 Stelle 48 c und 2 neue kleine Klassen (Stelle 48 e und f). Bei den fünf über 6 Nächte: 4 Barbier-Klasse und 1 neue kleine Klasse (Stelle 48 d).

**Nebenbei gefunden und behoben:** Im Simulator vergiftete ein vergifteter Giftmischer trotzdem und ein gestörtes Grubenweib verwandelte trotzdem. Unter einem Vortox wurde ein „Ja“ der Wahrsagerin auf einen Einsiedler zu einem wahren „Nein“. Im Solver galten bei der Hinrichtung die Nachbarn der Teedame vom Morgen, auch wenn einer davon am selben Tag schon gestorben war. Der Night-Walk bekam das Gift der Pukka aus der Vornacht zu spät gesagt, wenn ein Schlangenbeschwörer in derselben Nacht mit der Pukka tauschte.

### Die sechsten fünf experimentellen Charaktere · *erledigt am 10.10.2026*

Der volle Bericht steht in `claude/experimentelle-charaktere-batch-6.md`.

**Dein Auftrag vom 10.10.2026:** „weiter“. Ich habe Prediger, Jäger, Puzzlemeister, Xaan und Bombenleger mit den Lesarten A bis Q vorgelegt. Deine Antwort: alles wie vorgeschlagen, mit einer Korrektur zu O. In der Nacht des Xaan ist der Mathematiker selbst vergiftet und bekommt beliebige Informationen. Genau so ist es gebaut.

| Charakter | Zeile auf der Website | Was der Solver daraus macht |
|---|---|---|
| Prediger | „Preacher chose“ (Nacht) | Ein Scherge, den er arbeitend wählt, hat keine Fähigkeit, solange der Prediger lebt und arbeitet. Das ist Pflicht. Ein gepredigter Giftmischer oder eine gepredigte Witwe vergiftet niemanden. Ein gepredigter Wesir stirbt tagsüber trotzdem nicht (Jinx). Der Mathematiker zählt den Schergen. |
| Jäger | „Huntsman chose“ (Nacht), einmal | Er bringt die Unschuld statt eines Bürgers mit. Gewählt wird sie ein Bürger, der nicht im Spiel ist; welcher, liest der Solver aus ihrer Zeile „Became“. Bleibt sie die Unschuld, war der Jäger gestört. |
| Puzzlemeister | „Puzzlemaster guess“ (Tag) | Ein Spieler ist das ganze Spiel betrunken, kostenlos, auch ein Böser. Wird ihm der Dämon gezeigt, hat er den Betrunkenen erraten oder war selbst gestört. |
| Xaan | keine | Jede Zahl an Außenseitern ist erlaubt. In Nacht X (Zahl der ausgeteilten Außenseiter) sind alle Bürger vergiftet, auch der Mathematiker, wenn der Xaan lebt und arbeitet. |
| Bombenleger | „Boomdandy exploded“ (Tag) | Tatsache: der Hingerichtete ist der Bombenleger und arbeitet. Der Dämon stirbt nur durch das Zeigen, dann gewinnt Gut. |

Daraus folgt auch: „Jede Störung ruht, solange ihre Quelle gestört ist“ steckt für Prediger und Xaan jetzt im Plan, und wen die beiden stummschalten, der macht selbst niemanden betrunken oder vergiftet. Ein beendetes Spiel darf mit dem Tod des Dämons enden. Das hilft auch der Barbier-Klasse.

**Das Tor:**

| Nr. | Schritt | Ergebnis |
|---|---|---|
| 1 | Solver in Python und JavaScript | 17 neue Bretter, beide stimmen überein. 1.491 gemischte Partien mit den fünf kosten die wahre Welt in beiden gleich. |
| 2 | Simulator | Spielt alle fünf. In 3.000 gemischten Partien: 3.111 Wahlen des Predigers, 706 des Jägers, 412 Rateversuche des Puzzlemeisters, 267 Explosionen. |
| 3 | Night-Walk | Kennt Prediger und Jäger. Auf den eigenen Skripten 2 von 15.315 Nächten abweichend, beide bekannt (Stellen 46 und 47). |
| 4 | Gemischte Partien mit den fünf | 5 von 3.000 bei 4 Nächten, 9 bei 6 Nächten. Keine wegen der fünf. |
| 5 | Website | Vier neue Zeilen, im Browser geprüft. |
| 6 | Korpus und Suite | 311 Bretter, 1.409 Tests grün (29 neue), 2 übersprungen. |

**Messung:** Die zwei eigenen Skripte verlieren 0 von 12.000 Partien. Grundskripte: Prüfsummen gleich, Bad Moon Rising 0 von 6.000, Sects & Violets 43 statt 62 von 6.000, weil ein Spielende durch den Tod des Dämons jetzt erzählbar ist. Gemischte Partien ohne Pflicht: 5 von 3.000, davon 2 Barbier-Klasse, 1 Stelle 6 und 2 Stelle 48 e. Mit den fünf: 4 Barbier-Klasse und 1 Stelle 6 bei 4 Nächten. Bei 6 Nächten sind es 6 Barbier-Klasse, 2 Stelle 6 und 1 Stelle 48 e.

**Nebenbei gefunden und behoben:** Ein verlangter Charakter konnte auf einem gemischten Skript doppelt stehen; am Tor waren es zwei Xaan in einer Partie. Ein Jäger wachte im Simulator für die Kammerzofe nie auf. Ein Zombuul, den das Zeigen nach einer Explosion zum zweiten Mal traf, verlor im Simulator seinen ersten Tod. Die Website stürzte bei jedem Hinweis ab, dass ein Skript zu klein sei, und dieser Hinweis rechnete jede Wahl eines Charakters wie dem Xaan zusammen, statt die größte zu nehmen.

### Die siebten fünf experimentellen Charaktere · *erledigt am 11.10.2026*

Der volle Bericht steht in `claude/experimentelle-charaktere-batch-7.md`.

**Dein Auftrag vom 11.10.2026:** „Weiter“. Ich habe Feenkind, Dorftrottel, Werwolf, Harpyie und Lleech mit den Lesarten A bis V vorgelegt. Deine Antwort: alles wie vorgeschlagen, mit einer Korrektur zu J. Die falsche Pfote darf auch der Werwolf selbst sein. Genau so ist es gebaut.

| Charakter | Zeile auf der Website | Was der Solver daraus macht |
|---|---|---|
| Feenkind | „Pixie shown“ (Nacht 1) | Der gezeigte Bürger ist im Spiel oder ein Spion registriert als er, unter einem Vortox falsch. Ihn zu behaupten heißt, besessen von ihm zu sein, und kostet nichts. Stirbt sein Halter, während das Feenkind lebt, arbeitet und besessen von ihm ist, hat es die Fähigkeit ab der nächsten Nacht. Verweigert der Erzähler sie, kostet das 0,35. |
| Dorftrottel | „Village Idiot“ (Nacht) | Ein bis drei, zusätzliche ersetzen Bürger. Ab zwei ist einer das ganze Spiel betrunken, kostenlos. Gesinnung nach Registrieren. Der Mathematiker zählt den Betrunkenen. |
| Werwolf | „Lycanthrope chose“ (Nacht) | Ein guter Gewählter stirbt, und der Dämon tötet niemanden, auch das alte Gift der Pukka nicht. Kein Dämon-Kill: Mönch und Soldat schützen nicht. Ein guter Spieler, auch der Werwolf, registriert sicher als böse (falsche Pfote), solange der Werwolf lebt und arbeitet. |
| Harpyie | „Harpy madness“ (Tag) | Sagt der Besessene es, lebt eine Harpyie. Regel 24 des Cerenovus. Tagestode ohne Ursache, nie der Dämon. |
| Lleech | keine | Der Wirt ist vergiftet, solange der Lleech lebt, und das ruht, solange der Lleech gestört ist. Der Lleech stirbt nur mit dem Wirt, gestört erst, wenn er wieder arbeitet. Jinx mit Dämonenjäger und Strippenzieher gebaut. |

Daraus folgt auch: Wer die falsche Pfote ist und wer Wirt des Lleech, erzählt der Solver für jede mögliche Wahl einmal und behält die beste. Der Dorftrottel ist der erste Charakter, der mehrfach ausgeteilt wird.

**Das Tor:**

| Nr. | Schritt | Ergebnis |
|---|---|---|
| 1 | Solver in Python und JavaScript | 20 neue Bretter, beide stimmen überein. 1.488 gemischte Partien mit den fünf kosten die wahre Welt in beiden gleich. |
| 2 | Simulator | Spielt alle fünf. In 3.000 gemischten Partien: 5.386 Auskünfte der Dorftrottel, 1.217 des Feenkinds, 1.407 Wahlen des Werwolfs, 965 Wahn der Harpyie, 725 Lleeches. |
| 3 | Night-Walk | Kennt Werwolf, falsche Pfote, Harpyie und jeden Wirt. Auf den eigenen Skripten 3 von 15.526 Nächten abweichend, alle Stelle 47. |
| 4 | Gemischte Partien mit den fünf | 9 von 3.000 bei 4 Nächten, 8 bei 6 Nächten. Keine wegen der fünf. |
| 5 | Website | Vier neue Zeilen, im Browser geprüft. |
| 6 | Korpus und Suite | 331 Bretter, 1.449 Tests grün (40 neue), 2 übersprungen. |

**Messung:** Die zwei eigenen Skripte verlieren 0 von 12.000 Partien. Grundskripte: Prüfsummen gleich, Bad Moon Rising 0 von 6.000, Sects & Violets 37 von 6.000 wie auf dem Stand vor dem Batch. Gemischte Partien ohne Pflicht: 5 von 3.000, davon 2 Barbier-Klasse, 1 Stelle 41, 1 Stelle 42 und 1 Stelle 48 e. Mit den fünf: 6 Barbier-Klasse, 2 Stelle 6 und 1 Stelle 48 a bei 4 Nächten. Bei 6 Nächten 5 Barbier-Klasse, 2 Stelle 6 und 1 Stelle 48 a.

**Nebenbei gefunden und behoben:** Die Scharlachrote Frau übernahm nur am Tag; starb ein anderer Dämon als der Imp in der Nacht, gab es keine Erbin. Ein Philosoph mit dem Höfling machte nie jemanden betrunken, und Philosoph wie Höfling trafen von mehreren Haltern nur den ersten. Der Schuss des Dämonenjägers kannte in Python nur die Dämonen aus Trouble Brewing. Im Night-Walk endete die Trunkenheit durch Segler oder Gastwirt nicht, wenn der Giftmischer sie danach vergiftete, und ein Trunkenbold, den das Grubenweib verwandelt, wurde erst am Platz des Liebchens nüchtern. Im Simulator tötete der Schwätzer auch durch den Schutz des Gastwirts und des Seglers.

### Die achten fünf experimentellen Charaktere · *erledigt am 11.10.2026*

Der volle Bericht steht in `claude/experimentelle-charaktere-batch-8.md`.

**Dein Auftrag vom 11.10.2026:** Ich habe Kopfgeldjäger, Kultführer, Mezepheles, Leviathan und Yaggababble mit den Lesarten A bis Z vorgelegt. Deine Antwort: C Weg 2, I Weg 1, O Weg 2, S Weg 1, X Weg 1, dazu zwei Korrekturen. Zu F: Für den Kultführer zählt, wie ein Nachbar registriert, und ein Zombuul, der als tot gilt, ist kein Nachbar. Zu T: Weiß das Dorf vom Leviathan, richtet es vorsichtig hin. Genau so ist es gebaut.

| Charakter | Zeile auf der Website | Was der Solver daraus macht |
|---|---|---|
| Kopfgeldjäger | „Bounty Hunter“ (Nacht) | Der Gezeigte registriert als böse. Eine spätere Zeile gilt nur, wenn der zuvor Gezeigte gestorben ist, und nennt nie denselben Spieler. Mit einem ausgeteilten Kopfgeldjäger ist genau ein Bürger böse, auch der Kopfgeldjäger selbst darf es sein. |
| Kultführer | „Cult called“ (Tag) | Am Ende jeder Nacht nimmt er die Fraktion eines lebenden Nachbarn, so wie der registriert. Gestört oder tot behält er sie. Wo beides möglich ist, zählt er halb als böse. Wird der Kult gerufen und die Partie läuft weiter, ist einer gut, der nicht beitrat, oder der Kultführer war gestört. |
| Mezepheles | keine | Höchstens ein guter Spieler wird ab Nacht 2 böse, kostenlos. Der Mezepheles muss in dieser Nacht leben und arbeiten. Der Solver erzählt den Wechsel nur, wo eine Erzählung ohne ihn nicht aufgeht oder etwas kostet. |
| Leviathan | „Leviathan announced“ und „Nominated the executed“ (Tag) | Er tötet nie. Ohne Ansage war er an seinem ersten Tag gestört. Der zweite gute Hingerichtete und das Ende von Tag 5 beenden die Partie; läuft sie weiter, war er gestört. Jinxes mit König, Banshee, Farmer, Rabenhüter, Weise, Soldat, Gastwirt, Exorzist und Großmutter gebaut. |
| Yaggababble | keine | Ab Nacht 2 beliebig viele Tote je Nacht: der erste kostenlos, jeder weitere 0,5, stille Nächte kostenlos. Es sind Kills des Dämons. Wer beim Nominieren tot umfällt, kann ihr Opfer sein (0,25). |

Daraus folgt auch: Wer weiß, dass er böse geworden ist (der böse Bürger, der Gewechselte des Mezepheles), behält Charakter und Fähigkeit und darf lügen. Was er sagt und stimmt, gilt als gesagt, was nicht stimmt, kostet wie jede erfundene Auskunft. Ein Leviathan, der wegen seiner Jinxes jede Nacht wählt, kann den Schläger als Erster wählen und ist dann einen Tag betrunken.

**Das Tor:**

| Nr. | Schritt | Ergebnis |
|---|---|---|
| 1 | Solver in Python und JavaScript | 38 neue Bretter im Korpus, beide stimmen überein. Dazu 160 gespielte Bretter auf den eigenen Skripten außerhalb des Korpus verglichen, keine Abweichung wegen der fünf. *Berichtigt am 12.10.2026:* Die 63 gemischten Bretter, die ich hier zuerst mitgezählt hatte, enthielten keinen der fünf. Nachgeholt mit 96 gemischten Brettern, die alle fünf auf dem Skript haben: 95 gleich, eines geschätzt und deshalb nicht vergleichbar. |
| 2 | Simulator | Spielt alle fünf. In 3.000 gemischten Partien ausgeteilt: 1.222 Kopfgeldjäger, 1.266 Kultführer, 1.058 Mezepheles, 733 Leviathane, 708 Yaggababbles. |
| 3 | Night-Walk | Kennt den Wechsel des Mezepheles, die Toten der Yaggababble und die Wahl des Leviathans. Auf den eigenen Skripten 1 von 17.077 Nächten abweichend, nicht wegen der fünf (Stelle 51). |
| 4 | Gemischte Partien mit den fünf | 3 von 3.000 verlieren die wahre Welt, bei 4 und bei 6 Nächten. Keine wegen der fünf. |
| 5 | Website | Vier neue Zeilen, im Browser geprüft. |
| 6 | Korpus und Suite | 369 Bretter, 1.527 Tests grün (78 neue), 2 übersprungen. |

**Messung:** Die zwei eigenen Skripte verlieren 0 von 12.000 Partien. Grundskripte: Prüfsummen gleich, Bad Moon Rising 0 von 6.000, Sects & Violets 37 von 6.000 wie vorher. Gemischte Partien mit den fünf: 3 von 3.000 (Stellen 4, 36, 41). Ohne Pflicht: 5 von 3.000 (2 Barbier-Klasse, 2 Stelle 48 e, 1 Stelle 43).

**Nebenbei gefunden und behoben:** Eine Prinzessin, die das Grubenweib in derselben Nacht verwandelt, hielt den Dämon im Solver weiter auf. Im Night-Walk zählte bei einem Schläger, den das Grubenweib in derselben Nacht erschafft, das Grubenweib als erste Wahl. Im Simulator lasen Adlige, Gutsverwalter und Farmer die Fraktion aus dem Charakter statt vom Sitz. Auf der Website ließen sich Listen von Spielern nie eintragen; das betraf den Alsaahir. Und ein Absturz: Ein Barbier-Tausch zwischen einem hingerichteten Dämon und der Scharlachroten Frau, die ihn schon beerbt hat, teilte beim Verteilen der Anteile durch null. Das ging auf jedem Skript mit Barbier und Scharlachroter Frau, also auf keinem Grundskript.

**Bekannte Grenzen:** Der Jinx Leviathan–Mönch ist nicht gebaut, weil niemand aufschreibt, wen der Mönch schützt. Einen falschen Claim des bösen Bürgers findet der Solver nur an einem Sitz, der als nicht vertrauenswürdig markiert ist. Große Bretter auf Skripten mit Kopfgeldjäger und Mezepheles rechnen lange (Stelle 52). Lesart R hatte ich mit „Nacht 5“ vorgelegt; gebaut ist die Karte: Die Partie endet nach Tag 5, also darf es keine Nacht 6 geben.

### Geschwindigkeit mit Kopfgeldjäger und Mezepheles · *erledigt am 12.10.2026*

Der volle Bericht steht in `claude/geschwindigkeit-kopfgeldjaeger-mezepheles.md`.

**Deine Entscheidung vom 11.10.2026:** Weg 3, zuerst die Geschwindigkeit (offene Stelle 52).

**Gemessen:** Auf einem Brett mit 9 Spielern und 6 Nächten erklärte der Solver 645.000 Erzählungen für 55.000 Welten. Fast alle unterschieden sich nur darin, welcher Bürger böse ist oder wen der Mezepheles gedreht hat, und 87 % scheiterten an einer Nacht, die nichts erklärt.

**Geändert, ohne dass sich eine Antwort ändert:** Der Solver schreibt mit, nach wessen Fraktion er beim Erklären einer Erzählung gefragt hat. Unterscheidet sich eine zweite Erzählung nur in Sitzen, nach denen nie gefragt wurde, kostet sie dasselbe und wird nicht noch einmal erklärt. Ein Wechsel des Mezepheles wird gar nicht erst erzählt, wenn die Erzählung ohne ihn nicht aufgeht und nach dem Gedrehten ab dieser Nacht nie gefragt wurde. Nächte ohne Erklärung werden zuerst geprüft. Auf Skripten ohne die beiden läuft alles wie vorher.

| JavaScript, dieselben Bretter | vorher | jetzt | langsamstes Brett vorher | jetzt |
|---|---|---|---|---|
| 58 gespielte, eigenes Skript, 7 Spieler, 4 Nächte | 29 s | 19 s | 2,4 s | 2,7 s |
| 30 gespielte, eigenes Skript, 9 Spieler, 6 Nächte | 317 s | 100 s | 109 s | 30 s |
| 80 gemischte mit den fünf, 7 Spieler, 4 Nächte | 114 s | 89 s | 26 s | 22 s |
| 16 gemischte mit den fünf, 9 Spieler, 6 Nächte | 650 s | 353 s | 232 s | 99 s |
| 126 Bretter der Grundskripte | 83 s | 84 s | 5,8 s | 5,5 s |

**Geprüft:** 336 gespielte Bretter geben in Python und JavaScript dieselben Antworten wie vor der Änderung. Im Prüfmodus hat der Solver jede abgekürzte Erzählung trotzdem erklärt und verglichen: keine Abweichung auf 229 Brettern mit den fünf. Das Tor misst dasselbe wie vorher, 1.545 Tests grün (18 neue).

**Bleibt offen:** Große gemischte Bretter, auf denen Werwolf, Kopfgeldjäger und Mezepheles zusammenkommen, brauchen im Browser weiter ein bis zwei Minuten (Stelle 52).

### Die neunten drei experimentellen Charaktere · *erledigt am 12.10.2026*

Der volle Bericht steht in `claude/experimentelle-charaktere-batch-9.md`.

**Deine Antwort vom 12.10.2026:** A bis F jeweils Weg 1. Zu C: Die ganze Nachtreihenfolge gehen wir ganz am Ende gemeinsam durch (Punkt 1b).

| Charakter | Zeile auf der Website | Was der Solver daraus macht |
|---|---|---|
| Hohepriesterin | „High Priestess shown“ (Nacht) | Aufgezeichnet, nicht gewogen. Wacht jede Nacht auf, auch in der ersten; die Kammerzofe zählt sie. Nachtplatz von Hand: der des Generals (50 / 69). |
| General | „General told“ (Nacht): Gut, Böse oder keine | Aufgezeichnet, nicht gewogen. Wacht jede Nacht auf, auch in der ersten. |
| Fischer | „Fisherman advice“ (Tag) | Aufgezeichnet, nicht gewogen. Wacht nie auf. Ein zweiter Rat wird aufgezeichnet, die Seite weist darauf hin. |

**Das Tor:** Eigene Skripte 1 von 12.000 Partien verworfen (Stelle 43, nicht wegen der drei). Grundskripte unverändert: Prüfsummen gleich, Bad Moon Rising 0 von 6.000, Sects & Violets dieselben 43 von 6.000 wie vorher, Skripte von Batch 8 0 von 6.000. Gemischte Partien mit den drei: 9 von 3.000 (4 Nächte), 12 von 3.000 (6 Nächte), keine wegen der drei (12 Charakterwechsel in derselben Nacht, 1 neue Stelle 55, 1 Stelle 49). Ohne Pflicht 5 von 3.000 wie vorher. Website im Browser geprüft, Seite und Python zählen dieselben Welten. Korpus 386 Bretter (17 neue), 1.571 Tests grün (26 neue), 2 übersprungen.

**Gegen falsche Namen:** `tools/check_wording.py` prüft jeden Bericht vor dem Hochladen auf Namen, die nicht die der App sind (Trunkenbold statt „Säufer“, Kammerzofe statt „Zimmermädchen“, Grubenweib statt „Pit-Hag“ und weitere). Die Roadmap ist damit in 12 Zeilen berichtigt.

### Kultführer als Falsche Pfote (Stelle 55) · *erledigt am 12.10.2026*

Der volle Bericht steht in `claude/kultfuehrer-falsche-pfote.md`.

**Der Fehler:** Die Fraktion des Kultführers rechnet der Solver aus seinen Nachbarn. Dabei kehrte er zurück, bevor er fragte, ob der Kultführer die Falsche Pfote des Werwolfs ist. Ein guter Kultführer, der als Falsche Pfote böse registriert, war deshalb unmöglich, sobald ihn eine Fähigkeit als böse sah.

**Behoben in Python und JavaScript:** Erst die Fraktion aus den Nachbarn, dann wie bei jedem anderen guten Spieler die Falsche Pfote. Ein Kultführer als Falsche Pfote kostet jetzt genau so viel wie jeder andere gute Spieler als Falsche Pfote.

**Gemessen:** Die eine Partie vom Tor von Batch 9 (Seed 1238) behält ihre wahre Welt. Sonst ändert sich nichts: Prüfsummen gleich, eigene Skripte der Batches 7 bis 9 wie vorher, gemischte Partien mit Kultführer 12 von 3.000 und mit Werwolf 10 von 3.000, vor und nach der Änderung dieselben. Zwei neue Bretter im Korpus (388), kein altes geändert. 1.572 Tests grün.

### Stellen 56 und 57 · *untersucht am 12.10.2026, 57 behoben*

Der volle Bericht steht in `claude/stellen-56-und-57.md`.

**Stelle 57 behoben:** Eine Auskunft, die nur stimmt, weil die Falsche Pfote böse registriert, verlangte, dass der Werwolf arbeitet. Die andere Erklärung, dass die Auskunft falsch war und ihre Quelle gestört, prüfte der Solver nicht. Im Fund vergiftete ein Xaan in seiner Nacht den Werwolf und die Adlige zugleich. Jetzt wird je Nacht beides versucht, in Python und JavaScript. Die Partie (Seed 1177) behält ihre wahre Welt, sonst ändert sich nichts: Prüfsummen gleich, alle eigenen Skripte wie vorher, gemischte Partien mit Werwolf 10 von 3.000 (4 Nächte) und 15 von 3.000 (6 Nächte), dieselben wie vorher. 60 Bretter der Batches 7 und 8 geben in JavaScript dieselben Antworten in derselben Zeit. Korpus 390 Bretter (2 neue), 1.574 Tests grün.

**Stelle 56 ist größer als gedacht:** Nicht nur der Night-Walk, sondern auch Solver und Simulator geben einem Philosophen die genommene Fähigkeit meist nicht, wenn sie handelt statt zu lesen. Gebaut ist das nur für Schlangenbeschwörer, Glücksspieler, Nachtwächter, Banshee, Höfling und den Anspruch auf das Aufwachen. Gastwirt, Segler, Mönch, Teedame, Schwätzer, Bastler, Exorzist, Professor, Minnesänger, Mondkind, Pazifist und weitere schauen nur auf den, der das Plättchen hält. Simulator und Solver machen denselben Fehler, deshalb fiel er bei den Messungen nicht auf. In 3.000 gemischten Partien nimmt ein Philosoph 1.290-mal einen Charakter, 555-mal einen, der handelt. Das braucht deine Entscheidung (siehe Bericht).

### Philosoph mit genommener Fähigkeit, Schritt 1 · *erledigt am 13.10.2026*

Der volle Bericht steht in `claude/philosoph-schritt-1.md`.

**Deine Entscheidung vom 12.10.2026:** Stelle 56, Weg 1: Ein Philosoph hat jede genommene Fähigkeit, in zwei Schritten. **Deine Antworten vom 13.10.2026** zu Schritt 1 (Liebchen, Barbier, Tollpatsch, Mutant): A bis H jeweils Weg 1.

| Charakter | Was jetzt gilt |
|---|---|
| Liebchen | Ein Philosoph, der es genommen hat, macht beim Sterben ab dann einen Spieler betrunken. Das echte Liebchen, das er betrunken gemacht hat, löst beim Sterben nichts aus; stirbt es nach ihm, wieder. |
| Barbier | Ein eingetragener Philosoph-Barbier zählt wie ein Barbier-Anspruch, sein Tod erlaubt dem Dämon den Tausch. Der echte Barbier, betrunken durch ihn, löst nichts aus. |
| Tollpatsch | War im Solver schon gebaut. Der Simulator lässt ihn jetzt zeigen. |
| Mutant | Keine Änderung im Solver. Ein betrunkener echter Mutant versteckt sich weiter. |

**Das Tor:** Sects & Violets 17 von 3.000 Partien verworfen (vorher 19, keine neue) bei 4 Nächten, dieselben 24 bei 6 Nächten, Night-Walk 0 abweichend. Der Simulator spielt 123 von 3.000 Partien anders, die Prüfsumme von Sects & Violets ist deshalb neu (`1b9cc9c20f8cfedd`). Gemischte Partien mit Philosoph und den vier: dieselben verworfenen wie vorher. Korpus 400 Bretter (10 neue, kein altes geändert), 1.586 Tests grün.

### Philosoph mit genommener Fähigkeit, Schritt 2 · *erledigt am 14.10.2026 (Gruppen 1 bis 3 am 13.10., 4 bis 6 und I am 14.10.)*

**Deine Antworten vom 13.10.2026** zu Schritt 2: B bis M jeweils Weg 1. Bei I zeigt der Erzähler dem Philosophen ein Plättchen passend zur echten Fähigkeit: nimmt er die Verrückte, sieht er einen Dämon, nimmt er den Trunkenbold, einen Bürger. F (Einsiedler registriert auch tot) ist noch offen und kommt vor Gruppe 6. Gebaut wird Gruppe für Gruppe, jede durch das Tor (M).

**Gruppe 1, die Schützen:** Mönch, Soldat, Gastwirt, Segler, Teedame, Narr, Bürgermeister, Pazifist, Exorzist, Prinzessin. Ein Philosoph, der einen davon genommen hat, schützt wie der echte, in Solver (Python und JavaScript), Simulator und Night-Walk. Der echte, den er betrunken macht, schützt nicht. Wählen beide, werden beide Zeilen eingetragen, aber nur die Wahl des Philosophen wirkt (J).

**Am Tor gefunden und gleich behoben**, nicht wegen der Gruppe, aber durch sie sichtbar:

| Wo | Was |
|---|---|
| Simulator | Der Philosoph wählte in der ersten Nacht nach den frühen Wählern. Ein echter Höfling, den er betrunken gemacht hatte, machte trotzdem jemanden betrunken. Jetzt wählt er zuerst, wie am Tisch. Partien mit Philosoph laufen deshalb anders, die Prüfsumme von Sects & Violets ist neu. |
| Simulator | Was ein Gastwirt, Mönch, Exorzist oder Segler wählt, hängt wie bisher am Halter des Charakters am Ende der Nacht (ein Grubenweib kann den Wählenden danach verwandeln); nur die Wahl eines Philosophen hängt an ihm selbst. |
| Solver | Ein Philosoph, der beim Wählen betrunken war, hat nichts bekommen. Trotzdem durfte seine genommene Segler-Fähigkeit ihn selbst betrunken machen. Jetzt nicht mehr. |
| Solver | Ein toter Soldat, Segler, Narr oder Bürgermeister bot weiter kostenlos seinen Schutz an, obwohl Tote keine Fähigkeit haben. Jetzt bleibt nur „der Dämon traf einen Toten“, mit seinem Preis. |
| Solver | Erklärungen einer Nacht, die einen Sitz arbeitend brauchen, den eine unvermeidbare Quelle sicher stört (Minnesänger, Trunkenbold), fallen vor der Obergrenze von 400 Erklärungen heraus. Der Plan hätte sie ohnehin abgelehnt, aber sie nahmen die Plätze der richtigen weg (Seed 2413, 6 Nächte). Diese und die Zeile darüber ändern in 10 Brettern des Korpus die Prozente leicht, keine Zahl gültiger Welten. |
| Solver | Ein Trunkenbold mit dem Plättchen des Ritters, der etwas anderes behauptet, sagt, was er gezeigt bekam. Hatte ein Philosoph den Ritter genommen, wurde die Zeile dem Philosophen zugeschrieben, der dann in einer Nacht gestört sein musste, in der ihn nichts erreichen konnte. Jetzt gehört die Zeile dem, der sie sagt und sich für den Ritter hält (gemischte Partie 44 mit den ersten fünf). |

**Das Tor:**

| Was | vorher | nachher |
|---|---|---|
| Gemischt mit Philosoph und Gruppe 1, 3.000 Partien, 4 Nächte | 9 verworfen | dieselben 9. In 804 Partien nimmt ein Philosoph einen aus Gruppe 1 (327-mal neben dem echten), keine davon verworfen |
| dasselbe, 6 Nächte | 12 | 12: eine alte weniger (204), eine neue (1012, Barbier und Pukka; auch der alte Solver verwirft sie) |
| Night-Walk dort, 4 Nächte | 29 von 8.372 | 27 von 8.387. Zwei neue Nächte aus bekannten Klassen: Gift der Pukka aus der Vornacht (wie Stelle 47) und ein Giftmischer, der nach seiner Wahl betrunken wird (wie Stelle 49) |
| Gemischt ohne Pflicht | 5 | dieselben 5 |
| Sects & Violets, 3.000 Partien, 4 / 6 Nächte | 17 / 24 | 16 / 23. Die neuen Verworfenen sind Partien, die der Simulator jetzt anders spielt; der alte Solver verwirft sie auch (Barbier, Mathematiker) |
| Trouble Brewing, Bad Moon Rising | 0 | 0 |
| Batch 9, zweites Skript | 1 | 0 |
| Night-Walk TB, BMR, S&V (4 und 6 Nächte) | 0 | 0 |
| Night-Walk Batch 9, zweites Skript | 2 von 8.245 | 1 von 8.233 (Bastler gegen Mondkind, Stelle 51) |
| Prüfsummen | | TB und Oster-Skript gleich, S&V neu: `03f2299c74d793f5` |
| Gemischte Partien in der Testsammlung (600 je Liste) | | eine neue Verworfene, Seed 439: ein Barbier-Tausch, den niemand angesagt hat (bekannte Klasse, jetzt in der Liste) |
| Korpus | 400 Bretter | 418: 18 neue für Gruppe 1, ein gespieltes Brett ersetzt (`sv-played-981` heißt jetzt `sv-played-1143`, weil der Philosoph dort nicht mehr den Schlangenbeschwörer nimmt). Neue Seeds auch für `mixed-philosopher-gambler-dies` (735) und `sv-played-philosopher-klutz` (237). Python und JavaScript gleich |
| Testsammlung | 1.586 grün | 1.602 grün (16 neue Tests), 2 übersprungen |

**Gruppe 2, die Töter** · *erledigt am 13.10.2026:* Schwätzer, Bastler, Mondkind, Werwolf, Akrobatin. Ein Philosoph, der einen davon genommen hat, tötet wie der echte, in Solver (Python und JavaScript), Simulator und Night-Walk: nach einer wahren Aussage des Schwätzers stirbt jemand, als Bastler darf er jederzeit sterben, als Mondkind nimmt er beim Sterben jemanden mit, als Werwolf tötet er einen Guten (dann tötet der Dämon nicht) und hat eine Falsche Pfote, als Akrobatin stirbt er, wenn sein Gewählter gestört ist. Der echte, den er betrunken macht, tötet nicht.

Am Tor gefunden und behoben: Neben dem echten Werwolf zählte die Todes-Mechanik den Kill des Philosophen unter demselben Namen, also wie einen Werwolf, der zweimal tötet. Jetzt heißt er „Lycanthrope (Philosopher)“, ebenso beim Mondkind.

| Was | vorher | nachher |
|---|---|---|
| Gemischt mit Philosoph und Gruppe 2, 3.000 Partien, 4 / 6 Nächte | 8 / 8 verworfen | dieselben 8 / 8. In 410 Partien nimmt ein Philosoph einen aus Gruppe 2 (147-mal neben dem echten), keine davon verworfen |
| Night-Walk dort, 4 Nächte | 24 von 7.817 | 23 von 7.806. Eine neue Nacht aus Stelle 41 (Gastwirt schützt den springenden Fang Gu) |
| Gemischt ohne Pflicht | 5 | dieselben 5 |
| Bad Moon Rising, Batch 7 (beide Skripte), Batch 9 (zweites Skript) | 0 | 0, Night-Walk wie vorher |
| Prüfsummen | | TB, Oster-Skript und S&V gleich |
| Gemischte Partien in der Testsammlung | | eine neue Verworfene, Seed 204: ein Philosoph als Mondkind zeigt auf den Schlangenbeschwörer, der in derselben Nacht zum Dämon wird (Stelle 48 e) |
| Korpus | 418 | 434 (16 neue). Zwei alte Bretter geben andere Zahlen, weil ein Philosoph dort den Schwätzer genommen hat, der jetzt tötet (`mixed-undertaker-vortox` 3.297 → 3.519 Welten, `mixed-chambermaid-beside-a-philosopher` ist eine andere Partie) |
| Testsammlung | 1.602 grün | 1.611 grün |

**Gruppe 3, die Störer** · *erledigt am 13.10.2026:* Minnesänger, Prediger, Schläger, Puzzlemeister. Ein Philosoph, der einen davon genommen hat, stört wie der echte, in Solver (Python und JavaScript), Simulator und Night-Walk: als Minnesänger macht er nach der Hinrichtung eines Schergen alle anderen betrunken, als Prediger nimmt er gewählten Schergen die Fähigkeit, als Schläger macht er den Ersten betrunken, der ihn wählt, und wechselt dessen Fraktion (G), als Puzzlemeister hat er einen eigenen Betrunkenen. Der echte, den er betrunken macht, stört nicht.

Nebenbei im Simulator: Der Prediger handelt in Nacht 1 vor dem Philosophen. Hat der Philosoph ihn genommen, gilt die erste Predigt des echten Predigers jetzt nicht.

| Was | vorher | nachher |
|---|---|---|
| Gemischt mit Philosoph und Gruppe 3, 3.000 Partien, 4 / 6 Nächte | 5 / 7 verworfen | 4 / 6 (eine alte weniger, keine neue). In 296 Partien nimmt ein Philosoph einen aus Gruppe 3 (92-mal neben dem echten), keine davon verworfen |
| Night-Walk dort, 4 Nächte | 15 von 8.021 | 18 von 8.029. Die drei neuen Nächte sind Stelle 40: Ein Schlangenbeschwörer wählt den Philosophen mit dem Schläger, und der Simulator lässt den Schläger auf diese verdeckte Wahl nicht antworten |
| Gemischt ohne Pflicht | 5 | dieselben 5 |
| Bad Moon Rising, Batch 6 (beide Skripte), Batch 9 (zweites Skript) | 0 | 0, Night-Walk wie vorher |
| Prüfsummen | | gleich |
| Korpus | 434 | 458 (24 neue), kein altes Brett geändert |
| Testsammlung | 1.611 grün | 1.618 grün |

**Gruppe 4, Charakter und Fraktion** · *erledigt am 14.10.2026:* Farmer, Professor, Jäger, Feenkind, Kultführer, Oger. Ein Philosoph, der einen davon genommen hat, wirkt wie der echte, in Solver (Python und JavaScript), Simulator und Night-Walk. Als Farmer macht er bei seinem Tod in der Nacht einen Guten zum Farmer. Als Professor holt er einmal einen toten Bürger zurück. Als Jäger macht er die Unschuld zu einem Bürger, der nicht im Spiel ist. Als Feenkind erfährt er in der Nacht des Nehmens einen Bürger im Spiel (C). Als Oger wählt er in der Nacht des Nehmens und wechselt die Fraktion (G). Der Kultführer ging schon vorher und ist jetzt geprüft. Der echte, den er betrunken macht, wirkt nicht.

Am Tor gefunden und behoben:

| Wo | Was |
|---|---|
| Solver | Ein toter Philosoph mit der Fähigkeit des Professors, den der echte Professor zurückholt: Der echte war beim Wählen nüchtern, weil der Philosoph tot war, und ist erst ab dem Aufstehen wieder betrunken. Der Solver hielt ihn die ganze Nacht für betrunken und verwarf die Partie (Seed 2478 am Tor). Dieselbe Klasse machte das Korpus-Brett `x-nine-bmr-played-philosopher` unmöglich: jetzt 100 Welten statt 0. |
| Solver | Alle Auferstehungen zählten für einen einzigen Professor, „einmal im Spiel“ galt also für den echten und den Philosophen zusammen. Jetzt hat jeder sein eigenes Mal, in der Reihenfolge der Nächte, und ein neues nach der eigenen Auferstehung (neue Instanz, Regel vom 03.10.2026). |
| Solver | Wer von einem Professor zurückgeholt wird, schläft in dieser Nacht bei allen Charakteren vor dem Professor. Das galt nur für den echten Professor; beim Philosophen zählte die Kammerzofe den Zurückgeholten falsch (Batch 9, zweites Skript, Seed 881). |
| Simulator | Ein Philosoph, der das Feenkind nimmt, sagt jetzt den Bürger, den er erfährt (unter einem Vortox falsch). |

| Was | vorher | nachher |
|---|---|---|
| Gemischt mit Philosoph und Gruppe 4, 3.000 Partien, 4 / 6 Nächte | 12 / 14 verworfen | 8 / 11, vier alte weniger, keine neue. In 468 Partien nimmt ein Philosoph einen aus Gruppe 4 (154-mal neben dem echten), keine davon verworfen. Die eine Verworfene „wegen der neuen Zeilen“ (1523) hat keinen Philosophen: ein Jäger macht in Nacht 1 die Unschuld zum Feenkind |
| Night-Walk dort, 4 Nächte | 8 von 7.550 | dieselben 8 von 7.546 |
| Gemischt ohne Pflicht | 5 | dieselben 5 |
| Bad Moon Rising, Oster-Skript, Batch 6 und 7 (zweites Skript), Batch 8 (beide), Batch 9 (zweites Skript), je 3.000 Partien | 0 | 0, Night-Walk wie vorher. Batch 9 zeigte zuerst eine neue Verworfene (881), behoben, siehe oben |
| Sects & Violets, 3.000 Partien, 4 Nächte | 16 | dieselben 16 |
| Prüfsummen | | gleich |
| Korpus | 458 | 507 (49 neue, davon sechs gespielte Partien und die Partie 881 aus Batch 9). Ein altes Brett geändert: `x-nine-bmr-played-philosopher` 0 → 100 Welten (siehe oben). Python und JavaScript gleich |
| Testsammlung | 1.618 grün | 1.629 grün, 2 übersprungen |

**Gruppe 5, am Tag** · *erledigt am 14.10.2026:* Dämonenjäger, Jungfrau, Golem, Alsaahir, Eiferer, Butler. Was die Stadt am Tag sieht (ein Treffer, ein Nominierender, der stirbt, ein toter Nominierter des Golems, ein gewonnener Rateversuch), kommt jetzt auch von einem Philosophen, der den Charakter genommen hat, in Python und JavaScript. Der echte, den er betrunken macht, schafft es nicht. Ein Philosoph mit dem Eiferer muss abstimmen wie der echte. Der Butler ist für niemanden gebaut, auch nicht für den echten; für ihn gibt es nichts zu tun. Im Simulator nominiert ein Philosoph als Golem, rät als Alsaahir und stimmt als Eiferer ab.

**Unerwartet:** Der Simulator spielt Dämonenjäger und Jungfrau gar nicht, auch die echten nicht. Kein Schuss, keine Nominierung einer Jungfrau. Für diese zwei prüfen nur die Testbretter, nicht das Tor. Neue offene Stelle 59.

Am Tor gefunden und behoben:

| Wo | Was |
|---|---|
| Solver | Ein Treffer des Dämonenjägers legte das Ziel auf Imp oder Einsiedler fest, ein Wert aus Trouble Brewing. Ein Treffer auf einen anderen Dämon (Poe, Pukka, …) hatte über die Seite keine Welt. Jetzt jeder Dämon des Skripts oder der Einsiedler; neben einem Lleech wird nichts festgelegt, weil sein Wirt fallen kann. |
| Solver | Ein gewonnener Rateversuch des Alsaahir sollte eine Tatsache sein, wurde aber nie so gelesen: Kam er von einem Spieler, der kein Alsaahir sein konnte, kostete er nur 0,4. Jetzt fällt die Welt. JavaScript prüfte bei einem Sieg gar nicht, wer geraten hatte. Ein gespieltes Korpus-Brett mit Grubenweib und Alsaahir hat dadurch 12 statt 93 Welten. |

| Was | vorher | nachher |
|---|---|---|
| Gemischt mit Philosoph und Gruppe 5, 3.000 Partien, 4 / 6 Nächte | 5 / 6 verworfen | 4 / 5, eine alte weniger (873), keine neue. In 460 Partien nimmt ein Philosoph einen aus Gruppe 5 (137-mal neben dem echten), keine davon verworfen. Die eine „wegen der neuen Zeilen“ bei 6 Nächten (1947) ist auch vorher da: ein Golem, den der Schlangenbeschwörer aus dem Leviathan gemacht hat |
| Night-Walk dort, 4 Nächte | 5 von 7.543 | 4 von 7.520 |
| Trouble Brewing, Batch 2 (beide Skripte), Batch 5 (beide), 3.000 Partien | 0 | 0, Night-Walk gleich |
| Gemischt ohne Pflicht | 5 | dieselben 5 |
| Prüfsummen | | gleich |
| Korpus | 520 | 552 (32 neue, davon vier gespielte Partien), ein altes Brett geändert (siehe oben). Python und JavaScript gleich |
| Testsammlung | 1.644 grün | 1.654 grün, 2 übersprungen |

**Gruppe 6, Spielende und Registrieren, und I** · *erledigt am 14.10.2026.* Der Bericht zu ganz Schritt 2 steht in `claude/philosoph-schritt-2.md`. Deine Antworten vom 14.10.2026: F und N bis T jeweils Weg 1.

| Charakter | Was jetzt gilt |
|---|---|
| Heilige | Wird ein arbeitender Philosoph mit der Heiligen hingerichtet, verliert Gut (D). Läuft die Partie weiter, war er gestört. Der Simulator richtet ihn, wie die echte Heilige, nicht hin. |
| Einsiedler | Ein Philosoph mit dem Einsiedler kann für jede Auskunft wie der Einsiedler registrieren, auch tot (N, F). Gebaut als zweiter Blick: Hält eine Auskunft nicht, fragt der Solver sie noch einmal mit diesem Sitz als Einsiedler; dann war er nüchtern, oder die Quelle der Auskunft war gestört. Der Simulator lässt ihn nie falsch registrieren. |
| Unschuld | Rät ein Scherge auf den Philosophen mit der Unschuld, gewinnt Böse (O). Der Jäger macht ihn zu einem Bürger, der nicht im Spiel ist (P). |
| Großmutter | Er sieht in der Nacht des Nehmens einen Enkel und stirbt mit ihm, wenn der Dämon ihn tötet. |
| König, Chorknabe | Er erfährt als König einen lebenden Charakter wie der echte. Tötet der Dämon ihn, erfährt der Chorknabe den Dämon (Q). Was der Dämon über den König weiß, bildet der Solver nicht ab (R). |
| Ketzer, Politiker | Für niemanden gebaut, auch nicht für die echten. Nichts zu tun. |
| Trunkenbold (I, S) | Er sieht einen Bürger, der nicht im Spiel ist, wacht als dieser, bekommt erfundene Auskünfte und behauptet ihn. Die Suche nimmt für ihn den Philosophen als ausgeteilten Charakter. |
| Verrückte (I, T) | Er sieht den Dämon im Spiel, wacht wie dieser und wählt, ohne dass jemand stirbt. Eine Kammerzofe darf ihn wach gezählt haben. |

Am Tor gefunden und behoben: Der Night-Walk kannte nur eine Großmutter; ein Philosoph mit ihr starb dort nicht mit seinem Enkel.

| Was | vorher | nachher |
|---|---|---|
| Gemischt mit Philosoph, Heilige, Einsiedler, Unschuld, Großmutter, König, Chorknabe, 3.000 Partien, 4 / 6 Nächte | 4 / 4 verworfen | dieselben 4 / 4. In 452 Partien nimmt ein Philosoph einen davon (147-mal neben dem echten), keine davon verworfen |
| Gemischt mit Philosoph, Ketzer, Politiker, Trunkenbold, Verrückte, 4 / 6 Nächte | 3 / 3 | dieselben 3 / 3. In 312 Partien nimmt ein Philosoph einen davon |
| Night-Walk dort | 7 von 7.726 / 6 von 8.022 | 7 von 7.709 / 6 von 8.019 |
| Gemischt ohne Pflicht | 6 | dieselben 6 |
| Trouble Brewing, Bad Moon Rising, Oster-Skript, Sects & Violets, Batch 4, 5, 8, 9 | 0, S&V 16 | gleich, Night-Walk gleich |
| Prüfsummen | | gleich |
| Korpus | 564 | 627 (63 neue, davon neun gespielte Partien), kein altes Brett geändert. Python und JavaScript gleich |
| Testsammlung | 1.663 grün | 1.676 grün, 2 übersprungen |

### Stelle 59: Dämonenjäger und Jungfrau im Simulator · *erledigt am 14.10.2026*

Der Bericht steht in `claude/stelle-59-daemonenjaeger-jungfrau.md`.

**Deine Antwort vom 14.10.2026:** „ja baue 59“. Der Simulator spielt jetzt beide, die echten und einen Philosophen, der sie genommen hat:

| Charakter | Wie der Simulator ihn spielt |
|---|---|
| Dämonenjäger | Vor den Nominierungen schießt er an manchen Tagen (25 %), einmal pro Spiel, in einem Drittel der Fälle auf den Dämon, sonst auf irgendwen. Gestört schießt er, und nichts passiert. Ein arbeitender Einsiedler kann als Dämon registrieren (50 %). Trifft er den Dämon, übernimmt die Scharlachrote Frau bei fünf Lebenden, sonst hat Gut gewonnen. Auf einen Dämon, der davon nicht sterben würde (Zombuul, Lleech mit Wirt), schießt er nicht. |
| Jungfrau | Ihre erste Nominierung: Ist der Nominierende ein Bürger (oder der Spion), wird er sofort hingerichtet, und das ist die Hinrichtung des Tages. Gestört passiert nichts, die Fähigkeit ist trotzdem verbraucht. |
| Claims | Wer geschossen hat oder als Jungfrau ihren Nominierenden verloren hat, ist vor dem Dorf aufgedeckt und behauptet seinen Charakter. |

Am Tor gefunden und behoben:

| Wo | Was |
|---|---|
| Solver | Unter einem Vortox galten Schuss und Nominierung der Jungfrau als Auskunft und wurden umgedreht. Jetzt nicht mehr, aber sie werden weiter geprüft: Ein Fehlschuss auf den Dämon heißt, der Dämonenjäger war gestört. |
| Solver | Nach einer Übernahme durch die Scharlachrote Frau fragten Poe, Pukka, Shabaloth, Zombuul, Vortox, No Dashii und Vigormortis den toten alten Dämon, nicht den neuen. Ein Poe, den die Scharlachrote Frau erbte, tötete im Solver nie. Am Tisch genauso nach einer Hinrichtung. Jetzt gilt der Dämon, der ihn gerade hat. |
| Seite | Ein Treffer des Dämonenjägers legte das Ziel auf einen ausgeteilten Dämon fest. Hatte die Scharlachrote Frau übernommen oder ein Schlangenbeschwörer getauscht, gab es keine Welt. Das Ziel wird nicht mehr festgelegt; den Schützen und die Jungfrau legt die Seite nur noch fest, wenn auf dem Skript niemand Charaktere verändern kann. |
| Solver | Ein Philosoph mit dem Professor kann ihn ungesehen verbraucht haben, wie der echte. Die Kammerzofe neben ihm durfte das bisher nicht annehmen. |
| Solver | Ein Golem, der beim Nominieren durch die Yaggababble tot umfällt, hat keine Fähigkeit mehr. Sein Nominierter durfte trotzdem nicht überleben. |

**Das Tor** (3.000 Partien je Zeile):

| Was | vorher | nachher |
|---|---|---|
| Trouble Brewing, 4 / 6 Nächte | 0 / 0 verworfen, kein Schuss, keine Jungfrau | 0 / 0. 546 Schüsse, 219 Treffer, 131 Spiele enden durch einen Treffer; 574 Nominierungen der Jungfrau, 313 lösen aus |
| Oster-Skript | 0 | 0 (498 Schüsse, 578 Nominierungen) |
| Über die Seite, Trouble Brewing, 179 Partien mit Schuss oder Jungfrau | | 2 ohne Welt, beide mit einem guten Spieler, der grundlos lügt |
| Gemischt mit Philosoph, Dämonenjäger, Jungfrau, 4 / 6 Nächte | | 2 / 4 verworfen, alle aus bekannten Klassen (Barbier, Philosoph als Schlangenbeschwörer) oder Stelle 60. 33 Schüsse und 48 Nominierungen von Philosophen |
| Gemischt ohne Pflicht | 5 | 6: eine alte weniger, zwei neue mit Barbier (Stelle 4) |
| Gemischt mit Gruppe 5, 4 / 6 Nächte | 4 / 5 | 6 / 6. Die Partien laufen jetzt anders; die neuen sind Barbier (Stelle 4) oder Stelle 60 |
| Gemischt mit Gruppe 4 | 8 | dieselben 8 |
| Sects & Violets, Batch 4, 8, 9 (zweites Skript) | 16 / 0 / 0 / 0 | gleich |
| Night-Walk Trouble Brewing, Oster-Skript | 0 | 0 |
| Prüfsummen | | TB neu `6a929947cb5980b0`, Oster-Skript neu `c13863aafcc20af1`, S&V gleich |
| Korpus | 552 | 564 (12 neue). 13 gespielte Bretter auf Skripten mit Dämonenjäger oder Jungfrau sind jetzt andere Partien; 8 alte Bretter geben leicht andere Zahlen, meist ein paar Welten mehr, durch die Fehler oben. Python und JavaScript gleich |
| Testsammlung | 1.654 grün | 1.663 grün, 2 übersprungen. Drei alte Tests angepasst: das Ziel eines Treffers ist nicht mehr festgelegt, eine gemischte Partie hat einen neuen Seed (169 statt 140), und die Suche nach einer „sicher falschen“ Partie verlangt jetzt, dass die Wahrheit nichts kostet |

### Stelle 58: Wer einen Charakter bekommt, sagt es · *erledigt am 14.10.2026*

Der Bericht steht in `claude/stelle-58-farmer-erbe.md`.

**Deine Antworten vom 14.10.2026:** A, B, C, F Weg 1. D: Stirbt der Erbe in derselben Nacht, gibt es sofort einen neuen Erben; am nächsten Tag können zwei sagen, dass sie Farmer geworden sind, nur einer lebt. E: Der Spion kann es sagen oder nicht.

| | Was jetzt gilt |
|---|---|
| A | Der Erbe des Farmers sagt es immer, als Zeile „Claim changed“ (jetzt Farmer, vorher X), und behauptet danach den Farmer. |
| B | Die Suche liest die Zeile: Ein Spieler mit einer solchen Zeile wird als sein erstes „vorher“ gesucht, nicht als sein jetziger Claim. Das gilt für jede solche Zeile, also auch für Grubenweib, Barbier und die Unschuld, die der Jäger findet. Wer so einen Charakter bekommen hat, lügt nicht. Python und JavaScript. |
| C | „Wurde X“ erklärt der Solver mit einem Farmer, der in dieser Nacht starb, mit den Wegen, die es schon gab (Jinx mit dem Leviathan, Barbier, Jäger), oder neu mit einem Grubenweib, dessen Wahl niemand eingetragen hat: kostenlos, ab Nacht 2, das Grubenweib lebt, und nur für einen Charakter, der zu Beginn der Nacht nicht im Spiel war. |
| D | Ein Erbe, der in derselben Nacht stirbt, gibt den Farmer sofort weiter, in Simulator und Solver. Die Seite nimmt die Zeile „Claim changed“ auch von einem Spieler an, der in dieser Nacht starb. |
| E | Ein Spion, der Farmer wird, sagt es in der Hälfte der Partien (dann ohne „vorher“) und behauptet danach den Farmer; sonst behält er seine Tarnung. |
| F | Ein guter Spieler, den das Grubenweib verwandelt, sagt es mit derselben Zeile. Zwei solche Zeilen eines Spielers in einer Nacht werden eine. |

**Über die Seite gelöst** (7 Spieler, 4 Nächte, 3.000 Partien je Zeile):

| Partien | vorher ohne Welt | nachher |
|---|---|---|
| Batch 8, erstes Skript, 425 mit Farmer-Erben | 74 | 10 |
| gemischt mit Farmer, 312 mit Farmer-Erben | 50 und 2 Fehlermeldungen | 11 und 1 |
| gemischt mit Grubenweib, 197 mit einem guten Opfer | 15 und 1 | 7 und 1 |

Alle 10 übrigen auf Batch 8 haben einen guten Spieler, der grundlos einen anderen Charakter behauptet (Modell der Claims). Die Seite sucht solche Lügen nur, wenn man sie erlaubt. Die übrigen gemischten, die ich angesehen habe, sind dieselbe Klasse.

**Das Tor:**

| Was | vorher | nachher |
|---|---|---|
| Sects & Violets, 3.000 Partien | 16 verworfen | dieselben 16 |
| Batch 8, beide Skripte | 0 | 0 |
| Gemischt ohne Pflicht | 5 | dieselben 5 |
| Gemischt mit Grubenweib und Farmer | 14 | dieselben 14, Night-Walk gleich (11 von 7.998) |
| Night-Walk Sects & Violets, Batch 8 | 0 | 0 |
| Prüfsummen | | TB und Oster-Skript gleich, S&V neu (`2ecc6b64b260df86`), weil Opfer des Grubenweibs es jetzt sagen |
| Korpus | 507 | 520 (13 neue). Neun gespielte Bretter geben mehr Welten, weil dort jetzt die Zeile steht oder die Suche sie liest (Unschuld, die der Jäger findet; Jinx Leviathan–Farmer; Farmer-Erben). Python und JavaScript gleich |
| Testsammlung | 1.629 grün | 1.644 grün, 2 übersprungen |

### Stelle 60: Schlangenbeschwörer nach einer Übernahme, Savant am Tag eines Treffers · *erledigt am 19.10.2026*

Der Bericht steht in `claude/stelle-60.md`. **Deine Antwort zu (b) vom 19.10.2026:** Weg 2.

| | Was falsch war | Jetzt |
|---|---|---|
| (a) | Übernahm die Scharlachrote Frau am Tag und wählte sie später ein Schlangenbeschwörer, bot der Solver den Tausch nicht an. Er las die Partie in einem Durchgang, und darin kommt der Schlangenbeschwörer vor der Übernahme dran. | Ist der ausgeteilte Dämon vor dem Tausch gestorben, liest der Solver die Partie Nacht für Nacht. |
| (b) | Der Savant wurde am Ende des Tages geprüft, also nach Treffer und Übernahme. | Seine zwei Aussagen dürfen sich auf den Morgen oder den Abend beziehen. Das macht nur an Tagen einen Unterschied, an denen tagsüber ein neuer Dämon entsteht. Unter dem Vortox müssen beide zu einem dieser Zeitpunkte falsch sein. |
| (c) | Am Tor gefunden: Der Savant las die Fraktion eines Kultführers (auch eines Philosophen mit ihm) und eines Schlägers so, wie sie ausgeteilt war. | Wie alle anderen Auskünfte, auch unter dem Vortox. Die Falsche Pfote zählt für den Savant bewusst nicht; mit ihr verwarf das Tor mit Werwolf 18 statt 7 Partien, weil der Simulator dem Savant die echte Fraktion sagt. |

| Tor (3.000 Partien je Zeile) | vorher | nachher |
|---|---|---|
| Gemischt mit Schlangenbeschwörer, Scharlachroter Frau, Dämonenjäger, 4 / 6 Nächte | 13 / 15 | 7 / 9, die wegen neuer Zeilen alle mit Barbier (Stelle 4) |
| Gemischt mit Savant, Scharlachroter Frau, Dämonenjäger, 4 / 6 Nächte | 10 / 11 | 6 / 7, keine wegen neuer Zeilen |
| Gemischt mit Savant und Vortox / Kultführer und Philosoph / Werwolf und Schläger | 15 / 9 / 7 | 14 / 8 / 6 |
| Gemischt ohne Pflicht, Sects & Violets 4 / 6 Nächte | 6, 16 / 23 | gleich |
| Prüfsummen | | gleich |
| Korpus | 627 | 633 (6 gespielte Partien dieser Stelle). Ein altes Brett gibt mehr Welten (`mixed-gambler-right-before-a-swap`, 311 → 325), weil es jetzt Nacht für Nacht gelesen wird. Python und JavaScript gleich |
| Testsammlung | 1.676 grün | 1.684 grün, 2 übersprungen |

### Lord of Typhon, der erste große Charakter · *erledigt am 20.10.2026*

Der Bericht steht in `claude/lord-of-typhon.md`, die Lesarten in `claude/lord-of-typhon-lesarten.md`.

**Deine Antworten vom 19.10.2026:** A Weg 2, und der Einsiedler kann an jeder Stelle der Reihe als Scherge registrieren. B Weg 1. C Weg 1. D Weg 1, aber nicht ausschließlich.

| | Gebaut |
|---|---|
| Töten | Jede Nacht außer der ersten, wie ein gewöhnlicher Dämon, ohne Weitergabe. Nachtplatz vorerst der des Vortox. |
| Beutel | Ein Scherge mehr, Außenseiter zwischen vier weniger und vier mehr (wie beim Xaan). |
| Sitzregel | Alle Schergen und der Lord in einer lückenlosen Reihe, der Lord nicht an einem Ende. Ein Einsiedler darf an jeder Stelle mitstehen, mit Kopfgeldjäger auch ein Bürger. Nur beim Aufbau. Neues Feld `lines_up` im Katalog, geprüft in `worlds.seated_legally` und `worlds.mjs`. |
| Simulator | Teilt den Lord mit einem Schergen mehr aus, setzt die Bösen in eine Reihe (ein Einsiedler in einem Drittel der Partien darin), die Marionette neben den Lord. Seine Schergen behaupten in 70 % das gute Plättchen, das sie zuerst gesehen haben. |

| Tor (3.000 Partien je Zeile) | Partien mit Lord | verworfen | davon mit Lord |
|---|---|---|---|
| Lord of Typhon, 4 / 6 Nächte | 782 | 11 / 11 | 0 |
| mit Marionette und Einsiedler | 733 | 5 | 0 |
| mit Kopfgeldjäger | 773 | 10 | 0 |
| ohne Pflicht, Prüfsummen, feste Skripte | | gleich | |
| Über die Seite, 7 bis 9 Spieler | 175 | 0 durch den Lord; länger als 2 Minuten 8 % (mit No Dashii 5 %), Median 3 s (2 s) | |
| Korpus | | 633 → 638, kein altes Brett geändert | |
| Testsammlung | | 1.684 → 1.692 grün, 2 übersprungen | |

### Kazali, der zweite große Charakter, und Stelle 61 · *erledigt am 20.10.2026*

Der Bericht steht in `claude/kazali.md`, die Lesarten in `claude/kazali-lesarten.md`. **Deine Antworten vom 20.10.2026:** A bis D Weg 1, und „berichtige 61“.

| | Gebaut |
|---|---|
| Kazali | Tötet wie ein gewöhnlicher Dämon. Im Beutel die übliche Zahl Schergen und beliebig viele Außenseiter. Wacht in Nacht 1 als Erste auf (die Kammerzofe sieht es), sonst am Platz des Vortox. Der Simulator macht beliebige Spieler zu Schergen; sie behaupten in 70 % ihren alten Charakter. Die Jinxes mit Marionette und Kopfgeldjäger ergeben sich von selbst. |
| Stelle 61 | Stirbt ein Gastwirt oder Segler in der Nacht, in der er gewählt hat, ist sein Betrunkener am Tag nüchtern, im Simulator wie beim Schläger. Der Solver rechnete schon so. |

| Tor (3.000 Partien je Zeile) | verworfen | wegen der Kazali |
|---|---|---|
| Kazali, 4 / 6 Nächte | 11 / 9 | 0 |
| mit Kammerzofe und Marionette | 9 | 0; 2.530 Auskünfte der Kammerzofe wie im Night-Walk |
| mit Kopfgeldjäger | 7 | 0 (eine gehört zu Stelle 62) |
| Gastwirt, Psychopath, Segler | 13 → 13 | – |
| Ohne Pflicht, feste Skripte, Prüfsummen | gleich | – |
| Über die Seite, 7 bis 9 Spieler | 139 Partien, keine ohne Welt; länger als 2 Minuten 6 %, Median 4 s | |
| Korpus | 638 → 643, kein altes Brett geändert | |
| Testsammlung | 1.692 → 1.700 grün, 2 übersprungen | |

### Stellen 62 und 63 · *bearbeitet am 20.10.2026*

Der Bericht steht in `claude/stellen-62-63.md`.

| Stelle | Gebaut |
|---|---|
| 62 | Der Spieler, den der Kopfgeldjäger als böse gezeigt bekommt, wird als Falsche Pfote des Werwolfs probiert. Vorher nie, daher fand der Solver neben einem lügenden bösen Bürger keine Erklärung. |
| 63 | Unter dem Vortox gilt die Zahl des Mathematikers nur dann als sicher wahr, wenn keine andere möglich war. Vorher galt jede mögliche Zahl als wahr, und der Vortox oder der Mathematiker musste gestört sein. Die übrigen Fälle: zwei Barbier (Stelle 4), zwei offene Lesarten (J, K). |

| Tor (3.000 Partien je Zeile) | vorher (wegen der Zeilen) | nachher |
|---|---|---|
| Gastwirt, Psychopath, Segler | 13 (7) | 11 (5) |
| Kopfgeldjäger, Werwolf | 7 (2) | 5 (0) |
| Mathematiker, Vortox | 17 (5) | 13 (1) |
| Sects & Violets, 4 / 6 Nächte | 16 / 23 | 15 / 22 |
| Ohne Pflicht, Prüfsummen | | gleich |
| Korpus | 643 | 646 (3 neu; zwei alte mit etwas mehr Welten) |
| Testsammlung | 1.700 | 1.704 grün, 2 übersprungen |

**Deine Antworten vom 20.10.2026, gebaut im Simulator:** J Weg 3 (ein Fang Gu, der nicht sterben kann, springt nicht; der Außenseiter stirbt normal, der Sprung bleibt unverbraucht). K Weg 1, außer der neue Charakter ist eine Erste-Nacht-Rolle: dann erfährt er seine Information sofort (ein Feenkind aus der Unschuld in Nacht 1 sieht einen Bürger im Spiel; ein Philosoph wählt erst später).

| Tor (3.000 Partien je Zeile) | vorher (wegen der Zeilen) | nachher |
|---|---|---|
| Gastwirt, Psychopath, Segler | 11 (5) | 8 (2, beide Barbier) |
| Fang Gu, Gastwirt, Teedame, Mönch | 20 (15) | 5 (0) |
| Jäger, Unschuld, Feenkind | 12 (7) | 6 (1, Stelle 65) |
| Korpus | 646 | 649 |
| Testsammlung | 1.704 | 1.707 grün, 2 übersprungen |

### Al-Hadikhia, der dritte große Charakter · *erledigt am 21.10.2026*

Der Bericht steht in `claude/al-hadikhia.md`, die Lesarten in `claude/al-hadikhia-lesarten.md`. **Deine Antworten vom 21.10.2026:** A Weg 1, B ein Geschützter zählt als „Leben“ und bleibt, wenn die anderen sterben, C Weg 1, D Weg 2, E verbrauchte Rollen und schädliche Außenseiter wählen meistens Tod.

| | Gebaut |
|---|---|
| Al-Hadikhia | Eine Zeile pro Nacht mit den drei Gewählten. Im Solver ein eigener Tod: Einer der drei stirbt oder alle, außer einer war schon tot, war geschützt, oder sie selbst war betrunken oder vergiftet. Wer als Toter Leben wählt, kommt an ihrem Platz in der Nacht zurück (auch für die Kammerzofe). Im Simulator antworten die drei der Reihe nach; sterben alle drei, dann gleichzeitig. Jinxes mit Strippenzieher und Prinzessin gebaut, mit der Scharlachroten Frau nicht (im Simulator wählt sie sich nie selbst). |

| Tor (3.000 Partien je Zeile) | verworfen | wegen ihrer Zeilen |
|---|---|---|
| Al-Hadikhia, 4 / 6 Nächte | 13 / 10 | 0 (mit Al-Hadikhia nur Barbier) |
| mit Mönch, Gastwirt, Teedame, Schläger | 12 | 0; Stellen 66, 67 |
| mit Strippenzieher, Prinzessin, Scharlachroter Frau | 8 | 0; Stellen 66, 68 |
| mit Großmutter, Professor, Shabaloth | 6 | 0; Stelle 69 |
| ohne Pflicht, feste Skripte, Prüfsummen | gleich | – |
| Über die Seite, 7 bis 9 Spieler | 63 Partien, 0 ohne Welt durch die Al-Hadikhia (eine abgelehnt, weil ein Bastler in Nacht 1 stirbt, wie beim Lord of Typhon); länger als 2 Minuten 1, Median 1 s | |
| Korpus | 649 → 659, kein altes Brett geändert | |
| Testsammlung | 1.707 → 1.722 grün, 2 übersprungen | |

### Lil' Monsta, der vierte große Charakter · *erledigt am 21.10.2026*

Der Bericht steht in `claude/lil-monsta.md`, die Lesarten in `claude/lil-monsta-lesarten.md`. **Deine Antworten vom 21.10.2026:** A bis H Weg 1, I einverstanden.

| | Gebaut |
|---|---|
| Lil' Monsta | Kein Spieler ist der Dämon, dafür 1 Scherge mehr. Pro Nacht ein Babysitter, der als Dämon registriert, gesucht nur für Nächte, nach denen eine Information fragt (bis 64 Kombinationen alle, darüber Nacht für Nacht). Neue Zeile „hütet Lil' Monsta“. Ab Nacht 2 höchstens ein Toter, nie der Babysitter, als Tod durch den Dämon. Schlangenbeschwörer tauscht mit dem Babysitter der Nacht davor, Exorzist stoppt den Tod. Jinxes mit Scharlachroter Frau, Psychopath, Wesir, Magierin, Marionette gebaut; der Strippenzieher gibt einen Tag mehr, außer er hütet selbst. Nicht gebaut: Grubenweib erzeugt einen zweiten Dämon. |
| Nebenbei | Zwei Teedamen (der Philosoph nahm sie) neben einem Hingerichteten: Der Solver fragt jetzt beide, nicht nur die erste. Ein Babysitter gibt es nur in Geschichten, in denen jemand hütet, nicht wo das Grubenweib den Dämon zu etwas anderem machte. |

| Tor (3.000 Partien je Zeile) | verworfen | mit Lil' Monsta |
|---|---|---|
| Lil' Monsta, 4 / 6 Nächte | 10 / 9 | 0 / 1 (Stelle 36) |
| mit Schlangenbeschwörer, Exorzist, Kammerzofe | 11 | 1 (Stelle 36) |
| mit Scharlachroter Frau, Strippenzieher, Dämonenjäger | 9 | 1 (Barbier) |
| mit Magierin, Marionette, Psychopath, Wesir | 7 | 1 (Barbier) |
| mit Wahrsagerin, Uhrmacher, Blumenmädchen, Ritter | 9 | 2 (Barbier) |
| ohne Pflicht, feste Skripte, Prüfsummen | gleich | – |
| Über die Seite, 7 bis 9 Spieler | 65 Partien, 0 ohne Welt durch Lil' Monsta (eine braucht „gute Spieler dürfen lügen“); in Python 4 länger als 2 Minuten, Median 4 s; in JavaScript diese 4 geschätzt in 7 bis 15 s | |
| Korpus | 659 → 668, kein altes Brett geändert | |
| Testsammlung | 1.722 → 1.739 grün, 2 übersprungen | |

### Der Beschwörer, der fünfte große Charakter · *erledigt am 21.10.2026, berichtigt am 22.10.2026*

Der Bericht steht in `claude/beschwoerer.md`, die Lesarten in `claude/beschwoerer-lesarten.md`. **Deine Antworten vom 21.10.2026:** A bis E und G Weg 1; F: Der Uhrmacher zählt vom Beschwörer zum nächsten anderen Schergen, ohne einen erfährt er 0; H: Der Simulator macht einen bestätigten guten Spieler zum Dämon, sonst einen zufälligen guten; I einverstanden.

| | Gebaut |
|---|---|
| Beschwörer | Kein Dämon beim Aufbau, dafür ein Bürger mehr. Bis Nacht 3 gibt es keinen Dämon. Der Solver probiert in Nacht 3 (die Pukka auch in Nacht 2) jeden Spieler mit jedem Dämon des Skripts außer Lil' Monsta, Legion und Riot und behält jede Möglichkeit, die passt. Stirbt der Beschwörer vorher oder ist er in Nacht 3 gestört (nicht durch Höfling oder Prediger), kommt kein Dämon und Gut gewinnt dort. Jinxes mit Uhrmacher, Höfling, Prediger, Pukka, Zombuul, Marionette, Mohnzüchter und Lord of Typhon gebaut. |
| Marionette (22.10.2026) | Deine Korrektur: Sie wird erst festgelegt, wenn der Dämon kommt, als sein Nachbar, lebend oder tot. Bis dahin hält ihr Spieler wirklich seinen guten Charakter (Puzzlemeister, Kopfgeldjäger, Dorftrottel und roter Hering der Wahrsagerin zählen ihn so). Der Beschwörer wählt frei. Kommt kein Dämon, gibt es keine Marionette. Python, JavaScript und Simulator. |
| Stellen 70 und 71 (22.10.2026) | Erledigt nach deinen Antworten: Betrunken wird der Charakter, der Simulator macht es jetzt wie der Solver. Und ein gestörter Kultführer behält seine Gesinnung, ohne dass der Solver verlangt, dass er arbeitet (beim Dorftrottel und Kopfgeldjäger, die sie erfahren). |
| Nebenbei | Ein Lleech, den niemand ausgeteilt bekam, kann im Solver jetzt mit seinem Wirt sterben. Im Simulator mehrere Fehler behoben (Lleech-Wirt, der zurückgeholt wurde; Lord of Typhon mit Beschwörer; ein Mondkind und ein Glücksspieler-Opfer in der Nacht der Beschwörung). |

| Tor (3.000 Partien je Zeile) | verworfen | mit Beschwörer |
|---|---|---|
| Beschwörer, 4 / 6 Nächte | 8 / 11 | 2 / 2 (Stelle 48 e; seit 22.10. Stelle 72) |
| mit Schlangenbeschwörer, Exorzist, Kammerzofe | 6, am 22.10. 5 | 1 (Stelle 36) |
| mit Uhrmacher, Höfling, Prediger, Marionette, Mohnzüchter | 9, am 22.10. 7 | 3 (Stellen 70, 71), am 22.10. 1 (Barbier, Stelle 4) |
| mit Pukka, Zombuul, Lord of Typhon, No Dashii | 3 | 0 |
| mit Scharlachroter Frau, Strippenzieher, Dämonenjäger, Professor | 4 | 1 (Stelle 48 b) |
| ohne Pflicht, feste Skripte, Prüfsummen | gleich | – |
| Über die Seite, 7 bis 9 Spieler, 4 Nächte | 85 Partien, 0 ohne Welt durch den Beschwörer (eine braucht „gute Spieler dürfen lügen“); in Python 4 länger als 2 Minuten, Median 2 bis 3 s; in JavaScript drei davon 5 bis 16 s, eine 213 s, davon gut ein Viertel in den Welten mit Beschwörer | |
| Korpus | 668 → 677, am 22.10. 678, kein altes Brett geändert | |
| Testsammlung | 1.739 → 1.751, am 22.10. 1.754 grün, 2 übersprungen | |

### Als Nächstes

**1 · Deine Reihenfolge vom 15.10.2026:** erst Stelle 60 (erledigt am 19.10.2026), dann die großen Charaktere einzeln (Lord of Typhon und Kazali erledigt am 20.10.2026, Al-Hadikhia, Lil' Monsta und Beschwörer am 21.10.2026, Korrekturen zum Beschwörer am 22.10.2026; als Nächstes der Hutmacher, Reihenfolge siehe Stand des Katalogs), dann Ketzer und Politiker für die echten, danach die Nachtreihenfolge aller Charaktere.

**1a · Experimentelle Charaktere, einzeln und in Batches von fünf** (deine Entscheidung vom 05.10.2026, offene Stelle 14). Welche fünf in einen Batch kommen, entscheidest du.

Stand des Katalogs: 130 Einträge. Von den 138 Spielercharakteren der App sind 129 im Katalog (dazu der Wächter, ein Fabled), 9 fehlen: 4 Bürger, 3 Außenseiter, 2 Schergen. Davon sind 7 groß und 2 lassen sich gar nicht modellieren (Vergessliche, Zauberer). Mittlere und nur aufzeichenbare gibt es keine mehr. Erledigt: Lord of Typhon und Kazali (20.10.2026), Al-Hadikhia, Lil' Monsta und Beschwörer (21.10.2026). Deine Bemerkung vom 20.10.2026: Der Alchemist kommt erst, wenn alle Schergen gebaut sind. Die Reihenfolge, der du am 20.10.2026 zugestimmt hast, erst wer nichts leiht, dann wer leiht: Al-Hadikhia, Lil' Monsta, Beschwörer, Hutmacher, Ingenieur, Laborratte, Pestdoktor, Alchemist, Eremit, Kannibale. Der Zauberer (ein Scherge) lässt sich nicht modellieren. Sie kommen nur in ein zufälliges gemischtes Skript, wenn ein Lauf sie verlangt (`ONLY_WHEN_ASKED` in `tools/play_games.py`), damit alte Seeds ihre Partie behalten.

Ein Charakter gilt als fertig, wenn er durch das Tor ist: Solver in Python und JavaScript, Simulator, Night-Walk, vierzig gemischte Partien (`messung/tor.py`) ohne Brett, das wegen seiner Zeilen unmöglich wird, und eintragbar auf der Website.

**1b · Die Nachtreihenfolge erneuern, ganz am Ende und gemeinsam** (deine Entscheidung vom 12.10.2026; vorher zurückgestellt, Entscheidung E). Die Datei im Repo kennt 130 Charaktere, die aktuelle des Herausgebers 181. Von Hand eingetragen sind bisher die Plätze von Oger, Gutsverwalter, Ritter, Shugenja, Drehorgelspieler, Harpyie, Dorftrottel, Yaggababble und Hohepriesterin; die Hohepriesterin teilt sich vorläufig den Platz des Generals.

**2 · Zwei kleine Stellen in Sects & Violets,** die nebenher gehen:
- Wer früh in der Nacht handelt und in derselben Nacht vom Grubenweib verwandelt wird (offene Stelle 36).
- Der Simulator spielt die **Hinrichtung wegen Besessenheit** (Cerenovus) nicht.

**3 · Strenge Lesart für stille Nächte** (zurückgestellt): zwei Erklärungen für zwei Shabaloth-Kills, das Ziel der Pukka schützt sich nicht selbst. Im Versuch verlor sie 11 von 60.000 Partien, die der Solver hält.

**4 · Die Regeln an das Spiel zurückgeben.** Mehrere Funde (Teedame, Höfling, Glücksspieler, Vortox, Rückkehr mitten in der Nacht, Pukka eine Nacht später, Teedame neben dem Schläger, Gift auf einem Überlebenden, Höfling nennt den Schläger) betreffen auch das Regelwerk des Einzelspieler-Spiels. Das gehört in den anderen Chat.

### Offene Stellen

| Nr. | Bereich | Was offen ist |
|---|---|---|
| 1 | Bad Moon Rising | *Erledigt am 04.10.2026:* Gestörter Dämon als Erklärung für eine ruhige Nacht, jetzt auch bei Zombuul, Pukka und Shabaloth. Mit eingetragenen stillen Nächten gingen 83 von 60.000 Partien verloren, jetzt 0. |
| 2 | Bad Moon Rising | **„Jede Störung ruht, wenn ihre Quelle gestört ist“** (deine Entscheidung vom 02.10.2026). Abgebildet für Höfling und Philosoph (Tod, und Störung beim Wählen) und für die Pukka, seit dem 03.10. auch mit dem Kill, der dadurch später kommt. Nicht allgemein für eine Quelle, die erst später gestört wird. |
| 3 | Bad Moon Rising | **Poe und Meuchelmörder bleiben locker:** drei Tote in zwei Nächten hintereinander, und ein Meuchelmörder ohne eingetragene Zeile kann in mehreren Nächten zuschlagen (jeder Schlag kostet 0,25). |
| 4 | Sects & Violets | **Barbier-Tausch ohne gemeldeten Barbier** verliert die wahre Welt, in 40 von 6.000 Partien (4 Nächte, Stand 05.10.2026). Nach deiner Regel gewollt. |
| 5 | Sects & Violets | **Sitze, deren Rolle gewechselt hat,** werden nicht von ihrer ursprünglichen Rolle aus gesucht (halber Barbier-Tausch). 2 von 6.000 Partien. |
| 6 | Sects & Violets | **Mathematiker unter einem Vortox:** Seine Zahl wird als Bereich geprüft, deshalb bleibt hier die alte, lockere Regel. |
| 7 | Sects & Violets | **Barbier-Bretter brauchen im Browser etwa 20 Sekunden.** Die Seite friert dabei nicht mehr ein. |
| 8 | Echte Partien | **Ein Info-Claim, den alle kennen und der nie nachts stirbt,** deutet auf Trunkenbold, Marionette oder böse. Idee aus der ersten echten Partie, nicht gebaut. |
| 9 | Echte Partien | **Claims haben keinen Zeitpunkt.** Die Seite kennt einen Claim pro Sitz, der Rückblick sieht ihn schon am ersten Morgen. Ein Verlauf der Claims ist nicht gebaut. |
| 10 | Echte Partien | **Mehr Partien.** Eine ausgewertete Partie ist ein Anfang, belastbar wird es mit drei bis fünf weiteren. |
| 11 | Werkzeug | **Die alte lokale Python-App lehnt einen Tod in Nacht 1 ab,** die Seite nicht. Ein Bastler kann in Nacht 1 sterben. Der Night-Walk kennt den Fall auch nicht. |
| 12 | Werkzeug | **Exakte Zählung früher Bretter auf der Website.** Der Barbier-Multiplikator und der Aufbau der Zeitleisten sind die Hauptkosten. |
| 13 | Werkzeug | **NEXT.md** in eine kurze Roadmap und ein Archiv aufteilen. |
| 14 | Als Nächstes | **Experimentelle Charaktere,** einzeln und in Batches von fünf (deine Entscheidung vom 05.10.2026). Batch 1 ist am 05.10.2026 erledigt, Batch 2 am 07.10.2026, Batch 3 am 08.10.2026, Batch 4 bis 6 am 10.10.2026, Batch 7 und 8 am 11.10.2026. 17 offizielle Charaktere fehlen noch im Katalog. |
| 15 | Bad Moon Rising | *Erledigt am 03.10.2026:* Höfling nach einer Wiederbelebung. Deine Regel: Die Fähigkeit endet mit dem Tod, der Wiederbelebte ist eine neue Instanz. |
| 16 | Bad Moon Rising | **Kammerzofe und wer in derselben Nacht stirbt.** Simulator und Solver zählen einen Sitz als geweckt, auch wenn er vor seinem Platz in der Nacht getötet wurde (Professor an Platz 43, Dämon an 27). Beide machen es gleich, deshalb sieht es kein Messlauf. |
| 17 | Bad Moon Rising | *Erledigt am 03.10.2026:* Meuchelmörder, der seine Fähigkeit unsichtbar verbraucht. Gemessen und behoben. |
| 18 | Solver | **Der Plan der Störungen geht Nacht für Nacht vor** und nimmt bei Gleichstand die erste Lösung. Über mehrere Nächte gesehen kann eine andere besser sein. Das kostet Gewicht, keine Welten. |
| 19 | Simulator | **Der Mönch schützt in manchen Nächten zwei Spieler:** ein alter Münzwurf neben der eingetragenen Wahl. Ihn zu entfernen würde alle Trouble-Brewing-Partien neu austeilen, die Tests beim Namen nennen. Der Solver ist davon nicht betroffen. |
| 20 | Solver | **Der Solver rechnet in ganzen Nächten.** Das Pukka-Gift auf einem Überlebenden gilt bei ihm für die ganze Nacht und den Tag danach, am Tisch nur bis zum Zug der Pukka. Das hält zu viele Welten, verliert aber keine. |
| 21 | Simulator | **Ein Seitenwechsel des Schlägers gilt für die ganze Nacht,** nicht erst ab dem Platz, an dem er gewählt wurde. Simulator und Night-Walk machen es gleich. |
| 22 | Solver | **Grenze 400 für die Erzählungen der Nächte** bleibt eine Grenze (von dir bestätigt am 04.10.2026). Seit demselben Tag fallen Erzählungen, die das Brett ausschließt, vor dem Schnitt weg. In 60.000 Partien ging keine wahre Welt verloren, ausgeschlossen ist es bei sieben und mehr Nächten nicht. Sauber wäre, die Nächte einzeln statt als Produkt zu führen. **Erster gemessener Fall am 07.10.2026:** 1 von 3.000 Partien über 6 Nächte auf dem Skript „Second five, like Bad Moon Rising“ (Seed 2118). Mit einer Grenze von 2.000 hält der Solver sie. Seit dem Höfling vom 08.10.2026 ist es dort Seed 1073, weiter 1 von 3.000. |
| 23 | Solver | **Der Dämon-Typ wird aus stillen Nächten kaum erkannt.** Nach drei stillen Nächten ist es in 65 % ein Zombuul, der Solver sagt 38 %. Gemessen am 04.10.2026: Das zu ändern findet den Dämon nicht öfter. |
| 24 | Messung | **Nicht gemessen:** wie früh der Solver den Dämon findet (nur der Stand nach vier Nächten), und ob ein Dämon am Morgen vor seiner Hinrichtung vorn stand. Der Solver weiß nicht, dass eine Partie zu Ende ist. |
| 25 | Messung | **Kleine Tische:** Bei 7 und 8 Spielern sind nach vier Nächten fast alle Partien entschieden. Die frühere Auffälligkeit „9 Spieler“ bei Sects & Violets war ein Artefakt davon. |
| 26 | Simulator | *Erledigt am 04.10.2026:* Die Partie endet, wenn Böse gewonnen hat (zwei Lebende, Tag ohne Hinrichtung unter einem Vortox). |
| 27 | Messung | *Erledigt am 04.10.2026:* Stille Nächte und Tage ohne Hinrichtung sind in jedem Messlauf und Test mit gespielten Partien eingetragen. |
| 31 | Messung | **Die Dämon-Messung zeigt keinen Verlauf.** Sie wertet einen Morgen je Partie aus. Wie sich der Rang des Dämons von Morgen zu Morgen entwickelt, ist nicht gemessen. |
| 32 | Website | *Erledigt am 04.10.2026:* Schalter „the game is over“ unter Information. Ohne den Haken nimmt der Solver an, dass die Partie läuft. |
| 33 | Bad Moon Rising | **Bekannte Grenze:** Der Zombuul, der als tot gilt, steht bei drei oder mehr Lebenden auf dem Brett in 0 von 22 Partien vorn. Keine Regel fehlt. Stille Nächte zu bepreisen kostet mehr, als es findet (gemessen am 05.10.2026). Als Hilfe zeigt die Website seit dem 05.10.2026 den Kasten „Night pattern“. |
| 34 | Simulator | *Entschieden am 05.10.2026, bleibt so:* Das Dorf stimmt nicht ab wie ein Tisch (die meisten Stimmen reichen, auch eine einzige). Es richtet an 97 bis 99 % der Tage hin, und das passt zu deinem Tisch. |
| 28 | Simulator | **Das Dorf gewinnt im Simulator nie.** Es richtet den Dämon nur hin, wenn die Partie danach weitergeht (Scharlachrote Frau, Zombuul, Strippenzieher, Teufelsadvokat). Das ist Absicht, heißt aber: Alle gespielten Partien sind solche, in denen der Dämon überlebt. |
| 29 | Korpus | **`sv-played-1063` heißt „zwei Tausche hintereinander“ und enthält nur noch einen.** Der Seed ergab schon vor dem 04.10.2026 eine andere Partie als bei seiner Auswahl. Seed 183 hätte zwei. |
| 30 | Simulator gegen Night-Walk | *Erledigt am 05.10.2026:* Die 60 abweichenden Nächte in Sects & Violets waren zwei Lücken des Night-Walk, beide repariert. Jetzt 0 von 16.641. |
| 35 | Simulator | *Erledigt am 05.10.2026:* Die Reihenfolge der Nacht liest den aktuellen Charakter, nicht den ausgeteilten. |
| 36 | Sects & Violets | **Wer früh in der Nacht handelt und in derselben Nacht verwandelt wird:** Ein Schlangenbeschwörer wählt an Platz 11, das Grubenweib macht ihn an Platz 16 zu etwas anderem. Der Solver rechnet in ganzen Nächten und verwirft die Wahl. 1 von 6.000 Partien (Seed 1078, 4 Nächte). Gefunden am 05.10.2026, nicht gebaut. Am 08.10.2026 dieselbe Klasse in einer gemischten Partie: Ein Glücksspieler wählt den Schläger und wird betrunken, später in derselben Nacht springt ein Fang Gu in den Schläger. Der Solver sieht ab dem Sprung keinen Schläger mehr und hält den Glücksspieler für nüchtern, der Mathematiker zählt ihn aber (Tor, Seed 55). Am Tor von Batch 8 dieselbe Klasse dreimal: ein Schlangenbeschwörer tauscht, und der Barbier-Tausch folgt in derselben Nacht (Seed 1450, wahre Welt verloren); und im Night-Walk ein Mönch, der schützt und in derselben Nacht vom Grubenweib verwandelt wird (Seeds 1499 und 2295): Der Night-Walk hält den Schutz, der Simulator nicht. Am Tor von Lil' Monsta (21.10.2026) zweimal mit der Kammerzofe: Sie zählt im Simulator nach dem Charakter am Ende der Nacht und lässt einen Segler weg, den das Grubenweib danach zum Philosophen machte (Seed 73, 6 Nächte), und einen Schlangenbeschwörer, der mit einem guten Babysitter tauschte (Seed 2934). |
| 37 | Gemischte Skripte | *Erledigt am 07.10.2026:* Der Solver verlor in 3,2 % der gemischten Partien die wahre Welt (96 von 3.000), jetzt in 0,4 % (11 von 3.000). Der Rest steht in den Stellen 4, 6, 36, 41 und 42. |
| 38 | Solver | *Erledigt am 07.10.2026:* Vortox und Registrieren. Deine Entscheidung: Die Wirklichkeit zählt, auch bei der Adligen. Gebaut für Koch, Empath, Orakel, Schneiderin, Wahrsagerin, Jongleur, Großmutter und Adlige. |
| 39 | Werkzeug | **Die Nachtreihenfolge im Repo ist veraltet** (130 von 181 Charakteren). Für Gutsverwalter, Ritter und Shugenja sind die Plätze von Hand eingetragen. |
| 40 | Simulator | **Der Schläger antwortet nicht auf verdeckte Wahlen.** Giftmischer, Mönch, Hexe, Grubenweib und Schlangenbeschwörer wählen im Simulator, ohne dass der Schläger reagiert. Der Night-Walk macht es richtig, deshalb weichen 9 von 8.316 Nächten ab. Kommt nur auf gemischten Skripten vor. Sauber wäre, diese Wahlen in die Reihenfolge der Nacht einzuordnen. Das teilt alle Partien mit einem Giftmischer neu aus. |
| 41 | Regelfrage | **Ein Gastwirt schützt den Fang Gu, der in derselben Nacht in einen Außenseiter springt.** Im Simulator stirbt der alte Fang Gu trotzdem, der Solver hält ihn für geschützt. 2 von 3.000 gemischten Partien. Zu entscheiden ist, was am Tisch passiert. |
| 42 | Solver | **Eine Auskunft, die nur durch Registrieren stimmt, verlangt, dass der registrierende Sitz nicht gestört war.** Die andere Erklärung, dass die Quelle selbst gestört war, prüft der Solver dann nicht mehr. Gefunden an einem Totengräber, dem ein Spion als Soldat gezeigt wurde, in einer Nacht, in der ein Minnesänger alle betrunken gemacht hatte. 1 von 3.000 gemischten Partien. |
| 43 | Simulator | **Ein Philosoph nimmt einen Charakter, der echte Halter nennt seine Rolle nicht.** Dann rechnet der Solver die Auskunft des echten Halters dem Philosophen zu. 1 von 3.000 Partien in Sects & Violets (Seed 1698). Am 08.10.2026 dasselbe mit einem Trunkenbold, der glaubt, Träumer zu sein, und etwas anderes angibt: Seine Auskunft als Träumer wird dem Philosophen zugerechnet, der den Träumer genommen hat (Tor, Seed 2461). Am Tor von Batch 8 eine dritte Form: Ein Dorftrottel gibt einen anderen Charakter an und nennt trotzdem seine Auskunft. Bei zwei weiteren Dorftrottel-Claims rechnet der Solver sie dem ersten Dorftrottel zu, und zwei falsche Auskünfte brauchen dann zwei Störungen (gemischt, Seed 91). *Die Form mit dem Trunkenbold ist am 13.10.2026 behoben:* Hält niemand den Charakter, gehört die Zeile dem, der sie sagt und sich für ihn hält. |
| 44 | Night-Walk | **Akrobatin neben getauschten oder betrunkenen Sitzen:** Simulator und Night-Walk sind sich in etwa 12 von 8.316 Nächten nicht einig, ob das Ziel der Akrobatin gestört ist. Der Simulator vergiftet einen getauschten Dämon erst ab der nächsten Nacht, der Night-Walk sofort. |
| 45 | erledigt | **Ein Höfling nennt den Schläger.** Deine Entscheidung vom 08.10.2026: Weg 1, wie im Wiki. Das zählt als Wahl des Schlägers. Gebaut in Solver, Simulator und Night-Walk. Die Abweichung für das Einzelspieler-Spiel steht in `claude/handover-hoefling-schlaeger.md`. |
| 46 | Night-Walk | **Ein Segler wählt den Schläger zuerst, und der Gastwirt macht den Schläger in derselben Nacht betrunken.** Der Night-Walk bekommt den Schläger als von Anfang an betrunken gesagt und lässt ihn nicht antworten. 1 von 8.219 Nächten. |
| 47 | Night-Walk | **Gift der Pukka aus der Vornacht, und die Pukka wird in dieser Nacht vom Schläger betrunken.** Ein Glücksspieler, den die Pukka in der Nacht davor gewählt hat, ist an seinem frühen Platz noch vergiftet und überlebt einen falschen Tipp. Der Night-Walk weiß das nicht und lässt ihn sterben. 1 von 8.617 Nächten auf dem eigenen Skript aus Batch 3 (Seed 1571), nicht wegen der fünf. Auf dem Skript aus Batch 4 dasselbe einmal in 7.827 Nächten (Seed 2824). Auf dem zweiten Skript aus Batch 7 dreimal in 7.975 Nächten, dort trifft das Gift aus der Vornacht einen Gastwirt, einen Segler und einen Werwolf (Seeds 971, 1702, 1857). |
| 48 | Solver | **Drei kleine Klassen aus dem Tor von Batch 4, nicht wegen der vier.** (a) Ein Philosoph nimmt die Fähigkeit des Schlangenbeschwörers: 2 von 3.000 gemischten Partien (Seeds 535, 1393), noch nicht untersucht. (b) Ein vergifteter Höfling nennt einen Charakter, und der Mathematiker zählt dessen Trunkenheit vermutlich trotzdem mit: 1 Partie (Seed 1408). (c) Ein Farmer gibt seinen Charakter weiter, danach erschafft das Grubenweib einen Charakter, und der Solver hält die Erschaffung für unmöglich: 1 Partie (Seed 2009). (b) und (c) sind noch nicht im Einzelnen untersucht. Drei weitere aus dem Tor von Batch 5, nicht wegen der fünf: (d) ein Philosoph mit der Fähigkeit des Professors, der selbst hingerichtet und zurückgeholt wurde (Seed 2099, mit den fünf); (e) ein Mondkind, dessen Ziel in derselben Nacht durch einen Tausch mit dem Shabaloth zum Dämon wurde (Seed 2027); (f) ein Farmer gibt an einen Sitz weiter, der in derselben Nacht getauscht wurde (Seed 2264). Je 1 von 3.000 gemischten Partien, noch nicht untersucht. Am Tor von Batch 6 kam (e) dreimal vor, mit einem Schlangenbeschwörer, der mit dem Dämon tauscht, während das Mondkind auf ihn zeigt (Seeds 1312, 1638 und bei 6 Nächten 1769). Am Tor von Batch 8 kam (e) zweimal vor (Seeds 256 und 481, ohne Pflicht): Das Mondkind zeigt am Tag auf einen guten Spieler, der in der Nacht durch Tausch oder Sprung zum Dämon wird. Im Simulator stirbt er, weil er beim Zeigen gut war, und die Partie läuft ohne Dämon weiter. Der Solver und der Night-Walk lesen die Fraktion in der Nacht. Zu entscheiden wäre, welcher Moment zählt. |
| 49 | Night-Walk | **Ein Tausch mitten in der Nacht verschiebt Gift, und der Night-Walk merkt es erst am Platz des Liebchens.** Ein Philosoph mit der Fähigkeit des Schlangenbeschwörers tauscht an Platz 11 mit dem No Dashii, dessen Gift wandert mit. Der Night-Walk ändert die Störungen aus solchen Gründen erst an Platz 41, die Prinzessin galt beim Dämon an Platz 30 also noch als vergiftet. 1 von 8.246 Nächten im Tor von Batch 5 (Seed 879). Am Tor von Batch 7 dieselbe Klasse dreimal: ein Schlangenbeschwörer verschiebt das Gift des No Dashii (Seed 1801), ein Liebchen stirbt durch den Shabaloth und seine Trunkenheit trifft die Großmutter, die im selben Moment trauert (Seed 2031), und ein Mondkind tötet das Liebchen, dessen Trunkenheit es selbst trifft (Seed 1112, 6 Nächte). Zwei Fälle davon sind seither eng behoben: ein Tausch mit dem Lleech und ein Trunkenbold, den das Grubenweib verwandelt. |
| 50 | Simulator | **Der Mönch wählt vor dem Gastwirt.** Im Simulator schützt der Mönch vor allen frühen Wahlen, am Tisch handelt der Gastwirt (Platz 9) vor ihm (Platz 12). Macht der Gastwirt die Witwe betrunken, ruht ihr Gift auf dem Mönch schon, der Simulator lässt den Mönch aber vergiftet wählen. 3 von 8.246 Nächten im Tor von Batch 5 (Seed 2053). Das zu ändern teilt alle Partien mit einem Mönch neu aus, wie Stelle 19. Am Tor von Batch 6 dasselbe mit einer Witwe, die das Grubenweib in derselben Nacht erschafft (Platz 16 und 18): Ihr Gift auf dem Mönch zählt im Simulator schon an Platz 12. Am Tor von Batch 8: Der Simulator lässt den Giftmischer vor dem Segler handeln, der ihn gerade betrunken gemacht hat (Seed 2263), und schreibt die Wahl des Mönchs nicht auf, wenn der Dämon in dieser Nacht nicht handelt (Seed 1424, die Toten stimmen). |
| 51 | Simulator | **Der Bastler stirbt nach dem Mondkind.** Am Tisch handelt der Bastler an Platz 49, das Mondkind an Platz 50. Im Simulator ist es umgekehrt: Tötet das Mondkind den Gastwirt, der den Bastler schützt, stirbt der Bastler danach doch. 1 von 8.511 Nächten auf dem zweiten Skript aus Batch 8 (Seed 1361). Der Solver hält die Partie. |
| 52 | Solver | **Skripte mit Kopfgeldjäger und Mezepheles rechnen lange.** *Verbessert am 12.10.2026:* Erzählungen, die sich nur in ungefragten Sitzen unterscheiden, werden nicht mehr einzeln erklärt. Auf den eigenen Skripten ist JavaScript bei 9 Spielern und 6 Nächten dreimal so schnell (langsamstes Brett 109 → 30 Sekunden), auf gemischten knapp doppelt so schnell. Offen bleibt: Große gemischte Bretter, auf denen Werwolf (Falsche Pfote), Kopfgeldjäger und Mezepheles zusammenkommen, brauchen im Browser ein bis zwei Minuten (langsamstes 99 Sekunden), weil dort fast jede Erzählung nach fast jedem Sitz fragt. |
| 53 | Solver | **Die Barbier-Regel sieht eine Übergabe am Tag nicht.** Wo alle Regeln in einem Zug laufen, bietet sie „Dämon mit Scherge“ für einen schon hingerichteten Dämon und die Scharlachrote Frau an, die ihn beerbt hat. Der Absturz daraus ist am 11.10.2026 behoben, die Erzählung selbst bleibt und bekommt einen Anteil. Kein Grundskript hat Barbier und Scharlachrote Frau. |
| 55 | erledigt | **Kultführer als Falsche Pfote des Werwolfs.** *Behoben am 12.10.2026* in Python und JavaScript: Erst die Fraktion aus den Nachbarn, dann die Falsche Pfote wie bei jedem guten Spieler. War 1 von 3.000 gemischten Partien am Tor von Batch 9 (Seed 1238). |
| 56 | erledigt | **Ein Philosoph hat eine genommene Fähigkeit, die handelt, meist nicht.** *Erledigt am 14.10.2026* in zwei Schritten: Schritt 1 am 13.10.2026 (Liebchen, Barbier, Tollpatsch, Mutant), Schritt 2 in sechs Gruppen und I am 13. und 14.10.2026. Bericht `claude/philosoph-schritt-2.md`. |
| 57 | erledigt | **Werwolf, Xaan und Adlige.** *Behoben am 12.10.2026:* Eine Auskunft, die nur mit der Falschen Pfote stimmt, darf auch falsch gewesen sein, weil ihre Quelle gestört war; je Nacht werden beide Wege versucht. War 1 von 3.000 gemischten Partien mit Werwolf (Seed 1177). |
| 54 | Solver | **Der böse Bürger des Kopfgeldjägers mit falschem Claim** wird nur an einem Sitz gefunden, der als nicht vertrauenswürdig markiert ist. Sonst nimmt die Suche an, dass er seinen echten Charakter nennt. Der Jinx Leviathan–Mönch ist nicht gebaut, weil die Wahl des Mönchs nirgends steht. |
| 58 | erledigt | **Der Erbe des Farmers sagt nur „Farmer“.** *Behoben am 14.10.2026* (A bis F, siehe Abschnitt „Stelle 58“). Die Seite nimmt bei einem guten Spieler an, dass er seinen ausgeteilten Charakter nennt. War der alte Charakter des Erben wichtig (gemischte Partie 693 mit 7 Spielern: als Teedame hatte er am Vortag seinen Nachbarn vor der Hinrichtung bewahrt), findet sie keine Welt. Gilt genauso beim echten Farmer. Aufgefallen am 14.10.2026 bei Gruppe 4 des Philosophen, nicht gebaut. |
| 59 | erledigt | **Dämonenjäger und Jungfrau spielt der Simulator nicht.** *Gebaut am 14.10.2026*, siehe Abschnitt „Stelle 59“. |
| 60 | erledigt | **Schlangenbeschwörer nach einer Übernahme, Savant am Tag eines Treffers.** *Behoben am 19.10.2026*, siehe Abschnitt „Stelle 60“. Dabei gefunden und behoben: Der Savant las Kultführer und Schläger mit ihrer ausgeteilten Fraktion. |
| 61 | erledigt | **Der Gastwirt stirbt in der Nacht, seine Trunkenheit bleibt.** *Berichtigt am 20.10.2026*: Am Tag danach ist sein Betrunkener nüchtern, beim Segler genauso. |
| 62 | erledigt | **Kopfgeldjäger und Werwolf zusammen.** *Behoben am 20.10.2026*: Der Spieler des Kopfgeldjägers wird als Falsche Pfote probiert. |
| 63 | erledigt | **Gastwirt und Segler im Tor.** *Erledigt am 21.10.2026*: Mathematiker unter dem Vortox behoben, Lesarten J und K gebaut. Übrig nur Barbier (Stelle 4). |
| 64 | Solver | **Mathematiker neben einem Höfling, der den Philosophen nennt.** Der Solver zählt anders als der Simulator (gemischt mit Mathematiker und Vortox, Seed 2278). Nicht untersucht. |
| 65 | Solver | **Leviathan, Jäger und Unschuld.** Eine gemischte Partie (Pflicht Jäger, Unschuld, Feenkind, Seed 1988) scheitert schon ohne jede Zeile; die Unschuld wird erst Mathematiker, dann Narr. Nicht untersucht. |
| 66 | Simulator | **Xaan mit Segler oder Gastwirt.** Ein Segler oder Gastwirt, den der Xaan in seiner Nacht vergiftet, macht im Simulator trotzdem jemanden betrunken. Betrifft jeden Dämon (Tor der Al-Hadikhia, Seeds 243 und 584). |
| 67 | Solver | **Teedame neben einem, den die Al-Hadikhia kurz zurückholt.** Er kommt zurück, alle drei sterben, und für den Tisch ist nichts passiert; sein kurzes Leben hat aber den Schutz der Teedame gekippt (Seed 968). |
| 68 | Simulator | **Toter Scherge, den die Al-Hadikhia zurückholt** (Xaan, Witwe): Der Simulator lässt seine Wirkung schon ab Beginn der Nacht gelten (Seeds 1245, 446). |
| 69 | Solver | **Philosoph mit der Fähigkeit des Professors**, den die Al-Hadikhia zurückholt und der danach selbst jemanden zurückholt (Seed 1869). |
| 70 | erledigt | **Höfling und Charakterwechsel.** *Erledigt am 22.10.2026* nach deiner Antwort: Betrunken wird der Charakter, nicht der Spieler. Wird der Spieler ein anderer Charakter oder der Höfling selbst, ist er nüchtern. Der Solver hatte es schon so, der Simulator jetzt auch. |
| 71 | erledigt | **Gestörter Kultführer.** *Erledigt am 22.10.2026* nach deiner Antwort („dann passiert halt nichts“). Meine Beschreibung vom 21.10. war falsch: Ein Dorftrottel erfuhr die Gesinnung des Kultführers, und der Solver verlangte dafür, dass der Kultführer arbeitet. Jetzt verlangt er nichts mehr, beim Kopfgeldjäger genauso. |
| 72 | Solver | **Kultführer unter dem Vortox.** Unter dem Vortox muss die Zahl des Orakels falsch sein. Beim Prüfen „war sie wahr?“ nimmt der Solver nur die ausgeteilte Gesinnung des Kultführers, obwohl er offen lässt, ob dieser böse geworden ist. So verlangt er, dass der Vortox nicht arbeitet (gemischt mit Beschwörer, Seed 864). Gilt für jede Zahl-Auskunft, die Gesinnungen zählt. Nicht gebaut. |

**Berichtigt:** Die frühere Stelle 6 („der direkte Messlauf verwirft 20 von 1.500, der Lauf über das Brett nicht“) war falsch. Beide Wege verwerfen etwa gleich viel, und es ist die Barbier-Klasse aus Stelle 4. Die frühere Stelle 4 (Philosoph und Schlangenbeschwörer, Seeds 836 und 181) lässt sich nicht mehr nachstellen, weil der Simulator seither anders spielt. Im neuen Lauf über 3.000 Partien gibt es keine verworfene Partie ohne Barbier-Tausch.

---

## Was gestrichen ist

- **Night-Walk als Filter:** gemessen und abgeschlossen. 3.580 verworfene Geschichten, keine einzige Zahl bewegt, elfmal langsamer. Er bleibt als zweite unabhängige Umsetzung der Nacht.
- **Preacher, Nightwatchman, Poppy Grower** als nächste Charaktere: auf keinem deiner Skripte.
- **„43 Charaktere übrig":** falsch gezählt, siehe Befund 3.
