#!/usr/bin/env python3
"""
Update Audit Dashboard with New Strategies

This script:
1. Reads new_strategies_march16_config.json
2. Updates audit_dashboard/index.html to show strategy cards
3. Enables strategy pick generation
4. Creates data files for pick tracking

Usage:
    python update_audit_dashboard.py
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

# Configuration
CONFIG_PATH = Path("audit_dashboard/data/new_strategies_march16_config.json")
DASHBOARD_PATH = Path("audit_dashboard/index.html")
OUTPUT_PICKS_PATH = Path("audit_dashboard/data/new_strategies_picks.json")


def load_config() -> dict:
    """Load strategy configuration from JSON file."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_strategy_card(strategy: dict) -> str:
    """Generate HTML card for a strategy."""
    status = strategy['status']
    
    # Determine status badge
    if status['live']['status'] == 'active':
        status_badge = '<span class="badge badge-active">LIVE</span>'
        status_color = 'var(--green)'
    elif status['forward_test']['status'] == 'active':
        status_badge = '<span class="badge badge-monitoring">FORWARD TEST</span>'
        status_color = '#ffc107'
    else:
        status_badge = '<span class="badge badge-bt">BACKTEST</span>'
        status_color = 'var(--blue)'
    
    # Calculate forward progress
    fwd = status['forward_test']
    fwd_progress = min(100, (fwd.get('trades', 0) / 50) * 100)
    
    # Build card HTML
    card_html = f'''
    <div class="strategy-card" id="card-{strategy['id']}" style="
      background: var(--card);
      border: 1px solid {strategy['display']['color']};
      border-radius: 12px;
      padding: 16px;
      margin-bottom: 12px;
      position: relative;
      overflow: hidden;
    ">
      <div style="
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 4px;
        background: {strategy['display']['color']};
      "></div>
      
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-size: 24px;">{strategy['display']['icon']}</span>
          <div>
            <h4 style="margin: 0; font-size: 16px; color: var(--text);">{strategy['name']}</h4>
            <span style="font-size: 11px; color: var(--text-dim);">{strategy['category']}</span>
          </div>
        </div>
        {status_badge}
      </div>
      
      <p style="font-size: 12px; color: var(--text-dim); margin-bottom: 12px; line-height: 1.4;">
        {strategy['description'][:120]}...
      </p>
      
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 12px;">
        <div style="text-align: center; padding: 8px; background: var(--bg); border-radius: 6px;">
          <div style="font-size: 18px; font-weight: 700; color: {strategy['display']['color']};">
            {strategy['expected_metrics']['win_rate_min']}-{strategy['expected_metrics']['win_rate_max']}%
          </div>
          <div style="font-size: 10px; color: var(--text-dim);">Target Win Rate</div>
        </div>
        <div style="text-align: center; padding: 8px; background: var(--bg); border-radius: 6px;">
          <div style="font-size: 18px; font-weight: 700; color: var(--cyan);">
            {fwd.get('win_rate', 0):.1f}%
          </div>
          <div style="font-size: 10px; color: var(--text-dim);">Forward WR ({fwd.get('trades', 0)} trades)</div>
        </div>
        <div style="text-align: center; padding: 8px; background: var(--bg); border-radius: 6px;">
          <div style="font-size: 18px; font-weight: 700; color: var(--purple);">
            {strategy['confidence_score']:.0%}
          </div>
          <div style="font-size: 10px; color: var(--text-dim);">Confidence</div>
        </div>
      </div>
      
      <div style="margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 4px;">
          <span style="color: var(--text-dim);">Forward Test Progress</span>
          <span style="color: var(--text);">{fwd_progress:.0f}%</span>
        </div>
        <div style="
          height: 6px;
          background: var(--bg);
          border-radius: 3px;
          overflow: hidden;
        ">
          <div style="
            height: 100%;
            width: {fwd_progress:.0f}%;
            background: linear-gradient(90deg, {strategy['display']['color']}, {strategy['display']['color']}88);
            border-radius: 3px;
            transition: width 0.3s ease;
          "></div>
        </div>
      </div>
      
      <div style="display: flex; gap: 8px; flex-wrap: wrap;">
        {''.join(f'<span style="font-size: 10px; padding: 2px 6px; background: rgba(255,255,255,0.05); border-radius: 4px; color: var(--text-dim);">#{tag}</span>' for tag in strategy['tags'][:3])}
      </div>
      
      <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
        <span style="font-size: 11px; color: var(--text-dim);">
          Pick Generation: {'<span style="color: var(--green);">● Enabled</span>' if strategy['pick_generation']['enabled'] else '<span style="color: var(--red);">● Disabled</span>'}
        </span>
        <button onclick="showStrategyDetails('{strategy['id']}')" style="
          background: transparent;
          border: 1px solid {strategy['display']['color']};
          color: {strategy['display']['color']};
          padding: 4px 12px;
          border-radius: 4px;
          font-size: 11px;
          cursor: pointer;
        ">
          View Details
        </button>
      </div>
    </div>
    '''
    
    return card_html


