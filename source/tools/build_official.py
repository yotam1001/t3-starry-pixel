"""Build the Orbital Glass pack as official T3 Code themes.

T3 now has a themes feature: a theme is JSON with a palette (`canvas`, `accent`, `colors` roles)
plus up to 20,000 characters of CSS, published with T3's own theme tool. That replaces the
old approach of patching main.css inside server.asar.

    python build_official.py            # writes out/<name>.json for every theme + a size report

What changed from the patched version:
  * Colors go through official roles, so the terminal, search highlights, errors, sidebar rows,
    tooltips and other spots the patch could not reach now match the theme.
  * CSS only uses T3's stable selectors (data-slot / data-* hooks), so updates won't break it.
  * The wallpaper is re-encoded to fit the 20k budget alongside the CSS.
  * Koi Pond and Deep Current use lighter creatures and a smaller caustics texture to fit.
"""
import base64
import io
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
PACK = HERE.parent / 'themes'
sys.path.insert(0, str(PACK / 'tools'))

import animated  # noqa: E402
import animated2  # noqa: E402
import creatures  # noqa: E402
from build_css import THEMES  # noqa: E402

LIMIT = 20000
GRAIN = creatures.svg_uri(
    "<svg xmlns='http://www.w3.org/2000/svg' width='180' height='180'><filter id='n'>"
    "<feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2' stitchTiles='stitch'/>"
    "<feColorMatrix values='0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 .07 0'/></filter>"
    "<rect width='100%' height='100%' filter='url(#n)'/></svg>")


# --- small helpers ----------------------------------------------------------------
def webp_bytes(img, quality):
    buf = io.BytesIO()
    img.save(buf, 'WEBP', quality=quality, method=6)
    return buf.getvalue()


def small_uri(path, width=256, quality=30):
    """Recompress an embedded texture (AVIF, flattened on black; the layers use screen blend)."""
    img = Image.open(path).convert('RGBA')
    flat = Image.new('RGBA', img.size, '#000')
    flat.alpha_composite(img)
    flat = flat.convert('RGB').resize((width, round(img.height * width / img.width)), Image.LANCZOS)
    buf = io.BytesIO()
    flat.save(buf, 'AVIF', quality=quality, speed=2)
    return f'url("data:image/avif;base64,{base64.b64encode(buf.getvalue()).decode()}")'


def lean_svg_uri(svg):
    """Like creatures.svg_uri, but tighter: Chromium only needs % and # escaped."""
    svg = re.sub(r'\s+', ' ', svg)
    svg = re.sub(r'>\s+<', '><', svg)
    svg = re.sub(r'([A-Za-z]) (?=-?\d)', r'\1', svg)   # "M 12 58" -> "M12 58"
    svg = re.sub(r', ', ',', svg)
    svg = svg.replace('%', '%25').replace('#', '%23').replace('"', "'")
    return f'url("data:image/svg+xml,{svg}")'


def lean_jelly():
    """creatures.jelly_svg with fewer tentacles, to fit the 20k CSS budget."""
    svg = creatures.jelly_svg('#67e8f9', '#a5f3fc', 2.6, 1)
    paths = re.findall(r"<path d='M \d+ 58 C.*?</path>", svg, flags=re.S)
    for i, path in enumerate(paths):
        if i % 2:
            svg = svg.replace(path, '')
    return svg


# Lighter assets so the animated themes fit: AVIF caustics, tighter SVG encoding,
# the simpler SMIL koi from creatures.py, and one shared jellyfish (tinted with hue-rotate).
animated.file_uri = animated2.file_uri = lambda path, mime='image/webp': small_uri(path)
animated.svg_uri = animated2.svg_uri = creatures.svg_uri = lean_svg_uri
animated2.koi_svg = creatures.koi_svg
_jelly = lean_jelly()
animated.jelly_svg = lambda *a, **k: _jelly


def minify(css):
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    css = re.sub(r'\s+', ' ', css)
    css = re.sub(r'\s*([{};,>])\s*', r'\1', css)
    css = re.sub(r'(?<=[{;])\s*([a-z-]+)\s*:\s*', r'\1:', css)
    css = re.sub(r'(?<![\w.#-])0\.(\d)', r'.\1', css)
    css = re.sub(r'#([0-9a-fA-F])\1([0-9a-fA-F])\2([0-9a-fA-F])\3(?![0-9a-fA-F])', r'#\1\2\3', css)
    css = css.replace(';}', '}').replace(' !important', '!important')
    return css.strip()


