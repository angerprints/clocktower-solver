// Drive the seat inspector the way a person would, and see what sticks.
//
// The checkboxes on a seat are wired in one place and read back in
// another, and nothing about the solver notices if only half of that
// happened: the box ticks, looks right, and forgets the moment another
// seat is chosen. So this clicks a seat, ticks the boxes, clicks away
// and back, and reports what survived — and what the ledger drew.
import {readFileSync, writeFileSync} from "node:fs";
import {dirname, join} from "node:path";
import {fileURLToPath} from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..", "..", "docs");
const html = readFileSync(join(ROOT, "index.html"), "utf8");
const body = html.match(/<script type="module">([\s\S]*)<\/script>/)[1];
// The built page stamps its entry point — `./api.mjs?v=<fingerprint>` —
// so a fresh upload cannot be shadowed by a cached module. Matching the
// bare path missed it, and the harness went looking for a file that does
// not exist beside it.
const patched = body.replace(/from "\.\/api\.mjs(\?v=[0-9a-f]+)?"/,
                             `from "${join(ROOT, "api.mjs")}"`);

const byId = {};
const nodes = [];
const el = (tag = "div") => {
  const n = {tag, className: "", textContent: "", innerHTML: "", value: "",
    type: "", checked: false, title: "", hidden: false, disabled: false,
    style: {setProperty(){}, removeProperty(){}}, dataset: {}, children: [],
    classList: {add(c){ n.className += " " + c; }, remove(){}, toggle(){},
                contains(){ return false; }},
    appendChild(c){ n.children.push(c); return c; },
    querySelectorAll(){ return []; }, querySelector(){ return null; },
    remove(){}, addEventListener(){}, setAttribute(){}, scrollIntoView(){},
    insertBefore(){}, focus(){}, clientWidth: 640,
    getBoundingClientRect(){ return {left:0, top:0, bottom:0,
                                     width:0, height:0}; }};
  nodes.push(n);
  return n;
};
const get = id => (byId[id] = byId[id] || el());
globalThis.document = {createElement: el, createElementNS: el,
  createTextNode: t => { const n = el("#text"); n.textContent = t; return n; },
  getElementById: get,
  querySelector: sel => sel.startsWith("#") ? get(sel.slice(1)) : el(),
  querySelectorAll: () => [], addEventListener(){}, body: el()};
globalThis.window = {innerWidth: 1200, addEventListener(){}};
const store = {};
globalThis.localStorage = {getItem: k => store[k] || null,
  setItem(k, v){ store[k] = v; }, removeItem(k){ delete store[k]; }};
globalThis.fetch = () => Promise.reject(new Error("no server"));

const scratch = join(HERE, ".inspector_body.mjs");
writeFileSync(scratch, patched);
await import(scratch);
await new Promise(done => setTimeout(done, 250));

const seats = () => nodes.filter(n => typeof n.onclick === "function"
                                   && (n.className || "").startsWith("seat"));
const choose = i => seats()[i].onclick({stopPropagation(){}});

const voted = get("f-voted"), nominated = get("f-nominated");
const wired = ["f-voted", "f-nominated", "f-suspect"]
  .filter(id => typeof get(id).onchange === "function");

// Tick both on the third seat.
choose(2);
voted.checked = true;
voted.onchange({target: voted});
nominated.checked = true;
nominated.onchange({target: nominated});

// Go somewhere else and come back — the symptom being checked.
choose(4);
const awayVoted = voted.checked;
choose(2);
const backVoted = voted.checked, backNominated = nominated.checked;

const saved = JSON.parse(store["botc-grimoire"] || "{}");
const kept = (saved.players || []).map((p, i) => ({
  seat: i + 1, voted: p.voted || [], nominated: p.nominated || [],
})).filter(x => x.voted.length || x.nominated.length);

const acts = nodes.filter(n => (n.className || "").trim() === "day-acts")
                  .map(n => n.textContent.trim());

console.log(JSON.stringify({
  wired, kept, awayVoted, backVoted, backNominated,
  ledger: acts[acts.length - 1] || null,
}));
