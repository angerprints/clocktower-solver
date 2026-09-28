"""The folder a static host serves.

`tools/build_site.py` arranges the app into `docs/` — one folder,
everything at one level, `index.html` at its root. That is the shape a
host wants and the opposite of the shape the repository is in.

Flat on purpose, and it looks untidy for a reason worth writing down:
GitHub's web uploader lets you choose *files* and not folders, and its
editor cannot create an empty folder either. One level means selecting
everything and uploading it, on any browser, with no command line.

The checks here are that the *built* folder works, rather than the source
it came from. A build that only runs in the shape it was written in is
not a build.
"""

import json
import pathlib
import re
import shutil
import subprocess
import unittest

from helpers import SolverTest                    # sets up the import path

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = ROOT / "docs"
NODE = shutil.which("node")


class TheBuiltFolder(SolverTest):

    @classmethod
    def setUpClass(cls):
        import tools.build_site as build
        build.build()
        cls.page = (SITE / "index.html").read_text()
        cls.worker = (SITE / "sw.js").read_text()

    def test_the_page_is_at_the_root(self):
        self.assertTrue((SITE / "index.html").is_file())

    def test_everything_is_at_one_level(self):
        """A nested folder has to be dragged in, which only some browsers
        manage. Flat can be selected and uploaded anywhere."""
        self.assertEqual([p for p in SITE.iterdir() if p.is_dir()], [])

    def test_the_solver_came_with_it(self):
        modules = {p.name for p in SITE.glob("*.mjs")}
        self.assertIn("api.mjs", modules)
        self.assertIn("worlds.mjs", modules)
        self.assertGreater(len(modules), 15)

    def test_the_cross_checking_scripts_did_not(self):
        """`dump_*.mjs` exist to be read by the Python tests. A browser
        never loads one, so shipping them would be shipping the test
        harness."""
        self.assertEqual([p.name for p in SITE.glob("dump_*.mjs")], [])

    def test_the_import_was_flattened(self):
        # Stamped with the build fingerprint, so a cached module cannot
        # shadow a fresh upload.
        self.assertRegex(self.page, r'from "\./api\.mjs(\?v=[0-9a-f]+)?"')
        self.assertNotIn('from "../js/', self.page)

    def test_the_worker_points_at_the_right_place(self):
        self.assertNotIn('"../js/', self.worker)
        listed = re.findall(r'"\./([\w.]+\.mjs)"', self.worker)
        self.assertGreater(len(listed), 15)
        for name in listed:
            with self.subTest(module=name):
                self.assertTrue((SITE / name).is_file())

    def test_every_module_that_shipped_is_kept_offline(self):
        """The other direction: a module copied but not listed would be
        fetched from the network on a page that is meant to work without
        one."""
        listed = set(re.findall(r'"\./([\w.]+\.mjs)"', self.worker))
        shipped = {p.name for p in SITE.glob("*.mjs")}
        self.assertEqual(shipped - listed, set())

    def test_nothing_points_at_the_domain_root(self):
        """A project site lives in a subdirectory, so an absolute path
        would look one level too high and find nothing."""
        for text, where in ((self.page, "index.html"),
                            (self.worker, "sw.js"),
                            ((SITE / "manifest.webmanifest").read_text(),
                             "manifest")):
            with self.subTest(file=where):
                self.assertNotRegex(text, r'(href|src|from)\s*=?\s*"/[^/]')

    def test_jekyll_is_turned_off(self):
        """Left on, GitHub Pages runs the folder through a static site
        generator this has no use for, which silently drops anything
        beginning with an underscore."""
        self.assertTrue((SITE / ".nojekyll").is_file())

    def test_the_manifest_and_icons_are_there(self):
        self.assertTrue((SITE / "manifest.webmanifest").is_file())
        for name in ("icon-192.png", "icon-512.png", "apple-touch-icon.png"):
            with self.subTest(icon=name):
                self.assertTrue((SITE / name).is_file())

    def test_the_manifest_points_at_icons_that_are_there(self):
        """Flattening moved them, and a manifest still naming `icons/`
        would leave the installed app with no icon and no error."""
        data = json.loads((SITE / "manifest.webmanifest").read_text())
        for icon in data["icons"]:
            with self.subTest(icon=icon["src"]):
                self.assertTrue((SITE / icon["src"]).is_file())

    def test_the_worker_is_stamped_with_what_it_ships(self):
        """The only thing that makes an update reach anybody.

        A browser decides whether to reinstall a worker by comparing the
        bytes of `sw.js` with the copy it has. Everything it serves is
        cache-first, so with a fixed version string a changed page is
        never fetched, never installed and never activated — the old copy
        is served for ever and the update looks like it failed to upload.
        """
        version = re.search(r'const VERSION = "([^"]+)"', self.worker)
        self.assertIsNotNone(version)
        self.assertNotEqual(version.group(1), "clocktower-dev",
                            "the placeholder was never stamped")
        self.assertRegex(version.group(1), r"^clocktower-[0-9a-f]{12}$")

    def test_changing_the_page_changes_the_stamp(self):
        """Checked by doing it, because a stamp that does not move is
        exactly as bad as no stamp at all."""
        import tools.build_site as build
        page = ROOT / "ui" / "index.html"
        was = page.read_text()
        before = re.search(r'const VERSION = "([^"]+)"',
                           (SITE / "sw.js").read_text()).group(1)
        try:
            page.write_text(was + "\n<!-- a change -->\n")
            build.build()
            after = re.search(r'const VERSION = "([^"]+)"',
                              (SITE / "sw.js").read_text()).group(1)
        finally:
            page.write_text(was)
            build.build()
        self.assertNotEqual(before, after)
        again = re.search(r'const VERSION = "([^"]+)"',
                          (SITE / "sw.js").read_text()).group(1)
        self.assertEqual(before, again, "and it comes back when reverted")

    def test_the_page_asks_for_an_update_on_every_launch(self):
        """Browsers check on their own schedule, which can be a day."""
        self.assertIn("reg.update()", self.page)
        self.assertIn("updatefound", self.page)

    def test_it_is_small_enough_to_be_worth_no_bundler(self):
        total = sum(p.stat().st_size for p in SITE.rglob("*") if p.is_file())
        self.assertLess(total, 1_500_000)


@unittest.skipUnless(NODE, "Node is not installed")
class ItRunsFromThere(SolverTest):
    """The built page booted the way a browser would, with every `fetch`
    failing and counted."""

    @classmethod
    def setUpClass(cls):
        import tools.build_site as build
        build.build()
        got = subprocess.run(
            [NODE, str(ROOT / "tests" / "harness" / "site_boot.mjs")],
            capture_output=True, text=True, timeout=600)
        if got.returncode:
            raise AssertionError(f"the built site failed to boot:\n"
                                 f"{got.stderr}")
        cls.got = json.loads(got.stdout.strip().splitlines()[-1])

    def test_it_boots(self):
        self.assertTrue(self.got["booted"])

    def test_it_asks_nobody_for_anything(self):
        self.assertEqual(self.got["fetched"], 0)

    def test_it_solves(self):
        self.assertEqual(self.got["valid"], 630)
        self.assertEqual(self.got["seats"], 9)

    def test_the_guesswork_check_runs_too(self):
        """The last thing that needed a server."""
        self.assertEqual(self.got["guesswork"], 9)


if __name__ == "__main__":
    unittest.main()
