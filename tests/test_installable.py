"""The grimoire as something you can add to a home screen.

Three things make that work: a manifest, icons, and a service worker that
keeps a copy on the device. None of them affect a single number, so they
are easy to let rot — a renamed solver module and the offline copy is
half an application with no way to tell.

So the checks here are mostly about drift: the worker's list of files
against the files that exist, the manifest's icons against the icons on
disk, and the page against both.

One thing this deliberately does *not* claim: that the offline copy will
be there. A browser only registers a service worker on a secure origin —
https or localhost — so over plain http at a LAN address, which is how a
phone reaches a laptop today, it quietly does nothing. The page still
works and still installs; it just needs the laptop awake.
"""

import json
import pathlib
import re
import unittest

from helpers import SolverTest                    # sets up the import path

ROOT = pathlib.Path(__file__).resolve().parent.parent
UI = ROOT / "ui"
PAGE = UI / "index.html"
MANIFEST = UI / "manifest.webmanifest"
WORKER = UI / "sw.js"


class TheManifest(SolverTest):

    def setUp(self):
        self.data = json.loads(MANIFEST.read_text())

    def test_it_says_what_a_browser_needs_to_install_it(self):
        for key in ("name", "short_name", "start_url", "scope", "display",
                    "background_color", "theme_color", "icons"):
            with self.subTest(key=key):
                self.assertIn(key, self.data)
        self.assertEqual(self.data["display"], "standalone")

    def test_every_icon_it_names_is_there_and_the_right_size(self):
        from PIL import Image
        for icon in self.data["icons"]:
            path = UI / icon["src"]
            with self.subTest(icon=icon["src"]):
                self.assertTrue(path.is_file(), f"{path} is missing")
                want = int(icon["sizes"].split("x")[0])
                self.assertEqual(Image.open(path).size, (want, want))

    def test_one_icon_survives_being_cropped(self):
        """Android may crop an icon to whatever shape the launcher likes,
        so at least one has to be drawn with that in mind."""
        purposes = " ".join(i.get("purpose", "") for i in self.data["icons"])
        self.assertIn("maskable", purposes)


class TheServiceWorker(SolverTest):

    def setUp(self):
        self.source = WORKER.read_text()
        self.listed = re.findall(r'"(\.[^"]+)"', self.source)

    def test_it_lists_every_solver_module(self):
        """The list is written out rather than discovered, which is the
        right call — a worker that caches whatever it happens to see ends
        up with half an application. The cost is that it can go stale, so
        it is checked against what is on disk."""
        on_disk = {f"../js/{p.name}" for p in (ROOT / "js").glob("*.mjs")
                   if not p.name.startswith("dump_")}
        listed = {f for f in self.listed if f.startswith("../js/")}
        self.assertEqual(listed, on_disk)

    def test_it_lists_the_page_and_its_furniture(self):
        for wanted in ("./index.html", "./manifest.webmanifest",
                       "./icons/icon-192.png", "./icons/icon-512.png",
                       "./icons/apple-touch-icon.png"):
            with self.subTest(file=wanted):
                self.assertIn(wanted, self.listed)

    def test_everything_it_lists_actually_exists(self):
        for entry in self.listed:
            if entry in ("./",):
                continue
            with self.subTest(file=entry):
                self.assertTrue((UI / entry).resolve().is_file(), entry)

    def test_it_never_answers_a_solve_from_the_cache(self):
        """The guesswork check is the one thing still asking the server,
        and it needs a real answer or an honest failure — never a stale
        one."""
        self.assertIn('pathname.startsWith("/api/")', self.source)

    def test_an_older_copy_is_thrown_away(self):
        """So a stale solver module can never be paired with a fresh
        page."""
        self.assertIn("caches.delete", self.source)


class ThePageOffersItself(SolverTest):

    def setUp(self):
        self.html = PAGE.read_text()

    def test_it_points_at_the_manifest_and_the_icons(self):
        self.assertIn('rel="manifest"', self.html)
        self.assertIn('rel="apple-touch-icon"', self.html)

    def test_it_says_what_ios_needs_said_separately(self):
        """iOS reads its own meta tags rather than the manifest."""
        for tag in ("apple-mobile-web-app-capable",
                    "apple-mobile-web-app-title"):
            with self.subTest(tag=tag):
                self.assertIn(tag, self.html)

    def test_it_registers_the_worker_without_insisting(self):
        """Registration fails on a plain-http LAN address, which is how a
        phone reaches a laptop today. That has to be quiet: everything
        works, it just is not kept for later."""
        self.assertIn('navigator.serviceWorker.register("sw.js")', self.html)
        self.assertIn(".catch(", self.html)

    def test_the_fonts_fall_back_rather_than_fail(self):
        """The webfonts are the only thing still fetched from anywhere."""
        self.assertRegex(self.html, r'--display:"Cinzel".*Georgia')
        self.assertRegex(self.html, r'--body:"EB Garamond".*Georgia')


class TheServerHandsThemOver(SolverTest):

    def setUp(self):
        self.source = (ROOT / "app.py").read_text()

    def test_it_serves_the_manifest_and_the_worker(self):
        self.assertIn("manifest.webmanifest", self.source)
        self.assertIn("application/manifest+json", self.source)
        self.assertIn('"/sw.js"', self.source)

    def test_the_worker_comes_from_the_root(self):
        """A worker can only control pages at or below where it was
        served from, so one served at /ui/ could not control /."""
        self.assertIn('if path == "/sw.js"', self.source)

    def test_it_refuses_a_path_with_a_directory_in_it(self):
        self.assertIn("os.path.basename", self.source)


if __name__ == "__main__":
    unittest.main()
