# Unified Audit Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a single "birds-eye view" dashboard showing ALL picks, trades, portfolios, and system performance across every subsystem, deployed to GitHub Pages + FTP.

**Architecture:** Python generator reads ~30 data sources (JSON files + SQLite DBs), writes a single `audit_trail/data/dashboard_payload.json`. Static HTML/JS frontend loads it via inline injection. GitHub Actions runs generator every 15 min and deploys.

**Tech Stack:** Python 3 (stdlib: json, sqlite3, pathlib, glob), vanilla HTML/CSS/JS (no frameworks), GitHub Actions, FTP deploy.

---

### Task 1: Create Dashboard Generator — Data Collection Layer

**Files:**
- Create: `audit_trail/dashboard_generator.py`

**Step 1: Create the generator scaffold with data source readers**

```python
#!/usr/bin/env python3
"""
Unified Audit Dashboard Generator.
Reads ALL pick/trade/portfolio data sources and outputs a single JSON payload.
"""
import glob
import json
import sqlite3
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _safe_json(path: Path):
    """Load JSON file safely, return None on error."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _safe_sqlite(db_path: Path, query: str):
    """Run a SELECT query safely, return list of dicts."""
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


# ── JSON Pick Sources (skip mirrors/deploy copies) ──

JSON_PICK_SOURCES = [
    # (system_name, active_path, closed_path)
    ("alpha_engine",          "alpha_engine/data/active_picks.json",              "alpha_engine/data/closed_picks.json"),
    ("kimi_riseoftheclaw",    "KIMI_RISEOFTHECLAW/data/active_picks.json",       "KIMI_RISEOFTHECLAW/data/closed_picks.json"),
    ("battleground",          "battleground/data/active_picks.json",              "battleground/data/closed_picks.json"),
    ("mercury2",              "mercury2/data/active_picks.json",                  "mercury2/data/closed_picks.json"),
    ("paper_trading",         "paper_trading/data/active_picks.json",             "paper_trading/data/closed_picks.json"),
    ("ml_bg_system_a",        "ml_battleground/system_a_filter/data/active_picks.json",   "ml_battleground/system_a_filter/data/closed_picks.json"),
    ("ml_bg_system_b",        "ml_battleground/system_b_regime/data/active_picks.json",   "ml_battleground/system_b_regime/data/closed_picks.json"),
    ("ml_bg_system_c",        "ml_battleground/system_c_deeplearn/data/active_picks.json","ml_battleground/system_c_deeplearn/data/closed_picks.json"),
    ("ml_bg_system_d",        "ml_battleground/system_d_carry/data/active_picks.json",    "ml_battleground/system_d_carry/data/closed_picks.json"),
    ("ml_bg_system_e",        "ml_battleground/system_e_momentum/data/active_picks.json", "ml_battleground/system_e_momentum/data/closed_picks.json"),
    ("ml_bg_system_f",        "ml_battleground/system_f_clawsofdoom/data/active_picks.json","ml_battleground/system_f_clawsofdoom/data/closed_picks.json"),
    ("ml_bg_ensemble",        "ml_battleground/ensemble_data/active_picks.json",  "ml_battleground/ensemble_data/closed_picks.json"),
    ("breakout_a_sr",         "breakout_arena/approach_a_sr_breakout/data/active_picks.json","breakout_arena/approach_a_sr_breakout/data/closed_picks.json"),
    ("breakout_b_ml",         "breakout_arena/approach_b_ml_breakout/data/active_picks.json","breakout_arena/approach_b_ml_breakout/data/closed_picks.json"),
    ("breakout_c_spike",      "breakout_arena/approach_c_spike_reverse/data/active_picks.json","breakout_arena/approach_c_spike_reverse/data/closed_picks.json"),
    ("crypto_signal_engine",  "crypto_signal_engine/data/active_picks.json",      "crypto_signal_engine/data/closed_picks.json"),
    ("coinglass",             "coinglass_strategies/data/active_picks.json",       None),
    ("stocks_competition",    None,                                                None),  # special: STOCKS/competition/forward_picks.json
    ("claude_gainer_ml",      None,                                                None),  # special: claude_gainer_ml/tracker/claude_live_picks.json
    ("crypto_ml_edge",        "crypto_ml_edge/data/active_picks.json",            None),
    ("rl_agent",              "rl_agent/data/active_picks.json",                  None),
    ("genome",                "genome/active_picks.json",                          None),
    ("ml_crypto_predictor",   None,                                                "ml_crypto_predictor/enhanced_models/live_picks/all_picks_log.json"),
]

PORTFOLIO_SOURCES = [
    ("paper_trading",         "paper_trading/data/portfolios.json"),
    ("kimi_algorithms",       "KIMI_RISEOFTHECLAW/data/portfolio_state.json"),
    ("kimi_paper",            "KIMI_RISEOFTHECLAW/data/paper_portfolio.json"),
    ("portfolio_tracker",     "portfolio_tracker/data/portfolio_metrics.json"),
]
```

