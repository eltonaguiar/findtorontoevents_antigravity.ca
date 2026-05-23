# R:R Band — Per-Asset-Class Slice (addendum to 2026-05-04 reaudit)

Companion analysis to `reports/rr_band_reaudit_2026_05_04.md`. The cross-class aggregate showed every band PF<1.0, recommending withdrawal of the R:R hard gate. **Per-asset slice changes the picture: there IS a usable band, but only for COMMODITY.**

## Data quality note

92% of `closed_picks.json` (6,886 / 7,472) have `asset_class="UNKNOWN"`. This is itself a P1 data-quality issue — the asset-class tagger is not running on most resolver-output picks. The 586 picks with explicit asset_class are the only basis for per-class analysis.

| Asset | Total | Used (had TP/SL/entry/pnl) |
|---|---|---|
| COMMODITY | 74 | 74 |
| CRYPTO | 3 | 3 |
| EQUITY | 28 | 28 |
| FOREX | 449 | 449 |
| FUTURES | 31 | 31 |
| STOCKS | 1 | 1 |
| UNKNOWN | 6,886 | 6,886 |

## Per-asset R:R band table

| Asset | Band | n | WR | PF | Notes |
|---|---|---|---|---|---|
| **COMMODITY** | 1.0-1.5 | 72 | **84.7%** | **7.99** | **Genuinely profitable. Tradable band.** |
| EQUITY | 1.0-1.5 | 3 | 33.3% | 1.21 | Sample too small |
| EQUITY | 1.5-2.0 | 25 | 40.0% | 1.11 | Borderline positive but PF marginal |
| FOREX | 1.0-1.5 | 251 | 27.1% | 0.37 | Loss-making |
| FOREX | 1.5-2.0 | 198 | 23.7% | 0.35 | Loss-making (worst with COMMODITY-1.5-2.0 unsampled) |
| FUTURES | 1.5-2.0 | 31 | 0.0% | 0.00 | All losses; halt-worthy |
| CRYPTO | 1.0-1.5 | 3 | 33.3% | 0.75 | Sample too small |
| UNKNOWN | 1.0-1.5 | 380 | 51.8% | 0.40 | The tagger gap obscures real signal |
| UNKNOWN | 1.5-2.0 | 3,561 | 27.1% | 0.36 | The big bad cohort — 76% of all data |
| UNKNOWN | 2.0-3.0 | 2,883 | 37.0% | 0.45 | Loss-making |

## Recommendations

### 1. R:R hard gate should be PER-ASSET-CLASS, not global

Replace the proposed `RR_HARD_GATE_MIN/MAX` constants with a per-class table:

```python
# Per-class R:R bands derived from closed_picks.json analysis 2026-05-04
RR_BAND_BY_ASSET = {
    "COMMODITY": (1.0, 1.5),     # PF 7.99, WR 84.7%, n=72
    "EQUITY":    (1.5, 2.0),     # PF 1.11 (marginal), n=25
    "FOREX":     None,           # halt-worthy class; no profitable band
    "FUTURES":   None,           # all-loss in sampled band
    "CRYPTO":    None,           # n=3 insufficient
    # UNKNOWN class skipped — fix the tagger first
}
```

A pick whose `asset_class` is in the table and whose R:R falls outside the band is rejected. Picks with UNKNOWN asset class are pass-through (until the tagger is fixed — separate P1 PR).

### 2. The UNKNOWN-class problem is the bigger lever

92% of closed picks lack asset_class tagging. Whatever signal the per-class bands carry is being washed out in any cross-class analysis. **Highest-EV follow-up**: fix the asset-class tagger upstream (likely `audit_trail/dashboard_generator.py` or the source-system normalize path). This will both improve the audit dashboard's correctness and unlock per-asset gating for CRYPTO and FUTURES (currently n=3 and n=31 in clean cohorts; likely much larger once UNKNOWN is properly tagged).

### 3. FOREX halt remains correct

Live data PF 0.35-0.37 across both bands with n=449 confirms the existing recommendation. Per CLAUDE.md mutate-before-kill, this is the documented kill-with-mutation-attempts class.

### 4. COMMODITY 1.0-1.5 is the headline edge — but watch concentration

COMMODITY n=72 PF 7.99 IS the kind of edge claim that Kimi C1 reached for and missed. BEFORE shipping a COMMODITY-only gate, cross-check against the prior super-swarm finding (`reports/super_swarm_synthesis_2026_05_04.md`):

> COMMODITY KC=F = 147% of class PnL — single-symbol concentration risk

If the 72 winning picks in the 1.0-1.5 band are concentrated in KC=F (coffee), the PF 7.99 is a single-instrument fluke, not a tradable strategy. Verify symbol breakdown before any gate change.

## Updated R:R PR readiness

The `feat/rr-hard-gate-shadow-2026-05-04` branch is still **not mergeable as-coded** (uses [1.5, 2.0] global which targets the worst band). Three paths forward:

