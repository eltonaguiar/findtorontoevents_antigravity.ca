<#
.SYNOPSIS
    Launch Chrome with a CDP debugging port on a dedicated copy of your profile,
    without the first-run / sign-in / "Restore pages?" popups — and VERIFY that the
    copied profile actually carries your logged-in session.

.DESCRIPTION
    Chrome's cookie database is encrypted and lives in the profile. On Windows the file
    that matters is  User Data\Default\Network\Cookies  (+ its -journal). Chrome keeps
    background processes alive after you close every window, and while any chrome.exe is
    running those files are LOCKED. `Copy-Item -Recurse` does not fail on a locked file —
    it emits a non-terminating error you probably never see and copies the rest — so you
    end up with a profile that has no cookie DB, Chrome starts clean, and you are logged
    out of GitHub with no error anywhere. That is the "login will not persist" symptom.

    On Linux the equivalent file is still  Default/Cookies , which is why the same recipe
    works there and fails on Windows.

    So this script:
      1. hard-stops every chrome.exe and waits for the files to unlock,
      2. copies the profile CONTENTS into <root>\User Data,
      3. clears the inherited exit_type="Crashed" (the "Restore pages?" bubble),
      4. VERIFIES the copied cookie DB exists, is non-trivial, and actually mentions
         github.com — failing loudly instead of launching a logged-out browser,
      5. launches with the popup-suppressing flags and polls /json/version.

    Verification reads the DB bytes rather than opening SQLite: cookie host_keys are stored
    in plaintext, so a bytes search proves the login is present without any dependency.

.PARAMETER Refresh
    Re-copy the profile from the live Chrome user data. Implied on first run.

.PARAMETER Port
    CDP port. Default 9222.

.PARAMETER KeepChrome
    Do not stop Chrome. The copy will almost certainly be missing its cookie DB; the
    verification step will tell you so.

.PARAMETER ExpectedHost
    Host whose cookies must be present in the copy. Default github.com.

.EXAMPLE
    ./launch_debug_chrome.ps1 -Refresh
    ./launch_debug_chrome.ps1
#>
[CmdletBinding()]
param(
    [int]$Port = 9222,
    [switch]$Refresh,
    [switch]$KeepChrome,
    [string]$ExpectedHost = 'github.com',
    [string]$ChromePath,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Url
)

$ErrorActionPreference = 'Stop'

$SrcUserData = Join-Path $env:LOCALAPPDATA 'Google\Chrome\User Data'
$Root        = Join-Path $env:USERPROFILE '.chrome-debug-profile'
# Copy-Item nests a source directory inside the destination, so the profile lands one
# level down. --user-data-dir must point at the folder that CONTAINS Default\.
$UserDataDir = Join-Path $Root 'User Data'

# Cookie DB: Windows uses Default\Network\Cookies, older builds Default\Cookies.
$CookieCandidates = @('Default\Network\Cookies', 'Default\Cookies')

function Stop-AllChrome {
    $procs = @(Get-Process chrome -ErrorAction SilentlyContinue |
               Where-Object { $_.Path -like '*\Google\Chrome\Application\chrome.exe' })
    if ($procs.Count -eq 0) { Write-Host "  no chrome.exe running"; return }

    Write-Host "  stopping $($procs.Count) chrome process(es) so the profile files unlock"
    $procs | Stop-Process -Force -ErrorAction SilentlyContinue

    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 500
        if (-not (Get-Process chrome -ErrorAction SilentlyContinue)) { Write-Host "  all chrome.exe gone"; return }
    }
    throw "chrome.exe still running after 30s — close Chrome (check the tray) and retry, or pass -KeepChrome to copy anyway."
}

function Test-CopiedProfile {
    param([string]$ProfileRoot, [string]$Host_)

    $problems = @()

    $localState = Join-Path $ProfileRoot 'Local State'
    if (-not (Test-Path $localState)) {
        $problems += "Local State missing — Chrome's cookie encryption key lives there; a profile without it cannot decrypt any cookie."
    }

    $cookieDb = $null
    foreach ($rel in $CookieCandidates) {
        $p = Join-Path $ProfileRoot $rel
        if (Test-Path $p) { $cookieDb = $p; break }
    }
    if (-not $cookieDb) {
        $problems += ("No cookie database at Default\Network\Cookies or Default\Cookies. " +
                      "This is the locked-file symptom: Chrome was still running during the copy.")
        return [pscustomobject]@{ Ok = $false; Problems = $problems; CookieDb = $null; Size = 0; HostHits = 0 }
    }

    $size = (Get-Item $cookieDb).Length
    if ($size -lt 8KB) { $problems += "Cookie database is only $size bytes — truncated/empty copy." }

    $bytes = [System.IO.File]::ReadAllBytes($cookieDb)
    $text  = [System.Text.Encoding]::ASCII.GetString($bytes)
    $hits  = ([regex]::Matches($text, [regex]::Escape($Host_))).Count
    if ($hits -eq 0) {
        $problems += "Cookie database contains no '$Host_' rows — the copy did not capture the login."
    }

    [pscustomobject]@{
        Ok       = ($problems.Count -eq 0)
        Problems = $problems
        CookieDb = $cookieDb
        Size     = $size
        HostHits = $hits
    }
}