def hoist_images(css):
    """Embed each repeated data: image once, as a custom property on :root."""
    uris = re.findall(r'url\("data:[^"]+"\)', css)
    defs = []
    for i, uri in enumerate(dict.fromkeys(u for u in uris if uris.count(u) > 1)):
        css = css.replace(uri, f'var(--og{i})')
        defs.append(f'--og{i}:{uri}')
    return (f':root{{{";".join(defs)}}}' if defs else '') + css


def base64_svgs(css):
    """T3 drops any declaration whose value has `url(` not followed by data: or # (its filter also
    sees the url(%23id) references inside percent-encoded SVGs). Base64 those SVGs instead."""
    from urllib.parse import unquote

    def enc(m):
        svg = unquote(m.group(1))
        if 'url(' not in svg:
            return m.group(0)
        return f'url("data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}")'
    return re.sub(r'url\("data:image/svg\+xml,([^"]*)"\)', enc, css)


T3_REJECTS = re.compile(r"""image-set\(|\bsrc\(|url\((?![ \t\n\f\r]*["']?(?:data:|#))""", re.I)


def assert_t3_keeps(name, css):
    """Mirror T3's theme CSS filter so nothing gets silently dropped."""
    assert chr(92) not in css, f'{name}: backslash in CSS'
    m = T3_REJECTS.search(css)
    assert not m, f'{name}: T3 would drop: {css[max(0, m.start() - 80):m.start() + 40]}'


SELECTORS = [  # old patch selectors -> T3's stable hooks
    (r"main > header, \[role='main'\] > header", '[data-chat-header]'),
    (r"\[data-app-sidebar\]", '[data-slot=sidebar]'),
    (r"\.group\\\\?/composer-surface", '[data-slot=composer-host]'),
    (r"\[aria-label='Thread details'\]", '[data-thread-details-card]'),
    (r"\[aria-label='Conversation'\]", '[data-workspace-area=conversation]'),
]


def restable(css):
    for old, new in SELECTORS:
        css = re.sub(old, new, css)
    return css


# --- palette -> official color roles ----------------------------------------------
def roles(p):
    pr, fg, mu, chrome, side = p['primary'], p['fg'], p['muted'], p['chrome'], p['sidebar']
    sec = p['secondary'][:7]
    return {
        'canvas': p['canvas'], 'chrome': chrome,
        'toolbar': chrome + 'b3', 'toolbarForeground': fg, 'toolbarBorder': '#ffffff14',
        'toolbarControl': sec + 'a6', 'toolbarControlForeground': fg, 'toolbarControlHover': sec,
        'surface': p['card'], 'surfaceRaised': p['raised'], 'surfaceOverlay': p['popover'],
        'text': fg, 'textMuted': mu, 'border': '#ffffff17', 'input': '#ffffff26', 'focus': pr,
        'accent': pr, 'accentForeground': p['primary_fg'],
        'secondary': p['secondary'], 'secondaryForeground': p['secondary_fg'],
        'muted': p['muted_bg'], 'mutedForeground': mu,
        'placeholder': mu + 'a6', 'secondaryLabel': mu, 'iconMuted': mu + 'cc',
        'error': '#f87171', 'errorForeground': p.get('error_fg', '#fca5a5'), 'errorSurface': '#f871711f',
        'warning': '#fbbf24', 'warningForeground': p.get('warning_fg', '#fcd34d'), 'warningSurface': '#fbbf241a',
        'update': pr, 'updateForeground': p['primary_fg'], 'updateSurface': pr + '1f',
        'accentSurface': pr + '1f', 'accentSurfaceForeground': fg,
        'messageSurface': p['user'], 'messageForeground': fg,
        'messageAction': '#ffffff0d', 'messageActionForeground': mu, 'messageActionHover': '#ffffff1a',
        'codeBackground': p['code'], 'codeForeground': fg,
        'searchMatchBackground': pr + '40', 'searchMatchForeground': fg,
        'searchMatchActiveBackground': pr, 'searchMatchActiveForeground': p['primary_fg'],
        'sidebar': side, 'sidebarForeground': fg, 'sidebarMutedForeground': mu,
        'sidebarControlSurface': sec + 'b3', 'sidebarRowHover': '#ffffff0b',
        'sidebarRowActive': pr + '24', 'sidebarRowSelected': pr + '1a', 'sidebarBorder': '#ffffff10',
        'terminalBackground': chrome, 'terminalForeground': fg, 'terminalCursor': pr,
        'terminalSelection': pr + '40', 'terminalScrollbar': '#ffffff1f', 'terminalScrollbarHover': pr + '80',
    }