**Step 2: Run the file to verify it parses (no errors on import)**

Run: `cd /e/findtorontoevents_antigravity.ca && python -c "import audit_trail.dashboard_generator; print('OK')"`
Expected: `OK`

**Step 3: Commit scaffold**

```bash
git add audit_trail/dashboard_generator.py
git commit -m "feat(audit-dashboard): add generator scaffold with data source registry"
```

---

### Task 2: Generator — Normalize and Aggregate Picks

**Files:**
- Modify: `audit_trail/dashboard_generator.py`

**Step 1: Add pick normalization and aggregation functions**

Append to `dashboard_generator.py`:

```python
def _normalize_pick(raw, source_system: str, status: str = "OPEN") -> dict:
    """Normalize a pick from any source into a common schema."""
    symbol = raw.get("symbol", raw.get("pair", ""))
    direction = str(raw.get("direction", raw.get("signal_type", raw.get("signal", "")))).upper()
    if "BUY" in direction or "LONG" in direction:
        direction = "LONG"
    elif "SELL" in direction or "SHORT" in direction:
        direction = "SHORT"

    entry = raw.get("entry_price", raw.get("entryPrice", raw.get("entry", raw.get("price", 0))))
    tp = raw.get("take_profit", raw.get("targetPrice", raw.get("tp", raw.get("tp_price", 0))))
    sl = raw.get("stop_loss", raw.get("stopPrice", raw.get("sl", raw.get("sl_price", 0))))
    conf = raw.get("confidence", raw.get("ml_score", 0))
    strategy = raw.get("strategy", raw.get("strategy_name", ""))
    pnl = raw.get("pnl_pct", raw.get("unrealized_pnl_pct", 0))
    exit_reason = raw.get("exit_reason", raw.get("close_reason", ""))

    # Asset class derivation
    s = str(symbol).upper()
    if any(s.endswith(sfx) for sfx in ("USDT", "BTC", "ETH", "BUSD", "USDC")):
        asset_class = "CRYPTO"
    elif any(s.startswith(p) for p in ("EUR", "GBP", "USD", "JPY", "AUD", "CAD", "CHF", "NZD")):
        asset_class = "FOREX"
    else:
        asset_class = "EQUITY"

    return {
        "symbol": symbol,
        "direction": direction,
        "entry_price": _float(entry),
        "take_profit": _float(tp),
        "stop_loss": _float(sl),
        "confidence": _float(conf),
        "strategy": strategy,
        "source_system": source_system,
        "asset_class": asset_class,
        "status": status,
        "pnl_pct": _float(pnl),
        "exit_reason": exit_reason,
        "timestamp": raw.get("timestamp", raw.get("entry_date", raw.get("created_at", raw.get("generated_at", "")))),
    }


def _float(v):
    try:
        return float(v) if v else 0.0
    except (ValueError, TypeError):
        return 0.0


def collect_all_picks():
    """Read all JSON pick sources, return (active_picks, closed_picks)."""
    active, closed = [], []

    for sys_name, active_path, closed_path in JSON_PICK_SOURCES:
        if active_path:
            data = _safe_json(ROOT / active_path)
            if data:
                # Handle both array and object formats
                picks = data if isinstance(data, list) else data.get("activePicks", data.get("active_picks", data.get("picks", [])))
                for p in (picks or []):
                    active.append(_normalize_pick(p, sys_name, "OPEN"))

        if closed_path:
            data = _safe_json(ROOT / closed_path)
            if data:
                picks = data if isinstance(data, list) else data.get("closedPicks", data.get("closed_picks", data.get("picks", [])))
                for p in (picks or []):
                    closed.append(_normalize_pick(p, sys_name, "CLOSED"))

    # Special sources
    # STOCKS competition
    stocks = _safe_json(ROOT / "STOCKS/competition/forward_picks.json")
    if stocks and stocks.get("picks"):
        for p in stocks["picks"]:
            status = "CLOSED" if p.get("status") == "CLOSED" else "OPEN"
            active.append(_normalize_pick(p, "stocks_competition", status))

    # Claude Gainer ML
    claude = _safe_json(ROOT / "claude_gainer_ml/tracker/claude_live_picks.json")
    if claude and claude.get("picks"):
        for p in claude["picks"]:
            status = "CLOSED" if p.get("status") in ("resolved", "CLOSED") else "OPEN"
            bucket = closed if status == "CLOSED" else active
            bucket.append(_normalize_pick(p, "claude_gainer_ml", status))

    # KIMI active picks (special object format)
    kimi = _safe_json(ROOT / "KIMI_RISEOFTHECLAW/data/active_picks.json")
    if kimi and kimi.get("activePicks"):
        for p in kimi["activePicks"]:
            active.append(_normalize_pick(p, "kimi_riseoftheclaw", "OPEN"))

    return active, closed
```

