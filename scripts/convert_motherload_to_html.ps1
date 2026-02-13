# Convert MOTHERLOAD MD files to sanitized HTML
# Strips sensitive data (DB table names, SQL queries, IPs, keys, passwords)

$ROOT = "E:\findtorontoevents_antigravity.ca"
$OUT_DIR = "$ROOT\findstocks\ai-research"

# Ensure output directory exists
if (!(Test-Path $OUT_DIR)) { New-Item -ItemType Directory -Path $OUT_DIR -Force | Out-Null }

# Source files mapping: input path -> output filename, display title, AI model
$files = @(
    @{ In="$ROOT\ANTIGRAVITYMOTHERLOAD.MD"; Out="antigravity-motherload.html"; Title="Antigravity Motherload: Complete Trading Algorithm Analysis"; Model="Gemini 2.0 Flash Thinking Experimental"; Date="February 11, 2026" },
    @{ In="$ROOT\CHATGPT_CODEX_MOTHERLOAD.MD"; Out="chatgpt-codex-motherload.html"; Title="ChatGPT Codex Motherload: Strategy Roadmap"; Model="ChatGPT / OpenAI Codex"; Date="February 2026" },
    @{ In="$ROOT\DEEPSEEK_MOTHERLOAD.md"; Out="deepseek-motherload.html"; Title="DeepSeek Motherload: Algorithm Analysis & Enhancement Roadmap"; Model="DeepSeek V3.1 (671B)"; Date="February 11, 2026" },
    @{ In="$ROOT\GROK_XAI_MOTHERLOAD.MD"; Out="grok-xai-motherload.html"; Title="Grok xAI Motherload: Zero-Budget Quant Arsenal"; Model="Grok-4 (xAI)"; Date="February 12, 2026" },
    @{ In="$ROOT\GITHUB_MOTHERLOAD.MD"; Out="github-motherload.html"; Title="GitHub Motherload: Underdog vs. Big Players Strategy"; Model="GitHub Copilot"; Date="February 2026" },
    @{ In="$ROOT\OPUS46_MOTHERLOAD.MD"; Out="opus46-motherload.html"; Title="Opus 4.6 Motherload: Zero-Budget Quant Empire"; Model="Opus 4.6 (Anthropic)"; Date="February 12, 2026" },
    @{ In="$ROOT\KIMIMOTHERLOAD.MD"; Out="kimi-motherload.html"; Title="Kimi Motherload: Comprehensive Algorithm Review"; Model="Kimi AI"; Date="February 11, 2026" },
    @{ In="$ROOT\KIMI\KIMI_AGENTSWARM_MOTHERLOAD.md"; Out="kimi-agentswarm-motherload.html"; Title="Kimi Agent Swarm Motherload: The Underdog's Guide"; Model="Kimi AI (Agent Swarm)"; Date="February 2026" },
    @{ In="$ROOT\WINDSURF_MOTHERLOAD.MD"; Out="windsurf-motherload.html"; Title="Windsurf Motherload: Battle Plan vs. Wall Street"; Model="Windsurf Cascade AI"; Date="February 11, 2026" }
)