# --- CSS ------------------------------------------------------------------------------
def base_css(p, animated_ring=None):
    pr, fg, chrome, side = p['primary'], p['fg'], p['chrome'], p['sidebar']
    pop = p['popover'][:7]
    css = f"""
html {{ background: {chrome} !important; }}
body {{
  background:
    radial-gradient(130% 95% at 50% 35%, transparent 55%, #00000073 100%),
    linear-gradient(180deg, #0000000a, #00000033),
    {GRAIN} 0 0 / 180px 180px,
    url("__BG__") center / cover fixed no-repeat, {chrome} !important;
  color: {fg} !important;
}}
#root {{ position: relative; isolation: isolate; background: transparent !important; }}
#root > div, main, [role=main], [data-workspace-area=conversation], .messages-timeline-scroll {{
  background-color: transparent !important;
}}
/* Panels: near-opaque sidebar, glass header, soft hairlines. */
[data-slot=sidebar-inner] {{
  background: linear-gradient(180deg, {side}f7, {side}eb) !important;
  backdrop-filter: blur(30px) saturate(120%);
  box-shadow: inset -1px 0 #ffffff0d;
}}
[data-chat-header] {{
  background: linear-gradient(180deg, {side}e0, {side}b8) !important;
  backdrop-filter: blur(24px) saturate(120%);
  border-bottom: 1px solid #ffffff0d !important;
}}
[data-thread-details-card] {{
  background: {chrome}cc !important; backdrop-filter: blur(24px) saturate(110%);
  border: 1px solid #ffffff12 !important; border-radius: 16px;
}}
[data-thread-terminal-drawer] {{ border-top: 1px solid {pr}26 !important; }}
/* Selected thread: accent bar + wash. */
[data-thread-item] [aria-current]:not([aria-current=false]) {{
  background: linear-gradient(90deg, {pr}2b, {pr}08 85%) !important;
  box-shadow: inset 2px 0 {pr}, inset 0 1px #ffffff08;
  border-radius: 8px;
}}
[data-thread-item] [role=button] {{ transition: background-color .15s ease; }}
/* Composer: frosted card that lights up while typing. */
[data-slot=composer-host] {{
  position: relative;
  background: linear-gradient(135deg, {p['tint']}10, #fff0 55%), {p['composer_bg']} !important;
  backdrop-filter: blur(40px) saturate(140%);
  border: 1px solid #ffffff1a !important; border-radius: 24px !important;
  box-shadow: 0 18px 50px #00000059, inset 0 1px #ffffff14;
  transition: box-shadow .3s ease, border-color .3s ease;
}}
[data-slot=composer-host]:focus-within {{
  border-color: {pr}5c !important;
  box-shadow: 0 18px 50px #00000059, 0 0 0 3px {pr}1a, 0 0 42px {pr}24, inset 0 1px #ffffff14;
}}
/* Messages: readable cards over the wallpaper. */
[data-message-role=assistant] .chat-markdown {{
  background: linear-gradient(180deg, #ffffff06, #fff0 40%), {p['assistant']} !important;
  color: {fg} !important; --foreground: {fg}; --muted-foreground: {p['muted']};
  padding: 16px 20px; border: 1px solid #ffffff12; border-top-color: {pr}40;
  border-radius: 18px; box-shadow: 0 10px 32px #00000038; overflow-wrap: anywhere;
}}
.chat-markdown :is(h1, h2, h3, h4, strong) {{ color: #fff; }}
.chat-markdown a {{ color: {p['link']} !important; text-decoration-color: {p['link']}80; }}
.chat-markdown :not(pre) > code {{ color: {p['link']}; background: {pr}17; border-radius: 5px; }}
.chat-markdown-codeblock {{
  border: 1px solid #ffffff12; border-radius: 12px; overflow: hidden;
  box-shadow: inset 0 1px #ffffff0a, 0 6px 20px #00000026;
}}
[data-user-message-bubble] {{
  background: linear-gradient(135deg, {pr}26, {pr}0d 70%), {p['user']} !important;
  border: 1px solid {pr}33 !important; box-shadow: 0 8px 26px #00000033;
}}
/* Popups and controls. */
[data-slot=dialog-popup], [data-slot=popover-popup], [data-slot=menu-popup] {{
  background: {pop}ed !important; color: {fg} !important;
  backdrop-filter: blur(28px) saturate(130%);
  border: 1px solid #ffffff1a !important;
  box-shadow: 0 24px 64px #00000073, inset 0 1px #ffffff0d !important;
}}
[data-slot=tooltip-popup] {{ background: {chrome}f2 !important; color: {fg} !important; border: 1px solid {pr}33; }}
[data-slot=input]:focus-visible, [data-slot=select-trigger]:focus-visible {{ box-shadow: 0 0 0 3px {pr}26 !important; }}
svg.lucide {{ stroke-width: 1.8; }}
::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-thumb {{ background: #ffffff1f; border: 2px solid transparent; border-radius: 9px; background-clip: padding-box; }}
::-webkit-scrollbar-thumb:hover {{ background-color: {pr}80; }}
[data-slot=scroll-area-thumb] {{ background: #ffffff29 !important; }}
::selection {{ background: {p['select']}; color: #fff; }}
"""
    if animated_ring:
        stops = ', '.join(animated_ring + [animated_ring[0]])
        css += f"""
/* Animated layers sit between the wallpaper and the UI; only transform/opacity animate. */
#root {{ z-index: 1; }}
html::before, html::after, body::after {{ content: ''; position: fixed; pointer-events: none; z-index: 0; will-change: transform, opacity; }}
#root::before, #root::after {{ content: ''; position: fixed; pointer-events: none; z-index: -1; will-change: transform, opacity; }}
[data-slot=sidebar-inner], [data-chat-header] {{ backdrop-filter: none !important; }}
@property --og-spin {{ syntax: '<angle>'; inherits: false; initial-value: 0deg; }}
[data-slot=composer-host]::after {{
  content: ''; position: absolute; inset: -1px; z-index: 2; pointer-events: none;
  border-radius: inherit; padding: 1.5px;
  background: conic-gradient(from var(--og-spin), {stops});
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor; mask-composite: exclude;
  opacity: 0; transition: opacity .35s ease;
}}
[data-slot=composer-host]:focus-within::after {{ opacity: .9; animation: og-spin 5s linear infinite; }}
@keyframes og-spin {{ to {{ --og-spin: 360deg; }} }}
@media (prefers-reduced-motion: reduce) {{
  html::before, html::after, body::after, #root::before, #root::after, [data-slot=composer-host]::after {{ animation: none !important; }}
}}
"""
    return css