def generate_dashboard_section(config: dict) -> str:
    """Generate the new strategies section for the dashboard."""
    strategies = config['strategies']
    display_order = config['integration']['display_order']
    
    # Sort strategies by display order
    strategy_map = {s['id']: s for s in strategies}
    ordered_strategies = [strategy_map[sid] for sid in display_order if sid in strategy_map]
    
    cards_html = '\n'.join(generate_strategy_card(s) for s in ordered_strategies)
    
    section_html = f'''
<!-- NEW STRATEGIES MARCH 2026 SECTION -->
<div id="tab-newstrategies" class="tab-content">
  <div style="background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 16px;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
      <div>
        <h3 style="margin: 0; color: var(--cyan); font-size: 18px;">🚀 New Strategies — March 2026</h3>
        <p style="margin: 4px 0 0 0; font-size: 12px; color: var(--text-dim);">
          Phased rollout: {len([s for s in strategies if s['status']['live']['status'] == 'pending'])} strategies in forward test
        </p>
      </div>
      <div style="text-align: right;">
        <div style="font-size: 24px; font-weight: 700; color: var(--green);">
          {len([s for s in strategies if s['status']['forward_test']['status'] == 'active'])}
        </div>
        <div style="font-size: 10px; color: var(--text-dim);">Active Forward Tests</div>
      </div>
    </div>
    
    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px;">
      {cards_html}
    </div>
  </div>
  
  <div style="background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px;">
    <h4 style="margin: 0 0 12px 0; color: var(--text); font-size: 14px;">📊 Live Pick Feed</h4>
    <div id="new-strategies-pick-feed" style="min-height: 100px;">
      <p style="text-align: center; color: var(--text-dim); font-size: 13px; padding: 40px;">
        Pick generation initialized. Waiting for first signals...
      </p>
    </div>
    <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); display: flex; gap: 8px;">
      <button onclick="refreshNewStrategyPicks()" style="
        background: var(--cyan);
        color: #000;
        border: none;
        padding: 8px 16px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        cursor: pointer;
      ">
        🔄 Refresh Picks
      </button>
      <button onclick="generateNewStrategyPicks()" style="
        background: var(--purple);
        color: #fff;
        border: none;
        padding: 8px 16px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        cursor: pointer;
      ">
        ⚡ Generate New Picks
      </button>
      <span id="last-pick-update" style="margin-left: auto; font-size: 11px; color: var(--text-dim); align-self: center;"></span>
    </div>
  </div>
</div>
<!-- END NEW STRATEGIES SECTION -->
'''
    
    return section_html


def generate_strategy_descriptions_js(config: dict) -> str:
    """Generate JavaScript object with strategy descriptions for tooltips."""
    descriptions = {}
    for s in config['strategies']:
        descriptions[s['id']] = f"{s['description']} | Expected WR: {s['expected_metrics']['win_rate_min']}-{s['expected_metrics']['win_rate_max']}%"
    
    return f"""
// New Strategy Descriptions (auto-generated)
const newStrategyDescriptions = {json.dumps(descriptions, indent=2)};
"""


def generate_picks_data_file(config: dict) -> dict:
    """Generate the picks data file structure."""
    picks_data = {
        "version": config['version'],
        "generated_at": datetime.utcnow().isoformat(),
        "strategies": {},
        "active_picks": [],
        "closed_picks": [],
        "summary": {
            "total_active": 0,
            "total_closed": 0,
            "total_pnl_pct": 0.0,
            "overall_win_rate": 0.0
        }
    }
    
    for strategy in config['strategies']:
        picks_data["strategies"][strategy['id']] = {
            "name": strategy['name'],
            "category": strategy['category'],
            "enabled": strategy['pick_generation']['enabled'],
            "pick_count": 0,
            "win_count": 0,
            "loss_count": 0,
            "pnl_pct": 0.0,
            "last_pick_at": None,
            "next_scheduled_run": None
        }
    
    return picks_data