function Sanitize-Content {
    param([string]$content)
    
    # 1. Remove passwords
    $content = $content -replace 'POSTGRES_PASSWORD:\s*\S+', 'POSTGRES_PASSWORD: [REDACTED]'
    $content = $content -replace "password\s*[:=]\s*['\"]?[^'"";\s]+['\"]?", 'password: [REDACTED]'
    
    # 2. Remove API key values (but keep the concept)
    $content = $content -replace "API_KEY\s*=\s*'[^']*'", "API_KEY = '[REDACTED]'"
    $content = $content -replace "api_key\s*=\s*'[^']*'", "api_key = '[REDACTED]'"
    $content = $content -replace "key=API_KEY", "key=[API_KEY]"
    $content = $content -replace "key=\s*API_KEY", "key=[API_KEY]"
    
    # 3. Remove IP addresses (file references)
    $content = $content -replace '10_123_0_33', '[server]'
    $content = $content -replace '\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[server_ip]'
    
    # 4. Remove database names
    $content = $content -replace 'ejaguiar1_sportsbet', '[sports_database]'
    $content = $content -replace 'ejaguiar\w*', '[database]'
    
    # 5. Sanitize database table names - replace with generic descriptions
    $tableMap = @{
        'lm_signals' = '[signals_table]'
        'lm_trades' = '[trades_table]'
        'lm_market_regime' = '[regime_table]'
        'lm_kelly_fractions' = '[sizing_table]'
        'lm_algo_health' = '[health_table]'
        'lm_intelligence' = '[intelligence_table]'
        'lm_sports_daily_picks' = '[sports_picks_table]'
        'lm_sports_bets' = '[sports_bets_table]'
        'cp_signals' = '[crypto_signals_table]'
        'fx_signals' = '[forex_signals_table]'
        'gm_unified_picks' = '[unified_picks_table]'
        'algo_performance' = '[performance_table]'
        'daily_prices' = '[prices_table]'
        'stock_picks' = '[picks_table]'
        'market_data' = '[market_table]'
    }
    foreach ($key in $tableMap.Keys) {
        $content = $content -replace [regex]::Escape($key), $tableMap[$key]
    }
    
    # 6. Generic lm_* table pattern
    $content = $content -replace '\blm_\w+\b', '[internal_table]'
    
    # 7. Sanitize SQL queries in code blocks - leave structure but redact table refs
    $content = $content -replace "SELECT\s+\*\s+FROM\s+\S+", 'SELECT * FROM [table]'
    $content = $content -replace "SELECT\s+\w+\s+FROM\s+\S+", 'SELECT [columns] FROM [table]'
    $content = $content -replace "INSERT\s+INTO\s+\S+", 'INSERT INTO [table]'
    $content = $content -replace "CREATE\s+TABLE\s+\S+", 'CREATE TABLE [table]'
    
    # 8. Sanitize connection variable references with table names
    $content = $content -replace "db\.fetchall\([^)]*\)", 'db.fetch([query_redacted])'
    $content = $content -replace "db\.fetchone\([^)]*\)", 'db.fetch([query_redacted])'
    $content = $content -replace "db\.col\([^)]*\)", 'db.fetch([query_redacted])'
    $content = $content -replace "pd\.read_sql\([^)]*\)", 'pd.read_sql([query_redacted])'
    $content = $content -replace '\$db->query\([^)]*\)', '$db->query([query_redacted])'
    
    return $content
}

