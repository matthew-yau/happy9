# Build the playable Happy Nine game on Windows from this repo.
# Usage (from the repo root):  powershell -ExecutionPolicy Bypass -File scripts/build_game.ps1 [-Zip]
param([switch]$Zip)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"      # Invoke-WebRequest is very slow with the progress bar

$GodotVer = "4.7.2-stable"
$GdcefTag = "v0.21.0-godot4"
$GdcefZip = "gdcef-0.21.0_godot-4.7.zip"
$GodotZip = "Godot_v${GodotVer}_win64.exe.zip"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Dl = Join-Path $Root "build\downloads"
$Out = Join-Path $Root "build\HappyNine-windows"
Add-Type -AssemblyName System.IO.Compression.FileSystem

function Test-Zip($path) {
    if (-not (Test-Path $path)) { return $false }
    try { $z = [IO.Compression.ZipFile]::OpenRead($path); $z.Dispose(); return $true } catch { return $false }
}

function Get-File($url, $name) {
    $dest = Join-Path $Dl $name
    if (Test-Zip $dest) { Write-Host "have $name"; return $dest }
    Write-Host "downloading $name ..."
    $part = "$dest.part"
    for ($i = 1; $i -le 3; $i++) {
        try { Invoke-WebRequest -Uri $url -OutFile $part -UseBasicParsing; break }
        catch { if ($i -eq 3) { throw }; Write-Host "  retry ${i}: $_" }
    }
    Move-Item $part $dest -Force
    return $dest
}

New-Item -ItemType Directory -Force $Dl | Out-Null
$godot = Get-File "https://github.com/godotengine/godot/releases/download/$GodotVer/$GodotZip" $GodotZip
$cef = Get-File "https://github.com/Lecrapouille/gdcef/releases/download/$GdcefTag/$GdcefZip" $GdcefZip

Write-Host "assembling $Out ..."
if (Test-Path $Out) { Remove-Item $Out -Recurse -Force }
$game = Join-Path $Out "game"
New-Item -ItemType Directory -Force $game | Out-Null

# Godot: the zip holds Godot_v..._win64.exe and Godot_v..._win64_console.exe
$z = [IO.Compression.ZipFile]::OpenRead($godot)
foreach ($e in $z.Entries) {
    if ($e.Name -like "*_console.exe") { [IO.Compression.ZipFileExtensions]::ExtractToFile($e, (Join-Path $Out "HappyNine_console.exe"), $true) }
    elseif ($e.Name -like "*.exe") { [IO.Compression.ZipFileExtensions]::ExtractToFile($e, (Join-Path $Out "HappyNine.exe"), $true) }
}
$z.Dispose()

# the game project, without the import cache and other platforms' Chromium
$src = Join-Path $Root "RoomGame"
robocopy $src $game /E /NFL /NDL /NJH /NJS /NP /XD (Join-Path $src ".godot") (Join-Path $src "cef_artifacts\windows") (Join-Path $src "cef_artifacts\macos") (Join-Path $src "cef_artifacts\linux") | Out-Null
if ($LASTEXITCODE -ge 8) { throw "copying the project failed (robocopy $LASTEXITCODE)" }

# this platform's Chromium only
$prefix = "gdcef/cef_artifacts/windows/"
$dst = Join-Path $game "cef_artifacts\windows"
$z = [IO.Compression.ZipFile]::OpenRead($cef)
$n = 0
foreach ($e in $z.Entries) {
    if (-not $e.FullName.StartsWith($prefix) -or $e.FullName.EndsWith("/")) { continue }
    $rel = $e.FullName.Substring($prefix.Length) -replace "/", "\"
    if ($rel -like "*.lib" -or $rel -like "*.exp") { continue }
    $target = Join-Path $dst $rel
    New-Item -ItemType Directory -Force (Split-Path $target) | Out-Null
    [IO.Compression.ZipFileExtensions]::ExtractToFile($e, $target, $true)
    $n++
}
$z.Dispose()
if ($n -eq 0) { throw "no Windows files found in $GdcefZip" }

Write-Host "importing the project (first run, takes a minute) ..."
$log = Join-Path $Root "build\import_windows.log"
$ErrorActionPreference = "Continue"           # Godot writes harmless warnings to stderr
& (Join-Path $Out "HappyNine_console.exe") --headless --path $game --import *> $log
$ErrorActionPreference = "Stop"
if (-not (Test-Path (Join-Path $game ".godot\imported"))) {
    Get-Content $log -Tail 20
    throw "import failed - see build\import_windows.log"
}

Set-Content -Path (Join-Path $Out "Play Happy Nine.bat") -Encoding ascii -Value "@echo off`r`ncd /d `"%~dp0`"`r`nstart `"`" `"HappyNine.exe`" --path game`r`n"
Set-Content -Path (Join-Path $Out "READ ME.txt") -Encoding ascii -Value @"
MY ROOM
Double-click "Play Happy Nine.bat". If Windows Firewall asks, tick Private AND Public and click Allow.
If SmartScreen says "Windows protected your PC": More info > Run anyway.
Play together: both of you install Tailscale (tailscale.com/download) and sign in to the same
network. One clicks "Host a game" (shows a 100.x.x.x address); the other types it under "Join a friend".
"@

if ($Zip) {
    Write-Host "zipping ..."
    $zipPath = Join-Path $Root "build\HappyNine-windows.zip"
    if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
    [IO.Compression.ZipFile]::CreateFromDirectory($Out, $zipPath, [IO.Compression.CompressionLevel]::Optimal, $true)
    Write-Host "zip: $zipPath"
}
Write-Host "BUILD OK: $Out"
