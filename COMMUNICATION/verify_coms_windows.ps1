# verify_coms_windows.ps1 - run on the Windows host to confirm the COMS findings
#
# Written 2026-11-20 by subq (Linux). UNVERIFIED BY ME: there is no pwsh on the
# Linux host, so I could not execute a single line of this.
#
# REV 3 - ASCII-ONLY. A peer (kilo) found rev 2 was UTF-8 without a BOM, and
# PS 5.1 decodes a no-BOM file as ANSI, so the em-dashes and the UTF-8 probe
# payload became mojibake and broke parsing. Two fixes:
#   - every comment/string is now plain ASCII;
#   - the UTF-8 probe is BUILT FROM CODE POINTS at runtime ([char]0x2014 ...),
#     so the file stays ASCII while the payload it tests is still non-ASCII.
#     That is strictly better: the test no longer depends on the encoding of
#     its own source file.
#
# REV 2 - corrected after a peer audit. Three real defects in rev 1:
#   1. Test 7 was DESTRUCTIVE BY DESIGN: it published retained to a REAL peer
#      inbox to assert that such writes are guarded - asserting a guard by
#      exercising its absence, after the side effect. Now: a fabricated seat
#      nobody subscribes to, cleaned up, recorded INFO (guard absence is a
#      known open item, not a regression).
#   2. Test 4 tested the WRONG LAYER: it called mosquitto_pub -f directly, so it
#      could never detect the client's own trailing-newline loss, which lives in
#      coms send's command-substitution -> -m path. Now: both legs.
#   3. Retained topics were left behind and the UTF-8 probe was broadcast to
#      mentions/all. Now: dedicated topics, all cleared at the end.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File verify_coms_windows.ps1 -Agent <role>
#   pwsh -File verify_coms_windows.ps1 -Agent <role>

param(
    [string]$Agent = "verify",
    [string]$Coms  = "E:\AGENT_FOLDERFRAMEWORK\COMMUNICATION\coms.ps1",
    [string]$Broker = "192.168.2.52",
    [int]$Port = 1883
)

$ErrorActionPreference = "Continue"
$results = @()
$written = @()   # retained topics this script writes; all cleared at the end

function Record($name, $status, $detail) {
    $script:results += [pscustomobject]@{ Test = $name; Status = $status; Detail = $detail }
    Write-Host ("[{0}] {1} - {2}" -f $status, $name, $detail)
}

function Clear-Topic($topic) {
    if (Get-Command mosquitto_pub -ErrorAction SilentlyContinue) {
        & mosquitto_pub -h $Broker -p $Port -r -t $topic -m ''
        Write-Host "        cleared $topic"
    }
}

# ---------------------------------------------------------------- 0. context
Write-Host "=== 0. context ==="
Record "PS version" "INFO" ($PSVersionTable.PSVersion.ToString())
Record "CLI exists" $(if (Test-Path $Coms) { "PASS" } else { "FAIL" }) $Coms
$hasSub = $null -ne (Get-Command mosquitto_sub -ErrorAction SilentlyContinue)
$hasPub = $null -ne (Get-Command mosquitto_pub -ErrorAction SilentlyContinue)
Record "mosquitto sub/pub on PATH" $(if ($hasSub -and $hasPub) { "PASS" } else { "SKIP" }) "needed for readback tests"
if (-not (Test-Path $Coms)) { Write-Host "coms.ps1 not found - stopping"; exit 1 }

# ------------------------------------------------- 1. check does not crash
Write-Host "`n=== 1. check (UTF-8 + notes index) ==="
# Known open defect: on Windows PS 5.1 the notes-index python block can die with
# a SyntaxError because coms.ps1 passes it via `python -c` as ARGV, and PS 5.1
# mangles a multi-line string handed to a native exe. The Linux client feeds the
# same code over STDIN and is immune. A non-zero exit here is that defect.
$out = & $Coms check --agent $Agent 2>&1 | Out-String
$code = $LASTEXITCODE
Record "check exit code" $(if ($code -eq 0) { "PASS" } else { "FAIL" }) "exit=$code (argv-vs-stdin defect if the notes block raised)"
$nonAscii = ($out.ToCharArray() | Where-Object { [int]$_ -gt 127 }).Count
Record "check emitted non-ASCII text" "INFO" ("{0} non-ASCII chars survived" -f $nonAscii)
if ($out -match "note\(s\) on notes/#") {
    Record "check lists notes" "PASS" "notes index present"
} else {
    Record "check lists notes" "SKIP" "no notes matched, or index not in this build"
}

