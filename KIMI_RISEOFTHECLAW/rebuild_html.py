"""Rebuild dashboard_live.html from git-restored original + apply UI mods + external JS"""
import re

with open('dashboard_live_original.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update the header subtitle (line 542)
content = content.replace(
    '10 Strategies \u00d7 12 Assets \u2014 Forward-Looking Signal System',
    '24+ Strategies \u00d7 127 Assets \u2014 Live Signal Scanner with Confluence Filter'
)

# 2. Replace the filter bar (lines 551-563) with updated version including Forex + IDs
old_filter = '''        <!-- Filter bar -->
        <div class="filter-bar">
            <span class="filter-label">Filter:</span>
            <button class="filter-btn active" data-filter="all" onclick="setFilter('all')">All <span
                    class="filter-count">(5)</span></button>
            <button class="filter-btn" data-filter="crypto" onclick="setFilter('crypto')">\ud83e\ude99 Crypto <span
                    class="filter-count">(3)</span></button>
            <button class="filter-btn" data-filter="stock" onclick="setFilter('stock')">\ud83d\udcca Stocks <span
                    class="filter-count">(2)</span></button>
            <button class="filter-btn" data-filter="winning" onclick="setFilter('winning')">\ud83d\udfe2 Winning</button>
            <button class="filter-btn" data-filter="losing" onclick="setFilter('losing')">\ud83d\udd34 Losing</button>
            <button class="filter-btn" data-filter="live" onclick="setFilter('live')">\u25cf Live Only</button>
        </div>'''

new_filter = '''        <!-- Filter bar -->
        <div class="filter-bar" id="filter-bar">
            <span class="filter-label">Filter:</span>
            <button class="filter-btn active" data-filter="all" onclick="setFilter('all')">All <span class="filter-count" id="cnt-all"></span></button>
            <button class="filter-btn" data-filter="crypto" onclick="setFilter('crypto')">\ud83e\ude99 Crypto <span class="filter-count" id="cnt-crypto"></span></button>
            <button class="filter-btn" data-filter="stock" onclick="setFilter('stock')">\ud83d\udcca Stocks <span class="filter-count" id="cnt-stock"></span></button>
            <button class="filter-btn" data-filter="forex" onclick="setFilter('forex')">\ud83d\udcb1 Forex <span class="filter-count" id="cnt-forex"></span></button>
            <button class="filter-btn" data-filter="winning" onclick="setFilter('winning')">\ud83d\udfe2 Winning</button>
            <button class="filter-btn" data-filter="losing" onclick="setFilter('losing')">\ud83d\udd34 Losing</button>
            <button class="filter-btn" data-filter="live" onclick="setFilter('live')">\u25cf Live Only</button>
        </div>'''

content = content.replace(old_filter, new_filter)

# 3. Add scanner picks section before the footer AND update footer
old_footer = '''        <div class="footer">
            <p>Built by <strong>Antigravity</strong> \u2014 $0 budget, public APIs only</p>
            <p style="margin-top:6px">
                <a href="/updates/">\u2190 Updates</a> \u00b7
                <a href="/KIMI_RISEOFTHECLAW/METHODOLOGY_AUDIT_TRAIL.md">Audit Trail</a> \u00b7
                <a href="/KIMI_RISEOFTHECLAW/data/paper_portfolio.json">Portfolio JSON</a>
            </p>
            <p style="margin-top:8px;font-size:0.7rem;color:#555">Paper trading simulation only. Not financial advice.
            </p>
        </div>'''

new_footer = '''        <!-- Dynamic Scanner Picks -->
        <div class="methodology" id="scanner-picks-section" style="margin-top:24px">
            <h2>\ud83d\udd0d Live Scanner Picks \u2014 <span id="picks-count">Loading\u2026</span> Active Signals</h2>
            <p style="color:var(--text2);font-size:0.75rem;margin-bottom:12px">Auto-detected by 24+ algorithms scanning
                127 symbols. Crypto signals update 24/7.</p>
            <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
                <button class="filter-btn active" data-pfilter="all" onclick="setPickFilter('all')">All</button>
                <button class="filter-btn" data-pfilter="crypto" onclick="setPickFilter('crypto')">\ud83e\ude99 Crypto</button>
                <button class="filter-btn" data-pfilter="stock" onclick="setPickFilter('stock')">\ud83d\udcca Stocks</button>
                <button class="filter-btn" data-pfilter="forex" onclick="setPickFilter('forex')">\ud83d\udcb1 Forex</button>
            </div>
            <div id="scanner-picks" style="display:grid;gap:8px"></div>
        </div>

        <div class="footer">
            <p>Built by <strong>Antigravity</strong> \u2014 $0 budget, public APIs only</p>
            <p style="margin-top:6px">
                <a href="/updates/">\u2190 Updates</a> \u00b7
                <a href="scanner_log.html">\ud83d\udd0d Scanner Log</a> \u00b7
                <a href="/KIMI_RISEOFTHECLAW/METHODOLOGY_AUDIT_TRAIL.md">Audit Trail</a> \u00b7
                <a href="/KIMI_RISEOFTHECLAW/data/paper_portfolio.json">Portfolio JSON</a>
            </p>
            <p style="margin-top:8px;font-size:0.7rem;color:#555">Paper trading simulation only. Not financial advice.
            </p>
        </div>'''

content = content.replace(old_footer, new_footer)

# 4. Add forex CSS class (after .cat-stock)
old_css = '''        .cat-stock {
            background: rgba(170, 102, 255, 0.15);
            color: var(--purple);
            border: 1px solid rgba(170, 102, 255, 0.3);
        }'''

new_css = '''        .cat-stock {
            background: rgba(170, 102, 255, 0.15);
            color: var(--purple);
            border: 1px solid rgba(170, 102, 255, 0.3);
        }

        .cat-forex {
            background: rgba(0, 200, 200, 0.15);
            color: #00c8c8;
            border: 1px solid rgba(0, 200, 200, 0.3);
        }'''

content = content.replace(old_css, new_css)

# 5. Add clickable stat-card and detail-row CSS
old_stat_card = '''        .stat-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
            text-align: center;
        }'''

new_stat_card = '''        .stat-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
            text-align: center;
        }

        .stat-card.clickable {
            cursor: pointer;
            transition: all 0.2s;
        }

        .stat-card.clickable:hover {
            border-color: var(--blue);
            background: rgba(68, 136, 255, 0.05);
        }

        .click-hint {
            font-size: 0.55rem;
            color: var(--text2);
            opacity: 0.5;
            margin-top: 4px;
        }

        .detail-row {
            display: flex;
            justify-content: space-between;
            padding: 4px 0;
            font-size: 0.8rem;
        }

        .detail-label {
            color: var(--text2);
        }

        .pos-sym {
            color: var(--text2);
            font-size: 0.75rem;
        }

        .cat-badge {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 10px;
            font-size: 0.65rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-left: 8px;
        }

        .pos-details {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 4px 16px;
            margin: 8px 0;
        }'''

content = content.replace(old_stat_card, new_stat_card)

# 6. Replace everything from <script> to end with external JS references
script_idx = content.find('    <script>')
if script_idx == -1:
    print("ERROR: Could not find <script> tag!")
else:
    content = content[:script_idx]
    content += '''    <script>
    var ICONS = {};
    var NAMES = {};
    var CG_IDS = {};
    var BINANCE_IDS = {};
    var MIN_CONFLUENCE = 2;
    var PORTFOLIO = {starting_capital: 0, per_trade: 2000, positions: []};
    </script>
    <script src="dashboard_data.js"></script>
    <script src="dashboard_logic.js"></script>
</body>
</html>
'''

with open('dashboard_live.html', 'w', encoding='utf-8') as f:
    f.write(content)

with open('dashboard_live.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
print(f'Total lines: {len(lines)}')
print(f'Last 10 lines:')
for line in lines[-10:]:
    print(line.rstrip())