def strip_block(css, selector):
    """Remove `selector { ... }` (one level of braces) from generated layer CSS."""
    return re.sub(re.escape(selector) + r'\s*\{[^{}]*\}', '', css)


# --- theme registry -----------------------------------------------------------------
ORBITAL = dict(  # the original Orbital Glass (revision 5) palette
    title='Orbital Glass', blurb='Space shuttle on the horizon, charcoal glass, blue accents.',
    fg='#edeef0', muted='#b9bcc2', chrome='#101112', sidebar='#141414', canvas='#11131580',
    card='#181a1dd4', popover='#1b1c20f5', raised='#202329b8', composer='#25282db3', composer_bg='#171b208c',
    muted_bg='#24262b', secondary='#25282ec9', secondary_fg='#e5e7ec', primary='#80adf5', primary_fg='#10151c',
    accent='#a0bce51a', link='#a9ccff', code='#141519ed', assistant='#14171aeb', user='#252b34ed',
    message='#2a2d34bd', tint='#ffffff', select='#80adf54d')



# --- Starry Swirl (Van Gogh inspired; wallpaper painted by themes/tools/starry.py) ----------
STARRY = dict(
    title='Starry Swirl', blurb='Animated: a Van Gogh night, turning swirls, breathing stars and moon.',
    fg='#eef1fa', muted='#b3bdd8', chrome='#0a1330', sidebar='#0b1431', canvas='#0d1a4080',
    card='#111d44d4', popover='#13204af5', raised='#1a2a5ab8', composer='#172656b3', composer_bg='#0f1b428c',
    muted_bg='#18264f', secondary='#1b2b5cc9', secondary_fg='#e6ebf8', primary='#f4c84a', primary_fg='#1a1404',
    accent='#f4c84a1f', link='#ffd97a', code='#0b1433ed', assistant='#0c1638eb', user='#1d2d63ed',
    message='#1a2a5cbd', tint='#ffe9a8', select='#f4c84a4d', warning_fg='#ffd97a')


