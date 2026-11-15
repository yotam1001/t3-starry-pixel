# Installing Starry Pixel (instructions for the agent)

You are an agent running inside T3 Code. The user asked you to install the Starry Pixel theme.
Follow these steps. They work on Windows and macOS.

1. Download the latest release for this OS from
   https://github.com/yotam1001/t3-starry-pixel/releases/latest
   (`starry-pixel-windows.zip` or `starry-pixel-macos.zip`), or clone the repo.
   Unzip it into `~/.t3/starry-pixel-src/` (Windows: `%USERPROFILE%\.t3\starry-pixel-src\`).
2. Make sure Python 3.8+ is available (`python3 --version`, or `python --version` / `py --version` on Windows).
   macOS ships `/usr/bin/python3` with the Command Line Tools.
3. Check what will be patched: `python3 install.py status`
4. Install: `python3 install.py install`
   - It prepares a patched copy while T3 keeps running, verifies it, then a helper outside T3
     closes T3 about 8 seconds later, swaps the files in and reopens T3.
   - **Tell the user before you run it** that T3 will close and reopen by itself, and that this
     conversation will continue after the restart.
   - On macOS a Terminal window shows progress. If macOS asks whether Terminal may modify apps, the user should click Allow.
5. After T3 reopens, Starry Pixel is selected. If not, pick **Starry Pixel** in T3's theme menu.

To remove it: `python3 install.py uninstall` (T3 restarts once more, with the original app restored).

After a T3 update the theme disappears, because the update replaces the patched files. Run
`python3 install.py install` again.

## What it changes

- Adds a colors-only theme entry to `~/.t3/userdata/themes/starry-pixel.json`, so it shows up in the theme menu.
- Appends `theme/starry-pixel.css` and `theme/engine.js` to T3's bundled main CSS and JS inside its `.asar` archive.
  Every other file in the archive is verified byte for byte.
- Keeps verified backups in `~/.t3/starry-pixel/`.
- macOS only: updates the archive checksum in the app's `Info.plist` and re-signs the app ad hoc
  (the original developer signature is replaced; a full copy of the original app is kept for uninstall).
  Re-signing can stop T3's auto-update, and macOS may ask again for permissions T3 already had.

If anything fails, the installer leaves T3 unchanged (or rolls back) and reopens it.
