<#
.SYNOPSIS
    Fan-out swarm dispatcher: runs (PR x engine) review jobs in parallel,
    aggregates with merge-captain, optionally runs red-team pass.

    AutoResume prefers `python tools/swarm/session_manager.py list --json`
    (added 2026-05-03) and parses metadata_json.out_file directly to map
    sessions back to PRs. Falls back to the legacy table parser if --json
    is unavailable (older session_manager.py).

.EXAMPLE
    pwsh tools/swarm/swarm_dispatch.ps1 -Prs 669,676,665 -Engines claude,gemini,deepseek

.EXAMPLE
    # Resume an earlier review pass for the same PRs (manual session map).
    pwsh tools/swarm/swarm_dispatch.ps1 -Prs 669,676 -Engines claude,deepseek `
        -FromSessionsByPr @{ 669 = @{ deepseek = 'sid-abc'; claude = 'sid-xyz' };
                             676 = @{ deepseek = 'sid-qrs' } }

.EXAMPLE
    # Auto-resume: scan _sessions.db for the most recent active session per
    # (engine, PR) within the last 72h and reuse those.
    pwsh tools/swarm/swarm_dispatch.ps1 -Prs 669,676 -Engines claude,deepseek -AutoResume

.PARAMETER Prs
    Comma-separated PR numbers.

.PARAMETER Engines
    Engines to fan out per PR. Default: claude,gemini,deepseek.
    Supported: claude,gemini,opencode,kilo,copilot,deepseek,cerebras,xai,inception,ollama_cloud

.PARAMETER MaxParallel
    Throttle on concurrent worker jobs. Default 4.

.PARAMETER SkipMerge
    Skip merge-captain aggregation step.

.PARAMETER SkipRedteam
    Skip red-team pass.

.PARAMETER PromptFile
    Override default prompt template. Default: tools/swarm/prompts/pr_review_inline.md
    (the inline-diff template; expects {{PR_CAPTURE}} + {{PR_NUMBER}} placeholders).
    The legacy tools/swarm/prompts/pr_review.md is still available for
    backward-compat but will only work for shell-capable CLI engines
    (claude / gemini / opencode / kilo / copilot) that can run gh themselves.

.PARAMETER NoInlineCapture
    Disable server-side gh capture + inline embedding. Reverts to the
    legacy "every worker runs gh" flow (only safe for CLI engines with
    Bash tool access). Default: $false (capture + embed by default).

.PARAMETER RunDir
    Override output dir. Default: swarm_runs/<UTC-timestamp>

.PARAMETER FromSessionsByPr
    Hashtable of per-(PR, engine) session ids to resume from. Shape:
        @{ <pr-int> = @{ <engine-name> = '<session-id>'; ... }; ... }
    Any (PR, engine) pair without an entry runs fresh. Mutually exclusive with -AutoResume.

.PARAMETER PersistSessions
    When set (default $true), append --persist-session to every worker invocation
    so the round writes session rows to swarm_runs/_sessions.db. Pass
    -PersistSessions:$false to skip persistence (e.g., cheap dry runs).

.PARAMETER AutoResume
    Scan swarm_runs/_sessions.db (via session_manager.py) for the most-recent
    active session per (engine, PR) within the last 72h and use those as
    -FromSessionsByPr. Mutually exclusive with explicit -FromSessionsByPr.

.NOTES
    Workers are read-only. Comment posting is gated by comment_poster.ps1.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][int[]]$Prs,
    [string[]]$Engines = @('claude', 'gemini', 'deepseek'),
    [int]$MaxParallel = 4,
    [switch]$SkipMerge,
    [switch]$SkipRedteam,
    [string]$PromptFile = "$PSScriptRoot/prompts/pr_review_inline.md",
    [string]$RunDir,
    [hashtable]$FromSessionsByPr = @{},
    [switch]$PersistSessions = $true,
    [switch]$AutoResume,
    [switch]$NoInlineCapture
)

$ErrorActionPreference = 'Stop'

# Mutual-exclusivity guard: -AutoResume vs explicit -FromSessionsByPr.
if ($AutoResume -and $FromSessionsByPr -and $FromSessionsByPr.Count -gt 0) {
    throw "[swarm] -AutoResume and -FromSessionsByPr are mutually exclusive. Pick one."
}

$repoRoot = (Resolve-Path "$PSScriptRoot/../..").Path
$ts = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
if (-not $RunDir) { $RunDir = Join-Path $repoRoot "swarm_runs/$ts" }
New-Item -ItemType Directory -Path $RunDir -Force | Out-Null

$workerScript = Join-Path $repoRoot 'tools/swarm/worker_runner.py'
$validateScript = Join-Path $repoRoot 'tools/swarm/schema_validate.py'
$sessionMgrScript = Join-Path $repoRoot 'tools/swarm/session_manager.py'
$prCaptureScript = Join-Path $repoRoot 'tools/swarm/_pr_capture.py'
$prEmbedHelper = Join-Path $repoRoot 'tools/swarm/_pr_embed_helper.py'
$mergePrompt = Join-Path $repoRoot 'tools/swarm/prompts/merge_reviews.md'
$redteamPrompt = Join-Path $repoRoot 'tools/swarm/prompts/redteam.md'

function Resolve-SessionsForPRs {
    <#
    .SYNOPSIS
        Scan _sessions.db (via session_manager.py list) for the most-recent
        active session per (engine, PR) within the last 72h.
    .OUTPUTS
        Hashtable matching the shape of -FromSessionsByPr:
            @{ <pr-int> = @{ <engine> = '<session-id>'; ... }; ... }
    #>
    param(
        [Parameter(Mandatory = $true)][int[]]$Prs,
        [Parameter(Mandatory = $true)][string[]]$Engines
    )

    $result = @{}

    # Prefer --json mode (added 2026-05-03) for robustness; metadata_json is
    # already parsed into an object so we can read out_file directly without
    # a per-row `show` round-trip. Fall back to table parser if --json fails
    # (older session_manager.py that doesn't recognise the flag).
    $jsonOutput = & python $sessionMgrScript list --since-hours 72 --json 2>$null
    if ($LASTEXITCODE -eq 0 -and $jsonOutput) {
        try {
            $sessions = ($jsonOutput | Out-String) | ConvertFrom-Json
        } catch {
            $sessions = $null
            Write-Warning "[swarm] session_manager.py list --json parse failed: $($_.Exception.Message); falling back to table parser."
        }
        if ($sessions) {
            # JSON path — list is already ORDER BY last_used_utc DESC, first
            # hit per (engine, pr) wins.
            foreach ($s in $sessions) {
                $sid = "$($s.session_id)".Trim()
                $eng = "$($s.engine)".Trim()
                if (-not ($Engines -contains $eng)) { continue }
                if (-not $sid) { continue }

                # Pull out_file from parsed metadata_json (dict) and grep PR num.
                $outFile = $null
                if ($s.metadata_json -and $s.metadata_json.PSObject.Properties['out_file']) {
                    $outFile = "$($s.metadata_json.out_file)"
                }
                if (-not $outFile) { continue }
                $prMatch = ([regex]'pr_(\d+)\.[a-z_]+\.json').Match($outFile)
                if (-not $prMatch.Success) { continue }
                $prNum = [int]$prMatch.Groups[1].Value
                if (-not ($Prs -contains $prNum)) { continue }

                if (-not $result.ContainsKey($prNum)) { $result[$prNum] = @{} }
                if (-not $result[$prNum].ContainsKey($eng)) {
                    $result[$prNum][$eng] = $sid
                }
            }
            return $result
        }
    }

    # Fallback: legacy table parser.
    $listOutput = & python $sessionMgrScript list --since-hours 72 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "[swarm] session_manager.py list rc=$LASTEXITCODE; AutoResume yields empty map."
        return $result
    }

    # Table format produced by session_manager._print_table:
    #   session_id  engine  model  status  created_utc  last_used_utc  prompt_bytes
    #   ----------  ------  -----  ------  -----------  -------------  ------------
    #   <values...>
    # Followed by "(no rows)" or "<N> active session(s)." footer.
    $lines = @($listOutput | ForEach-Object { "$_" })
    if ($lines.Count -lt 2) { return $result }

    $headerIdx = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match '^\s*session_id\s+engine\b') { $headerIdx = $i; break }
    }
    if ($headerIdx -lt 0) { return $result }
    if (($headerIdx + 2) -ge $lines.Count) { return $result }
    # Skip header + separator row.
    $dataLines = @()
    for ($i = $headerIdx + 2; $i -lt $lines.Count; $i++) {
        $ln = $lines[$i]
        if ([string]::IsNullOrWhiteSpace($ln)) { break }
        if ($ln -match 'active session') { break }
        if ($ln -match '^\(no rows\)') { break }
        $dataLines += $ln
    }

    # Each PR (engine -> sid) — list is already ORDER BY last_used_utc DESC,
    # so the first hit per (engine, pr) wins.
    foreach ($ln in $dataLines) {
        # Whitespace-split: session_id engine model status created last_used prompt_bytes
        $cols = ($ln -split '\s{2,}') | Where-Object { $_ -ne '' }
        if ($cols.Count -lt 2) { continue }
        $sid = $cols[0].Trim()
        $eng = $cols[1].Trim()
        if (-not ($Engines -contains $eng)) { continue }

        # PR association: pull metadata_json via `show <sid>` and grep out_file path.
        # The list table doesn't carry metadata, so we fetch detail per-row.
        $showOut = & python $sessionMgrScript show $sid 2>&1
        if ($LASTEXITCODE -ne 0) { continue }
        $outFileMatch = ([regex]'pr_(\d+)\.[a-z_]+\.json').Match(($showOut -join "`n"))
        if (-not $outFileMatch.Success) { continue }
        $prNum = [int]$outFileMatch.Groups[1].Value
        if (-not ($Prs -contains $prNum)) { continue }

        if (-not $result.ContainsKey($prNum)) { $result[$prNum] = @{} }
        if (-not $result[$prNum].ContainsKey($eng)) {
            $result[$prNum][$eng] = $sid
        }
    }
    return $result
}