function Convert-MarkdownToHtml {
    param([string]$md)
    
    $lines = $md -split "`n"
    $html = New-Object System.Collections.Generic.List[string]
    $inCodeBlock = $false
    $codeLanguage = ""
    $inTable = $false
    $inList = $false
    $listType = ""
    
    foreach ($line in $lines) {
        $line = $line.TrimEnd("`r")
        
        # Code blocks
        if ($line -match '^```(\w*)') {
            if ($inCodeBlock) {
                $html.Add("</code></pre>")
                $inCodeBlock = $false
            } else {
                $codeLanguage = $Matches[1]
                $html.Add("<pre class='code-block'><code class='language-$codeLanguage'>")
                $inCodeBlock = $true
            }
            continue
        }
        
        if ($inCodeBlock) {
            $escapedLine = $line -replace '&', '&amp;' -replace '<', '&lt;' -replace '>', '&gt;'
            $html.Add($escapedLine)
            continue
        }
        
        # Tables
        if ($line -match '^\|') {
            if (-not $inTable) {
                $html.Add("<div class='table-wrapper'><table>")
                $inTable = $true
            }
            # Skip separator rows
            if ($line -match '^\|[\s\-:|]+\|$') { continue }
            
            $cells = ($line -split '\|' | Where-Object { $_ -ne '' }) | ForEach-Object { $_.Trim() }
            $tag = if ($html[-1] -match '<table>') { "th" } else { "td" }
            $row = "<tr>" + ($cells | ForEach-Object { "<$tag>$_</$tag>" }) -join '' + "</tr>"
            $html.Add($row)
            continue
        } elseif ($inTable) {
            $html.Add("</table></div>")
            $inTable = $false
        }
        
        # Close list if blank line
        if ($line -match '^\s*$' -and $inList) {
            $html.Add("</$listType>")
            $inList = $false
        }
        
        # Headers
        if ($line -match '^######\s+(.+)') { $html.Add("<h6>$($Matches[1])</h6>"); continue }
        if ($line -match '^#####\s+(.+)') { $html.Add("<h5>$($Matches[1])</h5>"); continue }
        if ($line -match '^####\s+(.+)') { $html.Add("<h4>$($Matches[1])</h4>"); continue }
        if ($line -match '^###\s+(.+)') { $html.Add("<h3>$($Matches[1])</h3>"); continue }
        if ($line -match '^##\s+(.+)') { $html.Add("<h2>$($Matches[1])</h2>"); continue }
        if ($line -match '^#\s+(.+)') { continue } # Skip H1, we use the title from metadata
        
        # Horizontal rules
        if ($line -match '^---+\s*$') { $html.Add("<hr>"); continue }
        
        # Lists  
        if ($line -match '^\s*[-*]\s+(.+)') {
            if (-not $inList -or $listType -ne 'ul') {
                if ($inList) { $html.Add("</$listType>") }
                $html.Add("<ul>")
                $inList = $true; $listType = 'ul'
            }
            $item = $Matches[1]
            $item = Format-InlineMarkdown $item
            $html.Add("<li>$item</li>")
            continue
        }
        if ($line -match '^\s*\d+\.\s+(.+)') {
            if (-not $inList -or $listType -ne 'ol') {
                if ($inList) { $html.Add("</$listType>") }
                $html.Add("<ol>")
                $inList = $true; $listType = 'ol'
            }
            $item = $Matches[1]
            $item = Format-InlineMarkdown $item
            $html.Add("<li>$item</li>")
            continue
        }
        
        # Blank lines
        if ($line -match '^\s*$') { continue }
        
        # Paragraphs
        $line = Format-InlineMarkdown $line
        $html.Add("<p>$line</p>")
    }
    
    # Close any open elements
    if ($inCodeBlock) { $html.Add("</code></pre>") }
    if ($inTable) { $html.Add("</table></div>") }
    if ($inList) { $html.Add("</$listType>") }
    
    return $html -join "`n"
}

function Format-InlineMarkdown {
    param([string]$text)
    
    # Bold
    $text = $text -replace '\*\*([^*]+)\*\*', '<strong>$1</strong>'
    $text = $text -replace '__([^_]+)__', '<strong>$1</strong>'
    
    # Italic 
    $text = $text -replace '\*([^*]+)\*', '<em>$1</em>'
    
    # Inline code
    $text = $text -replace '`([^`]+)`', '<code class="inline">$1</code>'
    
    # Links - convert MD links
    $text = $text -replace '\[([^\]]+)\]\(([^)]+)\)', '<a href="$2">$1</a>'
    
    # Emoji shortcuts
    $text = $text -replace ':white_check_mark:', '✅'
    $text = $text -replace ':x:', '❌'
    $text = $text -replace ':warning:', '⚠️'
    
    return $text
}

