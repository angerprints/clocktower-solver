"""Run the test suite.

    python run_tests.py              everything
    python run_tests.py -v           one line per test
    python run_tests.py wakes        only files matching "wakes"
    python run_tests.py -k virgin    only tests whose name matches "virgin"

Nothing to install: it is the standard library's unittest underneath.
"""

import os
import difflib
import pathlib
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.join(HERE, "tests")


def main(argv):
    verbose = "-v" in argv
    argv = [a for a in argv if a != "-v"]

    keyword = None
    if "-k" in argv:
        i = argv.index("-k")
        keyword = argv[i + 1] if i + 1 < len(argv) else None
        argv = argv[:i] + argv[i + 2:]

    # Run one part of the suite, as "2/3" — the second third.
    #
    # The whole thing has grown past what fits in a single sitting, and a
    # run that is killed halfway through prints no summary at all: the
    # failure is somewhere in a wall of dots and nothing says which. Its
    # files are split alphabetically, so the same third is the same files
    # every time and a failure can be chased.
    part = None
    for arg in list(argv):
        if "/" in arg and all(bit.isdigit() for bit in arg.split("/")):
            which, outof = (int(bit) for bit in arg.split("/"))
            part = (which, outof)
            argv.remove(arg)
            break

    pattern = f"test*{argv[0]}*.py" if argv else "test*.py"

    # A pattern matching no file is a mistake, not an empty suite.
    #
    # `run_tests.py waking` matched nothing and reported "Ran 0 tests —
    # all good". The file is `test_wakes`. For a whole session that hid
    # the very tests being looked for, and every run in between looked
    # like a pass.
    if argv:
        matched = sorted(pathlib.Path(TESTS).glob(pattern))
        if not matched:
            every = sorted(f.stem[len("test_"):]
                           for f in pathlib.Path(TESTS).glob("test_*.py"))
            print(f"nothing matches {argv[0]!r}.\n")
            # Close by spelling rather than by prefix. The first attempt
            # compared the first four letters, which is exactly wrong for
            # the case that prompted all this: "waki" is not a substring
            # of "wakes".
            near = difflib.get_close_matches(argv[0].lower(), every, n=3,
                                             cutoff=0.5)
            near += [n for n in every
                     if argv[0].lower() in n and n not in near]
            if near:
                print("did you mean: " + ", ".join(near) + "?\n")
            print("the test files are:")
            for name in every:
                print(f"  {name}")
            return 2

    sys.path.insert(0, TESTS)
    sys.path.insert(0, HERE)

    suite = unittest.defaultTestLoader.discover(TESTS, pattern=pattern,
                                                top_level_dir=TESTS)
    if part is not None:
        which, outof = part
        files = sorted(pathlib.Path(TESTS).glob(pattern))
        names = [f.stem for f in files]
        mine = {n for i, n in enumerate(names) if i % outof == which - 1}
        suite = filter_by_file(suite, mine)
        print(f"part {which} of {outof}: {', '.join(sorted(mine))}")
    if keyword:
        suite = filter_by(suite, keyword.lower())
        # Same reasoning: a keyword that filters everything away is a
        # typo, and reporting it as a pass is the wrong answer.
        if not suite.countTestCases():
            print(f"no test matches -k {keyword!r}.")
            return 2

    # Time each file, so it is obvious where a slow run is going.
    slow = {}
    _time_files(suite, slow)

    started = time.time()
    result = unittest.TextTestRunner(verbosity=2 if verbose else 1).run(suite)
    elapsed = time.time() - started

    if not result.testsRun:
        print("\nno tests ran at all, which is not a pass.")
        return 2

    print(f"\n{result.testsRun} tests in {elapsed:.1f}s")
    if slow:
        print("slowest files:")
        for name, secs in sorted(slow.items(), key=lambda kv: -kv[1])[:4]:
            print(f"  {secs:>5.1f}s  {name}")
    if result.wasSuccessful():
        print("all good")
    return 0 if result.wasSuccessful() else 1


def filter_by_file(suite, wanted):
    """Keep only the tests whose module is in this part."""
    kept = unittest.TestSuite()
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            got = filter_by_file(item, wanted)
            if got.countTestCases():
                kept.addTest(got)
        elif type(item).__module__ in wanted:
            kept.addTest(item)
    return kept


def _time_files(suite, slow):
    """Wrap every test so the time lands against its file."""
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            _time_files(item, slow)
            continue
        name = item.id().split(".")[0]
        slow.setdefault(name, 0.0)
        original = item.run

        def timed(result, _item=item, _name=name, _run=original):
            begun = time.time()
            out = _run(result)
            slow[_name] += time.time() - begun
            return out

        item.run = timed


def filter_by(suite, keyword):
    """Keep only tests whose id mentions the keyword."""
    kept = unittest.TestSuite()
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            inner = filter_by(item, keyword)
            if inner.countTestCases():
                kept.addTest(inner)
        elif keyword in item.id().lower():
            kept.addTest(item)
    return kept


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
