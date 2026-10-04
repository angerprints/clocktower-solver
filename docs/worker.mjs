// The solver, off the page's own thread.
//
// A big board takes seconds and a Barber's board twenty, and solved on
// the page the browser could not paint, scroll or even show that it was
// busy: it froze. Here it runs beside the page instead. The page stays
// usable, shows how far along it is, and can stop a solve it no longer
// wants by throwing this worker away.
//
// It speaks two messages, both answered with the same shape the page
// used to get by calling the solver directly:
//
//     {id, kind: "solve" | "guesswork" | "review", payload, truth}
//       -> {id, progress: 0..1}   now and then
//       -> {id, data}             once, at the end
//       -> {id, error}            or this
//
// Only `api.mjs` is imported, so the build can stamp this one import with
// the release fingerprint the way it stamps the page's.

import {guessworkFor, onProgress, reviewGame, solveBoard} from "./api.mjs?v=32a9e87ff469";

self.onmessage = event => {
  const {id, kind, payload, truth} = event.data || {};
  onProgress(fraction => self.postMessage({id, progress: fraction}));
  try {
    const data = kind === "guesswork" ? guessworkFor(payload)
               : kind === "review" ? reviewGame(payload, truth)
               : solveBoard(payload);
    self.postMessage({id, data});
  } catch (err) {
    self.postMessage({id, error: String((err && err.message) || err)});
  } finally {
    onProgress(null);
  }
};
