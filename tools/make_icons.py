"""Draw the app icons.

    python tools/make_icons.py

A clock face on the grimoire's own dark ground, with a gold rim, twelve
ticks and two hands at midnight — the same thing the dial is. Drawn
rather than fetched, so nothing has to be licensed, and generated rather
than checked in as opaque bytes so the next person can change the colour
without a graphics editor.

Three sizes for three different jobs:

  * 512 and 192 are what a web app manifest asks for, and what Android
    uses when the page is added to a home screen.
  * 180 is what iOS uses for `apple-touch-icon`, which it looks for
    separately and will not take from the manifest.

The 512 is also drawn *maskable*: Android may crop an icon to whatever
shape the launcher likes, so the face is kept well inside a safe circle
rather than filling the square.
"""

import pathlib
import sys

from PIL import Image, ImageDraw

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "ui" / "icons"

# The page's own palette, so the icon and the grimoire look like one
# thing rather than two.
NIGHT = (43, 34, 66)
NIGHT_DEEP = (30, 24, 47)
GOLD = (201, 169, 97)
GOLD_SOFT = (156, 127, 78)
PARCHMENT = (246, 237, 216)
CRIMSON = (142, 27, 34)


def draw(size, maskable=False):
    """One icon, at whatever size is asked for.

    Everything is a fraction of `size` rather than a pixel count, so the
    three come out as the same drawing rather than as three drawings that
    happen to look alike.
    """
    # Supersampled and shrunk, because a circle drawn straight at 180px
    # has visibly stepped edges and Pillow has no antialiased ellipse.
    scale = 4
    s = size * scale
    img = Image.new("RGB", (s, s), NIGHT_DEEP)
    d = ImageDraw.Draw(img)

    # Android may crop a maskable icon to any shape the launcher fancies,
    # so the face has to sit inside the circle that always survives.
    face = 0.34 if maskable else 0.44
    mid = s / 2

    # A little depth on the ground, so the face is not floating on flat
    # colour at large sizes. Plenty of steps: a dozen showed as rings.
    steps = 140
    for step in range(steps, 0, -1):
        r = s * (face + 0.10) * step / steps
        blend = step / steps
        colour = tuple(int(NIGHT_DEEP[i] + (NIGHT[i] - NIGHT_DEEP[i])
                           * (1 - blend)) for i in range(3))
        d.ellipse([mid - r, mid - r, mid + r, mid + r], fill=colour)

    rim = s * face
    d.ellipse([mid - rim, mid - rim, mid + rim, mid + rim],
              outline=GOLD, width=max(2, int(s * 0.012)))
    inner = s * face * 0.86
    d.ellipse([mid - inner, mid - inner, mid + inner, mid + inner],
              outline=GOLD_SOFT, width=max(1, int(s * 0.005)))

    # Twelve ticks, the quarters longer — the same face the dial draws.
    import math
    for i in range(12):
        angle = math.radians(i * 30 - 90)
        long_one = i % 3 == 0
        r1 = rim * 0.99
        r2 = rim * (0.82 if long_one else 0.90)
        width = max(2, int(s * (0.011 if long_one else 0.006)))
        d.line([mid + r1 * math.cos(angle), mid + r1 * math.sin(angle),
                mid + r2 * math.cos(angle), mid + r2 * math.sin(angle)],
               fill=GOLD, width=width)

    # Hands at midnight, which is when the whole game happens. Both point
    # straight up, so they have to be told apart by weight rather than by
    # angle — drawn the same width they were one hand.
    d.line([mid, mid, mid, mid - rim * 0.72], fill=PARCHMENT,
           width=max(2, int(s * 0.013)))
    d.line([mid, mid, mid, mid - rim * 0.44], fill=PARCHMENT,
           width=max(4, int(s * 0.028)))
    pin = s * 0.022
    d.ellipse([mid - pin, mid - pin, mid + pin, mid + pin], fill=CRIMSON)

    return img.resize((size, size), Image.LANCZOS)


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    for size, maskable, name in ((512, True, "icon-512.png"),
                                 (192, False, "icon-192.png"),
                                 (180, False, "apple-touch-icon.png")):
        path = OUT / name
        draw(size, maskable).save(path, optimize=True)
        made.append((name, path.stat().st_size))
    for name, size in made:
        print(f"  {name:<24} {size / 1024:5.1f} kB")
    print(f"{len(made)} icons written to {OUT.relative_to(HERE.parent)}")


if __name__ == "__main__":
    build()
