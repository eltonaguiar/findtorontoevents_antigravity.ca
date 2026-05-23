# Session Review — 2026-05-17 Round 5

## Context
You are a senior quant / systems engineer reviewing progress on a live trading edge system.
Review the session deliverables below and identify any remaining concerns, missed steps, or follow-up items.

## Session Deliverables (this session)

### 1. M-045 EQUITY VIX Filter Gate (SHIPPED)
- Added to `audit_trail/quality_gates.py` — blocks EQUITY picks when VIX > 25 (default OFF, shadow)
- 5 tests added to `tests/test_quality_gates.py` (TestM045EquityVixFilter), all passing
- Gate: EQUITY_VIX_FILTER=1 to enable. Threshold: EQUITY_VIX_FILTER_THRESHOLD (default 25.0)
- Fail-open: if VIX unavailable, picks pass

### 2. CI Test Fix — A9 Emitter Dedup (SHIPPED)
- Fixed `TestArchiveDedupGuard` in `tests/test_code_review_apr22_bugfixes.py`
- Root cause: A9 emitter-dedup (SHA1 key from asset_class+strategy+symbol+direction) collapsed all test picks
- Fix: `monkeypatch.setenv("EMITTER_DEDUP", "0")` in `_patch_paths` autouse fixture

### 3. quan_engine Investigation (SHIPPED)
- Created `docs/STRATEGY_INVESTIGATION_quan_engine_2026_05_17.md` per CLAUDE.md protocol
- Stage 1 (Reduce Risk): PF=0.70, ~18% CRYPTO volume, ~1452 resolved picks
- Three-axis autopsy NOT yet complete — hard block NOT authorized
- Timeline: autopsy 2026-05-24, review 2026-05-31, user approval 2026-06-07

### 4. Weekly Real-Money Filter Report (SHIPPED)
- `reports/weekly_filter_2026-05-17T0521Z.md` + `reports/weekly_filter_2026-05-17.md`
- Kelly sizing computed per quarter-Kelly (fraction=0.25):
  - EQUITY: 5.2% per pick ($524 at $10k), T2 certified (PF=1.65/WR=53.2%)
  - COMMODITY SHORT: 7.6% per pick, verified PF=2.10/WR=58.06% (OOS PF=1.71)
  - CRYPTO elite: 6.2% per pick (copy_trader/coinglass_whale/funding_rate_scanner only)
  - ETF: 9.3% (paper only, n=75 < 100)

### 5. EQUITY Tiered Conviction Sizing (SHIPPED)
- `alpha_engine/config.py`: EQUITY_CONVICTION_TIER constants (HIGH>80=1.5x, MED 60-80=1.0x, LOW<60=0.5x)
- `alpha_engine/kelly_position_sizer.py`: `equity_conviction_multiplier(score)` function
- Default OFF (EQUITY_CONVICTION_TIERS=1 to enable)

### 6. Edge Filter v3 Latest Run Results
edge_filter_engine_v3.py just ran (2026-05-17T0540Z):
- **EQUITY** at elite>=45: n=109, WR=64.2%, PF=3.24 IS; OOS PF=2.20/WR=51.28%/n=39
  - Current production floor: M-038 elite_score>=55 (WR=73.5%, PF=5.11 IS on n=68)
  - OOS n=39 is small — T1 potential but needs more data
- **COMMODITY SHORT**: n=62, WR=58.06%, PF=2.10; OOS PF=1.71/WR=54.55%/n=44 ✓ confirmed
  - ⚠️ Concentration: `cftc_cot_commercial_signal` = 51.6% of picks, HHI=0.485
- **CRYPTO proven**: n=330, WR=64.24%, PF=3.14; OOS PF=3.88/WR=67%/n=233 (very strong)
- **FOREX** `forex-rsi-ema-scout` only: n=22, WR=54.55%, PF=1.68 IS; OOS PF=0.65/WR=42.86%/n=7 — FAILS OOS
- **ETF**: n=105, OOS PF=1.90/WR=67.44%/n=43 (improving)

