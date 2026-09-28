// Load the page's own script the way a browser would, with just enough
// DOM to get through boot, and check it works with no server running.
//
//     node tests/harness/page_boot.mjs
//
// Not a substitute for opening the page — a stub DOM proves nothing
// about layout. What it does prove is that the module loads, that every
// declaration is in place before anything reaches for it, and that a
// board can be solved on the device. All three were broken at some point
// during the cutover, and none of them would have shown up in a test of
// the solver.
import {readFileSync, writeFileSync} from "node:fs";
import {dirname, join} from "node:path";
import {fileURLToPath} from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const html = readFileSync(join(ROOT, "ui", "index.html"), "utf8");
const body = html.match(/<script type="module">([\s\S]*)<\/script>/)[1];

// The import specifier is relative to ui/, so rewrite it for this file.
const patched = body.replace('from "../js/api.mjs"',
                             `from "${join(ROOT, "js", "api.mjs")}"`);

const made = [];
const el = () => {
  const node = {
    style: {setProperty(){}, removeProperty(){}}, dataset: {}, classList: {
      add(){}, remove(){}, toggle(){}, contains(){ return false; }},
    children: [], innerHTML: "", textContent: "", value: "", hidden: false,
    appendChild(c){ this.children.push(c); return c; },
    querySelectorAll(){ return []; }, querySelector(){ return null; },
    remove(){}, addEventListener(){}, getBoundingClientRect(){
      return {left:0, top:0, bottom:0, width:0, height:0}; },
    setAttribute(){}, scrollIntoView(){}, insertBefore(){}, focus(){},
    clientWidth: 640,
  };
  made.push(node);
  return node;
};
globalThis.document = {
  createElement: el, createElementNS: el, createTextNode: () => el(),
  getElementById: () => el(), querySelector: () => el(),
  querySelectorAll: () => [], addEventListener(){}, body: el(),
};
globalThis.window = {innerWidth: 1200, addEventListener(){},
                     matchMedia: () => ({matches:false, addEventListener(){}})};
globalThis.localStorage = {getItem: () => null, setItem(){}, removeItem(){}};
globalThis.alert = m => console.log("alert:", m);
// Anything reaching for a server is a failure, so it is counted rather
// than quietly satisfied.
let fetchCalls = 0;
globalThis.fetch = (...args) => {
  fetchCalls += 1;
  return Promise.reject(new Error("no server: " + args[0]));
};

// Written to a real file rather than a data: URL, which cannot resolve
// an import of its own.
const scratch = join(ROOT, "tests", "harness", ".page_body.mjs");
writeFileSync(scratch, patched);
await import(scratch);
await new Promise(done => setTimeout(done, 300));   // let boot finish

// And the thing it is all for: a board answered on the device.
const {solveBoard} = await import(join(ROOT, "js", "api.mjs"));
const claims = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
                "FortuneTeller", "Undertaker", "Recluse", "Saint"];
const got = solveBoard({n_players: 9, infos: [],
                        players: claims.map(c => ({claim: c, events: []}))});
if (got.error) throw new Error("solving failed: " + got.error);
if (!got.valid) throw new Error("no worlds survived a plain board");
console.log(JSON.stringify({
  booted: true, valid: got.valid, seats: got.rows.length,
  fetched: fetchCalls,
}));

