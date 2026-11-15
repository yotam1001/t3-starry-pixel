"""Build theme.css for each theme in the pack from a palette.

The structure mirrors Orbital Glass revision 5 (same selectors), so every theme
covers exactly what the original does. The first line keeps the
'/* T3 Orbital Glass.' marker that theme.py uses to detect an installed theme.
"""
from pathlib import Path
from string import Template

THEMES = {
    'ember-forge': dict(
        title='Ember Forge', blurb='Volcanic ridges, molten veins and drifting embers.',
        fg='#f3ece8', muted='#c4b5ac', chrome='#120c0a', sidebar='#140d0b', canvas='#1a0f0b80',
        card='#211612d4', popover='#231713f5', raised='#2c1d17b8', composer='#2a1a14b3', composer_bg='#1d120e8c',
        muted_bg='#2a1c17', secondary='#2e2019c9', secondary_fg='#eee3dc',
        primary='#ff8a4c', primary_fg='#1c0d06', accent='#ff8a4c1f', link='#ffb184',
        code='#160e0bed', assistant='#170f0ceb', user='#33211aed', message='#2f1f19bd',
        tint='#ffd2b0', select='#ff8a4c55'),
    'aurora': dict(
        title='Aurora', blurb='Northern lights over a dark ridge line.',
        fg='#e8f1f2', muted='#a9bcc4', chrome='#070d12', sidebar='#09111a', canvas='#06121c80',
        card='#0e1a24d4', popover='#0f1c27f5', raised='#152532b8', composer='#13212db3', composer_bg='#0b16208c',
        muted_bg='#142230', secondary='#162634c9', secondary_fg='#dfeaee',
        primary='#4ff0b4', primary_fg='#04140e', accent='#4ff0b41c', link='#8ef5d0',
        code='#08121aed', assistant='#0a141ceb', user='#182a3aed', message='#15283abd',
        tint='#b8fff0', select='#4ff0b44d'),
    'synthwave': dict(
        title='Synthwave', blurb='Neon sunset, chrome grid, 1986 forever.',
        fg='#f6eafd', muted='#c6b0d6', chrome='#0f0619', sidebar='#12071e', canvas='#14062480',
        card='#1d0d2ed4', popover='#200f33f5', raised='#2a1440b8', composer='#25103ab3', composer_bg='#1a0a2b8c',
        muted_bg='#26123a', secondary='#2b1542c9', secondary_fg='#f0e2fa',
        primary='#ff5fd2', primary_fg='#1d0518', accent='#ff5fd21f', link='#7ce8ff',
        code='#13081fed', assistant='#150a22eb', user='#341848ed', message='#2f1544bd',
        tint='#ffc2f1', select='#ff5fd255'),
    'abyss': dict(
        title='Abyss', blurb='Sunbeams into the deep, bioluminescent drifters.',
        fg='#e6f4fa', muted='#a3bfcc', chrome='#050d14', sidebar='#06101a', canvas='#04121e80',
        card='#0b1a27d4', popover='#0c1d2bf5', raised='#122636b8', composer='#0f2231b3', composer_bg='#0817238c',
        muted_bg='#102232', secondary='#132838c9', secondary_fg='#dcecf4',
        primary='#56d8f0', primary_fg='#03141a', accent='#56d8f01c', link='#8de6ff',
        code='#06121bed', assistant='#08141feb', user='#132d40ed', message='#12293bbd',
        tint='#b5f1ff', select='#56d8f04d'),
    'dune': dict(
        title='Dune', blurb='Moonrise over the sand sea at dusk.',
        fg='#f5ede6', muted='#c9b8ab', chrome='#140d10', sidebar='#160e12', canvas='#1c111480',
        card='#24171ad4', popover='#26181cf5', raised='#301f22b8', composer='#2c1c1fb3', composer_bg='#1f13168c',
        muted_bg='#2c1d21', secondary='#33222ac9', secondary_fg='#f0e6de',
        primary='#f2b46b', primary_fg='#1e1006', accent='#f2b46b1f', link='#f8cd98',
        code='#180f12ed', assistant='#1a1013eb', user='#3a262aed', message='#342228bd',
        tint='#ffe2bd', select='#f2b46b4d'),
}

