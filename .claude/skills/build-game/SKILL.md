---
name: build-game
description: Build the playable "Happy Nine" game from this repo on this computer (Mac or Windows) - downloads the matching Godot 4.7.2 runtime and the Godot CEF Chromium add-on (TV / computer / laptop screens), prepares the project and makes a double-click launcher, optionally a zip to send to someone. Use whenever someone says "build the game", "set up / install the game", "make it playable", "I cloned the repo, now what", "update my game", "make a zip of the game", or wants to play Happy Nine / happy9 on their own machine.
---
# Build Happy Nine on this computer

The repo holds the game's source (`RoomGame/`, a Godot 4.7 project) but not the big binaries
(Godot itself, ~90-170 MB, and the Godot CEF Chromium add-on for the in-game screens, ~1 GB),
which are too big for GitHub. The build script downloads those from their official GitHub releases,
so building needs internet and ~2.5 GB of free disk space the first time (downloads are cached in
`build/downloads/`, so rebuilding after a `git pull` is quick).

## Steps

1. **Check the machine.**
   - macOS: Apple Silicon or Intel — both work. The Godot CEF add-on ships as a universal binary.
   - Windows: 64-bit Windows 10/11.
2. **Get the latest game:** `git pull` in the repo root (skip if there's no remote or it fails
   because of local changes — say so).
3. **Run the build script from the repo root** (it takes a few minutes; run it in the foreground
   with a long timeout, ~15 min, or in the background and wait for it):
   - macOS: `bash scripts/build_game.sh` (add `--zip` to also make a zip)
   - Windows (PowerShell): `powershell -ExecutionPolicy Bypass -File scripts/build_game.ps1`
     (add `-Zip` to also make a zip)
   It prints `BUILD OK` and the folder it made at the end. Any other ending is a failure —
   read the error, fix it (often just a dropped download: run it again), and retry.
4. **Tell the person how to play** (in plain words):
   - macOS: open `build/HappyNine-mac` in Finder, double-click **Play Happy Nine.command**. If macOS
     asks about incoming network connections, Allow.
   - Windows: open `build\HappyNine-windows`, double-click **Play Happy Nine.bat**. If Windows
     Firewall asks, tick Private **and** Public and Allow.
   - To play together: both install Tailscale (https://tailscale.com/download) and sign in to the
     same Tailscale network; one clicks **Host a game** (it shows a 100.x.x.x address), the other
     types that address under **Join a friend**.
   - Offer to put a shortcut on the Desktop if they want one (Mac: `ln -s` the .command file;
     Windows: a .lnk via PowerShell `WScript.Shell`).
5. **Optional check:** the script already boots the game headless once to import it; if the person
   reports a blank TV / computer screen, run the game from a terminal to see the log:
   - macOS: `build/HappyNine-mac/Godot.app/Contents/MacOS/Godot --path build/HappyNine-mac/game`
   - Windows: `build\HappyNine-windows\HappyNine_console.exe --path build\HappyNine-windows\game`

## What the script does (so you can fix it if a step breaks)

- Downloads `Godot_v4.7.2-stable_macos.universal.zip` / `Godot_v4.7.2-stable_win64.exe.zip`
  from github.com/godotengine/godot releases, and `godot_cef-v2.1.3.zip` from
  github.com/dsh0416/godot-cef releases (tag `v2.1.3`), into `build/downloads/`.
- Copies `RoomGame/` to `build/HappyNine-<os>/game/` (without `.godot` cache, old `cef_artifacts/`,
  and the `addons/godot_cef/bin/` directory), then extracts `dist/addons/godot_cef/` from the
  Godot CEF zip into `game/addons/godot_cef/` (all platforms; Godot loads only the matching one).
- Runs Godot headless with `--import` once, which creates the `.godot` import cache the game needs.
- Writes the launcher (`Play Happy Nine.command` / `.bat`) and `READ ME.txt`; with zip, also
  `build/HappyNine-<os>.zip` (on macOS made with `ditto` so the apps keep their permissions).
- `build/` is in `.gitignore` — never commit it.

## Versions
Godot 4.7.2 and Godot CEF 2.1.3 must match what the project was made with (`RoomGame/project.godot`
and `RoomGame/addons/godot_cef/godot_cef.gdextension`). If those files change version, update
the constants at the top of both scripts.
