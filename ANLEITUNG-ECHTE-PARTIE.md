# Phase 4 · Eine echte Partie mitschreiben und auswerten

**Wozu:** Bisher wurde der Solver nur an Partien gemessen, die ein Simulator aus diesem Projekt gespielt hat. Eine echte Runde am Tisch zeigt, ob das Werkzeug hilft. Das Ziel ist deins: **Wurde der richtige Spieler als Dämon erkannt?**

**Was du brauchst:** ein Handy, Tablet oder Laptop mit Browser, sonst nichts. Die Seite rechnet auf dem Gerät selbst.

---

## Vor dem Spiel

1. Öffne **https://angerprints.github.io/clocktower-solver/**. Hast du sie schon einmal offen gehabt, lade sie einmal neu, damit du die neueste Version hast.
2. Tippe oben auf den Skriptnamen und wähle unter **Published** euer Skript. Bei einem eigenen Skript nimmst du **Or open a script file** mit der Skript-Datei aus der offiziellen App.
3. Stelle oben bei **Players** die Spielerzahl ein.
4. Tippe nacheinander auf jeden Sitz und trage unter **Name** den Namen ein, in der Reihenfolge, in der ihr sitzt.
5. **Deinen eigenen Sitz** antippen, deinen Charakter als **Claimed role** eintragen und darunter **This seat is me** wählen. Dein eigenes Token ist das Sicherste, was du weißt. In der ersten ausgewerteten Partie hat genau das den Dämon von Platz 2 auf Platz 1 gebracht.
6. Stand von einer alten Runde auf dem Gerät? Dann erst **…** → **Clear game**.

## Während des Spiels

Es reicht, **jeden Morgen** nachzutragen, was passiert ist. Wichtig ist nur, dass jede Eintragung bei der **richtigen Nacht bzw. dem richtigen Tag** steht, denn der Rückblick rechnet später jeden Morgen einzeln nach.

1. **Claims:** Sobald jemand sagt, wer er ist, den Sitz antippen und **Claimed role** setzen. Sagt jemand nur, wann er aufwacht, kommt das unter **What they said about waking**.
2. **Tode:** Den Sitz antippen und unter **What happened** wählen, zum Beispiel „Died night 2“ oder „Executed today, died“.
3. **Informationen:** Links bei **Information** unter **Add** die Art wählen, etwa „Empath“ oder „Fortune Teller“. Dann bei der passenden Nacht auf **+** tippen und ausfüllen, wer es gesagt hat und was.
4. **Stimmen:** Wer abgestimmt oder nominiert hat, am Sitz bei **Voted today** bzw. **Nominated today** abhaken. Das brauchen Flowergirl und Town Crier.
5. **Barbier:** Stirbt jemand, der Barbier behauptet hat, ist das wichtig. Der Solver rechnet einen Tausch nur, wenn der Barbier-Claim eingetragen ist. Hat sich ein Barbier nie gemeldet, ist das nach eurer Tischregel Sache des Dorfs.
6. **Rolle gewechselt:** Sagt jemand, er sei jetzt eine andere Figur (Pit-Hag, Barbier, Farmer …), trägst du das als Zeile **Became** ein.
7. **Solve** drücken darf man jederzeit, auch mitten im Spiel. Für die spätere Auswertung ist es nicht nötig. Die Seite friert dabei nicht mehr ein, und mit **Stop** bricht man ab.

**Die Partie wird laufend auf dem Gerät gespeichert.** Schließt du den Browser aus Versehen, ist beim nächsten Öffnen alles noch da.

## Nach dem Spiel

1. Sobald das Grimoire aufgedeckt ist: **…** → **After the game…**
2. Für jeden Sitz steht dort schon seine behauptete Rolle. **Nur die korrigieren, die gelogen haben oder betrunken waren.** Auf jeden Fall muss der Dämon stimmen. Gab es einen Starpass, beide Dämon-Sitze eintragen.
3. **Look back** drücken. Die Seite rechnet jeden Morgen der Partie neu, genau mit dem Wissen, das der Tisch damals hatte. Sie zeigt pro Morgen:
   - **Demon's place:** auf welchem Platz der echte Dämon stand, und ob er ihn sich mit anderen geteilt hat,
   - **Demon %:** wie sicher sich das Werkzeug war,
   - **Top suspect:** wen es für den wahrscheinlichsten Dämon hielt,
   - ✓ klarer Hauptverdacht · ≈ vorne, aber gleichauf mit anderen · ✗ jemand anderes lag vorn.
4. **…** → **Save to a file** speichert die Partie mitsamt Auflösung als Datei.
5. **Die Datei hier im Chat anhängen.** Ich werte sie mit demselben Rückblick aus und gehe die Morgen durch, an denen der Dämon nicht vorn lag: War es ein Fehler des Solvers, eine fehlende Eintragung oder einfach eine Partie, die der Tisch nicht lösen konnte?

## Gut zu wissen

- **Eine Partie ist ein Anfang.** Mehrere Partien sagen deutlich mehr. Jede Datei hilft.
- **Nicht alles eintragen zu können ist in Ordnung.** Lieber weniger, aber jede Eintragung bei der richtigen Nacht.
- **Wo steht was:** Die Auswertung liegt auf der Seite und in `tools/review_game.mjs`, die Logik dahinter in `js/review.mjs`.