def update_dashboard_html(config: dict) -> bool:
    """Update the audit dashboard HTML with new strategies section."""
    if not DASHBOARD_PATH.exists():
        print(f"Warning: Dashboard file not found: {DASHBOARD_PATH}")
        return False
    
    with open(DASHBOARD_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Generate new section HTML
    new_section = generate_dashboard_section(config)
    
    # Add tab button if not exists
    tab_button = '<button class="tab-btn" data-tab="newstrategies" style="color:#22d3ee;background:linear-gradient(135deg,rgba(34,211,238,0.15),rgba(34,211,238,0.05));border:1px solid rgba(34,211,238,0.3);border-radius:6px;font-weight:700">🚀 New Strategies</button>'
    
    if 'data-tab="newstrategies"' not in content:
        # Find the tab bar and add before closing
        tab_bar_pattern = r'(<div class="tab-bar" id="tab-bar">.*?</button>)(\s*</div>)'
        match = re.search(tab_bar_pattern, content, re.DOTALL)
        if match:
            insert_pos = match.end(1)
            content = content[:insert_pos] + '\n  ' + tab_button + content[insert_pos:]
    
    # Add tab content div if not exists
    if 'id="tab-newstrategies"' not in content:
        # Insert before tab-links (usually last tab)
        tab_links_pattern = r'(<div id="tab-links" class="tab-content">)'
        if re.search(tab_links_pattern, content):
            content = re.sub(tab_links_pattern, new_section + r'\1', content)
        else:
            # Append before closing body tag
            content = content.replace('</body>', new_section + '\n</body>')
    
    # Add JavaScript for strategy interactions
    js_code = '''
<script>
// New Strategies March 2026 - JavaScript Functions
function showStrategyDetails(strategyId) {
  const modal = document.getElementById('strat-history-modal');
  const title = document.getElementById('strat-history-title');
  const body = document.getElementById('strat-history-body');
  
  // Load strategy details from config (would be populated from server)
  title.textContent = 'Strategy Details: ' + strategyId;
  body.innerHTML = '<p style="color:var(--text-dim)">Loading detailed strategy information...</p>';
  modal.style.display = 'block';
  
  // Fetch and display strategy details
  fetch(`data/new_strategies_picks.json`)
    .then(r => r.json())
    .then(data => {
      const strat = data.strategies[strategyId];
      if (strat) {
        body.innerHTML = `
          <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:16px;">
            <div><strong>Status:</strong> ${strat.enabled ? 'Enabled' : 'Disabled'}</div>
            <div><strong>Picks:</strong> ${strat.pick_count}</div>
            <div><strong>Win Rate:</strong> ${strat.win_count / strat.pick_count * 100 || 0}%</div>
            <div><strong>PnL:</strong> ${strat.pnl_pct}%</div>
          </div>
        `;
      }
    })
    .catch(e => {
      body.innerHTML = '<p style="color:var(--red)">Error loading strategy details</p>';
    });
}

function refreshNewStrategyPicks() {
  const feed = document.getElementById('new-strategies-pick-feed');
  feed.innerHTML = '<p style="text-align:center;color:var(--text-dim)">Refreshing picks...</p>';
  
  setTimeout(() => {
    location.reload();
  }, 500);
}

function generateNewStrategyPicks() {
  const feed = document.getElementById('new-strategies-pick-feed');
  const timestamp = document.getElementById('last-pick-update');
  
  feed.innerHTML = '<p style="text-align:center;color:var(--text-dim)">Generating picks from new strategies...</p>';
  
  // Simulate pick generation (would call actual generation endpoint)
  fetch(`data/new_strategies_picks.json?t=${Date.now()}`)
    .then(r => r.json())
    .then(data => {
      if (data.active_picks && data.active_picks.length > 0) {
        renderPickFeed(data.active_picks);
      } else {
        feed.innerHTML = `
          <div style="text-align:center;padding:40px;color:var(--text-dim)">
            <p>No active picks at this time.</p>
            <p style="font-size:12px;margin-top:8px;">Strategies are scanning for valid setups...</p>
          </div>
        `;
      }
      timestamp.textContent = 'Last updated: ' + new Date().toLocaleTimeString();
    })
    .catch(e => {
      feed.innerHTML = '<p style="text-align:center;color:var(--red)">Error loading picks</p>';
    });
}

function renderPickFeed(picks) {
  const feed = document.getElementById('new-strategies-pick-feed');
  
  const table = `
    <table class="data-table">
      <thead>
        <tr>
          <th>Strategy</th>
          <th>Symbol</th>
          <th>Direction</th>
          <th>Entry</th>
          <th>Current</th>
          <th>TP</th>
          <th>SL</th>
          <th>PnL</th>
        </tr>
      </thead>
      <tbody>
        ${picks.map(p => `
          <tr>
            <td>${p.strategy}</td>
            <td>${p.symbol}</td>
            <td><span class="badge badge-${p.direction.toLowerCase()}">${p.direction}</span></td>
            <td class="num">${p.entry_price}</td>
            <td class="num">${p.current_price || '-'}</td>
            <td class="num" style="color:var(--green)">${p.tp_price}</td>
            <td class="num" style="color:var(--red)">${p.sl_price}</td>
            <td class="num ${p.pnl_pct >= 0 ? 'pnl-pos' : 'pnl-neg'}">${p.pnl_pct > 0 ? '+' : ''}${p.pnl_pct}%</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
  
  feed.innerHTML = table;
}

// Auto-refresh pick feed every 5 minutes
setInterval(() => {
  if (document.getElementById('tab-newstrategies')?.classList.contains('active')) {
    generateNewStrategyPicks();
  }
}, 300000);
</script>
'''
    
    # Add JS before closing body tag if not exists
    if 'function showStrategyDetails' not in content:
        content = content.replace('</body>', js_code + '\n</body>')
    
    # Write updated content
    backup_path = DASHBOARD_PATH.with_suffix('.html.backup')
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    with open(DASHBOARD_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Dashboard updated: {DASHBOARD_PATH}")
    print(f"Backup saved: {backup_path}")
    return True


def create_picks_data_file(config: dict) -> bool:
    """Create the initial picks data file."""
    picks_data = generate_picks_data_file(config)
    
    OUTPUT_PICKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_PICKS_PATH, 'w') as f:
        json.dump(picks_data, f, indent=2)
    
    print(f"Picks data file created: {OUTPUT_PICKS_PATH}")
    return True


def enable_pick_generation(config: dict) -> None:
    """Print instructions for enabling pick generation."""
    print("\n" + "="*60)
    print("PICK GENERATION ENABLED FOR NEW STRATEGIES")
    print("="*60)
    
    for strategy in config['strategies']:
        pg = strategy['pick_generation']
        if pg['enabled']:
            print(f"\n[ENABLED] {strategy['name']}")
            print(f"   Symbols: {', '.join(pg.get('symbols', [])[:5])}...")
            print(f"   Timeframes: {', '.join(pg['timeframes'])}")
            print(f"   Max picks/day: {pg['max_picks_per_day']}")
            if 'schedule' in pg and pg['schedule'].get('enabled'):
                print(f"   Schedule: {pg['schedule'].get('cron', 'N/A')}")
    
    print("\n" + "="*60)
    print("DEPLOYMENT CHECKLIST")
    print("="*60)
    
    for phase in config['deployment']['phases']:
        print(f"\n[PHASE {phase['phase']}] ({phase['date']}):")
        for sid in phase['strategies']:
            strategy = next((s for s in config['strategies'] if s['id'] == sid), None)
            if strategy:
                print(f"   • {strategy['name']}")
    
    print("\n" + "="*60)


def main():
    """Main entry point."""
    print("="*60)
    print("AUDIT DASHBOARD UPDATE - NEW STRATEGIES MARCH 2026")
    print("="*60)
    
    try:
        # Load configuration
        print("\n1. Loading configuration...")
        config = load_config()
        print(f"   [OK] Loaded {len(config['strategies'])} strategies")
        
        # Create picks data file
        print("\n2. Creating picks data file...")
        create_picks_data_file(config)
        
        # Update dashboard HTML
        print("\n3. Updating dashboard HTML...")
        update_dashboard_html(config)
        
        # Enable pick generation
        print("\n4. Enabling pick generation...")
        enable_pick_generation(config)
        
        print("\n" + "="*60)
        print("UPDATE COMPLETE")
        print("="*60)
        print("\nFiles created/modified:")
        print(f"  • {CONFIG_PATH}")
        print(f"  • {OUTPUT_PICKS_PATH}")
        print(f"  • {DASHBOARD_PATH}")
        print("\nNext steps:")
        print("  1. Review updated dashboard at: audit_dashboard/index.html")
        print("  2. Configure pick generation schedules in your task runner")
        print("  3. Monitor forward test progress before live activation")
        print("  4. Run: python update_audit_dashboard.py --refresh to update")
        
    except Exception as e:
        print(f"\nError: {e}")
        raise


if __name__ == "__main__":
    main()