if ($AutoResume) {
    Write-Host "[swarm] -AutoResume scanning _sessions.db (last 72h) for $($Prs.Count) PR(s) x $($Engines.Count) engine(s)..."
    $FromSessionsByPr = Resolve-SessionsForPRs -Prs $Prs -Engines $Engines
    $resumePairCount = 0
    foreach ($prKey in $FromSessionsByPr.Keys) {
        $resumePairCount += @($FromSessionsByPr[$prKey].Keys).Count
    }
    Write-Host "[swarm] -AutoResume mapped $resumePairCount (PR, engine) resume pair(s)."
}

Write-Host "[swarm] run dir: $RunDir"
Write-Host "[swarm] PRs: $($Prs -join ',')  engines: $($Engines -join ',')"
Write-Host "[swarm] persist-sessions: $([bool]$PersistSessions)  resume-pairs: $((@($FromSessionsByPr.Keys) | Measure-Object).Count) PR(s)"

# Per-PR artifact capture (server-side gh) + prompt embedding. Done once
# per PR so every engine for that PR receives the same diff. API engines
# (deepseek/xai/cerebras/inception/ollama_cloud) cannot run shell --
# without this step they fabricate gh output from the title alone (see
# swarm_runs/PR_REVIEW_ABORTED.md, 2026-05-03 forensics).
#
# Skip capture only if -NoInlineCapture is set (legacy "every worker runs
# gh themselves" path -- safe only for shell-capable CLI engines).
$capturePerPr = @{}    # int -> path to captured json
$promptPerPr = @{}     # int -> path to per-PR rendered prompt sidecar
if (-not $NoInlineCapture) {
    Write-Host "[swarm] capturing PR artifacts server-side for $($Prs.Count) PR(s)..."
    foreach ($pr in $Prs) {
        $capPath = Join-Path $RunDir "pr_${pr}_capture.json"
        & python $prCaptureScript $pr --out-file $capPath 2>&1 | Out-File -FilePath (Join-Path $RunDir "_pr_${pr}_capture.log") -Encoding utf8
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path $capPath)) {
            Write-Warning "[swarm] PR #$pr capture failed (rc=$LASTEXITCODE); workers will see empty diff."
            # Write a minimal stub so embed_into_prompt does not crash.
            $stub = @{ pr = $pr; title = ""; body = ""; author = ""; base = ""; head = "";
                       files = @(); mergeable = "UNKNOWN"; diff = ""; checks = @() } | ConvertTo-Json
            Set-Content -Path $capPath -Value $stub -Encoding UTF8
        }
        $capturePerPr[$pr] = $capPath

        $perPromptPath = Join-Path $RunDir "pr_${pr}_prompt.md"
        & python $prEmbedHelper --template $PromptFile --capture $capPath --out $perPromptPath 2>&1 |
            Out-File -FilePath (Join-Path $RunDir "_pr_${pr}_embed.log") -Encoding utf8 -Append
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path $perPromptPath)) {
            Write-Warning "[swarm] PR #$pr embed failed (rc=$LASTEXITCODE); falling back to raw template."
            Copy-Item -Path $PromptFile -Destination $perPromptPath -Force
        }
        $promptPerPr[$pr] = $perPromptPath
    }
}

