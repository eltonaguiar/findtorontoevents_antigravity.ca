# Prepend %USERPROFILE%\.local\bin to the *user* PATH if missing (GitHub CLI often installs here).
# Run once:  powershell -ExecutionPolicy Bypass -File tools/ensure_github_cli_on_path.ps1

$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$ghDir = Join-Path $env:USERPROFILE '.local\bin'
$ghExe = Join-Path $ghDir 'gh.exe'
if (-not (Test-Path $ghExe)) {
    Write-Host ('gh.exe not found at ' + $ghDir + ' - install from https://cli.github.com/ or winget install GitHub.cli')
    exit 1
}
if ($userPath -notlike ('*' + [Regex]::Escape($ghDir) + '*')) {
    $newPath = $ghDir + [char]59 + $userPath
    [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
    Write-Host ('Added ' + $ghDir + ' to user PATH. Open a new terminal, then run: gh --version')
} else {
    Write-Host ('Already on PATH: ' + $ghDir)
}