def starry_layers(p):
    import starry
    def swirl(sel, name, x, y, size, dur, direction, alpha):
        return f"""{sel} {{
  left: calc({x * 100:.0f}vw - {size / 2}vw); top: calc({y * 100:.0f}vh - {size / 2}vw);
  width: {size}vw; height: {size}vw; border-radius: 50%;
  background: repeating-conic-gradient(from 0deg, #e8eef800 0deg 9deg, #e8eef8{alpha} 12deg 15deg, #f2e7b000 19deg 26deg, #c9dcf4{alpha} 29deg 31deg, #e8eef800 34deg 40deg);
  mask-image: radial-gradient(closest-side, transparent 18%, #000 42%, #000 62%, transparent 100%);
  mix-blend-mode: screen;
  animation: {name} {dur}s linear infinite{' reverse' if direction < 0 else ''};
}}
@keyframes {name} {{ to {{ rotate: 360deg; }} }}
"""

    def glows(stars):
        return ', '.join(f'radial-gradient(circle {r * 1.6:.0f}px at {x * 100:.1f}% {y * 100:.1f}%, #fff6c8d9, #fbe48a66 30%, transparent 70%)'
                         for x, y, r in stars)
    a, b = starry.STARS[0::2], starry.STARS[1::2]
    mx, my, mr = starry.MOON
    return (swirl('html::before', 'og-swirl-a', .47, .33, 30, 140, 1, '33')
            + swirl('html::after', 'og-swirl-b', .63, .40, 19, 95, -1, '2b')
            + f"""#root::before {{ inset: 0; background: {glows(a)}; mix-blend-mode: screen;
  animation: og-twinkle 4.2s ease-in-out infinite alternate; }}
#root::after {{ inset: 0; background: {glows(b)}; mix-blend-mode: screen;
  animation: og-twinkle 5.6s ease-in-out -2.4s infinite alternate; }}
@keyframes og-twinkle {{ from {{ opacity: .25; }} to {{ opacity: 1; }} }}
body::after {{ inset: 0; mix-blend-mode: screen;
  background: radial-gradient(circle {mr * 2.6:.0f}px at {mx * 100:.0f}% {my * 100:.0f}%, #f7c94866, #f4c84a1f 45%, transparent 70%);
  animation: og-moon 7s ease-in-out infinite alternate; }}
@keyframes og-moon {{ from {{ opacity: .45; }} to {{ opacity: 1; }} }}
""")


def registry():
    out = {'orbital-glass': (ORBITAL, None, None)}
    out.update({k: (v, None, None) for k, v in THEMES.items()})
    out.update(animated.ANIMATED)
    out.update(animated2.ANIMATED2)
    out['starry-swirl'] = (STARRY, starry_layers, ['#f4c84a', '#86aee3', '#ffe9a8', '#3d72c4'])
    return out


def layers_for(name, fn, p):
    css = fn(p)
    if name == 'deep-current':
        css += '#root::after { filter: hue-rotate(75deg) saturate(1.2); }'
        css = strip_block(css, 'html::after')  # caustics are baked into the wallpaper instead
    if name == 'deep-current':
        css += '#root::after { filter: hue-rotate(75deg) saturate(1.2); }'
        css = strip_block(css, 'html::after')  # caustics are baked into the wallpaper instead
    if name == 'koi-pond':
        # Lily pads are baked into the wallpaper instead of a 17 KB overlay layer.
        css = strip_block(css, '#root::after')
        css = strip_block(css, '#root::before')  # caustics are baked into the wallpaper instead
        # Same stroke-and-coast easing, set once on the animation instead of on every keyframe.
        css = css.replace('; animation-timing-function: cubic-bezier(.25, .6, .45, 1);', ';')
        css = re.sub(r'(animation: t3-koi-\w) (\d+)s linear', r'\1 \2s cubic-bezier(.25,.6,.45,1)', css)
        css = re.sub(r'@keyframes t3-bob\s*\{[^{}]*\{[^{}]*\}[^{}]*\{[^{}]*\}\s*\}', '', css)
    return restable(css)


