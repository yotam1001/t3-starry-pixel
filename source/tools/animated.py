"""Animated themes for the T3 theme pack.

Pure CSS, appended to the same Orbital Glass base stylesheet. Up to five free layers sit
between the wallpaper and the UI:

    html::before, html::after, body::after   z-index 0 in the root stacking context
    #root::before, #root::after              z-index -1 inside #root (still under the UI)

Performance rules: only `transform`/`opacity` (and the individual rotate/scale/translate
properties) are animated, so each layer is painted once and then moved by the GPU compositor.
Opaque panels drop their backdrop blur because blurring a moving backdrop costs work on every
frame. Everything stops under the OS "reduce motion" setting.

Usage: python animated.py   (writes themes/<name>/theme.css for every animated theme)
"""
import random
from pathlib import Path

from build_css import THEMES, build
from creatures import ASSETS, file_uri, jelly_svg, svg_uri

LAYERS = ('html::before', 'html::after', 'body::after', '#root::before', '#root::after')


# --- helpers ------------------------------------------------------------------
def dot_field(seed, tile, count, colors, r=(1.0, 1.8), halo=0, margin=None):
    """Background images for `count` dots inside a tile, safe to repeat seamlessly."""
    rnd = random.Random(seed)
    margin = margin if margin is not None else int(r[1] + halo + 2)
    out = []
    for _ in range(count):
        x = rnd.randint(margin, tile - margin)
        y = rnd.randint(margin, tile - margin)
        rad = round(rnd.uniform(*r), 1)
        c = rnd.choice(colors)
        if halo:
            out.append(f'radial-gradient(circle at {x}px {y}px, {c} 0 {rad}px, {c}55 {rad + 0.6:.1f}px, '
                       f'transparent {rad + halo:.1f}px)')
        else:
            out.append(f'radial-gradient(circle at {x}px {y}px, {c} 0 {rad}px, transparent {rad + 0.7:.1f}px)')
    return ',\n    '.join(out)


def particles(sel, name, seed, tile, count, colors, dur, *, up=True, sway=0, r=(1.0, 1.8), halo=0,
              opacity=1.0, blend='normal', mask=None, delay=0):
    """A field of dots drifting vertically forever (seamless: moves exactly one tile)."""
    dy = -tile if up else tile
    top = '0' if up else f'-{tile}px'
    steps = ''
    if sway:
        steps = (f'  25% {{ transform: translate3d({sway}px, {dy * 0.25:.0f}px, 0); }}\n'
                 f'  50% {{ transform: translate3d(0, {dy * 0.5:.0f}px, 0); }}\n'
                 f'  75% {{ transform: translate3d({-sway}px, {dy * 0.75:.0f}px, 0); }}\n')
    m = mask_css(mask) if mask else ''
    return f"""{sel} {{
  left: -{sway + 4}px; right: -{sway + 4}px; top: {top}; height: calc(100vh + {tile}px);
  background-image:
    {dot_field(seed, tile, count, colors, r, halo)};
  background-size: {tile}px {tile}px;
  opacity: {opacity}; mix-blend-mode: {blend};{m}
  animation: {name} {dur}s linear {delay}s infinite;
}}
@keyframes {name} {{
  0% {{ transform: translate3d(0, 0, 0); }}
{steps}  100% {{ transform: translate3d(0, {dy}px, 0); }}
}}
"""


def twinkle(sel, name, seed, tile, count, colors, dur, delay=0, mask=None, low=0.2):
    m = mask_css(mask) if mask else ''
    return f"""{sel} {{
  inset: 0;
  background-image:
    {dot_field(seed, tile, count, colors, (0.8, 1.6))};
  background-size: {tile}px {tile}px;{m}
  animation: {name} {dur}s ease-in-out {delay}s infinite alternate;
}}
@keyframes {name} {{ from {{ opacity: 1; }} to {{ opacity: {low}; }} }}
"""


