"""Starry Pixel for T3 Code: installer for Windows and macOS.

    python install.py install     # add the theme (T3 restarts once, by itself)
    python install.py uninstall   # put the original app back
    python install.py status

Safe to run from an agent inside T3. The patched copy is prepared while T3 keeps running;
a small helper outside T3 then quits it, swaps the files and reopens it.

What it changes: T3's bundled main CSS and JS get the theme and its animation engine appended.
Nothing else in the archive changes (every other file is verified byte for byte). A verified
backup is kept in ~/.t3/starry-pixel/. On macOS the app is re-signed ad hoc, because the archive
checksum lives in Info.plist. T3 updates replace the patch; run install again after an update.
"""
import glob
import hashlib
import json
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE = Path.home() / '.t3' / 'starry-pixel'
MANIFEST = STATE / 'manifest.json'
THEMES_DIR = Path.home() / '.t3' / 'userdata' / 'themes'
MARKER = b'/* T3 Starry Pixel theme'
OLD_MARKERS = (MARKER, b'/* T3 Orbital Glass.')
CLIENT = '/apps/server/dist/client/assets/'
MAC = platform.system() == 'Darwin'
WIN = platform.system() == 'Windows'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def say(msg):
    print(msg, flush=True)


# --- asar ------------------------------------------------------------------------------
def read_asar(data):
    _, header_size, _, json_size = struct.unpack('<4I', data[:16])
    return json.loads(data[16:16 + json_size]), data[8 + header_size:]


def header_hash(data):
    _, _, _, json_size = struct.unpack('<4I', data[:16])
    return sha(data[16:16 + json_size])


def walk(tree, prefix=''):
    for name, value in tree['files'].items():
        path = prefix + '/' + name
        if 'files' in value:
            yield from walk(value, path)
        else:
            yield path, value


def encode_header(tree):
    data = json.dumps(tree, separators=(',', ':'), ensure_ascii=False).encode()
    padded = (len(data) + 3) // 4 * 4
    return struct.pack('<4I', 4, padded + 8, padded + 4, len(data)) + data + bytes(padded - len(data))


def client_assets(tree):
    files = dict(walk(tree))
    css = [n for n in files if re.fullmatch(re.escape(CLIENT) + r'main-[^/]+\.css', n)]
    js = [n for n in files if re.fullmatch(re.escape(CLIENT) + r'main-[^/]+\.js', n)]
    if len(css) != 1 or len(js) != 1:
        return None
    return css[0], js[0]


def has_client(path):
    try:
        with open(path, 'rb') as f:
            head = f.read(16)
            _, _, _, json_size = struct.unpack('<4I', head)
            tree = json.loads(f.read(json_size))
        return client_assets(tree) is not None
    except Exception:
        return False


def is_patched(data):
    tree, payload = read_asar(data)
    css_name, _ = client_assets(tree)
    entry = dict(walk(tree))[css_name]
    css = payload[int(entry['offset']):int(entry['offset']) + entry['size']]
    return any(m in css for m in OLD_MARKERS)


def patch(original, theme, engine):
    tree, payload = read_asar(original)
    names = client_assets(tree)
    if not names:
        raise SystemExit('Unrecognized T3 layout (no single main-*.css/js). Nothing changed.')
    files = dict(walk(tree))
    changes, tail = {}, b''
    for name, extra in zip(names, (theme, engine)):
        entry = files[name]
        start = int(entry['offset'])
        body = payload[start:start + entry['size']]
        if any(m in body for m in OLD_MARKERS):
            raise SystemExit('Archive is already themed; patch from the clean backup instead.')
        modified = body + b'\n' + extra
        entry['offset'] = str(len(payload) + len(tail))
        entry['size'] = len(modified)
        if 'integrity' in entry:
            block = entry['integrity'].get('blockSize', 4194304)
            entry['integrity'] = {'algorithm': 'SHA256', 'hash': sha(modified), 'blockSize': block,
                                  'blocks': [sha(modified[i:i + block]) for i in range(0, len(modified), block)]}
        changes[name] = modified
        tail += modified
    result = encode_header(tree) + payload + tail
    # Verify: every untouched file is byte-identical, the two changed files hold exactly the patch.
    new_tree, new_payload = read_asar(result)
    old_tree, old_payload = read_asar(original)
    new_files = dict(walk(new_tree))
    for name, old in walk(old_tree):
        new = new_files[name]
        if 'offset' not in old:
            assert new == old, name
            continue
        want = changes.get(name, old_payload[int(old['offset']):int(old['offset']) + old['size']])
        assert new_payload[int(new['offset']):int(new['offset']) + new['size']] == want, name
    return result, len(new_files)


