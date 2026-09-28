// Boot the built page the way a browser would, from docs/ rather than
// from the repository layout. A build that only works in the shape it
// was written in is not a build.
import {readFileSync, writeFileSync} from "node:fs";
import {dirname, join} from "node:path";
import {fileURLToPath} from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..", "..", "docs");
const html = readFileSync(join(ROOT, "index.html"), "utf8");
const body = html.match(/<script type="module">([\s\S]*)<\/script>/)[1];
// The built page stamps its entry point — `./api.mjs?v=<fingerprint>` —
// so a fresh upload cannot be shadowed by a cached module.
const patched = body.replace(/from "\.\/api\.mjs(\?v=[0-9a-f]+)?"/,
                             `from "${join(ROOT, "api.mjs")}"`);

const el = () => ({
  style: {setProperty(){}, removeProperty(){}}, dataset: {},
  classList: {add(){}, remove(){}, toggle(){}, contains(){return false;}},
  children: [], innerHTML: "", textContent: "", value: "", hidden: false,
  appendChild(c){ this.children.push(c); return c; },
  querySelectorAll(){ return []; }, querySelector(){ return null; },
  remove(){}, addEventListener(){}, setAttribute(){}, scrollIntoView(){},
  insertBefore(){}, focus(){}, clientWidth: 640,
  getBoundingClientRect(){ return {left:0, top:0, bottom:0,
                                   width:0, height:0}; },
});
globalThis.document = {createElement: el, createElementNS: el,
  createTextNode: () => el(), getElementById: () => el(),
  querySelector: () => el(), querySelectorAll: () => [],
  addEventListener(){}, body: el()};
globalThis.window = {innerWidth: 1200, addEventListener(){}};
globalThis.localStorage = {getItem: () => null, setItem(){}, removeItem(){}};
// Node has its own `navigator`, and it has no serviceWorker — which is
// exactly the case the page has to survive.

// Anything reaching for a server is a failure, so it is counted rather
// than quietly satisfied.
let fetched = 0;
globalThis.fetch = (...args) => {
  fetched += 1;
  return Promise.reject(new Error("no server: " + args[0]));
};

const scratch = join(HERE, ".site_body.mjs");
writeFileSync(scratch, patched);
await import(scratch);
await new Promise(done => setTimeout(done, 300));

const {solveBoard, guessworkFor} = await import(join(ROOT, "api.mjs"));
const claims = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
                "FortuneTeller", "Undertaker", "Recluse", "Saint"];
const players = claims.map(c => ({claim: c, events: []}));
const solved = solveBoard({n_players: 9, players, infos: []});
if (solved.error) throw new Error("solving failed: " + solved.error);
const guess = guessworkFor({n_players: 9, players, infos: []});
console.log(JSON.stringify({
  booted: true, fetched, valid: solved.valid, seats: solved.rows.length,
  guesswork: guess.rows.length,
}));
