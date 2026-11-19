"""Build MyRoom_mac.zip straight from the source zips so macOS file permissions (executables) survive."""
import os, zipfile

ROOT = "MyRoom_mac/"
GAME = r"C:/Users/thema/downloads/newgame/RoomGame"
GODOT_ZIP = r"C:/Users/thema/Downloads/godot_mac/Godot_mac.zip"
CEF_ZIP = r"C:/Users/thema/Downloads/gdcef_download/gdcef-0.21.0_godot-4.7.zip"
OUT = r"C:/Users/thema/Downloads/MyRoom_mac.zip"

PLAY = """#!/bin/bash
cd "$(dirname "$0")"
xattr -cr . 2>/dev/null
./Godot.app/Contents/MacOS/Godot --path game
"""

README = """MY ROOM - Mac (needs an M1 / M2 / M3 / M4 Mac)

1. Install Tailscale from the App Store (or https://tailscale.com/download) and sign in
   to the same Tailscale network as the other player.

2. Double-click the zip to unzip it, and move the MyRoom_mac folder to your Desktop.

3. ONE TIME ONLY - let macOS run it (it isn't from the App Store):
   open Terminal (Cmd+Space, type Terminal, Enter), type

       xattr -cr

   then a space, drag the MyRoom_mac folder into the Terminal window, and press Enter.

4. Double-click "Play My Room.command".
   If macOS asks to allow incoming network connections, click Allow.
   If it still says it can't be opened: System Settings > Privacy & Security >
   scroll down > "Open Anyway", then try again.

5. One of you clicks "Host a game" - it shows a Tailscale address (100.x.x.x).
   The other types that under "Join a friend" and clicks Join.
"""


def add_bytes(z, name, data, mode):
    zi = zipfile.ZipInfo(ROOT + name)
    zi.external_attr = (mode | 0o100000) << 16
    zi.create_system = 3          # Unix, so the mode is honoured
    zi.compress_type = zipfile.ZIP_DEFLATED
    z.writestr(zi, data)


def copy_zip(z, src, strip, prefix, skip=lambda n: False):
    n = 0
    with zipfile.ZipFile(src) as s:
        for i in s.infolist():
            if not i.filename.startswith(strip) or skip(i.filename):
                continue
            rel = i.filename[len(strip):]
            if not rel:
                continue
            zi = zipfile.ZipInfo(ROOT + prefix + rel, i.date_time)
            zi.external_attr = i.external_attr
            zi.create_system = 3
            zi.compress_type = zipfile.ZIP_DEFLATED
            if i.is_dir():
                z.writestr(zi, b"")
            else:
                with s.open(i) as f, z.open(zi, "w", force_zip64=True) as g:
                    while True:
                        b = f.read(1 << 20)
                        if not b:
                            break
                        g.write(b)
            n += 1
    return n


with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as z:
    print("godot entries", copy_zip(z, GODOT_ZIP, "", ""))
    print("cef entries", copy_zip(z, CEF_ZIP, "gdcef/cef_artifacts/macos/", "game/cef_artifacts/macos/"))
    files = 0
    for dp, dns, fns in os.walk(GAME):
        rel_dir = os.path.relpath(dp, GAME).replace("\\", "/")
        if rel_dir.startswith("cef_artifacts/windows") or rel_dir.startswith("cef_artifacts/linux"):
            continue
        for fn in fns:
            rel = fn if rel_dir == "." else rel_dir + "/" + fn
            with open(os.path.join(dp, fn), "rb") as f:
                add_bytes(z, "game/" + rel, f.read(), 0o644)
            files += 1
    print("game files", files)
    add_bytes(z, "Play My Room.command", PLAY.encode(), 0o755)
    add_bytes(z, "READ ME FIRST.txt", README.replace("\n", "\n").encode(), 0o644)
print("MB", os.path.getsize(OUT) // 1_000_000)
