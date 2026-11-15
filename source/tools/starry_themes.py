"""Patch-method stylesheets for the two Starry themes (wallpapers come from starry.py).

    python starry_themes.py   # writes ../starry-pixel/theme.css and ../starry-swirl/theme.css

starry-pixel  pixel-art wallpaper (Bayer dithered), crisp scaling, stepped animation.
starry-swirl  painterly full-resolution wallpaper, smooth animation.

Motion comes from ../../engine.js (patched into T3 next to the stylesheet), driven by --og-cfg:
    the real sky pixels turn around each vortex (sky.webp, painted without stars/hills/village),
    village windows switch on and off slowly by the local clock (all lit mornings, mostly dark at night),
    pixel theme: stars sparkle and a shooting star crosses, as pixels.
The painterly theme keeps soft SVG star glows (html::after) and a CSS shooting star (#root::before).
"""
import base64
import json
import math
import sys
from pathlib import Path

from animated import base
from build_css import build
import starry

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'official'))
from build_official import STARRY  # noqa: E402

RING = ['#f4c84a', '#86aee3', '#ffe9a8', '#3d72c4']
W, H = starry.W, starry.H


def data_uri(path):
    return f"url(data:image/webp;base64,{base64.b64encode(path.read_bytes()).decode()})"


def ground(w, k):
    """y of the front hill ridge every 4 canvas px (the path the animals walk), canvas units."""
    top = H * starry.HORIZON
    return [round((top + 2 * 55 + 28 * math.sin(x * k / 260 + 2 * 1.7) + 14 * math.sin(x * k / 97 + 2)) / k)
            for x in range(0, w + 4, 4)]


def engine_cfg(name, pixel):
    """Settings for engine.js, read from --og-cfg (all positions in canvas pixels)."""
    folder = HERE.parent / name
    data = json.loads((folder / 'engine.json').read_text())
    w, h = data['w'], data['h']
    k = W / w
    mx, my, mr = starry.MOON
    cfg = dict(
        w=w, h=h, pixel=pixel, unit=4 / k, fps=12 if pixel else 24, period=3.2, amp=0.7, horizon=[0.60, 0.69],
        vortices=[[round(cx * w, 1), round(cy * h, 1), round(r * 1.35 * h, 1), s, d] for cx, cy, r, s, d in starry.VORTICES],
        mask=data['mask'], cypress=data['cypress'], fade=2.5 if pixel else 3.0,
        windows=[[round(x / k), round(y / k), round(8 / k)] for x, y in data['windows']],
        lit=['#fff6c8', '#fbe48a', '#f4c84a'], dark='#1a2436',
        # Stars and the moon drift around their place: [x, y, radius, sparkle arm, drift]
        stars=[[round(x * w), round(y * h), round((r + 6) / k), 3 if r >= 40 else 2, round(14 / k, 1)] for x, y, r in starry.STARS]
        + [[round(mx * w), round(my * h), round((mr + 40) / k), 0, round(9 / k, 1)]],
        ground=ground(w, k), sky=[0.03, 0.42])
    return (f":root {{ --og-cfg: '{json.dumps(cfg, separators=(',', ':'))}'; "
            f"--og-sky: {data_uri(folder / 'sky.webp')}; --og-stars: {data_uri(folder / 'stars.webp')}; }}\n")


def layers(name, pixel):
    # Everything moving is drawn by engine.js: swirling sky, drifting stars and moon, birds,
    # animals on the hills, falling stars, village lights. The CSS overlays are switched off.
    css = engine_cfg(name, pixel) + "html::before, html::after, body::after, #root::before { content: none; }\n"
    return css + ('body { image-rendering: pixelated; }\n' if pixel else '')


THEMES = {
    'starry-pixel': (dict(STARRY, title='Starry Pixel',
                          blurb='Animated: Van Gogh night as pixel art; the sky really swirls, village lights follow the clock.'), True),
    'starry-swirl': (dict(STARRY, title='Starry Swirl',
                          blurb='Animated: Van Gogh night in brushwork; the sky really swirls, village lights follow the clock.'), False),
}

if __name__ == '__main__':
    root = HERE.parent
    for name, (palette, pixel) in THEMES.items():
        css = build(name, palette, base(palette, RING) + layers(name, pixel))
        css.encode('ascii')
        (root / name / 'theme.css').write_text(css, encoding='utf-8')
        print('wrote', name, len(css), 'bytes')