| Option | Description | Risk |
|---|---|---|
| A | Withdraw entirely | Lowest — but leaves the COMMODITY edge unclaimed |
| B | Repoint to global [1.0, 1.5] | Medium — least-bad cross-class band, still PF<1.0 in aggregate |
| **C** | **Replace with per-asset table above + symbol-concentration guard for COMMODITY** | **Recommended — captures the genuine COMMODITY edge if non-concentrated, drops obvious-bad classes** |
| D | Diagnostic-only logger for 14d | Safe; defers decision |

Option C is the right answer if the COMMODITY-1.0-1.5 PF 7.99 survives a KC=F deconcentration check.

## VERIFIED — COMMODITY edge is single-symbol fluke

Ran the symbol-breakdown check. Result:

| Symbol | n | WR | PnL sum |
|---|---|---|---|
| **CT=F** | 71 | 85.9% | +2.6215 |
| KC=F | 1 | 0.0% | -0.0491 |

**71 of 72 picks (98.6%) are on a single instrument (CT=F, cotton futures).** The COMMODITY-class "edge" is one symbol's anomaly, not a class-level pattern. Note this also corrects an earlier prior-swarm finding: the concentration warning had been pinned to KC=F (coffee at 147% of class PnL in `system_clean_metrics.multi_asset_cot.concentration_warning`), but in the closed-pick R:R-1.0-1.5 cohort, the concentration is on CT=F (cotton). Both symbols carry concentration risk; the dashboard surfaces the wrong one.

## Recommendation REVISED → Option D

Option C (per-asset gate) is **withdrawn**. Even the only seemingly-profitable per-class band collapses under symbol-concentration scrutiny.

**Final R:R remediation: Option D (diagnostic-only shadow logger, 14d)**:

- Implement `logs/rr_diagnostic.log` line per scored pick: `(timestamp, symbol, asset_class, strategy, rr, direction, score, will_close_with: TBD)` — no filtering.
- Daily summary cron computes per-(asset, symbol, band) PF/WR.
- After 14 days, review: only ship a hard gate for an (asset, symbol) pair if PF > 1.5 AND n ≥ 30 of distinct picks.
- Until then, keep the gate disabled. Remove the misleading +10/0/-5/-10 score-band adjustments in `audit_trail/quality_gates.py:2492-2511` (acting on stale numbers per the parent reaudit).

## What this kills

- The R:R hard gate as a P0 backlog item — done, withdrawn.
- The "Kimi C1 = golden zone PF 5.81" claim — fabricated/wrong sample.
- The local 2026-04-01 "DATA CORRECTED" comment — stale n=1,868 sample no longer holds.

## What this elevates

- **The asset-class tagger**. 92% UNKNOWN means the dashboard's per-class numbers are unreliable. Every other downstream gate (R:R, n-guard, trust_score) is degraded by this. Highest-EV follow-up is fixing the tagger upstream.
- **Symbol-concentration disclosure** site-wide. Both KC=F (147% of COMMODITY class PnL via system_clean_metrics) and CT=F (98.6% of COMMODITY R:R-1.0-1.5 cohort) need surfaced. The dashboard credibility audit needs to add concentration callouts wherever PF/WR is shown for an asset class.

---

(Original Option C verification block below is now historical; left in place for the audit trail.)

## Verification needed before C (now answered above — fluke confirmed)

```bash
# Filter COMMODITY 1.0-1.5 band and break down by symbol
python -c "
import json
from collections import defaultdict
d = json.load(open('alpha_engine/data/closed_picks.json'))
if isinstance(d, dict): d = d.get('picks', d)
by_sym = defaultdict(lambda: {'win':0,'loss':0,'pnl':[]})
for p in d:
    if (p.get('asset_class') or '').upper() != 'COMMODITY': continue
    e=p.get('entry_price',0); tp=p.get('take_profit',0); sl=p.get('stop_loss',0); pnl=p.get('pnl_pct')
    if not (e and tp and sl) or pnl is None: continue
    rr = abs(tp-e)/abs(e-sl) if abs(e-sl)>0 else 0
    if not 1.0 <= rr < 1.5: continue
    sym = p.get('symbol','?')
    by_sym[sym]['win' if pnl>0 else 'loss']+=1; by_sym[sym]['pnl'].append(pnl)
for s,b in sorted(by_sym.items(), key=lambda x: -(x[1]['win']+x[1]['loss']))[:10]:
    n=b['win']+b['loss']; wr=100*b['win']/n if n else 0
    print(f'{s:<10} n={n:<3} WR={wr:.1f}% PnL_sum={sum(b[\"pnl\"]):.4f}')
"
```

This 1-liner determines whether the COMMODITY edge is real or a KC=F artifact. If concentrated → fall back to Option D (diagnostic-only logger). If diversified → ship Option C.
