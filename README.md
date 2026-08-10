This folder is built, not written.

    python tools/build_site.py

It is what a static host serves: the page, the solver, the manifest, the
icons and the service worker, all at one level. Editing anything here is
a way of losing the change — edit `ui/` or `js/` and build again.