**Step 2: Test locally**

Run: `cd /e/findtorontoevents_antigravity.ca && python -c "from audit_trail.dashboard_generator import collect_all_picks; a,c = collect_all_picks(); print(f'Active: {len(a)}, Closed: {len(c)}')"`
Expected: Numbers matching our inventory (~150+ active, ~500+ closed)

**Step 3: Commit**

```bash
git add audit_trail/dashboard_generator.py
git commit -m "feat(audit-dashboard): add pick normalization and collection from all sources"
```

---

### Task 3: Generator — Portfolio, System Stats, and Audit Events

**Files:**
- Modify: `audit_trail/dashboard_generator.py`

**Step 1: Add portfolio, system stats, and audit event collectors**

Append to `dashboard_generator.py`:

```python
def collect_portfolios():
    """Read all portfolio data sources."""
    portfolios = []

    # Paper trading portfolios (array format)
    data = _safe_json(ROOT / "paper_trading/data/portfolios.json")
    if data and isinstance(data, list):
        for p in data:
            portfolios.append({
                "name": p.get("name", ""),
                "source": "paper_trading",
                "equity": _float(p.get("equity")),
                "cash": _float(p.get("cash")),
                "pnl_pct": _float(p.get("pnl_pct")),
                "win_rate": _float(p.get("win_rate")),
                "positions": p.get("active_positions", 0),
                "max_drawdown": _float(p.get("max_drawdown")),
            })

    # KIMI algorithm portfolios (object format)
    data = _safe_json(ROOT / "KIMI_RISEOFTHECLAW/data/portfolio_state.json")
    if data and data.get("algorithms"):
        for name, algo in data["algorithms"].items():
            portfolios.append({
                "name": name,
                "source": "kimi_algorithms",
                "equity": _float(algo.get("cash", algo.get("starting_value", 10000))),
                "cash": _float(algo.get("cash", 0)),
                "pnl_pct": 0.0,
                "win_rate": 0.0,
                "positions": len(algo.get("positions", [])),
                "max_drawdown": 0.0,
            })

    # Paper portfolio (KIMI)
    data = _safe_json(ROOT / "KIMI_RISEOFTHECLAW/data/paper_portfolio.json")
    if data:
        portfolios.append({
            "name": "KIMI Paper",
            "source": "kimi_paper",
            "equity": _float(data.get("starting_capital", 10000)),
            "cash": 0.0,
            "pnl_pct": 0.0,
            "win_rate": 0.0,
            "positions": len(data.get("positions", [])),
            "max_drawdown": 0.0,
        })

    # Paper trading SQLite
    rows = _safe_sqlite(ROOT / "paper_trading/data/paper.db",
        "SELECT name, portfolio_type, equity, pnl_pct, win_rate, max_drawdown FROM portfolios")
    for r in rows:
        portfolios.append({
            "name": r.get("name", ""),
            "source": "paper_db",
            "equity": _float(r.get("equity")),
            "cash": 0.0,
            "pnl_pct": _float(r.get("pnl_pct")),
            "win_rate": _float(r.get("win_rate")),
            "positions": 0,
            "max_drawdown": _float(r.get("max_drawdown")),
        })

    return portfolios


def collect_system_stats(active, closed):
    """Compute per-system stats from collected picks."""
    systems = {}
    for pick in active + closed:
        sys_name = pick["source_system"]
        if sys_name not in systems:
            systems[sys_name] = {"active": 0, "closed": 0, "wins": 0, "losses": 0,
                                  "total_pnl": 0.0, "asset_classes": set()}
        s = systems[sys_name]
        s["asset_classes"].add(pick["asset_class"])
        if pick["status"] == "OPEN":
            s["active"] += 1
        else:
            s["closed"] += 1
            pnl = pick.get("pnl_pct", 0)
            s["total_pnl"] += pnl
            if pnl > 0:
                s["wins"] += 1
            elif pnl < 0:
                s["losses"] += 1

    result = []
    for name, s in sorted(systems.items()):
        total = s["wins"] + s["losses"]
        wr = (s["wins"] / total * 100) if total > 0 else 0
        avg_pnl = (s["total_pnl"] / s["closed"]) if s["closed"] > 0 else 0
        result.append({
            "name": name,
            "active_picks": s["active"],
            "closed_picks": s["closed"],
            "win_rate": round(wr, 1),
            "avg_pnl_pct": round(avg_pnl, 2),
            "asset_classes": sorted(s["asset_classes"]),
            "status": "active" if s["active"] > 0 else ("retired" if s["closed"] > 0 else "empty"),
        })
    return result


def collect_audit_events(limit=50):
    """Read recent audit events from audit_trail.db."""
    return _safe_sqlite(
        ROOT / "data" / "audit_trail.db",
        f"SELECT event_type, pick_id, symbol, payload, origin, timestamp FROM audit_events ORDER BY timestamp DESC LIMIT {limit}"
    )


def collect_backtest_vs_forward():
    """Compare backtest vs forward win rates from audit DB."""
    db = ROOT / "data" / "audit_trail.db"
    # Forward WR by strategy
    fwd = _safe_sqlite(db, """
        SELECT strategy, COUNT(*) as trades,
               SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) as wins
        FROM (
            SELECT rp.strategy, cp.pnl_pct
            FROM raw_picks rp
            JOIN consensus_picks cp ON rp.aggregation_run_id = cp.aggregation_run_id
                AND rp.symbol = cp.symbol
            WHERE cp.status = 'CLOSED' AND rp.strategy != ''
        ) GROUP BY strategy HAVING trades >= 3
    """)
    # Backtest WR by strategy
    bt = _safe_sqlite(db, """
        SELECT strategy, total_trades as trades, wins
        FROM bt_backtest_runs
        WHERE total_trades >= 5
    """)
    fwd_map = {r["strategy"]: r for r in fwd}
    bt_map = {r["strategy"]: r for r in bt}
    results = []
    all_strats = set(list(fwd_map.keys()) + list(bt_map.keys()))
    for strat in sorted(all_strats):
        f = fwd_map.get(strat, {})
        b = bt_map.get(strat, {})
        fwd_wr = (f["wins"] / f["trades"] * 100) if f.get("trades") else None
        bt_wr = (b["wins"] / b["trades"] * 100) if b.get("trades") else None
        decay = round(fwd_wr - bt_wr, 1) if (fwd_wr is not None and bt_wr is not None) else None
        results.append({
            "strategy": strat,
            "bt_wr": round(bt_wr, 1) if bt_wr is not None else None,
            "fwd_wr": round(fwd_wr, 1) if fwd_wr is not None else None,
            "decay": decay,
            "bt_trades": b.get("trades", 0),
            "fwd_trades": f.get("trades", 0),
        })
    return results
```

