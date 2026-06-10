# Restore Copilot BYOK providers with real API keys from dbpasses.txt.
# Fixes empty DeepSeek url (Autopilot request errors) WITHOUT stripping other providers.
# Run in WINDOWS PowerShell (Win+X -> Terminal), NOT the SSH terminal.

param(
    [ValidateSet('reset', 'all')]
    [string]$Mode = 'all'
)

$ErrorActionPreference = 'Stop'

function Find-DbpassesPath {
    $candidates = @(
        (Join-Path $env:USERPROFILE 'dbpasses.txt'),
        '\\wsl.localhost\gx10-c9b9\home\eaguiar2015\dbpasses.txt',
        '\\wsl$\gx10-c9b9\home\eaguiar2015\dbpasses.txt',
        '\\wsl.localhost\eltonsGX10\home\eaguiar2015\dbpasses.txt',
        '\\wsl$\eltonsGX10\home\eaguiar2015\dbpasses.txt',
        'E:\findtorontoevents_antigravity.ca\..\dbpasses.txt',
        (Join-Path $PSScriptRoot '..\dbpasses.txt')
    ) | ForEach-Object { [System.IO.Path]::GetFullPath($_) } | Select-Object -Unique

    foreach ($path in $candidates) {
        if (Test-Path -LiteralPath $path) { return $path }
    }
    throw "dbpasses.txt not found. Copy to $env:USERPROFILE or ensure WSL gx10 path is reachable."
}

function Get-KeyAfterLabel {
    param([string[]]$Lines, [string]$Label, [string]$Pattern)
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        $lineLabel = $Lines[$i].Trim().TrimEnd(':').Trim()
        $wantLabel = $Label.Trim().TrimEnd(':').Trim()
        if ($lineLabel -ne $wantLabel) { continue }
        for ($j = $i + 1; $j -lt [Math]::Min($i + 4, $Lines.Count); $j++) {
            $candidate = $Lines[$j].Trim()
            if ($candidate -and $candidate -match $Pattern) { return $candidate }
        }
    }
    return $null
}

function Get-AllKeys {
    $path = Find-DbpassesPath
    Write-Host "Reading keys from $path"
    $lines = Get-Content -LiteralPath $path
    $keys = [ordered]@{}
    $specs = @(
        @{ Label = 'OPEN ROUTER API KEY'; Name = 'openrouter'; Pattern = '^sk-or-' },
        @{ Label = 'GROK NEW2'; Name = 'xai'; Pattern = '^xai-' },
        @{ Label = 'GROK NEW'; Name = 'xai'; Pattern = '^xai-' },
        @{ Label = 'ANTR_MAY2026'; Name = 'anthropic'; Pattern = '^sk-ant-' },
        @{ Label = 'ANTR'; Name = 'anthropic'; Pattern = '^sk-ant-' },
        @{ Label = 'DEEPSEEK_API'; Name = 'deepseek'; Pattern = '^sk-' }
    )
    foreach ($spec in $specs) {
        if ($keys.Contains($spec.Name)) { continue }
        $val = Get-KeyAfterLabel -Lines $lines -Label $spec.Label -Pattern $spec.Pattern
        if ($val) { $keys[$spec.Name] = $val }
    }
    if (-not $keys['deepseek']) {
        throw 'DEEPSEEK_API key missing in dbpasses.txt'
    }
    return $keys
}

$path = Join-Path $env:APPDATA 'Code\User\chatLanguageModels.json'
if (Test-Path $path) {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    Copy-Item -LiteralPath $path -Destination "$path.bak-$stamp" -Force
    Write-Host "Backup: $path.bak-$stamp"
}

if ($Mode -eq 'reset') {
    $json = '[]'
} else {
    $keys = Get-AllKeys
    $obj = @()

    if ($keys['openrouter']) {
        $obj += @{ name = 'OpenRouter'; vendor = 'openrouter'; apiKey = $keys['openrouter'] }
    }
    if ($keys['xai']) {
        $obj += @{ name = 'xAI'; vendor = 'xai'; apiKey = $keys['xai'] }
    }
    if ($keys['anthropic']) {
        $obj += @{ name = 'Anthropic'; vendor = 'anthropic'; apiKey = $keys['anthropic'] }
    }

    $obj += @{
        name = 'DeepSeek'
        vendor = 'customendpoint'
        apiKey = $keys['deepseek']
        apiType = 'chat-completions'
        models = @(
            @{
                id = 'deepseek-v4-pro'
                name = 'DeepSeek V4 Pro'
                url = 'https://api.deepseek.com/chat/completions'
                toolCalling = $true
                vision = $false
                thinking = $true
                maxInputTokens = 128000
                maxOutputTokens = 8192
                supportsReasoningEffort = @('low', 'medium', 'high')
            },
            @{
                id = 'deepseek-v4-flash'
                name = 'DeepSeek V4 Flash'
                url = 'https://api.deepseek.com/chat/completions'
                toolCalling = $true
                vision = $false
                thinking = $true
                maxInputTokens = 128000
                maxOutputTokens = 8192
                supportsReasoningEffort = @('low', 'medium', 'high')
            }
        )
    }

    $json = $obj | ConvertTo-Json -Depth 8
}

if ($PSVersionTable.PSVersion.Major -ge 7) {
    Set-Content -LiteralPath $path -Value $json -Encoding utf8NoBOM
} else {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($path, $json, $utf8NoBom)
}

Write-Host "Wrote $path"
if ($Mode -eq 'all') {
    Write-Host 'Providers restored with inline keys from dbpasses.txt (OpenRouter, xAI, Anthropic, DeepSeek).'
}
Write-Host 'Next: Developer: Reload Window'