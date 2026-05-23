# Session Review — findtorontoevents.ca Antigravity Trading System
## Date: 2026-05-17 | Reviewer: swarm

You are a quantitative systems reviewer auditing a live trading system session.

## What shipped this session (verified commits on main)

### CRYPTO hard gates (quality_gates.py)
- M-035: confidence > 0.90 blocked (WR=14.4% above this level) — enforced
- M-036: direction=BUY blocked (PF=0.38 vs LONG PF=3.14) — enforced  
- M-037: ml_score < 0.65 blocked, None = fail-open — enforced
- M-038: NUPL euphoria filter (Coin Metrics API, shadow NUPL_GATE_ENFORCE=0)
- M-039: Exchange spread divergence stub (EXCHANGE_DIVERGENCE_GATE=0 default)
- M-040: OBI/OFI order flow shadow gate (OBI_GATE_ENFORCE=0)
- ETF_TIGHT_GATE: blocks ETF picks with elite_score < 60 (off until n≥100)
- CRYPTO_MIN_SOURCE_CONSENSUS=3: requires 3+ source systems

### ML features wired
- OI momentum: oi_change_pct_4h, oi_price_diverge (zero-fill when OI absent)
- Garman-Klass vol: gk_vol_14 (20 total features now, up from 17)

### Infrastructure
- OBI/OFI: crypto_signal_engine/obiflow.py with 12-sample cold-start guard
- NUPL: tools/research/nupl_regime.py (fail-open stub, NUPL_OVERRIDE env)
- DBMF replication: tools/research/dbmf_replication.py fixed (pandas ME + squeeze) → 7 LONG signals
- OFOX AI engine: api.ofox.ai, model z-ai/glm-4.7-flash:free (free tier)
- Portfolio gates PCG-5: dashboard_generator.py wired (shadow)
- Schema drift watchdog: .github/workflows/schema-drift-audit.yml (nightly)

## Current asset class stats (dashboard_data.json, ~2026-05-17)
- EQUITY: WR=52.7% PF=1.56 n=421 — T2, ACTIVE real-money (small size)
- CRYPTO: WR=47.2% PF=1.33 n=7766 — below T2; M-035/036/037 now filtering
- COMMODITY: WR=55.22% PF=1.92 n=67 (base); SHORT-only: PF=2.10/WR=58.06% n=62
- ETF: WR=57.14% PF=1.32 n=105; OOS PF=1.90/WR=67.44%  
- FOREX: DISABLED (PF=0.27 class-wide; forex-rsi-ema-scout PF=1.68 n=22 but OOS PF=0.65)
- BOND: WR=55.6% PF=1.72 n=18 — below charter floor (n<20)

## Still running (agents in background)
- M-041 swarm single-tier gate (blocks tier=single without WR≥50%/PF≥1.30/n≥30)
- ETF sector rotation (macro veto + RS overlay, both shadow default OFF)
- Bond scanner expansion (TLT/HYG → 14 symbols)
- Confidence calibration tracker (bucket WR/PF drift detector)

## Known blockers / pending user actions
- MySQL ghost-row purge (655k stale rows) — PA MySQL not accessible from local
- UEPS_ENABLE_PEAD=1 check in prod .env — need PA console
- CT=F PROBATION review: 2026-06-06
- CVX PROBATION review: 2026-05-30
- Enable CRYPTO_CONF_INVERSION_GATE=1 after 2026-06-15 (30d shadow done)
- Enable ETF_TIGHT_GATE=1 when ETF n≥100 (currently n=105 — nearly ready)

## Your task

Review the above comprehensively and identify:

1. **Missed risks** — gates that are shadow/off but should be enforced NOW given the stats
2. **Missing gates** — edge cases not covered by M-035 through M-041
3. **Data integrity gaps** — schema drift, stale data, orphan strategies
4. **Quick wins** (S effort, <2h) the next agent should tackle immediately
5. **P0 issues** — anything that could cause real-money loss if not fixed

Output as structured JSON:
```json
{
  "missed_risks": [{"item": "...", "severity": "P0|P1|P2", "rationale": "..."}],
  "missing_gates": [{"gate": "...", "asset_class": "...", "evidence": "...", "effort": "S|M|L"}],
  "data_integrity_gaps": [{"gap": "...", "file_or_table": "...", "fix": "..."}],
  "quick_wins": [{"action": "...", "file": "...", "effort_hours": 0, "expected_impact": "..."}],
  "p0_issues": [{"issue": "...", "immediate_action": "..."}],
  "overall_verdict": "SHIP_READY|NEEDS_FIXES|CRITICAL_GAPS",
  "top_3_next_actions": ["action1", "action2", "action3"]
}
```
