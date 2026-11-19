#!/bin/bash
# Build the playable Happy Nine game on macOS from this repo.
# Usage (from the repo root):  bash scripts/build_game.sh [--zip]
set -euo pipefail

GODOT_VER="4.7.2-stable"
GODOT_CEF_VER="2.1.3"
GODOT_CEF_ZIP="godot_cef-v${GODOT_CEF_VER}.zip"
GODOT_CEF_SIZE=1082108384       # expected bytes; download resumes until this is reached
GODOT_ZIP="Godot_v${GODOT_VER}_macos.universal.zip"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DL="$ROOT/build/downloads"
OUT="$ROOT/build/HappyNine-mac"
MAKE_ZIP=0
[ "${1:-}" = "--zip" ] && MAKE_ZIP=1

if [ "$(uname -s)" != "Darwin" ]; then echo "This script is for macOS (use build_game.ps1 on Windows)"; exit 1; fi

fetch() {  # url file [expected_size]
    local URL="$1" FILE="$2" EXPECTED="${3:-0}"
    local DEST="$DL/$FILE"
    # Check cache: size match + valid zip
    if [ -s "$DEST" ]; then
        local actual; actual=$(stat -f%z "$DEST" 2>/dev/null || echo 0)
        if { [ "$EXPECTED" -eq 0 ] || [ "$actual" -ge "$EXPECTED" ]; } \
                && unzip -tq "$DEST" >/dev/null 2>&1; then
            echo "have $FILE"
            return
        fi
    fi
    echo "downloading $FILE ..."
    while true; do
        curl -C - -fL --max-time 600 --no-progress-meter -o "$DEST" "$URL" || true
        local actual; actual=$(stat -f%z "$DEST" 2>/dev/null || echo 0)
        if { [ "$EXPECTED" -eq 0 ] || [ "$actual" -ge "$EXPECTED" ]; } \
                && unzip -tq "$DEST" >/dev/null 2>&1; then
            break
        fi
        echo "  partial ($(( actual / 1048576 ))M / $(( EXPECTED / 1048576 ))M), resuming in 3s..."
        sleep 3
    done
    echo "done: $FILE"
}

mkdir -p "$DL"
fetch "https://github.com/godotengine/godot/releases/download/$GODOT_VER/$GODOT_ZIP" "$GODOT_ZIP"
fetch "https://github.com/dsh0416/godot-cef/releases/download/v${GODOT_CEF_VER}/$GODOT_CEF_ZIP" \
      "$GODOT_CEF_ZIP" "$GODOT_CEF_SIZE"

echo "assembling $OUT ..."
xattr -rc "$OUT" 2>/dev/null || true   # clear Finder metadata that blocks rm -rf
rm -rf "$OUT"
mkdir -p "$OUT/game"
ditto -x -k "$DL/$GODOT_ZIP" "$OUT"                       # -> Godot.app
# Copy game source, skipping the old gdCEF artifacts (Godot CEF goes in addons/)
rsync -a --exclude ".godot" --exclude "cef_artifacts" --exclude "addons/godot_cef" "$ROOT/RoomGame/" "$OUT/game/"
TMP="$ROOT/build/tmp_cef"
rm -rf "$TMP"; mkdir -p "$TMP"
unzip -q "$DL/$GODOT_CEF_ZIP" "dist/addons/godot_cef/*" -d "$TMP"
mkdir -p "$OUT/game/addons"
mv "$TMP/dist/addons/godot_cef" "$OUT/game/addons/godot_cef"
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
osascript -e 'tell application "Terminal" to close front window' > /dev/null 2>&1 || true
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
