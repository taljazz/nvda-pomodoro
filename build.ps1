# Build script for the Pomodoro NVDA add-on.
# Produces dist/pomodoro-<version>.nvda-addon inside the project.
#
# Usage (from this folder):  powershell -ExecutionPolicy Bypass -File .\build.ps1

$ErrorActionPreference = "Stop"

$source = $PSScriptRoot
$manifest = Join-Path $source "manifest.ini"
if (-not (Test-Path $manifest)) { throw "manifest.ini not found at $manifest" }

# Pull the version from the manifest so the filename always matches.
$versionLine = Select-String -Path $manifest -Pattern '^\s*version\s*=\s*(.+)$' | Select-Object -First 1
if (-not $versionLine) { throw "version not found in manifest.ini" }
$version = ($versionLine.Matches[0].Groups[1].Value).Trim().Trim('"')

$outDir = Join-Path $source "dist"
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }
$outZip = Join-Path $outDir "pomodoro-$version.zip"
$outPath = Join-Path $outDir "pomodoro-$version.nvda-addon"

# Compress-Archive only accepts .zip — we build a .zip then rename to .nvda-addon.
foreach ($p in @($outZip, $outPath)) {
    if (Test-Path $p) { Remove-Item $p -Force }
}

# Stage to a temp directory so __pycache__ and the build script itself stay out of the package.
$staging = Join-Path $env:TEMP ("pomodoro_addon_build_" + [guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $staging | Out-Null
try {
    $items = @("manifest.ini", "globalPlugins", "doc")
    foreach ($item in $items) {
        $src = Join-Path $source $item
        if (Test-Path $src) {
            Copy-Item -Path $src -Destination $staging -Recurse
        }
    }

    # Strip __pycache__ folders if any sneaked in from a prior run.
    Get-ChildItem -Path $staging -Recurse -Directory -Filter "__pycache__" `
        | ForEach-Object { Remove-Item $_.FullName -Recurse -Force }

    # Zip the staging contents (not the staging folder itself), then rename to .nvda-addon.
    Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $outZip -Force
    Rename-Item -Path $outZip -NewName ([System.IO.Path]::GetFileName($outPath))
}
finally {
    Remove-Item $staging -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Output "Built: $outPath"