**Step 2: Test**

Run: `cd /e/findtorontoevents_antigravity.ca && python -c "from audit_trail.dashboard_generator import collect_portfolios; p = collect_portfolios(); print(f'Portfolios: {len(p)}')"`
Expected: ~12-22 portfolios

**Step 3: Commit**

```bash
git add audit_trail/dashboard_generator.py
git commit -m "feat(audit-dashboard): add portfolio, system stats, and audit event collectors"
```

---

### Task 4: Generator — Bundle Data + Main Generate Function

**Files:**
- Modify: `audit_trail/dashboard_generator.py`

**Step 1: Add bundle reader and main generate function**

Append to `dashboard_generator.py`:

```python
def collect_bundles():
    """Read baby strat bundles from battleground dashboard."""
    data = _safe_json(ROOT / "battleground/data/baby_strats_dashboard.json")
    if not data:
        return []
    for section in data.get("sections", []):
        if section.get("section") == "BUNDLE_BABIES_TOP":
            return section.get("bundles", [])
    return []


def generate():
    """Main entry point: collect all data, write payload JSON."""
    now = datetime.now(timezone.utc).isoformat()
    print(f"[{now}] Generating unified audit dashboard payload...")

    active, closed = collect_all_picks()
    systems = collect_system_stats(active, closed)
    portfolios = collect_portfolios()
    audit_events = collect_audit_events(50)
    bt_vs_fwd = collect_backtest_vs_forward()
    bundles = collect_bundles()

    # Summary
    total_active = len(active)
    total_closed = len(closed)
    wins = sum(1 for p in closed if p.get("pnl_pct", 0) > 0)
    losses = sum(1 for p in closed if p.get("pnl_pct", 0) < 0)
    overall_wr = round(wins / (wins + losses) * 100, 1) if (wins + losses) > 0 else 0
    total_pnl = round(sum(p.get("pnl_pct", 0) for p in closed), 2)

    # Asset class breakdown
    ac_breakdown = {}
    for p in active + closed:
        ac = p["asset_class"]
        if ac not in ac_breakdown:
            ac_breakdown[ac] = {"active": 0, "closed": 0, "wins": 0, "losses": 0, "pnl": 0.0}
        b = ac_breakdown[ac]
        if p["status"] == "OPEN":
            b["active"] += 1
        else:
            b["closed"] += 1
            pnl = p.get("pnl_pct", 0)
            b["pnl"] += pnl
            if pnl > 0: b["wins"] += 1
            elif pnl < 0: b["losses"] += 1

    for ac, b in ac_breakdown.items():
        total = b["wins"] + b["losses"]
        b["win_rate"] = round(b["wins"] / total * 100, 1) if total > 0 else 0
        b["pnl"] = round(b["pnl"], 2)

    payload = {
        "generated_at": now,
        "summary": {
            "total_systems": len(systems),
            "total_active_picks": total_active,
            "total_closed_picks": total_closed,
            "overall_win_rate": overall_wr,
            "total_pnl_pct": total_pnl,
            "total_portfolios": len(portfolios),
        },
        "systems": systems,
        "picks": {
            "active": sorted(active, key=lambda x: x.get("timestamp", ""), reverse=True),
            "recent_closed": sorted(closed, key=lambda x: x.get("timestamp", ""), reverse=True)[:200],
        },
        "portfolios": portfolios,
        "performance": {
            "by_asset_class": ac_breakdown,
        },
        "backtest_vs_forward": bt_vs_fwd,
        "bundles": bundles,
        "audit_events": audit_events,
    }

    out_dir = ROOT / "audit_trail" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "dashboard_payload.json"
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    size_kb = out_path.stat().st_size / 1024
    print(f"  Active picks:  {total_active}")
    print(f"  Closed picks:  {total_closed}")
    print(f"  Systems:       {len(systems)}")
    print(f"  Portfolios:    {len(portfolios)}")
    print(f"  Overall WR:    {overall_wr}%")
    print(f"  Payload size:  {size_kb:.1f} KB")
    print(f"  Written to:    {out_path}")
    return payload


if __name__ == "__main__":
    generate()
```

