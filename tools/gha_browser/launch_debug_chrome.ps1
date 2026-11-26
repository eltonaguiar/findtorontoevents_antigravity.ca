<#
.SYNOPSIS
    Launch Chrome with a CDP debugging port on a dedicated copy of your profile,
    without the first-run / sign-in / "Restore pages?" / crash-bubble popups.

.DESCRIPTION
    Why the naive version pops up on every launch:

    1. Path level. `Copy-Item -Path "$env:LOCALAPPDATA\Google\Chrome\User Data"
       -Destination "$env:USERPROFILE\.chrome-debug-profile" -Recurse` puts the source
       directory INSIDE the destination, i.e. the profile really ends up at
       `.chrome-debug-profile\User Data`. Launching with
       `--user-data-dir=$env:USERPROFILE\.chrome-debug-profile` then points Chrome at a
       directory that has no `Default\`, so it creates a blank profile => welcome /
       sign-in / "make Chrome your default" popups, and none of your logins.
       $UserDataDir is computed correctly below.

    2. Crash state. A copied profile inherits `profile.exit_type = "Crashed"` from the
       live one (Chrome writes that on every unclean shutdown). Chrome then shows the
       "Restore pages?" bubble on EVERY launch. -ResetCrashFlags clears it.

    3. Chrome 136+ ignores --remote-debugging-port unless --user-data-dir is also
       given, so the dedicated profile is required rather than merely tidy.

    4. Debugging against the DEFAULT profile while Chrome is already running just opens
       a tab in the existing process and the port never binds. A separate
       --user-data-dir makes the second instance possible; --disable-background-mode
       stops a lingering instance from silently stealing it next time.

.PARAMETER Refresh
    Re-copy the profile from the live Chrome user data (do this while Chrome is closed).
    Without it, an existing debug profile is reused as-is.

.PARAMETER Port
    CDP port. Default 9222.

.EXAMPLE
    ./launch_debug_chrome.ps1
    ./launch_debug_chrome.ps1 -Refresh -Url https://github.com/login
#>
[CmdletBinding()]
param(
    [int]$Port = 9222,
    [switch]$Refresh,
    [switch]$SkipRunningCheck,
    [string]$ChromePath,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Url
)

$ErrorActionPreference = 'Stop'

$SrcUserData = Join-Path $env:LOCALAPPDATA 'Google\Chrome\User Data'
$Root        = Join-Path $env:USERPROFILE '.chrome-debug-profile'
$UserDataDir = Join-Path $Root 'User Data'   # see note 1 in .DESCRIPTION

function Reset-CrashFlags {
    param([string]$ProfileRoot)

    $prefs = Join-Path $ProfileRoot 'Default\Preferences'
    if (-not (Test-Path $prefs)) {
        Write-Warning "No Default\Preferences under $ProfileRoot - skipping crash-flag reset."
        return
    }
    try {
        $json = Get-Content -Path $prefs -Raw | ConvertFrom-Json
        if (-not $json.PSObject.Properties['profile']) {
            $json | Add-Member -NotePropertyName profile -NotePropertyValue ([pscustomobject]@{})
        }
        $json.profile | Add-Member -NotePropertyName exit_type      -NotePropertyValue 'Normal' -Force
        $json.profile | Add-Member -NotePropertyName exited_cleanly -NotePropertyValue $true    -Force
        $json | ConvertTo-Json -Depth 100 -Compress | Set-Content -Path $prefs -Encoding UTF8
        Write-Host "  cleared crash/restore flags in Default\Preferences"
    }
    catch {
        Write-Warning "Could not rewrite $prefs ($($_.Exception.Message)). The --hide-crash-restore-bubble flag still suppresses the bubble."
    }

    # Saved tab sets are what the restore bubble wants to reopen.
    $sessions = Join-Path $ProfileRoot 'Default\Sessions'
    if (Test-Path $sessions) {
        Remove-Item -Path $sessions -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  removed Default\Sessions"
    }
}

# --- 1. copy the profile (once) -------------------------------------------------
if ($Refresh -or -not (Test-Path $UserDataDir)) {
    if (-not (Test-Path $SrcUserData)) { throw "Chrome user data not found at $SrcUserData" }

    $chromeRunning = @(Get-Process chrome -ErrorAction SilentlyContinue).Count -gt 0
    if ($chromeRunning -and -not $SkipRunningCheck) {
        throw ("Chrome is running. Close every Chrome window first: Cookies, History and " +
               "Preferences are locked, so a live copy is partial and the new profile " +
               "behaves unpredictably. Re-run with -SkipRunningCheck to copy anyway.")
    }

    Write-Host "Copying profile:"
    Write-Host "  from $SrcUserData"
    Write-Host "  to   $UserDataDir"
    if (Test-Path $Root) { Remove-Item -Path $Root -Recurse -Force }
    New-Item -ItemType Directory -Path $UserDataDir -Force | Out-Null
    # Copy the CONTENTS of "User Data" into $UserDataDir, not the folder itself.
    Copy-Item -Path (Join-Path $SrcUserData '*') -Destination $UserDataDir -Recurse -Force
}
else {
    Write-Host "Reusing existing debug profile at $UserDataDir (-Refresh to re-copy)."
}

Reset-CrashFlags -ProfileRoot $UserDataDir

# --- 2. locate chrome.exe -------------------------------------------------------
if (-not $ChromePath) {
    # Built one at a time: Join-Path throws on a null base, and PROGRAMFILES(X86) is
    # undefined on some installs.
    $candidates = @()
    foreach ($base in @($env:PROGRAMFILES, ${env:PROGRAMFILES(X86)}, $env:LOCALAPPDATA)) {
        if ($base) { $candidates += (Join-Path $base 'Google\Chrome\Application\chrome.exe') }
    }
    $ChromePath = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $ChromePath) { throw "chrome.exe not found. Pass -ChromePath." }

# --- 3. launch ------------------------------------------------------------------
$flags = @(
    "--user-data-dir=$UserDataDir"
    "--remote-debugging-port=$Port"
    "--remote-debugging-address=127.0.0.1"
    "--remote-allow-origins=*"            # CDP clients that send an Origin header
    "--no-first-run"
    "--no-default-browser-check"
    "--disable-session-crashed-bubble"    # the "Chrome didn't shut down correctly" bar
    "--hide-crash-restore-bubble"         # the "Restore pages?" bubble
    "--disable-features=InfiniteSessionRestore,ChromeWhatsNewUI"
    "--disable-background-mode"           # don't linger and hold the port
    # deliberately NOT --enable-automation: that is what shows the
    # "Chrome is being controlled by automated test software" banner
)

Write-Host "Launching $ChromePath on port $Port"
Start-Process -FilePath $ChromePath -ArgumentList ($flags + $Url)

# --- 4. prove the port actually bound (the silent failure mode) ------------------
$deadline = (Get-Date).AddSeconds(25)
$version  = $null
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 500
    try {
        $version = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/json/version" -TimeoutSec 2
        break
    }
    catch { }
}

if ($version) {
    Write-Host "CDP is up on 127.0.0.1:$Port"
    Write-Host "  $($version.Browser)"
    Write-Host "  ws: $($version.webSocketDebuggerUrl)"
    Write-Host "  attach: playwright.connect_over_cdp('http://127.0.0.1:$Port')"
}
else {
    Write-Warning ("No CDP listener on 127.0.0.1:$Port after 25s. Usually means another " +
                   "Chrome instance already owns this --user-data-dir, or the port is taken. " +
                   "Check: Get-Process chrome | Select-Object Id,MainWindowTitle")
}