def mask_css(*masks):
    if len(masks) == 1 and isinstance(masks[0], tuple):
        masks = masks[0]
    joined = ', '.join(masks)
    if len(masks) == 1:
        return f'\n  -webkit-mask-image: {joined}; mask-image: {joined};'
    return (f'\n  -webkit-mask-image: {joined}; mask-image: {joined};'
            f'\n  -webkit-mask-composite: source-in; mask-composite: intersect;')


SKY_ONLY = 'linear-gradient(to bottom, #000 0 40%, transparent 68%)'


def base(p, ring):
    """Shared plumbing for every animated theme."""
    stops = ', '.join(ring + [ring[0]])
    return f"""/* --- Animated layers (CSS only, GPU-composited) --- */
#root {{ z-index: 1; }}
html::before, html::after, body::after {{
  content: ''; position: fixed; pointer-events: none; z-index: 0; will-change: transform, opacity;
}}
#root::before, #root::after {{
  content: ''; position: fixed; pointer-events: none; z-index: -1; will-change: transform, opacity;
}}
/* Opaque panels don't need a live blur of the moving wallpaper behind them. */
[data-app-sidebar], [data-slot='sidebar-inner'], main > header, [role='main'] > header {{
  backdrop-filter: none !important; -webkit-backdrop-filter: none !important;
}}
[aria-label='Thread details'] {{
  background: {p['chrome']}e6 !important; backdrop-filter: none !important;
}}
/* Spinning light ring around the message box while you type. */
@property --t3-spin {{ syntax: '<angle>'; inherits: false; initial-value: 0deg; }}
.group\\/composer-surface::after {{
  content: ''; position: absolute; inset: 0; z-index: 2; pointer-events: none;
  border-radius: inherit; padding: 1.5px;
  background: conic-gradient(from var(--t3-spin), {stops});
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor; mask-composite: exclude;
  opacity: 0; transition: opacity .35s ease;
}}
.group\\/composer-surface:focus-within::after {{ opacity: .9; animation: t3-spin 5s linear infinite; }}
@keyframes t3-spin {{ to {{ --t3-spin: 360deg; }} }}
/* Selected thread gets a slow shimmer. */
[data-app-sidebar] button[aria-current='page'],
[data-app-sidebar] [data-active='true'] {{
  background: linear-gradient(100deg, {p['primary']}26 0%, {p['primary']}0a 40%, {p['primary']}2e 50%, {p['primary']}0a 60%, {p['primary']}1a 100%) 0 0 / 300% 100% !important;
  animation: t3-shimmer 9s ease-in-out infinite;
}}
@keyframes t3-shimmer {{ 0%, 100% {{ background-position: 100% 0; }} 50% {{ background-position: 0 0; }} }}
@media (prefers-reduced-motion: reduce) {{
  html::before, html::after, body::after, #root::before, #root::after,
  .group\\/composer-surface::after, [data-app-sidebar] [aria-current='page'], [data-app-sidebar] [data-active='true'] {{
    animation: none !important;
  }}
}}
"""


# --- themes -------------------------------------------------------------------
def ray_bands(seed, period=512):
    rnd, pos, stops = random.Random(seed), 0, []
    while pos < period:
        wdt = min(rnd.choice([4, 8, 8, 12, 16, 24]), period - pos)
        stops.append(f"#000{rnd.choice('fdb97543')} {pos}px {pos + wdt}px")
        pos += wdt
    return f"repeating-linear-gradient(90deg, {', '.join(stops)})"


