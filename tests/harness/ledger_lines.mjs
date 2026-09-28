// Render the ledger for a game with something happening on most nights
// and days, and print the lines that frame each one. The page is asked
// what it draws rather than trusted to draw it.
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

const nodes = [];
const el = (tag="div") => {
  const n = {tag, className:"", textContent:"", innerHTML:"", value:"",
    type:"", checked:false, title:"", hidden:false,
    style:{setProperty(){},removeProperty(){}}, dataset:{}, children:[],
    classList:{add(c){n.className+=" "+c;}, remove(){}, toggle(){},
               contains(){return false;}},
    appendChild(c){ n.children.push(c); return c; },
    querySelectorAll(){return [];}, querySelector(){return null;},
    remove(){}, addEventListener(){}, setAttribute(){}, scrollIntoView(){},
    insertBefore(){}, focus(){}, clientWidth:640,
    getBoundingClientRect(){return {left:0,top:0,bottom:0,width:0,height:0};}};
  nodes.push(n); return n;
};
const rowsBox = el();
globalThis.document = {createElement:el, createElementNS:el,
  createTextNode:t=>{const n=el("#text"); n.textContent=t; return n;},
  getElementById:id=>id==="rows"?rowsBox:el(),
  querySelector:sel=>sel==="#rows"?rowsBox:el(),
  querySelectorAll:()=>[], addEventListener(){}, body:el()};
globalThis.window = {innerWidth:1200, addEventListener(){}};
const store = {};
globalThis.localStorage = {getItem:k=>store[k]||null,
                           setItem(k,v){store[k]=v;}, removeItem(k){delete store[k];}};
globalThis.fetch = () => Promise.reject(new Error("no server"));

// A game with something happening on most nights and days.
store["botc-grimoire"] = JSON.stringify({
  n: 9, done: [1, 3],
  players: ["Washerwoman","Librarian","Investigator","Chef","Empath",
            "FortuneTeller","Undertaker","Recluse","Professor"]
    .map((claim, i) => ({name: ["Anna","Ben","Cara","Dan","Eve","Finn",
                                "Gita","Hugo","Ines"][i],
      claim, events: i===2 ? ["N2","R4"] : i===4 ? ["X2"] : i===6 ? ["N3"] : [],
      certainty:"", read:0, wake:""})),
  infos: [], quiet: [], history: [], fabled: [], notes: {},
});

const scratch = join(HERE, ".ledger_body.mjs");
writeFileSync(scratch, patched);
await import(scratch);
await new Promise(d => setTimeout(d, 300));

const text = n => n.textContent ||
  n.children.map(c => c.textContent ||
    (c.children||[]).map(g=>g.textContent).join("")).join(" ");
const lines = [];
for (const n of nodes) {
  const kind = (n.className || "").trim();
  if (kind === "night-open" || kind.startsWith("day-foot"))
    lines.push({kind, text: text(n).trim()});
}
console.log(JSON.stringify(lines));