def theme_payload():
    theme = (HERE / 'theme' / 'starry-pixel.css').read_bytes()
    engine = (HERE / 'theme' / 'engine.js').read_bytes()
    if not theme.startswith(MARKER):
        raise SystemExit('theme/starry-pixel.css is missing its header; re-download the release.')
    return theme, engine


# --- locating T3 -----------------------------------------------------------------------
def find_app():
    """Returns (app_root, archive_path, executable)."""
    override = os.environ.get('T3_APP')
    if MAC:
        cands = [override] if override else sorted(
            glob.glob('/Applications/T3 Code*.app') + glob.glob(str(Path.home() / 'Applications/T3 Code*.app')))
        for app in map(Path, filter(None, cands)):
            for asar in sorted((app / 'Contents/Resources').glob('*.asar')):
                if has_client(asar):
                    exe = app / 'Contents/MacOS' / app.stem
                    return app, asar, exe
    elif WIN:
        base = Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs'
        cands = [override] if override else sorted(glob.glob(str(base / 't3*'))) + sorted(glob.glob(str(base / 'T3*')))
        for root in map(Path, filter(None, cands)):
            for asar in sorted((root / 'resources').glob('*.asar')):
                if has_client(asar):
                    exes = [p for p in root.glob('*.exe') if p.name.lower().startswith('t3')]
                    return root, asar, (exes[0] if exes else None)
    else:
        raise SystemExit('Only Windows and macOS are supported.')
    raise SystemExit('Could not find T3 Code. Set T3_APP to the app (macOS: the .app; Windows: its install folder).')


def t3_running(app_root):
    if MAC:
        out = subprocess.run(['ps', '-axo', 'comm='], capture_output=True, text=True).stdout
        return any(line.strip().startswith(str(app_root) + '/') for line in out.splitlines())
    out = subprocess.run(['powershell', '-NoProfile', '-Command',
                          'Get-Process | Where-Object { $_.Path } | Select-Object -ExpandProperty Path'],
                         capture_output=True, text=True).stdout
    root = str(app_root).lower()
    return any(line.strip().lower().startswith(root) for line in out.splitlines())


# --- menu entry ------------------------------------------------------------------------
def add_menu_entry():
    THEMES_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HERE / 'theme' / 'starry-pixel.json', THEMES_DIR / 'starry-pixel.json')


def select_theme():
    """Best effort: make Starry Pixel the selected theme."""
    settings = Path.home() / '.t3' / 'userdata' / 'settings.json'
    try:
        data = json.loads(settings.read_text()) if settings.exists() else {}
        data['defaultTheme'] = 'starry-pixel'
        data['defaultThemeSetAt'] = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
        tmp = settings.with_suffix('.json.tmp')
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(settings)
    except Exception as e:  # the user can still pick it from the theme menu
        say(f'(Could not preselect the theme: {e}. Pick "Starry Pixel" in the T3 theme menu.)')