def aurora_live(p):
    stripes = ray_bands(71)
    fade = 'linear-gradient(to bottom, transparent 0, #0006 22%, #000 45%, #000 78%, transparent 100%)'
    return f"""html::before {{
  left: -30vw; width: 160vw; top: 2vh; height: 58vh; transform-origin: 50% 100%;
  background:
    radial-gradient(ellipse 18% 38% at 18% 70%, #22f5a0e0, transparent 70%),
    radial-gradient(ellipse 24% 34% at 45% 66%, #34d399d0, transparent 72%),
    radial-gradient(ellipse 18% 40% at 72% 70%, #2dd4bfd0, transparent 70%),
    radial-gradient(ellipse 30% 22% at 46% 42%, #8b5cf699, transparent 70%),
    radial-gradient(ellipse 20% 22% at 80% 44%, #c084fc80, transparent 70%);
  mix-blend-mode: screen;{mask_css(stripes, fade)}
  animation: t3-aurora-a 26s ease-in-out infinite alternate;
}}
@keyframes t3-aurora-a {{
  0%   {{ transform: translateX(-8vw) skewX(-12deg) scaleY(.88); opacity: .5; }}
  45%  {{ transform: translateX(3vw) skewX(7deg) scaleY(1.1); opacity: .9; }}
  100% {{ transform: translateX(10vw) skewX(-5deg) scaleY(.96); opacity: .62; }}
}}
html::after {{
  left: -20vw; width: 140vw; top: 8vh; height: 48vh; transform-origin: 50% 100%;
  background:
    radial-gradient(ellipse 22% 36% at 30% 70%, #2dd4bfc0, transparent 70%),
    radial-gradient(ellipse 16% 40% at 62% 68%, #4ade80b0, transparent 70%),
    radial-gradient(ellipse 26% 24% at 58% 44%, #e879f980, transparent 70%);
  mix-blend-mode: screen;{mask_css(ray_bands(72, 704), fade)}
  animation: t3-aurora-b 34s ease-in-out -9s infinite alternate-reverse;
}}
@keyframes t3-aurora-b {{
  0%   {{ transform: translateX(6vw) skewX(9deg) scaleY(1.05); opacity: .35; }}
  50%  {{ transform: translateX(-4vw) skewX(-6deg) scaleY(.9); opacity: .75; }}
  100% {{ transform: translateX(-10vw) skewX(4deg) scaleY(1.12); opacity: .45; }}
}}
{twinkle('body::after', 't3-tw-a', 11, 380, 14, ['#ffffff', '#dbeafe', '#ccfbf1'], 3.8, mask=SKY_ONLY)}
{twinkle('#root::before', 't3-tw-b', 12, 530, 16, ['#ffffff', '#e0e7ff'], 5.6, delay=-2.5, mask=SKY_ONLY)}
#root::after {{
  top: 10vh; left: 62vw; width: 220px; height: 2px; border-radius: 2px;
  background: linear-gradient(90deg, #ffffff, #b8fff0aa 20%, transparent);
  box-shadow: 0 0 8px #b8fff0aa;
  opacity: 0;
  animation: t3-shooting 14s ease-in 4s infinite;
}}
@keyframes t3-shooting {{
  0%, 90%  {{ opacity: 0; transform: translate(0, 0) rotate(-12deg); }}
  91%      {{ opacity: 1; }}
  96%      {{ opacity: 0; transform: translate(-42vw, 15vh) rotate(-12deg); }}
  100%     {{ opacity: 0; transform: translate(-42vw, 15vh) rotate(-12deg); }}
}}
"""


