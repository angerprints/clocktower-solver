"""Write the unsupported-character table out as a JavaScript module.

    python tools/gen_limits.py

The wording *is* the feature here — these entries are what somebody reads
when the solver refuses their script — so keeping two copies by hand
would be a way of letting them drift apart. Generated instead, like the
catalogue.
"""

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from botc import limits                                      # noqa: E402

OUT = HERE.parent / "js" / "limits.mjs"
MARK = "export const UNSUPPORTED = "


def build():
    text = OUT.read_text()
    head = text[:text.index(MARK) + len(MARK)]
    tail = text[text.index("\n\n/** Which named characters"):]
    body = json.dumps(limits.UNSUPPORTED, indent=1, ensure_ascii=False)
    OUT.write_text(head + body + ";" + tail)
    print(f"{len(limits.UNSUPPORTED)} entries written to "
          f"{OUT.relative_to(HERE.parent)}")


if __name__ == "__main__":
    build()
