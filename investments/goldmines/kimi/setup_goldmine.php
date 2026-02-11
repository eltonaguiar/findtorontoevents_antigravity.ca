<?php
/**
 * KIMI Goldmine Setup Wizard
 * One-click setup for the goldmine system
 */
?>
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>KIMI Goldmine Setup</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0f;
            color: #fff;
            padding: 2rem;
            max-width: 800px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .logo {
            font-size: 2rem;
            background: linear-gradient(135deg, #ffd700, #ffaa00);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 700;
        }
        .step {
            background: #12121a;
            border: 1px solid #2a2a3a;
            border-radius: 0.5rem;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }
        .step-header {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1rem;
            font-weight: 600;
        }
        .step-number {
            background: #ffd700;
            color: #0a0a0f;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
        }
        .btn {
            background: #ffd700;
            color: #0a0a0f;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 0.5rem;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            margin-top: 0.5rem;
        }
        .btn:hover {
            opacity: 0.9;
        }
        .status {
            padding: 0.75rem;
            border-radius: 0.5rem;
            margin-top: 0.75rem;
            font-size: 0.875rem;
        }
        .status-success {
            background: rgba(0, 200, 83, 0.2);
            color: #00c853;
        }
        .status-error {
            background: rgba(255, 23, 68, 0.2);
            color: #ff1744;
        }
        .status-info {
            background: rgba(0, 176, 255, 0.2);
            color: #00b0ff;
        }
        code {
            background: #1a1a25;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-family: 'Courier New', monospace;
            font-size: 0.875rem;
        }
        .cron-list {
            background: #1a1a25;
            padding: 1rem;
            border-radius: 0.5rem;
            margin-top: 0.75rem;
        }
        .cron-list code {
            display: block;
            margin-bottom: 0.5rem;
            word-break: break-all;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🏆 KIMI GOLDMINE</div>
        <h2>Setup Wizard</h2>
        <p style="color: #a0a0b0;">Hidden Winners Discovery System</p>
    </div>

    <!-- Step 1: Database Setup -->
    <div class="step">
        <div class="step-header">
            <span class="step-number">1</span>
            <span>Create Database Tables</span>
        </div>
        <p style="color: #a0a0b0; margin-bottom: 1rem;">
            This will create all KIMI_GOLDMINE_* tables and populate default sources.
        </p>
        <button class="btn" onclick="runSetup('schema')">Run Schema Setup</button>
        <div id="schema-status"></div>
    </div>

    <!-- Step 2: Initial Data Collection -->
    <div class="step">
        <div class="step-header">
            <span class="step-number">2</span>
            <span>Import Existing Picks</span>
        </div>
        <p style="color: #a0a0b0; margin-bottom: 1rem;">
            Import all existing predictions from stocks, crypto, sports, and other sources.
        </p>
        <button class="btn" onclick="runSetup('collect')">Collect All Data</button>
        <div id="collect-status"></div>
    </div>

    <!-- Step 3: Calculate Performance -->
    <div class="step">
        <div class="step-header">
            <span class="step-number">3</span>
            <span>Calculate Performance Metrics</span>
        </div>
        <p style="color: #a0a0b0; margin-bottom: 1rem;">
            Generate performance statistics for all sources and periods.
        </p>
        <button class="btn" onclick="runSetup('performance')">Calculate Performance</button>
        <div id="performance-status"></div>
    </div>

    <!-- Step 4: Find Winners -->
    <div class="step">
        <div class="step-header">
            <span class="step-number">4</span>
            <span>Discover Winners</span>
        </div>
        <p style="color: #a0a0b0; margin-bottom: 1rem;">
            Scan for picks that have achieved exceptional returns.
        </p>
        <button class="btn" onclick="runSetup('winners')">Find Winners</button>
        <div id="winners-status"></div>
    </div>

    <!-- Step 5: GitHub Actions (Recommended) -->
    <div class="step">
        <div class="step-header">
            <span class="step-number">5</span>
            <span>Enable GitHub Actions (Recommended - No Cron Jobs!)</span>
        </div>
        <p style="color: #a0a0b0; margin-bottom: 1rem;">
            GitHub Actions collects data automatically - no server cron jobs needed!
        </p>
        <div class="cron-list">
            <p style="color: #00c853; margin-bottom: 0.5rem;">✅ Data collection runs every 15 minutes (FREE)</p>
            <p style="color: #a0a0b0; font-size: 0.875rem;">
                The GitHub Actions workflow is already configured in the repository.<br>
                It will automatically collect picks and save them as JSON files.<br>
                The client dashboard fetches directly from GitHub - no server load!
            </p>
            <br>
            <a href="https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions" target="_blank" class="btn" style="background: #22c55e;">View GitHub Actions</a>
        </div>
    </div>

    <!-- Step 6: Access Dashboard -->
    <div class="step">
        <div class="step-header">
            <span class="step-number">6</span>
            <span>Access Your Dashboard</span>
        </div>
        <p style="color: #a0a0b0; margin-bottom: 1rem;">
            Your goldmine dashboard is ready!
        </p>
        <a href="kimi-goldmine.html" class="btn">🚀 Launch Dashboard</a>
    </div>

    <script>
        async function runSetup(action) {
            const statusDiv = document.getElementById(action + '-status');
            statusDiv.innerHTML = '<div class="status status-info">⏳ Running...</div>';
            
            let url = '';
            switch(action) {
                case 'schema':
                    url = 'kimi_goldmine_schema.php';
                    break;
                case 'collect':
                    url = 'kimi_goldmine_collector.php?action=collect&source=all&key=goldmine2026';
                    break;
                case 'performance':
                    url = 'kimi_goldmine_collector.php?action=calculate_performance&key=goldmine2026';
                    break;
                case 'winners':
                    url = 'kimi_goldmine_collector.php?action=find_winners&key=goldmine2026';
                    break;
            }
            
            try {
                const response = await fetch(url);
                const data = await response.json();
                
                if (data.ok) {
                    statusDiv.innerHTML = '<div class="status status-success">✅ Success: ' + JSON.stringify(data).substring(0, 200) + '</div>';
                } else {
                    statusDiv.innerHTML = '<div class="status status-error">❌ Error: ' + (data.error || 'Unknown error') + '</div>';
                }
            } catch (error) {
                statusDiv.innerHTML = '<div class="status status-error">❌ Error: ' + error.message + '</div>';
            }
        }
    </script>
</body>
</html>