def neon_drive(p):
    # Perspective floor. Horizon (62vh) = viewport bottom - P*cot(theta): P=71.5vh, theta=62deg.
    line = '#ff3ec8'
    return f"""html::before {{
  left: -100vw; width: 300vw; top: -200vh; height: 320vh;
  transform-origin: 50% 300vh;
  background:
    repeating-linear-gradient(90deg, {line} 0 2px, {line}40 2px 5px, transparent 5px 9vh),
    repeating-linear-gradient(180deg, {line} 0 2px, {line}40 2px 5px, transparent 5px 9vh);
  background-position: 50% 0;{mask_css('linear-gradient(to bottom, transparent 0, #0000 30%, #000c 70%, #000 100%)',
                                     'linear-gradient(90deg, transparent, #000 28%, #000 72%, transparent)')}
  animation: t3-drive 2.6s linear infinite;
}}
@keyframes t3-drive {{
  from {{ transform: perspective(71.5vh) rotateX(62deg) translateY(0); }}
  to   {{ transform: perspective(71.5vh) rotateX(62deg) translateY(9vh); }}
}}
html::after {{
  left: 0; right: 0; top: 50vh; height: 26vh;
  background: radial-gradient(ellipse 55% 45% at 50% 46%, #ff2e88b0, #ff4fd840 45%, transparent 72%);
  mix-blend-mode: screen;
  animation: t3-pulse 3.4s ease-in-out infinite alternate;
}}
@keyframes t3-pulse {{ from {{ opacity: .45; transform: scaleX(.94); }} to {{ opacity: .95; transform: scaleX(1.06); }} }}
body::after {{
  left: 0; right: 0; top: 0; height: 22vh;
  background: linear-gradient(to bottom, transparent, #ff9ef50d 40%, #7ce8ff14 50%, #ff9ef50d 60%, transparent);
  animation: t3-vhs 9s linear infinite;
}}
@keyframes t3-vhs {{ from {{ transform: translateY(-25vh); }} to {{ transform: translateY(125vh); }} }}
{twinkle('#root::before', 't3-tw-a', 21, 420, 16, ['#ffe6ff', '#ffffff', '#7ce8ff'], 2.8,
         mask='linear-gradient(to bottom, #000 0 30%, transparent 55%)')}
"""


def deep_current(p):
    rnd = random.Random(31)
    a, stops = 150.0, []
    while a < 250:
        wdt = rnd.uniform(0.6, 2.6)
        gap = rnd.uniform(1.5, 6.0)
        alpha = rnd.choice(['24', '30', '3d', '1c'])
        stops.append(f'transparent {a:.1f}deg, #9be7ff{alpha} {a + 0.2:.1f}deg {a + wdt:.1f}deg, transparent {a + wdt + 0.3:.1f}deg')
        a += wdt + gap
    rays = ', '.join(stops)
    caustic = file_uri(ASSETS / 'caustics.webp')
    jelly_a = svg_uri(jelly_svg('#67e8f9', '#a5f3fc', 2.8, 1))
    jelly_b = svg_uri(jelly_svg('#c084fc', '#f0abfc', 2.3, 2))
    jelly_c = svg_uri(jelly_svg('#5eead4', '#99f6e4', 2.0, 3))
    return f"""html::before {{
  left: -30vw; top: -20vh; width: 160vw; height: 150vh; transform-origin: 40% 0;
  background: conic-gradient(from 0deg at 40% 0%, transparent 0deg 150deg, {rays}, transparent 250deg 360deg);
  mix-blend-mode: screen;{mask_css('linear-gradient(to bottom, #000 0, #0009 35%, transparent 80%)')}
  animation: t3-rays 17s ease-in-out infinite alternate;
}}
@keyframes t3-rays {{
  0%   {{ transform: rotate(-3.5deg); opacity: .65; }}
  50%  {{ opacity: 1; }}
  100% {{ transform: rotate(3.5deg); opacity: .75; }}
}}
html::after {{
  inset: -10vh -10vw 35vh -10vw;
  background: {caustic} 0 0 / 512px 512px, {caustic} 180px 90px / 736px 736px;
  mix-blend-mode: screen; opacity: .4;{mask_css('linear-gradient(to bottom, #000, #0007 45%, transparent 95%)')}
  animation: t3-caustic 14s ease-in-out infinite alternate;
}}
@keyframes t3-caustic {{
  from {{ transform: translate(0, 0) scale(1); opacity: .28; }}
  to   {{ transform: translate(-96px, 40px) scale(1.05); opacity: .5; }}
}}
{particles('body::after', 't3-snow', 41, 420, 18, ['#bae6fd99', '#e0f2fe77', '#7dd3fc66'], 48, up=False, sway=14, r=(0.8, 1.6))}
#root::before {{
  left: 64vw; top: 0; width: 170px; height: 397px;
  background: {jelly_a} 0 0 / 100% 100% no-repeat;
  mix-blend-mode: screen;
  animation: t3-jelly-a 80s linear -22s infinite, t3-jelly-tilt 11s ease-in-out infinite alternate;
}}
@keyframes t3-jelly-a {{
  0% {{ transform: translate(0, 105vh); }} 25% {{ transform: translate(-4vw, 62vh); }}
  50% {{ transform: translate(2vw, 20vh); }} 75% {{ transform: translate(-2vw, -22vh); }}
  100% {{ transform: translate(0, -70vh); }}
}}
#root::after {{
  left: 12vw; top: 0; width: 330px; height: 520px;
  background:
    {jelly_b} 0 0 / 104px 243px no-repeat,
    {jelly_c} 236px 250px / 76px 177px no-repeat;
  mix-blend-mode: screen;
  animation: t3-jelly-b 105s linear -64s infinite, t3-jelly-tilt 13s ease-in-out -5s infinite alternate;
}}
@keyframes t3-jelly-b {{
  0% {{ transform: translate(0, 105vh); }} 30% {{ transform: translate(5vw, 55vh); }}
  60% {{ transform: translate(-2vw, 5vh); }} 100% {{ transform: translate(3vw, -85vh); }}
}}
@keyframes t3-jelly-tilt {{ from {{ rotate: -5deg; }} to {{ rotate: 6deg; }} }}
"""


