"""Assemble the folder a static host serves.

    python tools/build_site.py

The app is already static — the solver runs in the browser and `app.py`
only hands over files — so this is arranging, not compiling. There is no
bundler, no minifier and no build cache, because nothing here needs one:
the whole thing is under half a megabyte of files a browser reads
directly.

What it does need is a different *shape*. In the repository the page sits
in `ui/` and imports the solver from `../js/`, which is tidy to work in
and wrong to publish.

**Flat, with no subfolders at all**, which looks untidy and is the whole
point. GitHub's web uploader lets you choose *files* and not folders, and
its editor cannot create an empty folder either — so anything nested has
to be dragged in, which only some browsers manage. One level means
selecting everything and uploading it, on any browser, with no command
line. Tidiness is worth less than that.

Everything stays relative. Pages serves a project site from a
subdirectory — `https://you.github.io/the-repo/` — and an absolute path
would look for the files at the domain root and find nothing.
"""

import hashlib
import pathlib
import re
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "docs"

# Everything the page needs, and nothing else. The tests, the Python
# solver and the scratch files stay behind.
PAGES = [("ui/index.html", "index.html"),
         ("ui/manifest.webmanifest", "manifest.webmanifest"),
         ("ui/sw.js", "sw.js")]
ICONS = "ui/icons"
MODULES = "js"

NOTE = """This folder is built, not written.

    python tools/build_site.py

It is what a static host serves: the page, the solver, the manifest, the
icons and the service worker, all at one level. Editing anything here is
a way of losing the change — edit `ui/` or `js/` and build again.
"""


def solver_modules():
    """The solver, without the cross-checking scripts.

    `dump_*.mjs` exist to be read by the Python tests and print JSON. A
    browser never loads one, so shipping them would be shipping the test
    harness.
    """
    return sorted(p for p in (ROOT / MODULES).glob("*.mjs")
                  if not p.name.startswith("dump_"))


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    # Regenerate the character data before copying anything.
    #
    # `js/characters.mjs` is written out of the Python catalogue by
    # `tools/gen_characters.py`, and the build used to assume somebody
    # had remembered to run it. Nobody did. A character added to Python
    # reached the solver, the tests and the ledger, and never reached the
    # built site — which is exactly the failure that took a dozen rounds
    # to find, because every artifact *except* the generated one was
    # correct and each one confirmed the last.
    #
    # A build step that depends on a human is not a build step.
    import subprocess
    subprocess.run([sys.executable, str(HERE / "gen_characters.py")],
                   check=True, capture_output=True)

    for module in solver_modules():
        shutil.copy2(module, OUT / module.name)
    for icon in sorted((ROOT / ICONS).glob("*.png")):
        shutil.copy2(icon, OUT / icon.name)

    for source, target in PAGES:
        text = (ROOT / source).read_text()
        # Every path collapses to the same level. In the repository the
        # page sits in `ui/` and reaches up into `js/`; here there is
        # nowhere to reach. Rewritten rather than maintained twice: a
        # second copy is a second thing to forget.
        text = text.replace('from "../js/', 'from "./')
        text = text.replace('"../js/', '"./')
        text = text.replace('"./icons/', '"./')
        text = text.replace('"icons/', '"./')
        (OUT / target).write_text(text)

    # Stamp the worker with a fingerprint of everything shipped.
    #
    # This is what makes an update actually reach a phone. A browser only
    # reinstalls a service worker when the bytes of `sw.js` change, and
    # everything it serves is cache-first — so with a fixed version
    # string a changed page is never fetched, never installed and never
    # activated. The old copy is served for ever, and the update looks
    # like it failed to upload. It did not; it was never asked for.
    stamp = hashlib.sha256()
    for name in sorted(p.name for p in OUT.iterdir() if p.is_file()):
        if name == "sw.js":
            continue                  # its own text is about to change
        stamp.update(name.encode())
        stamp.update((OUT / name).read_bytes())
    version = stamp.hexdigest()[:12]
    worker = OUT / "sw.js"
    worker.write_text(worker.read_text().replace(
        '"clocktower-dev"', f'"clocktower-{version}"'))

    # And stamp the page's own entry point.
    #
    # The worker's fingerprint makes it *reinstall*, but the page still
    # asks for `./api.mjs` by a fixed name — and a browser caches an ES
    # module hard, so a stale copy can be served under a fresh worker.
    # One character added and not appearing, in two different browsers,
    # traced through five correct artifacts before the served file was
    # looked at directly.
    #
    # Only the entry point needs it: everything below is reached through
    # imports that resolve relative to a URL which now carries the query,
    # so the whole graph moves together.
    page = OUT / "index.html"
    page.write_text(page.read_text().replace(
        'from "./api.mjs"', f'from "./api.mjs?v={version}"').replace(
        '"./worker.mjs"', f'"./worker.mjs?v={version}"'))
    # The background worker is a second entry point, so it gets the same
    # treatment: its own URL carries the fingerprint, and so does the one
    # import it makes.
    background = OUT / "worker.mjs"
    background.write_text(background.read_text().replace(
        'from "./api.mjs"', f'from "./api.mjs?v={version}"'))

    (OUT / "README.md").write_text(NOTE)
    # Without this, GitHub Pages runs the whole folder through Jekyll,
    # which is a static site generator this has no use for and which
    # silently drops anything beginning with an underscore.
    (OUT / ".nojekyll").write_text("")

    files = sorted(p for p in OUT.rglob("*") if p.is_file())
    total = sum(p.stat().st_size for p in files)
    print(f"{len(files)} files, {total / 1024:.0f} kB, written to "
          f"{OUT.relative_to(ROOT)}/ — all at one level, nothing nested")

    listed = re.findall(r'"\./([\w.]+\.mjs)"', (OUT / "sw.js").read_text())
    missing = [m for m in listed if not (OUT / m).is_file()]
    if missing:
        print(f"\nWARNING: the worker lists files that were not copied: "
              f"{missing}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
