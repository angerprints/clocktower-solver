// Keeps the grimoire on the device, so it opens with nothing behind it.
//
// Everything it needs is a fixed, small list — one page, fifteen solver
// modules, a manifest and three icons — because the solver moved into the
// browser. Nothing is fetched at run time, so nothing has to be guessed
// at here.
//
// One thing worth knowing before expecting too much of this: a browser
// will only register a service worker on a **secure** origin, which means
// https or localhost. Opening the page over plain http at a LAN address —
// which is how a phone reaches a laptop today — will not register it. The
// page still works and still installs to a home screen; it just needs the
// laptop awake. Real offline needs https, which means hosting it or
// wrapping it.

// Stamped by `tools/build_site.py` from the contents of everything
// shipped. It has to change whenever any of them does, and this is the
// only thing that makes an update reach anybody:
//
// A browser decides whether to reinstall a worker by comparing the bytes
// of *this file* with the copy it already has. Everything below is
// cache-first, so with a fixed version string a changed page is never
// fetched, never installed and never activated — the old copy is served
// for ever and the update looks like it failed to upload.
const VERSION = "clocktower-5a1c9e481aa6";

// Listed rather than discovered. A service worker that caches whatever it
// happens to see ends up with half an application and no way to tell.
const FILES = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./icon-192.png",
  "./icon-512.png",
  "./apple-touch-icon.png",
  "./api.mjs",
  "./catalogue.mjs",
  "./characters.mjs",
  "./characters.rules.mjs",
  "./deaths.mjs",
  "./diagnose.mjs",
  "./impairment.mjs",
  "./info.mjs",
  "./limits.mjs",
  "./phases.mjs",
  "./priors.mjs",
  "./report.mjs",
  "./rng.mjs",
  "./roles.mjs",
  "./scoring.mjs",
  "./sensitivity.mjs",
  "./scripts.mjs",
  "./state.mjs",
  "./waking.mjs",
  "./worlds.mjs",
];

self.addEventListener("install", event => {
  event.waitUntil((async () => {
    const cache = await caches.open(VERSION);
    // One at a time rather than `addAll`, which throws the whole install
    // away if a single file is missing — and then the page silently has
    // no offline copy at all.
    const missing = [];
    await Promise.all(FILES.map(async file => {
      try {
        await cache.add(new Request(file, {cache: "reload"}));
      } catch (err) {
        missing.push(file);
      }
    }));
    if (missing.length) console.warn("not cached:", missing);
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    // Anything from an older version goes, so a stale solver module can
    // never be paired with a fresh page.
    for (const name of await caches.keys())
      if (name !== VERSION) await caches.delete(name);
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET") return;

  // The guesswork check is the one thing that still asks the server, and
  // it needs a real answer or an honest failure — never a stale one.
  if (new URL(request.url).pathname.startsWith("/api/")) return;

  event.respondWith((async () => {
    // Cache first: everything here is part of the application rather than
    // content, so the copy on the device is as good as the copy on the
    // wire and does not need the laptop to be awake.
    const hit = await caches.match(request, {ignoreSearch: true});
    if (hit) return hit;
    try {
      const fresh = await fetch(request);
      if (fresh && fresh.ok && fresh.type === "basic") {
        const cache = await caches.open(VERSION);
        cache.put(request, fresh.clone());
      }
      return fresh;
    } catch (err) {
      // Offline and never seen: better to say so than to hang.
      const page = await caches.match("./index.html");
      if (page && request.mode === "navigate") return page;
      throw err;
    }
  })());
});