def ember_storm(p):
    return f"""html::before {{
  left: -10vw; right: -10vw; top: 25vh; height: 55vh;
  background: radial-gradient(ellipse 50% 40% at 45% 62%, #ff6a1f90, #c2410c40 45%, transparent 75%);
  mix-blend-mode: screen;
  animation: t3-flicker 6.5s ease-in-out infinite;
}}
@keyframes t3-flicker {{
  0%, 100% {{ opacity: .55; }} 12% {{ opacity: .72; }} 27% {{ opacity: .5; }}
  44% {{ opacity: .85; }} 58% {{ opacity: .62; }} 76% {{ opacity: .9; }} 88% {{ opacity: .58; }}
}}
html::after {{
  left: 0; top: 18vh; width: 200vw; height: 60vh;
  background:
    radial-gradient(ellipse 18% 40% at 10% 50%, #0000004d, transparent 70%),
    radial-gradient(ellipse 24% 30% at 32% 35%, #1a0a0640, transparent 70%),
    radial-gradient(ellipse 14% 36% at 61% 60%, #00000047, transparent 70%),
    radial-gradient(ellipse 22% 28% at 84% 42%, #1a0a063d, transparent 70%);
  background-size: 100vw 100%; background-repeat: repeat-x;
  animation: t3-smoke 80s linear infinite;
}}
@keyframes t3-smoke {{ from {{ transform: translateX(0); }} to {{ transform: translateX(-100vw); }} }}
{particles('body::after', 't3-embers-a', 51, 460, 16, ['#ffb066', '#ff8a3c', '#ffd27a', '#ff6a1f'], 12, up=True, sway=26, r=(1.0, 2.0), halo=6, blend='screen')}
{particles('#root::before', 't3-embers-b', 52, 300, 14, ['#ff9a3c', '#ffc47a'], 7.5, up=True, sway=12, r=(0.7, 1.3), halo=3, opacity=0.8, blend='screen')}
{particles('#root::after', 't3-embers-c', 53, 900, 5, ['#ff7a2e', '#ffb35c'], 21, up=True, sway=40, r=(2.5, 4.0), halo=18, opacity=0.55, blend='screen')}
"""