### 7. Modules Verified as Wired (NOT orphans)
- `phase5_dashboard_integration.load_hourly_picks()` → `audit_trail/dashboard_generator.py:4141`
- `CopytraderManager` → `alpha_engine/smart_picks_engine.py:1634`

## Current Open Items

### BLOCKED (require external access)
- MySQL ghost-row purge: 655k stale rows in `ejaguiar1_stocks` (PA console required)
- UEPS_ENABLE_PEAD=1: check prod `.env` on PythonAnywhere (PA console required)

### PENDING (code-actionable)
- **edge_concentrator ATR**: current uses proxy `|entry - existing_sl|`; real ATR-14 would need yfinance fetch
  - Q: Is the ATR proxy sufficient or should we add yfinance ATR-14 lookup?
- **COMMODITY concentration cap**: cftc_cot_commercial_signal at 51.6% (HHI=0.485 > 0.25 threshold)
  - Options: (a) add 30% per-source cap in quality_gates, (b) document as known risk, (c) require 2nd confirmed source
- **EQUITY OOS at elite>=45**: OOS PF=2.20 (n=39) — promising but sample too small to loosen M-038 floor
  - Q: Should we shadow-test at elite>=50 (between current 55 and experimental 45)?
- **CRYPTO OOS at PF=3.88**: very strong — should we document this as T1-class elite filter?
- **FOREX OOS failure**: forex-rsi-ema-scout OOS PF=0.65 confirms class-wide disable is correct

## Questions for the Swarm

1. **COMMODITY concentration**: Single strategy (cftc_cot_commercial_signal) = 51.6% of all COMMODITY picks.
   Is this acceptable for a PF=2.10 strategy with OOS PF=1.71? Or should we require a 2-source minimum before sizing?

2. **EQUITY floor optimization**: M-038 sets elite_score>=55. OOS data shows elite>=45 gives PF=2.20 (n=39 OOS).
   What's the appropriate action: shadow at >=50, wait for OOS n>=100, or keep floor at 55?

3. **CRYPTO proven strategies** (PF=3.14 IS, OOS PF=3.88): This is exceptional. What could cause OOS > IS?
   Is this a data artifact (OOS period happened to be a bull market) or genuine edge?

4. **edge_concentrator real ATR vs proxy**: `|entry - existing_sl|` is a usable proxy for ATR.
   Is the added complexity of yfinance ATR-14 fetch worth the risk (network calls, API limits)?

5. **Any remaining actionable items** this session that weren't addressed?

## Success Criteria Check (from /money-maker-readyv2)

1. ✅ EQUITY: T2 certified (PF=1.65/WR=53.2%/n=393) — weekly filter shows 5.2% Kelly sizing
2. ✅ CRYPTO: Elite strategies identified (PF=2.34-3.97, copy_trader/coinglass_whale/funding_rate_scanner)
3. ✅ COMMODITY: POST-COT-dedup SHORT-only PF=2.10 confirmed (n=62), OOS PF=1.71
4. ⚠️ ETF: n=75 (was 105) — building toward stable; OOS PF=1.90 is strong
5. 🚫 FOREX: OOS PF=0.65 — hard disable confirmed correct
6. ⚠️ BOND: n=11 — still below M-043 floor (n<20)
7. ✅ Kelly sizing: computed per class in weekly filter reports

## Format
Respond with JSON:
```json
{
  "verdict": "NEEDS_WORK | MOSTLY_DONE | DONE",
  "critical_gaps": ["item1", "item2"],
  "commodity_concentration_verdict": "ACCEPTABLE | REQUIRES_CAP | REQUIRES_2ND_SOURCE",
  "equity_floor_recommendation": "KEEP_55 | SHADOW_50 | LOWER_45",
  "crypto_oos_better_than_is_explanation": "...",
  "atr_proxy_verdict": "PROXY_SUFFICIENT | UPGRADE_TO_REAL_ATR",
  "remaining_actionable_items": ["item1"],
  "summary": "one paragraph"
}
```
