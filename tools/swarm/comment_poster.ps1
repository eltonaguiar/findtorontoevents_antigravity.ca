<#
.SYNOPSIS
    Reads final_merge_plan.json and optional redteam.json from a swarm run,
    prints proposed comment per PR, prompts y/N, and posts via gh.

.EXAMPLE
    pwsh tools/swarm/comment_poster.ps1 -RunDir swarm_runs/20260503T120000Z

.PARAMETER RunDir
    Path to a swarm run directory.

.PARAMETER DryRun
    Print proposed comments only.

.NOTES
    The ONLY swarm process with GH write permission. Each PR gated
    individually by interactive y/N.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$RunDir,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$mergePath = Join-Path $RunDir 'final_merge_plan.json'
$redteamPath = Join-Path $RunDir 'redteam.json'

if (-not (Test-Path $mergePath)) {
    Write-Error "missing $mergePath"
    return
}

$plan = Get-Content $mergePath -Raw | ConvertFrom-Json
$redteam = $null
if (Test-Path $redteamPath) {
    $redteam = Get-Content $redteamPath -Raw | ConvertFrom-Json
}

if (-not $plan.prs) {
    Write-Warning "no prs[] in plan"
    return
}

$ghCmd = Get-Command gh -ErrorAction Stop

foreach ($entry in $plan.prs) {
    $pr = $entry.pr
    $verdict = $entry.final_verdict
    $body = $entry.final_commentary_text
    if (-not $body) { continue }

    if ($redteam) {
        $rt = $redteam.pr_results | Where-Object { $_.pr -eq $pr }
        if ($rt) {
            $rtNotes = ($rt.concerns | ForEach-Object { "- [$($_.verdict)] $($_.claim)" }) -join "`n"
            if ($rtNotes) {
                $body += "`n`n---`n_Red-team verification:_`n$rtNotes"
            }
        }
    }

    Write-Host ""
    Write-Host "================================================================="
    Write-Host "PR #$pr  ::  verdict=$verdict"
    Write-Host "================================================================="
    Write-Host $body
    Write-Host "================================================================="
    if ($DryRun) {
        Write-Host "[dry-run] would post above comment to PR #$pr"
        continue
    }
    $resp = Read-Host "Post this comment to PR #$pr ? (y/N)"
    if ($resp -ne 'y' -and $resp -ne 'Y') {
        Write-Host "[skip] PR #$pr"
        continue
    }

    $tmp = New-TemporaryFile
    try {
        $body | Out-File -FilePath $tmp.FullName -Encoding utf8
        & $ghCmd.Source pr comment $pr --body-file $tmp.FullName
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "[fail] gh pr comment $pr exit $LASTEXITCODE"
        } else {
            Write-Host "[posted] PR #$pr"
        }
    } finally {
        Remove-Item $tmp.FullName -ErrorAction SilentlyContinue
    }
}