def nebula_drift(p):
    return f"""html::before {{
  left: 50%; top: 50%; width: 170vmax; height: 170vmax; margin: -85vmax 0 0 -85vmax;
  background:
    radial-gradient(circle at 35% 40%, #d9468a66, transparent 22%),
    radial-gradient(circle at 62% 55%, #5b3df566, transparent 20%),
    radial-gradient(circle at 45% 65%, #9333ea4d, transparent 18%),
    radial-gradient(circle at 58% 34%, #db277740, transparent 16%);
  mix-blend-mode: screen;
  animation: t3-spin-a 260s linear infinite, t3-breathe-a 21s ease-in-out infinite alternate;
}}
@keyframes t3-spin-a {{ to {{ rotate: 360deg; }} }}
@keyframes t3-breathe-a {{ from {{ scale: 1; opacity: .55; }} to {{ scale: 1.12; opacity: .95; }} }}
html::after {{
  left: 50%; top: 50%; width: 150vmax; height: 150vmax; margin: -75vmax 0 0 -75vmax;
  background:
    radial-gradient(circle at 60% 40%, #14b8a64d, transparent 20%),
    radial-gradient(circle at 38% 60%, #f59e0b2e, transparent 16%),
    radial-gradient(circle at 52% 52%, #6366f14d, transparent 24%);
  mix-blend-mode: screen;
  animation: t3-spin-b 190s linear infinite, t3-breathe-b 27s ease-in-out -8s infinite alternate;
}}
@keyframes t3-spin-b {{ to {{ rotate: -360deg; }} }}
@keyframes t3-breathe-b {{ from {{ scale: 1.1; opacity: .4; }} to {{ scale: .95; opacity: .85; }} }}
{twinkle('body::after', 't3-tw-a', 61, 360, 15, ['#ffffff', '#f5d0fe', '#c7d2fe'], 3.2)}
{twinkle('#root::before', 't3-tw-b', 62, 500, 17, ['#ffffff', '#a5f3fc', '#fde68a'], 4.9, delay=-2)}
#root::after {{
  left: 0; top: 0; width: calc(100vw + 700px); height: 100vh;
  background-image:
    {dot_field(63, 700, 7, ['#ffffff', '#e9d5ff', '#bae6fd'], (1.4, 2.0), halo=7)};
  background-size: 700px 700px;
  animation: t3-parallax 150s linear infinite;
}}
@keyframes t3-parallax {{ from {{ transform: translateX(0); }} to {{ transform: translateX(-700px); }} }}
"""


def prism_flow(p):
    def blob(sel, name, color, size, x, y, path, dur, delay=0):
        kf = '\n'.join(f'  {pct}% {{ transform: translate({dx}vw, {dy}vh) scale({s}); }}' for pct, dx, dy, s in path)
        return f"""{sel} {{
  left: calc({x}vw - {size / 2}vmax); top: calc({y}vh - {size / 2}vmax); width: {size}vmax; height: {size}vmax;
  background: radial-gradient(circle, {color} 0, {color[:7]}55 30%, transparent 68%);
  mix-blend-mode: screen; opacity: .85;
  animation: {name} {dur}s ease-in-out {delay}s infinite alternate;
}}
@keyframes {name} {{
{kf}
}}
"""
    bayer = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
    rects = ''.join(f"<rect x='{c * 4}' y='{r * 4}' width='4' height='4' fill-opacity='{bayer[r][c] / 16 * 0.42:.3f}'/>"
                    for r in range(4) for c in range(4))
    svg = f"<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16'>{rects}</svg>"
    svg = svg.replace('<', '%3C').replace('>', '%3E').replace('#', '%23')
    return (
        blob('html::before', 't3-blob-a', '#8b5cf6ff', 70, 25, 30,
             [(0, 0, 0, 1), (33, 18, 22, 1.15), (66, 34, -6, .9), (100, 10, 40, 1.05)], 23)
        + blob('html::after', 't3-blob-b', '#fb7185ee', 60, 80, 25,
               [(0, 0, 0, 1), (40, -30, 30, 1.2), (100, -12, 55, .9)], 29, -6)
        + blob('body::after', 't3-blob-c', '#22d3eedd', 55, 65, 85,
               [(0, 0, 0, 1.1), (50, -40, -35, .9), (100, -15, -60, 1.15)], 31, -11)
        + blob('#root::before', 't3-blob-d', '#fbbf24b0', 40, 15, 85,
               [(0, 0, 0, .9), (45, 30, -20, 1.2), (100, 55, -50, 1)], 37, -3)
        + f"""/* Ordered-dither screen over the moving colour, matching the wallpaper's pixel texture. */
#root::after {{
  inset: 0; will-change: auto;
  background: url("data:image/svg+xml,{svg}") 0 0 / 16px 16px;
  image-rendering: pixelated;
}}
""")


