// Render the ledger for a game on Bad Moon Rising and print the block
// that counts its nights against the day before each. The game comes in
// as JSON in GAME (seats' events, quiet nights, days done); SCRIPT names
// the built-in script. The page is asked what it draws rather than
// trusted to draw it.
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

const api = await import(join(ROOT, "api.mjs"));
const game = JSON.parse(process.env.GAME);
const names = ["Anna","Ben","Cara","Dan","Eve","Finn","Gita","Hugo","Ines"];
const script = api.loadScript({name: process.env.SCRIPT, n_players: 9}).script;
store["botc-grimoire"] = JSON.stringify({
  n: 9, done: game.done || [],
  script: {name: script.name, author: script.author,
           characters: script.characters},
  players: names.map((name, i) => ({name, claim: "",
    events: (game.events || {})[name] || [], certainty:"", read:0, wake:""})),
  infos: [], quiet: game.quiet || [], history: [], fabled: [], notes: {},
});

const scratch = join(HERE, ".pattern_body.mjs");
writeFileSync(scratch, patched);
await import(scratch);
await new Promise(d => setTimeout(d, 300));

const plain = html => html.replace(/<\/(b|div)>/g, "\n").replace(/<[^>]+>/g, "")
  .replace(/&middot;/g, "\u00b7").split("\n").map(l => l.trim()).filter(Boolean);
const blocks = nodes.filter(n => (n.className || "").trim() === "night-pattern");
console.log(JSON.stringify(blocks.length ? plain(blocks[blocks.length - 1].innerHTML) : null));