TEMPLATE = Template(r"""/* T3 Orbital Glass. Theme pack: $title - $blurb */
:root, html[data-theme-id], [data-app-sidebar] {
  color-scheme: dark !important;
  --background: $canvas !important;
  --app-chrome-background: $chrome !important;
  --foreground: $fg !important;
  --contrast-foreground: $fg !important;
  --muted-foreground: $muted !important;
  --contrast-muted-foreground: $muted !important;
  --card: $card !important;
  --card-foreground: $fg !important;
  --popover: $popover !important;
  --popover-foreground: $fg !important;
  --surface-raised: $raised !important;
  --border: #ffffff16 !important;
  --input: #ffffff24 !important;
  --primary: $primary !important;
  --primary-foreground: $primary_fg !important;
  --accent: $accent !important;
  --accent-foreground: $fg !important;
  --ring: $primary !important;
  --muted: $muted_bg !important;
  --secondary: $secondary !important;
  --secondary-foreground: $secondary_fg !important;
  --sidebar: ${sidebar}99 !important;
  --sidebar-foreground: $fg !important;
  --sidebar-muted-foreground: $muted !important;
  --sidebar-border: #ffffff12 !important;
  --contrast-sidebar-foreground: $fg !important;
  --contrast-sidebar-muted-foreground: $muted !important;
  --contrast-sidebar-border: #ffffff12 !important;
  --sidebar-accent: $accent !important;
  --sidebar-accent-foreground: $fg !important;
  --toolbar-background: ${chrome}a6 !important;
  --toolbar-foreground: $fg !important;
  --toolbar-control: ${secondary_solid}a6 !important;
  --toolbar-control-hover: $secondary_solid !important;
  --toolbar-control-foreground: $fg !important;
  --toolbar-border: #ffffff16 !important;
  --code-background: $code !important;
  --code-foreground: $fg !important;
  --contrast-message-foreground: $fg !important;
  --message-surface: $message !important;
  --message-foreground: $fg !important;
  --glass-opacity: 54% !important;
  --glass-blur: 28px !important;
  --glass-saturation: 90% !important;
  --chat-composer-glass-surface: $composer !important;
  --chat-composer-outline: #ffffff24 !important;
  --app-theme-canvas: $canvas !important;
  --app-theme-chrome: $chrome !important;
  --app-theme-surface: $card !important;
  --app-theme-surface-raised: $composer !important;
  --app-theme-text: $fg !important;
  --app-theme-message-surface: $message !important;
  --app-theme-message-foreground: $fg !important;
  --app-theme-border: #ffffff16 !important;
  --app-theme-accent: $primary !important;
  --app-theme-text-muted: $muted !important;
}
html { background: $chrome !important; }
body {
  background: linear-gradient(180deg, #03050708, #03050724), url('__BACKGROUND_DATA__') center / cover fixed no-repeat !important;
  color: $fg !important;
}
body::before { content: none !important; }
#root { position: relative; isolation: isolate; background: transparent !important; }
#root > div, main, [role='main'] { background-color: transparent !important; }
[data-app-sidebar], [data-slot='sidebar-inner'] {
  background: $sidebar !important;
  backdrop-filter: blur(30px) saturate(85%);
  border-color: #ffffff14 !important;
}
.sidebar-stage-backdrop { opacity: 0 !important; }
main > header, [role='main'] > header {
  background: ${sidebar}ed !important;
  backdrop-filter: blur(24px) saturate(85%);
  border-bottom: 1px solid #ffffff0d;
}
[aria-label='Conversation'] {
  background: transparent !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  border: 0;
  border-radius: 0;
  margin: 0;
  box-shadow: none;
}
.group\/composer-surface {
  --chat-composer-glass-surface: $composer !important;
  --chat-composer-outline: #ffffff21 !important;
  background: linear-gradient(135deg, ${tint}0d, #ffffff00 60%), $composer_bg !important;
  backdrop-filter: blur(40px) saturate(120%);
  border-radius: 26px;
  box-shadow: 0 14px 50px #00000030, inset 0 1px #ffffff14;
  transition: box-shadow .25s ease;
}
.group\/composer-surface:focus-within {
  box-shadow: 0 14px 50px #00000030, 0 0 0 1px ${primary}55, 0 0 32px ${primary}26, inset 0 1px #ffffff14;
}
[aria-label='Message input'] { padding-bottom: 6px; }
[aria-label='Thread details'] {
  background: ${chrome}8c !important;
  backdrop-filter: blur(24px) saturate(85%);
  border-left: 1px solid #ffffff12;
}
.dialog-glass, .dropdown-glass, [role='dialog'], [role='menu'], [role='listbox'] {
  background: $popover_solid !important;
  color: $fg !important;
  border-color: #ffffff1c !important;
  backdrop-filter: blur(28px) saturate(90%);
  box-shadow: 0 16px 48px #00000038, inset 0 1px #ffffff08;
}
pre, .cm-editor, .xterm-viewport { background-color: $code !important; }
[data-app-sidebar] button[aria-current='page'],
[data-app-sidebar] [data-active='true'] {
  background: linear-gradient(90deg, ${primary}24, ${primary}08) !important;
  box-shadow: inset 2px 0 $primary, inset 0 1px #ffffff08;
}
::selection { background: $select; color: #fff; }
/* Protect message text locally, keeping the workspace wallpaper exposed. */
[data-message-role='assistant'] .chat-markdown {
  background: $assistant !important;
  color: $fg !important;
  --foreground: $fg !important;
  --contrast-foreground: $fg !important;
  --muted-foreground: $muted !important;
  --contrast-muted-foreground: $muted !important;
  padding: 16px 20px;
  border: 1px solid #ffffff16;
  border-top-color: ${primary}33;
  border-radius: 18px;
  box-shadow: 0 6px 24px #0000001f;
  overflow-wrap: anywhere;
}
[data-message-role='assistant'] .chat-markdown :is(p, li, blockquote, th, td) {
  color: $fg;
}
[data-message-role='assistant'] .chat-markdown :is(h1, h2, h3, h4, strong) {
  color: #fff;
}
[data-message-role='assistant'] .chat-markdown a {
  color: $link !important;
  text-decoration-color: ${link}80;
}
[data-message-role='assistant'] .chat-markdown :not(pre) > code {
  color: $link;
}
[data-message-role='user'] {
  --message-surface: $user !important;
  --app-theme-message-surface: $user !important;
  --message-foreground: $fg !important;
  --contrast-message-foreground: $fg !important;
  --app-theme-message-foreground: $fg !important;
}
$extra/* End T3 Orbital Glass */
""")


def build(name, palette=None, extra=''):
    p = dict(palette or THEMES[name])
    p['extra'] = extra
    p['secondary_solid'] = p['secondary'][:7]
    p['popover_solid'] = p['popover'][:7] + 'eb'
    return TEMPLATE.substitute(p)


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    for name in THEMES:
        (root / name).mkdir(exist_ok=True)
        (root / name / 'theme.css').write_text(build(name), encoding='utf-8')
        print('wrote', name)