# --- install / uninstall ---------------------------------------------------------------
def prepare():
    """Build the patched app/archive in STATE/staging while T3 keeps running."""
    app, asar, exe = find_app()
    STATE.mkdir(parents=True, exist_ok=True)
    theme, engine = theme_payload()
    current = asar.read_bytes()
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    if is_patched(current):
        clean_path = Path(manifest.get('cleanArchive', ''))
        if not clean_path.is_file() or sha(clean_path.read_bytes()) != manifest.get('cleanSha256'):
            raise SystemExit('T3 is already patched by something else and no clean backup is known. '
                             'Reinstall T3, then run install again.')
        clean = clean_path.read_bytes()
    else:
        clean = current
        clean_path = STATE / f'clean-{sha(clean)[:16]}.asar'
        if not clean_path.exists():
            shutil.copyfile(asar, clean_path)
        manifest = {'cleanArchive': str(clean_path), 'cleanSha256': sha(clean)}
    patched, count = patch(clean, theme, engine)
    say(f'Patch verified: {count} files in the archive, only main CSS and JS change.')
    staging = STATE / 'staging'
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()
    if MAC:
        original_copy = STATE / 'original' / app.name
        if not original_copy.exists() and not is_patched(current):
            say('Saving a full copy of the original app for uninstall...')
            original_copy.parent.mkdir(exist_ok=True)
            subprocess.run(['ditto', str(app), str(original_copy)], check=True)
            manifest['originalApp'] = str(original_copy)
        staged = staging / app.name
        subprocess.run(['ditto', str(app), str(staged)], check=True)
        staged_asar = staged / asar.relative_to(app)
        staged_asar.write_bytes(patched)
        plist = staged / 'Contents/Info.plist'
        key = 'Resources/' + asar.name
        info = subprocess.run(['plutil', '-extract', 'ElectronAsarIntegrity', 'json', '-o', '-', str(plist)],
                              capture_output=True, text=True)
        if info.returncode == 0:
            integrity = json.loads(info.stdout)
            if key in integrity:
                integrity[key] = {'algorithm': 'SHA256', 'hash': header_hash(patched)}
                subprocess.run(['plutil', '-replace', 'ElectronAsarIntegrity', '-json', json.dumps(integrity),
                                str(plist)], check=True)
        say('Re-signing the patched copy (ad hoc)...')
        subprocess.run(['codesign', '--force', '--deep', '--sign', '-', str(staged)], check=True, capture_output=True)
        subprocess.run(['xattr', '-cr', str(staged)], check=False)
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(staged)], check=True)
        manifest.update(app=str(app), staged=str(staged))
    else:
        staged = staging / asar.name
        staged.write_bytes(patched)
        assert sha(staged.read_bytes()) == sha(patched)
        manifest.update(app=str(app), archive=str(asar), staged=str(staged), exe=str(exe) if exe else None)
    manifest['patchedSha256'] = sha(patched)
    MANIFEST.write_text(json.dumps(manifest, indent=2))
    return app, exe


def mac_swap_script(app, src, label):
    """A Terminal script that quits T3, swaps `src` in for the app and reopens it (rolls back on failure)."""
    script = STATE / 'swap.command'
    old = Path.home() / '.Trash' / f'{app.stem} before {label} {time.strftime("%H%M%S")}.app'
    script.write_text(f'''#!/bin/bash
APP={json.dumps(str(app))}; NEW={json.dumps(str(src))}; OLD={json.dumps(str(old))}
running() {{ ps -axo comm= | grep -qF "$APP/"; }}
echo "Starry Pixel: T3 will close in 8 seconds and reopen."; sleep 8
osascript -e "tell application \\"$(basename "$APP" .app)\\" to quit" 2>/dev/null
for i in $(seq 1 30); do running || break; sleep 1; done
running && {{ pkill -f "$APP/Contents/"; sleep 3; }}
running && {{ echo "T3 would not close. Nothing changed."; exit 1; }}
mv "$APP" "$OLD" || {{ echo "Could not move the app. Nothing changed."; open "$APP"; exit 1; }}
if ! ditto "$NEW" "$APP"; then rm -rf "$APP"; mv "$OLD" "$APP"; open "$APP"; echo "Swap failed; original restored."; exit 1; fi
open "$APP"; for i in $(seq 1 25); do running && break; sleep 1; done; sleep 5
if running; then echo "Done. Previous app moved to the Trash."; else
  echo "T3 did not start; restoring the previous app."; rm -rf "$APP"; mv "$OLD" "$APP"; open "$APP"; fi
''')
    script.chmod(0o755)
    subprocess.run(['open', '-a', 'Terminal', str(script)], check=True)


def ps_quote(value):
    """A PowerShell single-quoted literal (backslashes stay single; json.dumps would double them)."""
    return "'" + str(value).replace("'", "''") + "'"