function Build-HtmlPage {
    param(
        [string]$title,
        [string]$model,
        [string]$date,
        [string]$bodyHtml
    )
    
    return @"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>$title | AI Deep Research | FTE Invest</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0e1a;
            color: #c8c8e0;
            min-height: 100vh;
            line-height: 1.7;
        }
        a { color: #6366f1; text-decoration: none; }
        a:hover { text-decoration: underline; color: #818cf8; }

        .top-bar {
            background: #08081a;
            border-bottom: 1px solid #1e1e3a;
            padding: 0.75rem 2rem;
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        .top-bar a { color: #8888aa; font-size: 0.85rem; }
        .top-bar a:hover { color: #e0e0f0; }

        .hero {
            background: linear-gradient(135deg, #12122a 0%, #1a1040 50%, #0a0e1a 100%);
            border-bottom: 1px solid #1e1e3a;
            padding: 3rem 2rem 2.5rem;
            text-align: center;
        }
        .hero h1 {
            font-size: 1.8rem;
            font-weight: 800;
            background: linear-gradient(135deg, #6366f1, #a78bfa, #22d3ee);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.6rem;
            line-height: 1.3;
        }
        .hero .meta {
            display: flex;
            justify-content: center;
            gap: 1.5rem;
            flex-wrap: wrap;
        }
        .hero .meta span {
            color: #8888aa;
            font-size: 0.85rem;
        }
        .hero .meta .model-badge {
            background: rgba(99, 102, 241, 0.15);
            color: #a78bfa;
            padding: 2px 10px;
            border-radius: 6px;
            font-weight: 600;
        }

        .container {
            max-width: 920px;
            margin: 0 auto;
            padding: 2rem 1.5rem 4rem;
        }

        h2 {
            font-size: 1.4rem;
            font-weight: 700;
            color: #e0e0f0;
            margin: 2.5rem 0 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #1e1e3a;
        }
        h3 {
            font-size: 1.15rem;
            font-weight: 600;
            color: #d0d0e8;
            margin: 2rem 0 0.75rem;
        }
        h4 {
            font-size: 1rem;
            font-weight: 600;
            color: #b0b0d0;
            margin: 1.5rem 0 0.5rem;
        }
        h5, h6 {
            font-size: 0.9rem;
            font-weight: 600;
            color: #9999bb;
            margin: 1rem 0 0.5rem;
        }

        p {
            margin: 0.75rem 0;
            font-size: 0.92rem;
            color: #aaaacc;
        }

        ul, ol {
            margin: 0.5rem 0 1rem 1.8rem;
            font-size: 0.92rem;
        }
        li {
            margin-bottom: 0.4rem;
            color: #aaaacc;
        }
        li strong { color: #e0e0f0; }

        .table-wrapper {
            overflow-x: auto;
            margin: 1rem 0;
            border-radius: 8px;
            border: 1px solid #1e1e3a;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.82rem;
        }
        th {
            background: #161630;
            color: #b0b0d0;
            font-weight: 700;
            text-align: left;
            padding: 10px 12px;
            border-bottom: 2px solid #2a2a4a;
            white-space: nowrap;
        }
        td {
            padding: 8px 12px;
            border-bottom: 1px solid #1a1a34;
            color: #aaaacc;
        }
        tr:hover td { background: rgba(99, 102, 241, 0.04); }

        pre.code-block {
            background: #0d0d20;
            border: 1px solid #1e1e3a;
            border-radius: 8px;
            padding: 1rem 1.2rem;
            margin: 1rem 0;
            overflow-x: auto;
            font-size: 0.82rem;
            line-height: 1.6;
        }
        pre.code-block code {
            color: #a78bfa;
            font-family: 'Fira Code', 'Cascadia Code', Consolas, monospace;
        }

        code.inline {
            background: rgba(99, 102, 241, 0.12);
            color: #a78bfa;
            padding: 1px 6px;
            border-radius: 4px;
            font-size: 0.85em;
            font-family: 'Fira Code', 'Cascadia Code', Consolas, monospace;
        }

        hr {
            border: none;
            border-top: 1px solid #1e1e3a;
            margin: 2rem 0;
        }

        strong { color: #e0e0f0; }

        .footer {
            text-align: center;
            color: #555577;
            font-size: 0.8rem;
            margin-top: 3rem;
            padding-top: 1.5rem;
            border-top: 1px solid #1e1e3a;
        }

        .redacted {
            background: rgba(245, 158, 11, 0.1);
            color: #f59e0b;
            padding: 1px 4px;
            border-radius: 3px;
            font-size: 0.85em;
        }

        @media (max-width: 700px) {
            .hero { padding: 2rem 1rem; }
            .hero h1 { font-size: 1.3rem; }
            .container { padding: 1rem; }
            table { font-size: 0.75rem; }
            th, td { padding: 6px 8px; }
        }
    </style>
</head>
<body>

<div class="top-bar">
    <a href="/findstocks/updates.html">&larr; Back to Updates</a>
    <a href="/findstocks/ai-research/">All AI Research</a>
</div>

<div class="hero">
    <h1>$title</h1>
    <div class="meta">
        <span class="model-badge">$model</span>
        <span>$date</span>
        <span>AI System Evaluation</span>
    </div>
</div>

<div class="container">
$bodyHtml

    <div class="footer">
        <p>This document was generated by an AI system as part of the Antigravity AI evaluation process. Security-sensitive information has been redacted.</p>
        <p style="margin-top: 0.5rem;">All trading data is from paper trading simulations. Not financial advice. Past performance does not guarantee future results.</p>
        <p style="margin-top: 0.5rem;">&copy; 2026 Antigravity &middot; <a href="/findstocks/updates.html">Updates</a></p>
    </div>
</div>

<script src="/findstocks/portfolio2/stock-nav.js"></script>
</body>
</html>
"@
}

# Process each file
$count = 0
foreach ($file in $files) {
    $count++
    Write-Host "[$count/9] Processing: $($file.In | Split-Path -Leaf)"
    
    if (!(Test-Path $file.In)) {
        Write-Host "  WARNING: File not found, skipping."
        continue
    }
    
    # Read content
    $content = Get-Content -Path $file.In -Raw -Encoding UTF8
    
    # Sanitize
    $sanitized = Sanitize-Content $content
    
    # Convert to HTML
    $bodyHtml = Convert-MarkdownToHtml $sanitized
    
    # Build full page
    $fullHtml = Build-HtmlPage -title $file.Title -model $file.Model -date $file.Date -bodyHtml $bodyHtml
    
    # Write output
    $outPath = "$OUT_DIR\$($file.Out)"
    $fullHtml | Out-File -FilePath $outPath -Encoding UTF8
    
    Write-Host "  -> Saved: $outPath"
}

# Create index page for ai-research directory
$indexHtml = @"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Deep Research | FTE Invest</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0e1a;
            color: #e0e0f0;
            min-height: 100vh;
            line-height: 1.6;
        }
        a { color: #6366f1; text-decoration: none; }
        a:hover { text-decoration: underline; color: #818cf8; }

        .top-bar {
            background: #08081a;
            border-bottom: 1px solid #1e1e3a;
            padding: 0.75rem 2rem;
        }
        .top-bar a { color: #8888aa; font-size: 0.85rem; }

        .hero {
            background: linear-gradient(135deg, #12122a 0%, #1a1040 50%, #0a0e1a 100%);
            border-bottom: 1px solid #1e1e3a;
            padding: 3rem 2rem 2.5rem;
            text-align: center;
        }
        .hero h1 {
            font-size: 2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #6366f1, #a78bfa, #22d3ee);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
        }
        .hero .subtitle { color: #8888aa; font-size: 1rem; }

        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem 1.5rem 3rem;
        }

        .card {
            background: #12122a;
            border: 1px solid #1e1e3a;
            border-radius: 12px;
            padding: 1.25rem 1.5rem;
            margin-bottom: 1rem;
            transition: border-color 0.2s, box-shadow 0.2s;
            display: block;
        }
        .card:hover {
            border-color: rgba(99, 102, 241, 0.5);
            box-shadow: 0 0 16px rgba(99, 102, 241, 0.1);
            text-decoration: none;
        }
        .card .title {
            font-size: 1.05rem;
            font-weight: 700;
            color: #e0e0f0;
            margin-bottom: 0.3rem;
        }
        .card .meta {
            font-size: 0.8rem;
            color: #8888aa;
        }
        .card .model-badge {
            display: inline-block;
            background: rgba(99, 102, 241, 0.15);
            color: #a78bfa;
            padding: 1px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-right: 8px;
        }
        .footer-note {
            text-align: center;
            color: #555577;
            font-size: 0.8rem;
            margin-top: 2rem;
            padding-top: 1.5rem;
            border-top: 1px solid #1e1e3a;
        }
        @media (max-width: 600px) {
            .hero { padding: 1.5rem 1rem; }
            .hero h1 { font-size: 1.5rem; }
            .container { padding: 1rem; }
        }
    </style>
</head>
<body>

<div class="top-bar">
    <a href="/findstocks/updates.html">&larr; Back to Updates</a>
</div>

<div class="hero">
    <h1>AI System Evaluation &amp; Deep Research</h1>
    <p class="subtitle">Comprehensive algorithm analysis by 9 different AI systems</p>
</div>

<div class="container">
    <a class="card" href="antigravity-motherload.html">
        <div class="title">Complete Trading Algorithm Analysis</div>
        <div class="meta"><span class="model-badge">Gemini 2.0 Flash</span> Industry standards comparison &amp; strategic roadmap &mdash; Feb 11, 2026</div>
    </a>
    <a class="card" href="windsurf-motherload.html">
        <div class="title">The Battle Plan vs. Wall Street's Supercomputers</div>
        <div class="meta"><span class="model-badge">Windsurf Cascade</span> 50+ upgrades, live data audit, gap analysis &mdash; Feb 11, 2026</div>
    </a>
    <a class="card" href="kimi-agentswarm-motherload.html">
        <div class="title">The Underdog's Guide to Competing with Billion-Dollar Firms</div>
        <div class="meta"><span class="model-badge">Kimi Agent Swarm</span> Agent swarm architecture, technical deep-dive &mdash; Feb 2026</div>
    </a>
    <a class="card" href="kimi-motherload.html">
        <div class="title">Comprehensive Algorithm Review vs. Industry Standards</div>
        <div class="meta"><span class="model-badge">Kimi AI</span> 23-algorithm inventory, performance analysis &mdash; Feb 11, 2026</div>
    </a>
    <a class="card" href="deepseek-motherload.html">
        <div class="title">Algorithm Analysis &amp; Enhancement Roadmap</div>
        <div class="meta"><span class="model-badge">DeepSeek V3.1 671B</span> Core problem analysis, phased implementation &mdash; Feb 11, 2026</div>
    </a>
    <a class="card" href="opus46-motherload.html">
        <div class="title">Zero-Budget Quant Empire vs. Wall Street Giants</div>
        <div class="meta"><span class="model-badge">Opus 4.6</span> Deep audit, 50 upgrades, free stack &mdash; Feb 12, 2026</div>
    </a>
    <a class="card" href="grok-xai-motherload.html">
        <div class="title">Zero-Budget Quant Arsenal &amp; Roadmap</div>
        <div class="meta"><span class="model-badge">Grok-4 (xAI)</span> Ready-to-execute code drafts, 100 upgrades &mdash; Feb 12, 2026</div>
    </a>
    <a class="card" href="github-motherload.html">
        <div class="title">Underdog vs. Big Players Strategy</div>
        <div class="meta"><span class="model-badge">GitHub Copilot</span> Strategic plan, advanced quant techniques &mdash; Feb 2026</div>
    </a>
    <a class="card" href="chatgpt-codex-motherload.html">
        <div class="title">Codex Strategy Roadmap</div>
        <div class="meta"><span class="model-badge">ChatGPT Codex</span> Phased roadmap, free data stack &mdash; Feb 2026</div>
    </a>

    <div class="footer-note">
        Security-sensitive information has been redacted from all documents.<br>
        All trading data is from paper trading simulations. Not financial advice.
    </div>
</div>

<script src="/findstocks/portfolio2/stock-nav.js"></script>
</body>
</html>
"@

$indexHtml | Out-File -FilePath "$OUT_DIR\index.html" -Encoding UTF8
Write-Host "`n[DONE] Created index page: $OUT_DIR\index.html"
Write-Host "Total files created: $($count + 1) (9 research pages + 1 index)"