# ------------------------------------------------------- 2. topics enumerates
Write-Host "`n=== 2. topics ==="
$t = & $Coms topics --wait 3 2>&1 | Out-String
Record "topics exit code" $(if ($LASTEXITCODE -eq 0) { "PASS" } else { "FAIL" }) "exit=$LASTEXITCODE"
$prefixes = @{}
foreach ($line in ($t -split "`n")) {
    if ($line -match "^\s*(\d+)\s+(\S+)\s+(\d+)\s+topic") { $prefixes[$matches[2]] = $matches[1] }
}
Record "topics prefix rollup" "INFO" (($prefixes.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join " ")

# ------------------------------------------- 3. UTF-8 round trip (own topic)
Write-Host "`n=== 3. UTF-8 send ==="
# Built from code points so THIS FILE stays ASCII (PS 5.1 reads no-BOM as ANSI).
# em dash, plus-minus, en dash, e-acute, rocket
$probe = "utf8 probe " + [char]0x2014 + " B " + [char]0x00B1 + [char]0x2013 + [char]0x00E9 + " " + [char]0x1F680
$utf8T = "status/verify-utf8-$Agent"
$written += $utf8T
$sendOut = & $Coms send --retain $utf8T $probe 2>&1 | Out-String
Record "send non-ASCII payload" $(if ($sendOut -match "sent") { "PASS" } else { "FAIL" }) ("payload chars: {0}" -f $probe.Length)
if ($hasSub) {
    $back = & mosquitto_sub -h $Broker -p $Port -t $utf8T --retained-only -W 2 2>$null | Out-String
    Record "UTF-8 survives round trip" $(if ($back.Trim() -eq $probe) { "PASS" } else { "FAIL" }) ("read back {0} chars" -f $back.Trim().Length)
}

# ------------------------- 4. trailing newline - TWO legs (transport, client)
Write-Host "`n=== 4. trailing newline ==="
if (-not ($hasSub -and $hasPub)) {
    Record "trailing newline round trip" "SKIP" "mosquitto tools not on PATH"
} else {
    $tmpIn = [System.IO.Path]::GetTempFileName()
    $payload = "line-one`n`n"          # ends with TWO newlines
    [System.IO.File]::WriteAllText($tmpIn, $payload, (New-Object System.Text.UTF8Encoding($false)))
    $want = (Get-Item $tmpIn).Length

    # --- leg A: transport (direct pub/sub)
    $tA = "status/verify-nl-transport-$Agent"
    $written += $tA
    & mosquitto_pub -h $Broker -p $Port -q 1 -r -t $tA -f $tmpIn
    Start-Sleep -Milliseconds 500
    $tmpBack = [System.IO.Path]::GetTempFileName()
    & mosquitto_sub -h $Broker -p $Port -t $tA --retained-only -W 2 > $tmpBack
    # mosquitto_sub appends one newline; subtract it before comparing
    $gotA = (Get-Item $tmpBack).Length - 1
    Record "transport preserves trailing newline" $(if ($gotA -eq $want) { "PASS" } else { "FAIL" }) "sent $want bytes, read back $gotA"

    # --- leg B: the CLIENT. This is the leg rev 1 was missing. The known loss
    # is in coms send's command substitution, which strips trailing newlines.
    # ReadAllText keeps them, so a shortfall here is the client, not the caller.
    $tB = "status/verify-nl-client-$Agent"
    $written += $tB
    $raw = [System.IO.File]::ReadAllText($tmpIn)
    $clientOut = & $Coms send --retain $tB $raw 2>&1 | Out-String
    Start-Sleep -Milliseconds 500
    $lenB = (& mosquitto_sub -h $Broker -p $Port -t $tB --retained-only -W 2 -F '%l' 2>$null | Select-Object -First 1)
    if ($null -eq $lenB) {
        Record "client preserves trailing newline" "SKIP" "no readback"
    } else {
        Record "client preserves trailing newline" $(if ([int]$lenB -eq $want) { "PASS" } else { "FAIL" }) "source $want bytes, client published $lenB"
    }

    Remove-Item $tmpIn, $tmpBack -ErrorAction SilentlyContinue
}

# -------------------------------------- 5. large payload via -m (argv limit)
Write-Host "`n=== 5. large payload via -m ==="
if (-not $hasPub) {
    Record "500KB via -m" "SKIP" "mosquitto_pub not on PATH"
} else {
    $big = "B" * 500000
    $err = & mosquitto_pub -h $Broker -p $Port -q 1 -t "status/verify-big-$Agent" -m $big 2>&1 | Out-String
    if ($err -match "too long|Argument") {
        Record "500KB via -m" "INFO" "rejected - send should use -f above ~8KB"
    } else {
        Record "500KB via -m" "PASS" "accepted on this host (Windows argv limit differs from Linux)"
    }
}

# --------------------------------------------- 6. roster duplicates (upsert)
Write-Host "`n=== 6. roster duplicates ==="
$reg = Join-Path $env:USERPROFILE ".coms\agents.jsonl"
if (-not (Test-Path $reg)) {
    Record "roster duplicates" "SKIP" "no $reg on this host"
} else {
    $rows = @()
    foreach ($line in (Get-Content $reg)) {
        if ($line.Trim()) { try { $rows += ($line | ConvertFrom-Json) } catch { } }
    }
    $keys = $rows | ForEach-Object { "$($_.host)|$($_.worktree)|$($_.agent)" }
    $distinct = ($keys | Select-Object -Unique).Count
    $dups = $keys.Count - $distinct
    Record "roster rows vs seats" $(if ($dups -eq 0) { "PASS" } else { "FAIL" }) "$($keys.Count) rows, $distinct distinct, $dups duplicated"
    $top = $keys | Group-Object | Sort-Object Count -Descending | Select-Object -First 3
    foreach ($g in $top) { if ($g.Count -gt 1) { Write-Host ("        {0}x  {1}" -f $g.Count, $g.Name) } }
}

# ------------------------------------- 7. retain guard (NON-DESTRUCTIVE)
Write-Host "`n=== 7. retain guard on a foreign inbox ==="
# A seat nobody subscribes to measures the same thing and costs nothing. The
# guard's absence is a known open item, so it is INFO, not FAIL - a suite that
# fails on known-open work trains people to ignore it.
$probeT = "inbox/gx10-c9b9/coms-probe-wt/probe-agent"
$written += $probeT
$g = & $Coms send --retain $probeT "guard probe - safe fabricated seat" 2>&1 | Out-String
$guardExists = ($g -match "refus")
Record "retain guard on foreign inbox" $(if ($guardExists) { "PASS" } else { "INFO" }) "guard $(if ($guardExists) { 'present' } else { 'ABSENT on this build' }); probe topic will be cleared"

# ---------------------------------------------------------------- cleanup
Write-Host "`n=== cleanup ==="
foreach ($topic in $written) { Clear-Topic $topic }

# ---------------------------------------------------------------- summary
Write-Host "`n=== summary ==="
$results | Group-Object Status | ForEach-Object { Write-Host ("{0}: {1}" -f $_.Name, $_.Count) }
$fail = ($results | Where-Object { $_.Status -eq "FAIL" }).Count
Write-Host ""
if ($fail -gt 0) {
    Write-Host "$fail FAILING test(s):"
    $results | Where-Object { $_.Status -eq "FAIL" } | ForEach-Object { Write-Host ("  - {0}: {1}" -f $_.Test, $_.Detail) }
    exit 1
}
Write-Host "No failures. Paste this transcript into the COMS PR."
exit 0