function Reset-CrashFlags {
    param([string]$ProfileRoot)

    $prefs = Join-Path $ProfileRoot 'Default\Preferences'
    if (-not (Test-Path $prefs)) { Write-Warning "no Default\Preferences under $ProfileRoot"; return }
    try {
        $json = Get-Content -Path $prefs -Raw | ConvertFrom-Json
        if (-not $json.PSObject.Properties['profile']) {
            $json | Add-Member -NotePropertyName profile -NotePropertyValue ([pscustomobject]@{})
        }
        $json.profile | Add-Member -NotePropertyName exit_type      -NotePropertyValue 'Normal' -Force
        $json.profile | Add-Member -NotePropertyName exited_cleanly -NotePropertyValue $true    -Force
        $json | ConvertTo-Json -Depth 100 -Compress | Set-Content -Path $prefs -Encoding UTF8
        Write-Host "  exit_type=Normal, exited_cleanly=true"
    }
    catch { Write-Warning "could not rewrite Preferences: $($_.Exception.Message)" }

    $sessions = Join-Path $ProfileRoot 'Default\Sessions'
    if (Test-Path $sessions) {
        Remove-Item -Path $sessions -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  removed Default\Sessions"
    }
}

# --- 1. copy (with Chrome fully stopped) ----------------------------------------
if ($Refresh -or -not (Test-Path $UserDataDir)) {
    if (-not (Test-Path $SrcUserData)) { throw "Chrome user data not found at $SrcUserData" }

    Write-Host "== preparing"
    if ($KeepChrome) {
        Write-Warning "-KeepChrome: locked Cookies/Login Data will not copy; the login is expected to be missing."
    } else {
        Stop-AllChrome
    }

    Write-Host "== copying"
    Write-Host "  from $SrcUserData"
    Write-Host "  to   $UserDataDir"
    if (Test-Path $Root) { Remove-Item -Path $Root -Recurse -Force }
    New-Item -ItemType Directory -Path $UserDataDir -Force | Out-Null
    # Copy the CONTENTS of "User Data" (not the folder itself).
    Copy-Item -Path (Join-Path $SrcUserData '*') -Destination $UserDataDir -Recurse -Force
}
else {
    Write-Host "== reusing existing debug profile at $UserDataDir (-Refresh to re-copy)"
}

Reset-CrashFlags -ProfileRoot $UserDataDir

# --- 2. verify the login actually came across ----------------------------------
Write-Host "== verifying copied profile"
$v = Test-CopiedProfile -ProfileRoot $UserDataDir -Host_ $ExpectedHost
if ($v.CookieDb) {
    Write-Host ("  cookie db: {0} ({1:N0} bytes, {2} '{3}' rows)" -f `
        (Split-Path $v.CookieDb -Leaf), $v.Size, $v.HostHits, $ExpectedHost)
}
if (-not $v.Ok) {
    foreach ($p in $v.Problems) { Write-Host "  FAIL: $p" -ForegroundColor Red }
    throw ("Copied profile does not carry the '$ExpectedHost' login. Fix the copy before " +
           "launching — otherwise Chrome just starts logged out. Run with -Refresh and make " +
           "sure Chrome is fully closed (tray icon too), or pass -KeepChrome to see the same failure.")
}
Write-Host "  OK: '$ExpectedHost' cookies present in the copy"

# --- 3. locate chrome.exe -------------------------------------------------------
if (-not $ChromePath) {
    $candidates = @()
    foreach ($base in @($env:PROGRAMFILES, ${env:PROGRAMFILES(X86)}, $env:LOCALAPPDATA)) {
        if ($base) { $candidates += (Join-Path $base 'Google\Chrome\Application\chrome.exe') }
    }
    $ChromePath = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $ChromePath) { throw "chrome.exe not found. Pass -ChromePath." }

# --- 4. launch ------------------------------------------------------------------
$flags = @(
    "--user-data-dir=$UserDataDir"
    "--remote-debugging-port=$Port"
    "--remote-debugging-address=127.0.0.1"
    "--remote-allow-origins=*"
    "--no-first-run"
    "--no-default-browser-check"
    "--disable-session-crashed-bubble"
    "--hide-crash-restore-bubble"
    "--disable-features=InfiniteSessionRestore,ChromeWhatsNewUI"
    "--disable-background-mode"
    # NOT --enable-automation: that shows the "controlled by automated test software" banner
)

Write-Host "== launching $ChromePath on port $Port"
Start-Process -FilePath $ChromePath -ArgumentList ($flags + $Url)

# --- 5. prove the port bound ----------------------------------------------------
$deadline = (Get-Date).AddSeconds(25)
$version  = $null
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 500
    try { $version = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/json/version" -TimeoutSec 2; break } catch { }
}

if ($version) {
    Write-Host "CDP is up on 127.0.0.1:$Port"
    Write-Host "  $($version.Browser)"
    Write-Host "  $($version.webSocketDebuggerUrl)"
    Write-Host "  attach: playwright.connect_over_cdp('http://127.0.0.1:$Port')"
}
else {
    Write-Warning ("No CDP listener on 127.0.0.1:$Port after 25s. Another Chrome likely already owns " +
                   "this --user-data-dir, or the port is taken.")
}