ANIMATED = {
    'aurora-live': (dict(THEMES['aurora'], title='Aurora Live',
                         blurb='Animated: swaying northern lights, twinkling stars, the odd shooting star.'),
                    aurora_live, ['#22f5a0', '#2dd4bf', '#8b5cf6']),
    'neon-drive': (dict(THEMES['synthwave'], title='Neon Drive',
                        blurb='Animated: endless neon grid, pulsing horizon, VHS tracking glow.'),
                   neon_drive, ['#ff5fd2', '#7ce8ff', '#ffe66d']),
    'deep-current': (dict(THEMES['abyss'], title='Deep Current',
                          blurb='Animated: pulsing jellyfish drifting up through swaying sunbeams, rippling caustics, marine snow.'),
                     deep_current, ['#56d8f0', '#5eead4', '#c084fc']),
    'ember-storm': (dict(THEMES['ember-forge'], title='Ember Storm',
                         blurb='Animated: rising sparks, flickering forge glow, drifting smoke.'),
                    ember_storm, ['#ff8a4c', '#ffd27a', '#ff3d1f']),
    'nebula-drift': (dict(THEMES['synthwave'], title='Nebula Drift',
                          blurb='Animated: slowly turning nebula, twinkling and drifting stars.',
                          fg='#efeafc', muted='#bdb3d8', chrome='#0a0716', sidebar='#0c0919', canvas='#0d081c80',
                          card='#161029d4', popover='#18112df5', raised='#21183cb8', composer='#1d1535b3',
                          composer_bg='#130d248c', muted_bg='#1e1734', secondary='#231a3ec9', secondary_fg='#e9e3f8',
                          primary='#e879f9', primary_fg='#1c0620', accent='#e879f91f', link='#a5b4fc',
                          code='#100b1ded', assistant='#110c20eb', user='#2a1f46ed', message='#261c40bd',
                          tint='#f5d0fe', select='#e879f94d'),
                     nebula_drift, ['#e879f9', '#818cf8', '#2dd4bf']),
    'prism-flow': (dict(THEMES['synthwave'], title='Prism Flow',
                        blurb='Animated: a slow lava-lamp of colour behind a pixel-dither screen.',
                        fg='#eeedf5', muted='#b6b4c8', chrome='#0b0a12', sidebar='#0d0c15', canvas='#0e0c1880',
                        card='#16141fd4', popover='#181622f5', raised='#201d2cb8', composer='#1c1a28b3',
                        composer_bg='#12101c8c', muted_bg='#1c1a27', secondary='#22202fc9', secondary_fg='#e7e6f0',
                        primary='#a78bfa', primary_fg='#130b26', accent='#a78bfa1f', link='#f0abfc',
                        code='#100e18ed', assistant='#110f1aeb', user='#29243ced', message='#252137bd',
                        tint='#ddd6fe', select='#a78bfa4d'),
                   prism_flow, ['#a78bfa', '#fb7185', '#22d3ee', '#fbbf24']),
}


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    for name, (palette, layers, ring) in ANIMATED.items():
        css = build(name, palette, base(palette, ring) + layers(palette))
        css.encode('ascii')  # theme.py reads with the platform default codec
        (root / name).mkdir(exist_ok=True)
        (root / name / 'theme.css').write_text(css, encoding='utf-8')
        print('wrote', name, len(css), 'bytes')