$plan = @()
foreach ($pr in $Prs) {
    # Per-PR effective prompt: inline-embedded sidecar when capture is on,
    # otherwise the raw template.
    $effectivePrompt = if ($promptPerPr.ContainsKey($pr)) { $promptPerPr[$pr] } else { $PromptFile }
    foreach ($eng in $Engines) {
        $outFile = Join-Path $RunDir "pr_${pr}.${eng}.json"
        $resumeSid = ''
        if ($FromSessionsByPr.ContainsKey($pr)) {
            $perPr = $FromSessionsByPr[$pr]
            if ($perPr -is [hashtable] -and $perPr.ContainsKey($eng)) {
                $resumeSid = [string]$perPr[$eng]
            }
        }
        $plan += [pscustomobject]@{
            Pr = $pr
            Engine = $eng
            OutFile = $outFile
            FromSession = $resumeSid
            PromptFile = $effectivePrompt
        }
    }
}

Write-Host "[swarm] dispatching $($plan.Count) jobs (max-parallel=$MaxParallel)"

$jobs = @()
foreach ($task in $plan) {
    while (@($jobs | Where-Object { $_.State -eq 'Running' }).Count -ge $MaxParallel) {
        Start-Sleep -Milliseconds 500
    }
    $job = Start-Job -ScriptBlock {
        param($repoRoot, $worker, $engine, $promptFile, $outFile, $pr, $fromSession, $persistSession)
        Set-Location $repoRoot
        $pyArgs = @(
            $worker,
            '--engine', $engine,
            '--prompt-file', $promptFile,
            '--out-file', $outFile,
            '--pr', $pr
        )
        if ($fromSession) {
            $pyArgs += @('--from-session', $fromSession)
        }
        if ($persistSession) {
            $pyArgs += '--persist-session'
        }
        & python @pyArgs 2>&1
        if ($LASTEXITCODE -ne 0) {
            "[swarm-job] python exit $LASTEXITCODE for engine=$engine pr=$pr"
        }
    } -ArgumentList $repoRoot, $workerScript, $task.Engine, $task.PromptFile, $task.OutFile, $task.Pr, $task.FromSession, [bool]$PersistSessions `
      -Name "swarm-pr$($task.Pr)-$($task.Engine)"
    $jobs += $job
}

Write-Host "[swarm] waiting for $($jobs.Count) workers..."
$jobs | Wait-Job | Out-Null
foreach ($j in $jobs) {
    Receive-Job -Job $j 2>&1 | Out-File -FilePath (Join-Path $RunDir "_job_$($j.Name).log") -Encoding utf8
    Remove-Job -Job $j -Force | Out-Null
}

# Schema-validate every output.
$validResults = @()
$invalidResults = @()
foreach ($task in $plan) {
    if (-not (Test-Path $task.OutFile)) {
        Write-Warning "[swarm] missing output: $($task.OutFile)"
        $invalidResults += $task.OutFile
        continue
    }
    $validateOut = & python $validateScript $task.OutFile 2>&1
    $rc = $LASTEXITCODE
    if ($rc -eq 0) {
        $validResults += $task.OutFile
    } else {
        Write-Warning "[swarm] schema-invalid: $($task.OutFile) :: $validateOut"
        $invalidResults += $task.OutFile
    }
}

Write-Host "[swarm] validation: $($validResults.Count) ok / $($invalidResults.Count) invalid"
# PowerShell ConvertTo-Json requires string keys for hashtable serialization;
# coerce int PR keys -> strings so $capturePerPr / $promptPerPr survive.
$captureFilesStr = @{}
foreach ($k in $capturePerPr.Keys) { $captureFilesStr["$k"] = $capturePerPr[$k] }
$perPrPromptStr = @{}
foreach ($k in $promptPerPr.Keys) { $perPrPromptStr["$k"] = $promptPerPr[$k] }

$summary = [pscustomobject]@{
    ts = $ts
    run_dir = $RunDir
    prs = $Prs
    engines = $Engines
    valid_files = $validResults
    invalid_files = $invalidResults
    plan = $plan
    persist_sessions = [bool]$PersistSessions
    auto_resume = [bool]$AutoResume
    inline_capture = (-not [bool]$NoInlineCapture)
    capture_files = $captureFilesStr
    per_pr_prompt_files = $perPrPromptStr
    prompt_template = $PromptFile
}
$summary | ConvertTo-Json -Depth 8 | Out-File -FilePath (Join-Path $RunDir '_summary.json') -Encoding utf8

if ($SkipMerge) {
    Write-Host "[swarm] -SkipMerge set, exiting after fan-out"
    return
}
if ($validResults.Count -eq 0) {
    Write-Warning "[swarm] no valid worker outputs; cannot run merge-captain"
    return
}

# Build merge-captain payload.
$mergeInputPath = Join-Path $RunDir '_merge_input.md'
$fence = '```'
$mergeBody = New-Object System.Collections.Generic.List[string]
$mergeBody.Add((Get-Content $mergePrompt -Raw))
$mergeBody.Add("`n## Worker outputs to consolidate`n")
foreach ($f in $validResults) {
    $leaf = Split-Path $f -Leaf
    $mergeBody.Add("`n### $leaf`n${fence}json")
    $mergeBody.Add((Get-Content $f -Raw))
    $mergeBody.Add($fence)
}
($mergeBody -join "`n") | Out-File -FilePath $mergeInputPath -Encoding utf8

$mergeOut = Join-Path $RunDir 'final_merge_plan.json'
Write-Host "[swarm] running merge-captain (claude opus)..."
$mergeArgs = @(
    $workerScript,
    '--engine', 'claude',
    '--prompt-file', $mergeInputPath,
    '--out-file', $mergeOut,
    '--model', 'opus'
)
if ($PersistSessions) { $mergeArgs += '--persist-session' }
& python @mergeArgs 2>&1 | Out-File (Join-Path $RunDir '_merge.log') -Encoding utf8

if (-not $SkipRedteam -and (Test-Path $mergeOut)) {
    $redteamInputPath = Join-Path $RunDir '_redteam_input.md'
    $redteamBody = @(
        (Get-Content $redteamPrompt -Raw),
        "`n## Aggregated plan to verify`n",
        "${fence}json",
        (Get-Content $mergeOut -Raw),
        $fence
    )
    ($redteamBody -join "`n") | Out-File -FilePath $redteamInputPath -Encoding utf8

    $redteamOut = Join-Path $RunDir 'redteam.json'
    Write-Host "[swarm] running fabrication-red-team (claude opus)..."
    $redteamArgs = @(
        $workerScript,
        '--engine', 'claude',
        '--prompt-file', $redteamInputPath,
        '--out-file', $redteamOut,
        '--model', 'opus'
    )
    if ($PersistSessions) { $redteamArgs += '--persist-session' }
    & python @redteamArgs 2>&1 | Out-File (Join-Path $RunDir '_redteam.log') -Encoding utf8
}

Write-Host "[swarm] done. Run dir: $RunDir"
Write-Host "[swarm] To post comments: pwsh tools/swarm/comment_poster.ps1 -RunDir '$RunDir'"

# ---- next-steps reminder ----------------------------------------------------
# Surface follow-up options (resume, red-team, persona, etc.) so operators don't
# have to remember the flag list. Long-form details:
# tools/swarm/POST_RUN_OPTIONS.md.
function Write-NextStepsFooter {
    param(
        [Parameter(Mandatory = $true)][string]$RunDir,
        [Parameter(Mandatory = $true)][int]$ValidCount,
        [Parameter(Mandatory = $true)][int]$InvalidCount,
        [Parameter(Mandatory = $true)][int[]]$Prs,
        [Parameter(Mandatory = $true)][string[]]$Engines
    )
    $total = $ValidCount + $InvalidCount
    $prsCsv = ($Prs -join ',')
    $engCsv = ($Engines -join ',')
    Write-Host ""
    Write-Host "[swarm-dispatch] complete. valid=$ValidCount/$total dir=$RunDir"
    Write-Host ""
    Write-Host "NEXT STEPS (see tools/swarm/POST_RUN_OPTIONS.md for details):"
    Write-Host "  1. Inspect outputs      python tools/swarm/swarm_inspect.py $RunDir"
    Write-Host "  2. Post comments        pwsh tools/swarm/comment_poster.ps1 -RunDir '$RunDir' -DryRun"
    Write-Host "                          pwsh tools/swarm/comment_poster.ps1 -RunDir '$RunDir'"
    Write-Host "  3. Auto-resume same PRs pwsh tools/swarm/swarm_dispatch.ps1 -Prs $prsCsv -Engines $engCsv -AutoResume"
    Write-Host "  4. Resume one dissenter python tools/swarm/worker_runner.py --engine <eng> --from-session <sid> --prompt-file <followup.md> --persist-session"
    Write-Host "  5. Red-team again       re-run with red-team prompt (omit -SkipRedteam) or invoke claude opus directly on final_merge_plan.json"
    Write-Host "  6. Multi-turn deep-dive python tools/swarm/swarm_followup.py --config tools/swarm/examples/<x>.yaml"
    Write-Host "  7. Switch engine bundle pwsh tools/swarm/swarm_dispatch.ps1 -Prs $prsCsv -Engines claude,kilo,deepseek"
    Write-Host ""
    Write-Host "Active sessions:  python tools/swarm/session_manager.py list"
    Write-Host "Stats / drift:    python tools/swarm/swarm_stats.py"
}

try {
    Write-NextStepsFooter -RunDir $RunDir `
        -ValidCount ([int]$validResults.Count) `
        -InvalidCount ([int]$invalidResults.Count) `
        -Prs $Prs `
        -Engines $Engines
} catch {
    Write-Warning "[swarm] footer print failed: $($_.Exception.Message)"
}