**Step 2: Run full generation**

Run: `cd /e/findtorontoevents_antigravity.ca && python -m audit_trail.dashboard_generator`
Expected: Summary output with pick counts, system count, payload written

**Step 3: Commit**

```bash
git add audit_trail/dashboard_generator.py audit_trail/data/dashboard_payload.json
git commit -m "feat(audit-dashboard): complete generator with main generate() entry point"
```

---

### Task 5: Build HTML/JS Frontend — Structure and Summary Cards

**Files:**
- Create: `audit_dashboard/index.html`

**Step 1: Create the HTML file with summary section**

Create `audit_dashboard/index.html` — a single-file dark-themed dashboard with inline CSS/JS.

Key sections in the HTML:
1. CSS with dark theme variables (`--bg: #0a0a12`, `--card: #1a1a2e`, etc.)
2. Header with title, timestamp, summary stat cards
3. Filter bar (asset class, system, status, direction, search)
4. Tab navigation (Overview / Active Picks / Closed Picks / Portfolios / Systems / Backtest vs Forward / Bundles / Audit Log)
5. Content sections for each tab
6. JavaScript: load `DATA` global, render all sections, wire filters

The data will be injected as `window.DASHBOARD_DATA = {...}` at build time by the generator.

CSS pattern: follow existing dark theme conventions from `alpha_engine/live_dashboard.html`:
- `background: #0a0a12` for body
- `background: #1a1a2e` for cards
- `#4caf50` for positive/wins, `#f44336` for negative/losses
- `#a78bfa` for purple accents
- Monospace font for numbers

