# Audit Dashboard Rebuild Guide

## Overview

The audit dashboard is a static HTML page (`audit_dashboard/index.html`) generated from multiple JSON data sources. It's rebuilt automatically via GitHub Actions on every push to `main` (path-filtered) and hourly via cron.

---

## Local Rebuild (One Command)

```bash
python -m audit_trail.dashboard_generator
```

This single command:
1. Acquires a lock file (`audit_trail/data/.generator.lock`) to prevent concurrent runs
2. Calls `generate()` → reads all JSON data sources, applies quality gates, stamps, scores
3. Calls `build_html()` → merges the payload into `audit_dashboard/template.html`
4. Writes `audit_dashboard/index.html`
5. Releases the lock

**Typical runtime:** 30–90 seconds depending on data volume.

---

## Full Pipeline Rebuild (Step by Step)

If you've changed scoring logic, quality gates, or strategy thresholds and want the dashboard to reflect those changes, run **each step in order**:

### Step 1: Stamp pick quality (backfill `strat_fwd_wr`, `strat_fwd_trades`, trust tiers)

```bash
python audit_trail/stamp_pick_quality.py                    # active_picks.json (default)
python audit_trail/stamp_pick_quality.py --file alpha_engine/data/closed_picks.json  # closed picks
```

### Step 2: Score booster (recalculate elite scores with new weights/penalties)

```bash
python -m alpha_engine.score_booster
```

### Step 3: Smart Picks engine (regenerate `smart_picks.json`)

```bash
python alpha_engine/smart_picks_engine.py
```

### Step 4: Generate dashboard

```bash
python -m audit_trail.dashboard_generator
```

### Step 5: Generate blueprint (portfolio strategy breakdown)

```bash
python -m audit_dashboard.blueprint_generator
```

---

## CI Pipeline (GitHub Actions)

The workflow `.github/workflows/audit-dashboard.yml` runs the full pipeline automatically:

| Step | Command | Fatal? |
|------|---------|--------|
| Resolve picks | `python -m audit_trail.universal_pick_resolver` | ✅ |
| Prediction markets | `python -m prediction_market_agents.orchestrator` | ❌ |
| Non-crypto consensus | `python -m copy_trader_intel.non_crypto_consensus` | ❌ |
| ML Gatekeeper | `python ml_gatekeeper/gatekeeper.py` | ❌ |
| ML Consensus | `python ml_consensus/consensus.py` | ❌ |
| Walk-forward validator | `python -m alpha_engine.walkforward_validator` | ❌ |
| Score booster + Dashboard | `python -m alpha_engine.score_booster && python -m audit_trail.dashboard_generator` | ✅ |
| Blueprint | `python -m audit_dashboard.blueprint_generator` | ✅ |

**Trigger:** Push to `main` (path-filtered to dashboard source files) or hourly cron at `:10`.

---

## Key Data Files

| File | Purpose |
|------|---------|
| `alpha_engine/data/active_picks.json` | All live/unresolved picks |
| `alpha_engine/data/closed_picks.json` | All resolved picks with P&L |
| `alpha_engine/data/smart_picks.json` | Smart Picks output (scored subset) |
| `audit_dashboard/template.html` | HTML template with JS for rendering |
| `audit_dashboard/index.html` | Generated output (deployed to GitHub Pages) |
| `audit_trail/data/dashboard_payload.json` | Intermediate JSON payload |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Could not acquire lock — exiting` | Delete `audit_trail/data/.generator.lock` if stale |
| Picks missing `strat_fwd_wr` | Re-run `stamp_pick_quality.py` on the affected JSON file |
| Dashboard shows stale data | The generator reads JSON files at runtime — ensure they're updated first |
| CI dashboard out of sync | Check the workflow run logs; non-fatal steps may have skipped data updates |
| `very_low_rr` filtering picks | New two-tier RR gate: RR<0.5 hard-blocked, RR 0.5-0.8 gets -10pt soft penalty |

---

## Session Changes Reflected in Current Build

- **Soft penalties**: `confidence_floor` and `low_rr` converted from hard-blocks to -10pt penalties
- **Two-tier RR gate**: RR<0.5 hard-blocked (`very_low_rr`), RR 0.5-0.8 soft -10pt
- **VA gate tightened**: `fwd_wr ≥ 55% + n ≥ 10` (was n≥5; n≥20 excluded good picks at 66.7% WR)
- **Strategy stats backfilled**: 99% of closed picks now have `strat_fwd_wr`
- **Goldmine crypto blocked**: `goldmine_1x/2x/3x_consensus` on CRYPTO asset class
- **Trust penalty reduced**: -15 → -10 (was stacking to -35 total)
- **Non-crypto expansion**: MAX_NON_CRYPTO_PICKS 3→5, expanded allowlists
- **Forward-validated bypass**: Strategies with ≥20 trades + ≥50% WR bypass min score gate
