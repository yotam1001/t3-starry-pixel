"""Starry Swirl: a wallpaper painted in the spirit of Van Gogh's The Starry Night (1889).

Everything is procedural: a flow field of vortices and wind drives thousands of short, thick
brush strokes; stars and the moon are built from concentric ring strokes; a flame-shaped
cypress and a small village sit under rolling hills.

    python starry.py      # writes background.webp, sky.webp and engine.json for starry-swirl and starry-pixel
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

W, H = 1920, 1080
HORIZON = 0.70  # hills start here (fraction of height)

# (x, y, radius, strength, direction): the big double swirl and smaller eddies.
VORTICES = [
    (0.47, 0.33, 0.17, 1.0, 1), (0.63, 0.40, 0.11, 0.9, -1),
    (0.30, 0.22, 0.08, 0.6, 1), (0.82, 0.20, 0.09, 0.5, 1),
]
# (x, y, halo radius in px): the stars.
STARS = [
    (0.12, 0.12, 48), (0.27, 0.40, 36), (0.39, 0.10, 42), (0.56, 0.15, 30), (0.70, 0.12, 40),
    (0.76, 0.48, 34), (0.92, 0.38, 44), (0.20, 0.58, 28), (0.62, 0.62, 26), (0.05, 0.36, 30),
]
MOON = (0.88, 0.14, 70)

SKY = ['#0d2259', '#14307a', '#1d4596', '#2a5cb0', '#3d72c4', '#5a8fd6', '#86aee3', '#b5cdee']
SWIRL = ['#9ec0ea', '#c9dcf4', '#e8eef8', '#7fa6dc', '#f2e7b0']
GOLD = ['#fff6c8', '#fbe48a', '#f4c84a', '#e9a92f']


def flow(x, y):
    """Direction of the brush at (x, y) in pixels."""
    u, v = x / W, y / H
    ang = 0.35 * math.sin(u * 7 + v * 5) + 0.15 * math.sin(u * 17 - v * 9)
    vx, vy = math.cos(ang), math.sin(ang) * 0.6
    swirl = 0.0
    for cx, cy, r, s, d in VORTICES:
        dx, dy = (u - cx) * W / H, v - cy
        dist2 = dx * dx + dy * dy
        w = s * math.exp(-dist2 / (r * r)) * 3.2
        vx += -dy * d * w / (math.sqrt(dist2) + 1e-6)
        vy += dx * d * w / (math.sqrt(dist2) + 1e-6)
        swirl = max(swirl, s * math.exp(-dist2 / (r * r * 1.4)))
    n = math.hypot(vx, vy) or 1
    return vx / n, vy / n, swirl


def mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def stroke(draw, x, y, steps, step, width, color, field=flow):
    pts = [(x, y)]
    for _ in range(steps):
        dx, dy, _ = field(x, y)
        x, y = x + dx * step, y + dy * step
        pts.append((x, y))
    draw.line(pts, fill=color, width=width, joint='curve')


def sky(draw, rnd, fine=False):
    horizon = H * HORIZON
    for _ in range(70000 if fine else 30000):
        x, y = rnd.uniform(-20, W + 20), rnd.uniform(-20, horizon + 30)
        _, _, swirl = flow(x, y)
        depth = y / horizon  # lighter toward the horizon
        base = SKY[min(len(SKY) - 1, int(depth * 4.5 + rnd.random() * 2.5))]
        if rnd.random() < swirl * 0.85:
            base = rnd.choice(SWIRL)
        col = mix(base, rnd.choice(SKY), rnd.random() * 0.25)
        if fine:
            stroke(draw, x, y, rnd.randint(3, 6), rnd.uniform(4, 6), rnd.randint(3, 6), col)
        else:
            stroke(draw, x, y, rnd.randint(3, 5), rnd.uniform(5, 8), rnd.randint(5, 8), col)


def halo(draw, rnd, cx, cy, radius, core, rings):
    for r in range(radius, 0, -5):
        t = r / radius
        n = max(10, int(r * 0.9))
        col_choices = rings if t > 0.45 else GOLD
        for i in range(n):
            a0 = 2 * math.pi * i / n + rnd.uniform(-0.1, 0.1)
            a1 = a0 + rnd.uniform(0.25, 0.5)
            box = [cx - r, cy - r, cx + r, cy + r]
            draw.arc(box, math.degrees(a0), math.degrees(a1), fill=rnd.choice(col_choices), width=rnd.randint(4, 6))
    draw.ellipse([cx - core, cy - core, cx + core, cy + core], fill='#fffbe6')


def stars(draw, rnd):
    for sx, sy, r in STARS:
        halo(draw, rnd, sx * W, sy * H, r, max(5, r // 6), ['#cfe0f5', '#f6eebd', '#9fc0ea', '#fbe48a'])
    mx, my, mr = MOON[0] * W, MOON[1] * H, MOON[2]
    halo(draw, rnd, mx, my, mr + 34, 0, ['#f6d77a', '#fbe8a6', '#e9b949', '#cfe0f5'])
    r = mr * .58
    draw.ellipse([mx - r, my - r, mx + r, my + r], fill='#f7c948')
    ox, oy, r2 = mx + r * .45, my - r * .3, r * .86  # bite out of the top right -> crescent
    draw.ellipse([ox - r2, oy - r2, ox + r2, oy + r2], fill='#e9b949')
    draw.ellipse([ox - r2 * .92, oy - r2 * .92, ox + r2 * .92, oy + r2 * .92], fill='#f6d77a')


def hills(draw, rnd):
    top = H * HORIZON

    def ridge(x, layer):
        return top + layer * 55 + 28 * math.sin(x / 260 + layer * 1.7) + 14 * math.sin(x / 97 + layer)

    for layer, cols in enumerate((['#1f3f6e', '#2b5285', '#183358'], ['#17304f', '#22446a', '#10243e'],
                                  ['#0e1f33', '#162c45', '#0a1626'])):
        for x in range(-20, W + 20, 3):
            y0 = ridge(x, layer)
            rim = ['#5b86c0', '#4a76b2', '#3b679f'][layer]
            stroke(draw, x, y0 + rnd.uniform(-2, 4), 2, rnd.uniform(6, 9), rnd.randint(4, 6), rim,
                   lambda px, py: (1.0, 0.2 * math.cos(px / 260 + layer * 1.7), 0))
            for _ in range(3):
                y = rnd.uniform(y0 + 6, H + 10)
                field = lambda px, py: (1.0, 0.18 * math.cos(px / 120 + layer), 0)  # noqa: E731
                stroke(draw, x, y, 3, rnd.uniform(6, 10), rnd.randint(5, 8), rnd.choice(cols), field)


WINDOWS = []  # (x, y) top-left of each 8x8 village window, full-res px; filled by village()


def village(draw, rnd):
    WINDOWS.clear()
    base = H * HORIZON + 95
    for i in range(34):
        x = W * 0.36 + i * 26 + rnd.uniform(-6, 6)
        w, h = rnd.randint(18, 30), rnd.randint(14, 28)
        y = base + 18 * math.sin(i / 3) + rnd.uniform(0, 14)
        draw.rectangle([x, y - h, x + w, y], fill=rnd.choice(['#1a2a40', '#23354f', '#141f30']))
        draw.polygon([(x - 3, y - h), (x + w / 2, y - h - 10), (x + w + 3, y - h)], fill='#0f1a2b')
        for _ in range(rnd.choice((1, 1, 2))):
            wx = int(x + rnd.randint(3, max(4, w - 11))) // 4 * 4
            wy = int(y - rnd.randint(9, max(10, h - 4))) // 4 * 4
            if (wx, wy) not in WINDOWS:
                WINDOWS.append((wx, wy))
    sx = W * 0.58  # church spire
    draw.polygon([(sx - 9, base + 10), (sx, base - 110), (sx + 9, base + 10)], fill='#101b2c')
    for wx, wy in WINDOWS:  # painted dark: the theme engine lights them by the clock
        rnd.random()
        draw.rectangle([wx, wy, wx + 7, wy + 7], fill='#1a2436')


def cypress(draw, rnd):
    cx, base, top = W * 0.24, H + 20, H * 0.12
    for _ in range(2600):
        t = rnd.random() ** 0.8
        y = top + (base - top) * t
        half = 22 + 120 * t ** 0.7
        sway = 22 * math.sin(t * 9 + 1)
        x = cx + sway + rnd.uniform(-half, half) * (0.55 + 0.45 * rnd.random())
        col = rnd.choice(['#0b1712', '#13241a', '#1c3322', '#24402a', '#3a2a1a', '#0e1a14'])
        field = lambda px, py: (0.25 * math.sin(py / 40), -1.0, 0)  # noqa: E731
        stroke(draw, x, y, 3, rnd.uniform(9, 15), rnd.randint(5, 9), col, field)


def diff_mask(after, before):
    return ImageChops.difference(after, before).convert('L').point(lambda v: 255 if v else 0)


def paint(fine=False, layers=False):
    """The finished painting. With layers=True, the pieces the theme engine animates separately:
    a dict of wallpaper (no stars/moon), full (with them), sky (sky alone), and masks
    land (hills, village, cypress), cypress, stars."""
    rnd = random.Random(1889)
    img = Image.new('RGB', (W, H), '#14307a')
    draw = ImageDraw.Draw(img)
    sky(draw, rnd, fine)
    sky_only = img.copy()
    starred = img.copy()
    stars(ImageDraw.Draw(starred), rnd)
    hills(draw, rnd)
    village(draw, rnd)
    before_cypress = img.copy()
    cypress(draw, rnd)
    land = diff_mask(img, sky_only)
    full = Image.composite(img, starred, land)
    if not layers:
        return full.filter(ImageFilter.SMOOTH)
    star_mask = ImageChops.subtract(diff_mask(starred, sky_only).filter(ImageFilter.MaxFilter(3)), land)
    return dict(wallpaper=img.filter(ImageFilter.SMOOTH), full=full.filter(ImageFilter.SMOOTH),
                sky=sky_only.filter(ImageFilter.SMOOTH), land=land.filter(ImageFilter.MaxFilter(5)),
                cypress=diff_mask(img, before_cypress), stars=star_mask)


# Colors the median cut would wash out: the golds of stars/moon/windows, the cypress darks.
KEEP = ['#fff6c8', '#fbe48a', '#f4c84a', '#e9a92f', '#f7c948', '#0b1712', '#1c3322', '#3a2a1a']
BAYER4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def pixel_palette(small, colors=32):
    adaptive = small.quantize(colors - len(KEEP), method=Image.Quantize.MEDIANCUT).getpalette()[:3 * (colors - len(KEEP))]
    fixed = [int(c[i:i + 2], 16) for c in KEEP for i in (1, 3, 5)]
    palette = Image.new('P', (1, 1))
    palette.putpalette(adaptive + fixed + [0] * (768 - len(adaptive) - len(fixed)))
    return palette


def pixelate(img, scale=4, colors=32, spread=34, palette=None, upscale=True):
    """Pixel-art version: downsample, ordered (Bayer) dither to a small palette, upscale crisp.
    Returns (image, palette); pass the palette back in to dither another layer identically."""
    import numpy as np
    small = img.resize((W // scale, H // scale), Image.BOX)
    palette = palette or pixel_palette(small, colors)
    a = np.asarray(small).astype(np.float32)
    bayer = (np.array(BAYER4, np.float32) + 0.5) / 16 - 0.5
    tile = np.tile(bayer, (a.shape[0] // 4 + 1, a.shape[1] // 4 + 1))[:a.shape[0], :a.shape[1]]
    a = np.clip(a + tile[..., None] * spread, 0, 255).astype(np.uint8)
    q = Image.fromarray(a).quantize(palette=palette, dither=Image.Dither.NONE).convert('RGB')
    return (q.resize((W, H), Image.NEAREST) if upscale else q), palette


def rle(mask):
    """Run lengths of a 0/255 mask, row-major, alternating sky/over starting with sky."""
    runs, cur, n = [], 0, 0
    for v in mask.tobytes():
        v = 1 if v else 0
        if v == cur:
            n += 1
        else:
            runs.append(n)
            cur, n = v, 1
    runs.append(n)
    return runs


def small_mask(mask, size, threshold=8):
    return mask.resize(size, Image.BOX).point(lambda v: 255 if v > threshold else 0)


def engine_data(parts, size):
    """What the theme engine needs besides its images: where the land is, and the windows."""
    return {'w': size[0], 'h': size[1], 'mask': rle(small_mask(parts['land'], size)),
            'cypress': rle(small_mask(parts['cypress'], size, 100)), 'windows': list(WINDOWS)}


def star_layer(colors, mask):
    """Stars and moon alone (transparent elsewhere) so the engine can drift them across the sky."""
    layer = colors.convert('RGBA')
    layer.putalpha(mask)
    return layer


if __name__ == '__main__':
    import json
    root = Path(__file__).resolve().parents[1]
    for name, fine in (('starry-swirl', True), ('starry-pixel', False)):
        out = root / name
        out.mkdir(exist_ok=True)
        parts = paint(fine=fine, layers=True)
        if fine:
            size = (W // 2, H // 2)
            parts['wallpaper'].save(out / 'background.webp', 'WEBP', method=6, quality=90)
            parts['sky'].resize(size, Image.LANCZOS).save(out / 'sky.webp', 'WEBP', method=6, quality=88)
            star_layer(parts['full'].resize(size, Image.LANCZOS), small_mask(parts['stars'], size, 60)).save(
                out / 'stars.webp', 'WEBP', method=6, lossless=True)
        else:
            size = (W // 4, H // 4)
            _, palette = pixelate(parts['full'])
            pixelate(parts['wallpaper'], palette=palette)[0].save(out / 'background.webp', 'WEBP', method=6, lossless=True)
            pixelate(parts['sky'], palette=palette, upscale=False)[0].save(out / 'sky.webp', 'WEBP', method=6, lossless=True)
            star_layer(pixelate(parts['full'], palette=palette, upscale=False)[0], small_mask(parts['stars'], size, 60)).save(
                out / 'stars.webp', 'WEBP', method=6, lossless=True)
        (out / 'engine.json').write_text(json.dumps(engine_data(parts, size), separators=(',', ':')))
        print('wrote', name, *((f, (out / f).stat().st_size) for f in ('background.webp', 'sky.webp', 'stars.webp')))
