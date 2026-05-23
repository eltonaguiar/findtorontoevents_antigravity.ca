# One-time: make python /tmp/check_active_picks.py work on Windows (E:\tmp and C:\tmp).
$ErrorActionPreference = "Stop"
$shimSource = Join-Path $PSScriptRoot "check_active_picks_shim.py"
if (-not (Test-Path $shimSource)) {
    Write-Error "Missing $shimSource"
}
$targets = @(
    "E:\tmp\check_active_picks.py",
    "C:\tmp\check_active_picks.py"
)
foreach ($dest in $targets) {
    $dir = Split-Path $dest -Parent
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    Copy-Item -Path $shimSource -Destination $dest -Force
    Write-Host "Installed shim: $dest"
}
Write-Host "Done. Try: python /tmp/check_active_picks.py  (from E: drive uses E:\tmp\...)"