**Step 2: Verify the file renders in a browser**

Open `audit_dashboard/index.html` in browser, verify dark theme renders with placeholder data.

**Step 3: Commit**

```bash
git add audit_dashboard/index.html
git commit -m "feat(audit-dashboard): add HTML frontend with summary cards and filter bar"
```

---

### Task 6: Frontend — Active/Closed Picks Tables with Filters

**Files:**
- Modify: `audit_dashboard/index.html`

**Step 1: Add picks table rendering with filter logic**

JavaScript functions to add:
- `renderActivePicks(picks)` — table with symbol, direction, system, entry, TP/SL, confidence, PnL, timestamp
- `renderClosedPicks(picks)` — same plus exit reason, final PnL
- `applyFilters()` — reads filter bar values, filters both tables
- Each row color-coded by PnL (green/red)
- Badge for asset class (CRYPTO=purple, FOREX=blue, EQUITY=green)
- Badge for direction (LONG=green, SHORT=red)
- Click column headers to sort

**Step 2: Test with sample data**

Embed a small test payload in the HTML, verify tables render and filters work.

**Step 3: Commit**

```bash
git add audit_dashboard/index.html
git commit -m "feat(audit-dashboard): add active/closed picks tables with filtering and sorting"
```

---

### Task 7: Frontend — Portfolios, Systems, Backtest vs Forward, Bundles, Audit Log

**Files:**
- Modify: `audit_dashboard/index.html`

**Step 1: Add remaining tab content renderers**

- `renderPortfolios(portfolios)` — card grid with equity, PnL%, WR, positions, drawdown
- `renderSystems(systems)` — status grid with health indicators (active/retired/empty)
- `renderBtVsFwd(data)` — table: strategy, BT WR, FWD WR, decay, trade counts
- `renderBundles(bundles)` — card grid with confidence badge, WR, trade breakdown
- `renderAuditLog(events)` — chronological event list with type badges

