// Save a fully-populated game, reload it, and see what came back.
// A field that saves but does not load is invisible until somebody
// reopens a game mid-session and finds half of it gone.
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

const byId = {};
const el = () => {
  const n = {className:"", textContent:"", innerHTML:"", value:"", type:"",
    checked:false, title:"", hidden:false, disabled:false, children:[],
    style:{setProperty(){},removeProperty(){}}, dataset:{},
    classList:{add(c){n.className+=" "+c;},remove(){},toggle(){},contains(){return false;}},
    appendChild(c){n.children.push(c);return c;},
    querySelectorAll(){return [];}, querySelector(){return null;},
    remove(){}, addEventListener(){}, setAttribute(){}, scrollIntoView(){},
    insertBefore(){}, focus(){}, clientWidth:640,
    getBoundingClientRect(){return {left:0,top:0,bottom:0,width:0,height:0};}};
  return n;
};
const get = id => (byId[id] = byId[id] || el());
globalThis.document = {createElement:el, createElementNS:el,
  createTextNode:t=>{const n=el();n.textContent=t;return n;},
  getElementById:get, querySelector:s=>s.startsWith("#")?get(s.slice(1)):el(),
  querySelectorAll:()=>[], addEventListener(){}, body:el()};
globalThis.window = {innerWidth:1200, addEventListener(){}};

// A game with something in every field the page can record.
const game = {
  n: 9, quiet: [3], done: [1, 2], over: true, fabled: [],
  notes: {"1": "a note"},
  open: ["ledger"],
  players: ["Anna","Ben","Cara","Dan","Eve","Finn","Gita","Hugo","Ines"]
    .map((name, i) => ({
      name, claim: ["Clockmaker","Dreamer","Oracle","Sage","Juggler",
                    "Klutz","Barber","Mutant","Sweetheart"][i],
      events: i === 2 ? ["N2"] : [],
      certainty: i === 0 ? "confirmed" : "",
      read: i === 1 ? 2 : 0, wake: "", suspect: i === 3,
      voted: i === 4 ? [2] : [], nominated: i === 5 ? [2] : [],
    })),
  infos: [{type: "ClockmakerInfo", night: 1, player: 0, count: 1}],
};
const store = {"botc-grimoire": JSON.stringify(game)};
globalThis.localStorage = {getItem: k => store[k] || null,
  setItem(k, v){ store[k] = v; }, removeItem(k){ delete store[k]; }};
globalThis.fetch = () => Promise.reject(new Error("no server"));

const scratch = join(HERE, ".round_trip_body.mjs");
writeFileSync(scratch, patched);
await import(scratch);
await new Promise(d => setTimeout(d, 300));

const back = JSON.parse(store["botc-grimoire"]);
const lost = [];
const check = (path, want, got) => {
  if (JSON.stringify(want) !== JSON.stringify(got))
    lost.push(`${path}: saved ${JSON.stringify(want)}, back ${JSON.stringify(got)}`);
};
for (const key of ["n", "quiet", "done", "over", "notes"])
  check(key, game[key], back[key]);
game.players.forEach((p, i) => {
  for (const f of ["name","claim","events","certainty","read","suspect",
                   "voted","nominated"])
    check(`seat ${i+1}.${f}`, p[f], back.players[i][f]);
});
check("infos", game.infos, back.infos);
console.log(JSON.stringify({lost}));
