#!/bin/bash
# Build the playable Happy Nine game on macOS (Apple Silicon) from this repo.
# Usage (from the repo root):  bash scripts/build_game.sh [--zip]
set -euo pipefail

GODOT_VER="4.7.2-stable"
GDCEF_TAG="v0.21.0-godot4"
GDCEF_ZIP="gdcef-0.21.0_godot-4.7.zip"
GODOT_ZIP="Godot_v${GODOT_VER}_macos.universal.zip"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DL="$ROOT/build/downloads"
OUT="$ROOT/build/HappyNine-mac"
MAKE_ZIP=0
[ "${1:-}" = "--zip" ] && MAKE_ZIP=1

if [ "$(uname -s)" != "Darwin" ]; then echo "This script is for macOS (use build_game.ps1 on Windows)"; exit 1; fi
if [ "$(uname -m)" != "arm64" ]; then echo "Needs an Apple Silicon Mac (M1 or newer): gdCEF's macOS build is arm64 only"; exit 1; fi

fetch() {  # url file
    if [ -s "$DL/$2" ] && unzip -tq "$DL/$2" >/dev/null 2>&1; then echo "have $2"; return; fi
    echo "downloading $2 ..."
    curl -fL --retry 3 -o "$DL/$2.part" "$1"
    mv "$DL/$2.part" "$DL/$2"
}

mkdir -p "$DL"
fetch "https://github.com/godotengine/godot/releases/download/$GODOT_VER/$GODOT_ZIP" "$GODOT_ZIP"
fetch "https://github.com/Lecrapouille/gdcef/releases/download/$GDCEF_TAG/$GDCEF_ZIP" "$GDCEF_ZIP"

echo "assembling $OUT ..."
rm -rf "$OUT"
mkdir -p "$OUT/game"
ditto -x -k "$DL/$GODOT_ZIP" "$OUT"                       # -> Godot.app
rsync -a --exclude ".godot" --exclude "cef_artifacts/windows" --exclude "cef_artifacts/linux" \
      --exclude "cef_artifacts/macos" "$ROOT/RoomGame/" "$OUT/game/"
TMP="$ROOT/build/tmp_cef"
rm -rf "$TMP"; mkdir -p "$TMP"
unzip -q "$DL/$GDCEF_ZIP" "gdcef/cef_artifacts/macos/*" -d "$TMP"
mv "$TMP/gdcef/cef_artifacts/macos" "$OUT/game/cef_artifacts/macos"
rm -rf "$TMP"
xattr -cr "$OUT" 2>/dev/null || true

echo "importing the project (first run, takes a minute) ..."
"$OUT/Godot.app/Contents/MacOS/Godot" --headless --path "$OUT/game" --import >"$ROOT/build/import_mac.log" 2>&1 || true
if [ ! -d "$OUT/game/.godot/imported" ]; then
    echo "import failed - see build/import_mac.log"; tail -20 "$ROOT/build/import_mac.log"; exit 1
fi

cat > "$OUT/Play Happy Nine.command" <<'EOF'
#!/bin/bash
cd "$(dirname "$0")"
./Godot.app/Contents/MacOS/Godot --path game
EOF
chmod +x "$OUT/Play Happy Nine.command"
cat > "$OUT/READ ME.txt" <<'EOF'
MY ROOM
Double-click "Play Happy Nine.command". If macOS asks about incoming network connections, click Allow.
Play together: both of you install Tailscale (tailscale.com/download) and sign in to the same
network. One clicks "Host a game" (shows a 100.x.x.x address); the other types it under "Join a friend".
If you got this folder as a zip from someone, first run once in Terminal:  xattr -cr <drag this folder here>
EOF

if [ $MAKE_ZIP = 1 ]; then
    echo "zipping ..."
    rm -f "$ROOT/build/HappyNine-mac.zip"
    ditto -c -k --keepParent "$OUT" "$ROOT/build/HappyNine-mac.zip"
    echo "zip: $ROOT/build/HappyNine-mac.zip"
fi
echo "BUILD OK: $OUT"