def wallpaper(name):
    img = Image.open(PACK / name / 'background.webp').convert('RGBA')
    overlay = PACK / name / 'overlay.webp'
    if overlay.exists():
        ov = Image.open(overlay).convert('RGBA').resize(img.size, Image.NEAREST)
        img = Image.alpha_composite(img, ov)
    if name in CAUSTIC_BAKE:
        img = bake_caustics(img.convert('RGB'), CAUSTIC_BAKE[name])
    return img.convert('RGB')


CAUSTIC_BAKE = {'deep-current': .38, 'koi-pond': .13}


def bake_caustics(img, strength):
    """Screen the caustics tile over the wallpaper, fading out toward the bottom."""
    from PIL import ImageChops
    tile = Image.open(PACK / 'tools' / 'assets' / 'caustics.webp').convert('RGBA')
    flat = Image.new('RGBA', tile.size, '#000')
    flat.alpha_composite(tile)
    tile = flat.convert('RGB')
    layer = Image.new('RGB', img.size)
    for x in range(0, img.width, tile.width):
        for y in range(0, img.height, tile.height):
            layer.paste(tile, (x, y))
    fade = Image.linear_gradient('L').resize(img.size).point(lambda v: int((255 - v) * strength))
    return Image.composite(ImageChops.screen(img, layer), img, fade)


def fit_image(img, budget):
    """Sharpest AVIF wallpaper whose data: URI fits `budget` characters.

    The source wallpapers carry dithering grain, which costs most of the bytes. It is smoothed
    away here and put back as a resolution-independent SVG noise layer in CSS (GRAIN).
    """
    prefix = len('data:image/avif;base64,')
    img = img.filter(ImageFilter.GaussianBlur(1.4))
    fallback = None
    for width in (1600, 1440, 1280, 1120, 960, 832, 720, 640):
        small = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
        for q in range(70, 9, -3):
            buf = io.BytesIO()
            small.save(buf, 'AVIF', quality=q, speed=5)
            data = buf.getvalue()
            if prefix + (len(data) + 2) // 3 * 4 <= budget:
                if q >= 34:
                    return data, width, q
                if not fallback or q > fallback[2] + 6:
                    fallback = (data, width, q)
                break
    if not fallback:
        raise SystemExit(f'wallpaper does not fit in {budget} chars')
    return fallback


def build(name, p, fn, ring):
    css = base_css(p, ring) + (layers_for(name, fn, p) if fn else '')
    css = hoist_images(base64_svgs(minify(css)))
    header = f'/* Orbital Glass: {p["title"]} */'
    budget = LIMIT - len(header) - len(css) + len('__BG__') - 40
    data, width, q = fit_image(wallpaper(name), budget)
    css = header + css.replace('__BG__', 'data:image/avif;base64,' + base64.b64encode(data).decode())
    assert len(css) <= LIMIT, (name, len(css))
    assert_t3_keeps(name, css)
    theme = {
        'version': 1, 'name': p['title'], 'appearance': 'dark',
        'canvas': p['chrome'], 'accent': p['primary'], 'colors': roles(p), 'css': css,
    }
    return theme, dict(css=len(css), bg_width=width, bg_q=q, bg_bytes=len(data), animated=bool(fn))


def main():
    out = HERE / 'out'
    out.mkdir(exist_ok=True)
    only = set(sys.argv[1:])
    for name, (p, fn, ring) in registry().items():
        if only and name not in only:
            continue
        theme, info = build(name, p, fn, ring)
        (out / f'{name}.json').write_text(json.dumps(theme, indent=1), encoding='utf-8')
        print(f'{name:15} {info}')


if __name__ == '__main__':
    main()
