import {readFileSync} from "node:fs";
import {readBoard} from "../js/api.mjs";
import {explanationCost} from "../js/scoring.mjs";
import {World} from "../js/worlds.mjs";
const d = JSON.parse(readFileSync(process.argv[2], "utf8"));
const st = readBoard(d.payload).state;
let bad = 0;
for (const [roles, believes, c] of d.worlds) {
  const got = explanationCost(new World(roles, believes), st);
  const differ = (got === null) !== (c === null) ||
                 (got !== null && Math.abs(got - c) > 1e-9);
  if (differ) {
    if (bad < 6) console.log(JSON.stringify(roles), JSON.stringify(believes), "py", c, "js", got);
    bad++;
  }
}
console.log("abweichend", bad, "von", d.worlds.length);
