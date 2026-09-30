// A saved real game, looked back on — the same review the page's "After
// the game" panel shows, for a file somebody sent.
//
//     node tools/review_game.mjs game.json
//     node tools/review_game.mjs game.json --json
//
// The file is what the page's "Save to a file" writes. It has to carry
// the truth — what each seat really was — which the page stores once
// "After the game" has been filled in. See js/review.mjs for what each
// morning is and how it is judged.

import {readFileSync} from "node:fs";
import {reviewGame} from "../js/api.mjs";

const [file, flag] = process.argv.slice(2);
if (!file) {
  console.error("usage: node tools/review_game.mjs game.json [--json]");
  process.exit(2);
}
const doc = JSON.parse(readFileSync(file, "utf8"));
if (doc.format !== "clocktower-solver-game" || !doc.game) {
  console.error("Das ist keine gespeicherte Partie der Seite.");
  process.exit(2);
}
const S = doc.game;
if (!Array.isArray(S.truth) || !S.truth.some(Boolean)) {
  console.error("In der Datei fehlt die Auflösung. Auf der Seite unter " +
                "„…“ → „After the game…“ eintragen und neu speichern.");
  process.exit(2);
}
const script = doc.script
  ? {name: doc.script.name, author: doc.script.author || "",
     characters: doc.script.characters}
  : S.script;
const payload = {
  n_players: S.n, allow_good_lies: false,
  players: S.players.slice(0, S.n), infos: S.infos || [],
  quiet_nights: S.quiet || [], days_done: S.done || [],
  script, fabled: S.fabled || [],
};
const got = reviewGame(payload, S.truth.slice(0, S.n));

if (flag === "--json") {
  console.log(JSON.stringify(got, null, 1));
  process.exit(0);
}
const name = i => (S.players[i] && S.players[i].name) || `Sitz ${i + 1}`;
console.log(`Skript: ${script.name} · ${S.n} Spieler · ` +
            `Dämon: ${got.demons.map(name).join(" und ") || "?"}`);
console.log("");
console.log("Morgen  Platz des Dämons      Dämon %  Hauptverdacht");
for (const n of got.nights) {
  if (n.error) { console.log(`${String(n.night).padEnd(8)}${n.error}`); continue; }
  const d = n.demon;
  const place = !d ? "—" : d.level ? `${d.rank} (gleichauf mit ${d.level})`
                                   : String(d.rank);
  const mark = n.found && d && !d.level ? "✓" : n.found ? "≈" : "✗";
  console.log(`${String(n.night).padEnd(8)}${place.padEnd(22)}` +
              `${(d ? d.pct.toFixed(0) + " %" : "—").padEnd(9)}` +
              `${name(n.topSeat)} (${n.topPct.toFixed(0)} %)  ${mark}`);
}
const clean = got.nights.filter(n => n.found && n.demon && !n.demon.level);
console.log("");
console.log(`Klarer Hauptverdacht an ${clean.length} von ` +
            `${got.nights.length} Morgen.`);