**Step 2: Test all tabs render**

**Step 3: Commit**

```bash
git add audit_dashboard/index.html
git commit -m "feat(audit-dashboard): add portfolios, systems, BT vs FWD, bundles, and audit log tabs"
```

---

### Task 8: Wire Generator to Inject Data into HTML

**Files:**
- Modify: `audit_trail/dashboard_generator.py`

**Step 1: Add HTML build step to generator**

At the end of `generate()`, after writing JSON, also inject into HTML:

```python
def build_html(payload):
    """Inject payload JSON into the HTML dashboard template."""
    html_path = ROOT / "audit_dashboard" / "index.html"
    if not html_path.exists():
        print("  ⚠️  audit_dashboard/index.html not found, skipping HTML build")
        return
    html = html_path.read_text(encoding="utf-8")
    # Replace placeholder with actual data
    marker = "// __DASHBOARD_DATA_PLACEHOLDER__"
    replacement = f"window.DASHBOARD_DATA = {json.dumps(payload, default=str)};"
    if marker in html:
        html = html.replace(marker, replacement)
    else:
        # Fallback: inject before closing </script>
        html = html.replace("</script>", f"\n{replacement}\n</script>", 1)
    html_path.write_text(html, encoding="utf-8")
    print(f"  HTML updated: {html_path}")
```

Call `build_html(payload)` at end of `generate()`.

**Step 2: Run generator and verify HTML has data**

Run: `cd /e/findtorontoevents_antigravity.ca && python -m audit_trail.dashboard_generator`
Then verify: `grep -c "DASHBOARD_DATA" audit_dashboard/index.html` returns 1+

**Step 3: Commit**

```bash
git add audit_trail/dashboard_generator.py audit_dashboard/index.html
git commit -m "feat(audit-dashboard): wire generator to inject data into HTML template"
```

---

### Task 9: GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/audit-dashboard.yml`

**Step 1: Create the workflow**

```yaml
name: Unified Audit Dashboard

on:
  schedule:
    - cron: '*/15 * * * *'   # every 15 min
  push:
    branches: [main]
    paths:
      - 'audit_trail/dashboard_generator.py'
      - 'audit_dashboard/index.html'
      - '.github/workflows/audit-dashboard.yml'
  workflow_dispatch:

permissions:
  contents: write
  pages: write

jobs:
  generate-and-deploy:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Generate dashboard payload
        run: python -m audit_trail.dashboard_generator

      - name: Commit updated data
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add audit_trail/data/dashboard_payload.json audit_dashboard/index.html
          git diff --cached --quiet && echo "No changes" && exit 0
          git commit -m "chore(audit-dashboard): refresh payload [skip ci]"
          git pull --rebase origin main
          git push

      - name: Deploy to findtorontoevents.ca via FTP
        continue-on-error: true
        env:
          FTP_HOST: ${{ secrets.FTP_HOST }}
          FTP_USER: ${{ secrets.FTP_USER }}
          FTP_PASS: ${{ secrets.FTP_PASS }}
        run: |
          python3 - <<'PYEOF'
          import ftplib, os, sys
          from pathlib import Path
          host = os.environ.get("FTP_HOST", "")
          user = os.environ.get("FTP_USER", "")
          pwd  = os.environ.get("FTP_PASS", "")
          if not all([host, user, pwd]):
              print("FTP credentials not set, skipping")
              sys.exit(0)
          src = Path("audit_dashboard/index.html")
          SITE_ROOT = "findtorontoevents.ca"
          try:
              ftp = ftplib.FTP(host, timeout=30)
              ftp.login(user, pwd)
              ftp.cwd(SITE_ROOT)
              try: ftp.mkd("audit")
              except: pass
              ftp.cwd("audit")
              with open(src, "rb") as f:
                  ftp.storbinary("STOR index.html", f)
              print(f"Uploaded {src.stat().st_size} bytes")
              ftp.quit()
          except Exception as e:
              print(f"FTP failed: {e}")
              sys.exit(1)
          PYEOF

      - name: Deploy to torontoevent.net via FTP
        continue-on-error: true
        env:
          FTP_HOST: ${{ secrets.FTPGODADDYHOST_TE_DOTNET }}
          FTP_USER: ${{ secrets.FTPGODADDYUSER }}
          FTP_PASS: ${{ secrets.FTPGODADDYPASS }}
        run: |
          python3 - <<'PYEOF'
          import ftplib, os, sys
          from pathlib import Path
          host = os.environ.get("FTP_HOST", "")
          user = os.environ.get("FTP_USER", "")
          pwd  = os.environ.get("FTP_PASS", "")
          if not all([host, user, pwd]):
              print("FTP credentials not set, skipping")
              sys.exit(0)
          src = Path("audit_dashboard/index.html")
          try:
              ftp = ftplib.FTP(host, timeout=30)
              ftp.login(user, pwd)
              try: ftp.mkd("audit")
              except: pass
              ftp.cwd("audit")
              with open(src, "rb") as f:
                  ftp.storbinary("STOR index.html", f)
              print(f"Uploaded {src.stat().st_size} bytes")
              ftp.quit()
          except Exception as e:
              print(f"FTP failed: {e}")
              sys.exit(1)
          PYEOF

      - name: Verify URLs
        if: always()
        run: |
          sleep 8
          s1=$(curl -o /dev/null -s -w "%{http_code}" --max-time 15 "https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/audit_dashboard/")
          s2=$(curl -o /dev/null -s -w "%{http_code}" --max-time 15 "https://findtorontoevents.ca/audit/")
          echo "GitHub Pages: $s1"
          echo "findtorontoevents.ca/audit/: $s2"
```