def win_swap_script(manifest, src, label):
    """A PowerShell script, started outside T3's process tree, that quits T3, replaces the archive and reopens T3."""
    script = STATE / 'swap.ps1'
    log = STATE / 'swap.log'
    root, archive, exe = manifest['app'], manifest['archive'], manifest.get('exe') or ''
    script.write_text(f"""$ErrorActionPreference = 'Stop'
$root = {ps_quote(root)}; $archive = {ps_quote(archive)}; $src = {ps_quote(src)}; $exe = {ps_quote(exe)}
$prefix = $root.TrimEnd([char]92).ToLower() + [char]92  # [char]92 is a backslash
Start-Transcript -Path {ps_quote(log)} -Force | Out-Null
function T3Processes {{ @(Get-Process | Where-Object {{ $_.Path -and $_.Path.ToLower().StartsWith($prefix) }}) }}
"{label}: T3 closes in 8 seconds"
Start-Sleep -Seconds 8
T3Processes | Where-Object {{ $_.MainWindowHandle -ne 0 }} | ForEach-Object {{ $_.CloseMainWindow() | Out-Null }}
for ($i = 0; $i -lt 30 -and (T3Processes).Count; $i++) {{ Start-Sleep -Seconds 1 }}
if ((T3Processes).Count) {{ "{label}: T3 did not close by itself; stopping it"; T3Processes | Stop-Process -Force; Start-Sleep -Seconds 3 }}
$tmp = $archive + '.starry-tmp'; $replaced = $false
for ($i = 0; $i -lt 15 -and -not $replaced; $i++) {{
  try {{
    [System.IO.File]::Copy($src, $tmp, $true)
    [System.IO.File]::Replace($tmp, $archive, [NullString]::Value)
    $replaced = $true
  }} catch {{ "{label}: archive busy, retrying ($($_.Exception.Message))"; Start-Sleep -Seconds 2 }}
}}
if ($replaced) {{ "{label}: archive replaced" }} else {{ "{label}: FAILED to replace the archive; T3 is unchanged"; Remove-Item -LiteralPath $tmp -ErrorAction SilentlyContinue }}
if ($exe) {{ Start-Process -FilePath $exe }}
"{label}: done"
Stop-Transcript | Out-Null
""", encoding='utf-8')
    cmd = f'powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{script}"'
    # Start it through WMI so it is not a child of T3 or of the agent's shell: an agent's job object
    # kills its children when the command returns, even with DETACHED_PROCESS and breakaway flags.
    create = ('$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create '
              '-Arguments @{CommandLine = $env:STARRY_SWAP}; exit $r.ReturnValue')
    result = subprocess.run(['powershell', '-NoProfile', '-Command', create],
                            env=dict(os.environ, STARRY_SWAP=cmd), capture_output=True, text=True)
    if result.returncode != 0:  # no WMI: fall back to a detached child
        flags = 0x00000008 | 0x00000200 | 0x01000000  # DETACHED_PROCESS | NEW_PROCESS_GROUP | BREAKAWAY_FROM_JOB
        args = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-File', str(script)]
        try:
            subprocess.Popen(args, creationflags=flags, close_fds=True)
        except OSError:
            subprocess.Popen(args, creationflags=flags & ~0x01000000, close_fds=True)
    say(f'Helper started; progress is logged to {log}')


def install():
    add_menu_entry()
    app, exe = prepare()
    select_theme()
    manifest = json.loads(MANIFEST.read_text())
    running = t3_running(app)
    if MAC:
        mac_swap_script(app, Path(manifest['staged']), 'Starry Pixel')
    else:
        win_swap_script(manifest, manifest['staged'], 'install')
    say('Installed. T3 closes in about 8 seconds and reopens with Starry Pixel.' if running else
        'Installed. T3 will open with Starry Pixel.')


def uninstall():
    if not MANIFEST.exists():
        raise SystemExit('Starry Pixel is not installed by this installer.')
    manifest = json.loads(MANIFEST.read_text())
    (THEMES_DIR / 'starry-pixel.json').unlink(missing_ok=True)
    if MAC:
        original = Path(manifest.get('originalApp', ''))
        if not original.exists():
            raise SystemExit('Original app copy is missing; reinstall T3 from its website instead.')
        mac_swap_script(Path(manifest['app']), original, 'uninstall')
    else:
        clean = Path(manifest['cleanArchive'])
        if sha(clean.read_bytes()) != manifest['cleanSha256']:
            raise SystemExit('Backup verification failed; nothing changed. Reinstall T3 instead.')
        win_swap_script(manifest, clean, 'uninstall')
    say('Uninstalling: T3 closes in about 8 seconds and reopens without the theme.')


def status():
    app, asar, _ = find_app()
    print(json.dumps({'app': str(app), 'archive': str(asar), 'installed': is_patched(asar.read_bytes()),
                      'running': t3_running(app)}, indent=2))


if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'status'
    {'install': install, 'uninstall': uninstall, 'status': status}.get(action, lambda: sys.exit(__doc__))()