**Step 2: Verify YAML syntax**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/audit-dashboard.yml'))" 2>/dev/null || echo "install pyyaml first"`

**Step 3: Commit**

```bash
git add .github/workflows/audit-dashboard.yml
git commit -m "ci(audit-dashboard): add 15-min generation + FTP deploy workflow"
```

---

### Task 10: Run Backfill + End-to-End Test

**Files:**
- No new files

**Step 1: Run the backfill to ensure audit DB has all data**

Run: `cd /e/findtorontoevents_antigravity.ca && python -m audit_trail.backfill`
Expected: Summary of records imported from all sources

**Step 2: Run the generator end-to-end**

Run: `cd /e/findtorontoevents_antigravity.ca && python -m audit_trail.dashboard_generator`
Expected: Payload JSON written, HTML updated with injected data

**Step 3: Open HTML in browser and verify all tabs work**

Check: summary cards show correct totals, picks tables render, filters work, portfolios show, bundles have confidence badges.

**Step 4: Push and verify CI**

```bash
git push
```

Monitor: `gh run watch` — verify workflow runs successfully

**Step 5: Verify deployed URLs**

Run: `curl -s -o /dev/null -w "%{http_code}" "https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/audit_dashboard/"`
Expected: 200

---

## Deployment URLs

- **GitHub Pages (guaranteed):** `https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/audit_dashboard/`
- **FTP (best-effort):** `https://findtorontoevents.ca/audit/`
- **FTP mirror:** `https://torontoevent.net/audit/`

## Summary

| Task | Description | Key Files |
|------|-------------|-----------|
| 1 | Generator scaffold + data source registry | `audit_trail/dashboard_generator.py` |
| 2 | Pick normalization + collection | `audit_trail/dashboard_generator.py` |
| 3 | Portfolios, system stats, audit events | `audit_trail/dashboard_generator.py` |
| 4 | Bundles + main generate() entry | `audit_trail/dashboard_generator.py` |
| 5 | HTML frontend — structure + summary | `audit_dashboard/index.html` |
| 6 | HTML — picks tables + filters | `audit_dashboard/index.html` |
| 7 | HTML — remaining tabs | `audit_dashboard/index.html` |
| 8 | Wire generator → HTML injection | both files |
| 9 | GitHub Actions workflow | `.github/workflows/audit-dashboard.yml` |
| 10 | Backfill + E2E test + deploy | verification |
