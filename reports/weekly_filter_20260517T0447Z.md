# Weekly Real-Money Filter — 2026-05-17

**Generated:** 2026-05-17T04:47Z  
**Dashboard freshness:** 1.9h (generated 2026-05-17T02:02Z)  
**Data sources:** `dashboard_data.json::picks.recent_closed` (n=3,500), `closed_picks.json` (n=8,421), `asset_class_health` (post-resolver-v2.1)  
**Kelly method:** 0.25× fractional Kelly on empirical win/loss distributions — conservative sizing, not financial advice.

---

## Baseline Snapshot (post-resolver-v2.1)

| Asset Class | n (all-time) | WR | PF | OOS WR | Tier | Sizing |
|---|---|---|---|---|---|---|
| EQUITY | 393 | 53.2% | 1.65 | 66.1% (7 folds) | T2 candidate | ✅ allowed |
| CRYPTO | 7,514 | 46.8% | 1.32 | 45.3% (54 folds) | sub-T2 | ✅ allowed |
| COMMODITY | 228 | 85.5% | 7.71 | — | T1 | ✅ allowed |
| ETF | 75 | 66.7% | 2.25 | 75.0% (5 folds) | T1 candidate | ⚠️ n<100 |
| FOREX | 251 | 57.8% | 0.85 | — | sub-floor | ❌ disabled |
| BOND | 11 | 54.5% | 0.66 | 56.2% | thin | ❌ n<100 |

*OOS WR from `walkforward.by_class` (walk-forward cross-validation)*

---

## EQUITY Top Picks Filter

**Filter:** `source_system = kimi_riseoftheclaw`, `asset_class = EQUITY`, `status = OPEN`

| Metric | Value | Source |
|---|---|---|
| Historical n | 210 (recent_closed window) | picks.recent_closed |
| Win Rate | 56.7% | empirical |
| Profit Factor | 2.09 | empirical |
| OOS Walk-Forward WR | 66.1% ± 12.9pp (7 folds) | walkforward.by_class |
| Average Win | +3.2% | computed |
| Average Loss | −2.0% | computed |
| Raw Kelly | 29.5% | computed |
| **0.25× Kelly (position size)** | **7.4% of account** | fractional Kelly |
| **$ per pick at $10k account** | **$738** | |

**How to apply on `/audit`:**
1. Filter: Asset Class = Equity → Source = kimi_riseoftheclaw → Status = Open
2. Sort by `elite_score` descending — take top 3–5 picks
3. Size each at **7.4%** of account (cap total EQUITY exposure at 3 picks max = 22.2%)
4. Honor TP/SL as set on pick; no manual overrides

**Risk note:** OOS WR=66.1% (7 folds, std=12.9pp) is well above the 55% T2 floor. EQUITY is the only class with proven OOS > in-sample signal. The kimi filter dominates: 210/252 (83%) of recent EQUITY closed picks.

---

## COMMODITY Top Picks Filter

**Filter:** `direction = SHORT`, `source_system IN (multi_asset_cot, multi_asset_copytrader)`, `asset_class = COMMODITY`

| Metric | Value | Source |
|---|---|---|
| Historical n | 261 (closed_picks.json) | closed_picks.json |
| Win Rate | 77.4% | empirical |
| Profit Factor | 4.73 | empirical |
| Average Win | +2.7% | computed |
| Average Loss | −2.0% | computed |
| Raw Kelly | 61.0% | computed |
| **0.25× Kelly (position size)** | **5.0% of account (capped)** | fractional Kelly, capped at 5% |
| **$ per pick at $10k account** | **$500** | |

**Sub-source breakdown (closed_picks.json):**

| Source | Direction | n | WR | PF |
|---|---|---|---|---|
| multi_asset_cot | SHORT | 130 | 79.4% | 4.94 |
| multi_asset_copytrader | SHORT | 131 | 74.8% | 4.52 |
| cta_replicator | SHORT | 59 | 17.2% | 0.22 |
| cta_replicator | LONG | 24 | 0.0% | 0.00 |

⚠️ **cta_replicator is drag** — exclude entirely. Only multi_asset_cot + multi_asset_copytrader SHORT qualify.  
⚠️ **LONG COMMODITY = hard avoid** — multi_asset_cot LONG is n=1, WR=0%. No LONG COMMODITY picks.

**Raw Kelly is 61% — capped to 5% per pick for risk management** (COMMODITY picks carry basis risk; commodity leverage can gap).

**Active picks matching this filter RIGHT NOW:** 4
- ZW=F SHORT (elite_score=26.8) — Wheat futures
- CT=F SHORT (elite_score=26.8) — Cotton futures  
- CT=F SHORT (elite_score=26.2) — Cotton (second entry)
- ZW=F SHORT (elite_score=25.2) — Wheat (second entry)

**How to apply on `/audit`:**
1. Filter: Asset Class = Commodity → Direction = Short → Source = multi_asset_cot OR multi_asset_copytrader
2. Size each at **5.0%** of account (max 3 concurrent = 15% total COMMODITY exposure)
3. REJECT any COMMODITY LONG pick — no edge confirmed

---

## ETF Top Picks Filter

**Filter:** `source_system = kimi_riseoftheclaw`, `asset_class = ETF`, `status = OPEN`

| Metric | Value | Source |
|---|---|---|
| Historical n | 99 (recent_closed window) | picks.recent_closed |
| Win Rate | 56.6% | empirical |
| Profit Factor | 1.39 | empirical |
| OOS Walk-Forward WR | 75.0% ± 5.5pp (5 folds) | walkforward.by_class |
| Average Win | +2.4% | computed |
| Average Loss | −2.3% | computed |
| Raw Kelly | 15.8% | computed |
| **0.25× Kelly (position size)** | **3.9% of account** | fractional Kelly |
| **$ per pick at $10k account** | **$394** | |

**Charter note:** ETF all-time n=75 < 100-pick charter floor → `sizing_allowed=False` in dashboard. The recent_closed window shows n=99 which is near threshold. **Use paper-trade sizing only until all-time n≥100** — expected within 1–2 weeks at current pick rate.

**How to apply:**
1. Filter: Asset Class = ETF → Source = kimi_riseoftheclaw → Status = Open
2. **Paper trade only** at 3.9% size until n_all_time hits 100
3. Track OOS WR — 75% is T1-grade; promote to live sizing at n≥100

---

## CRYPTO Elite Filter

**Filter:** `source_system IN (mega_mutation, kimi_riseoftheclaw, claude_gainer_st, dna_winner_picks, signal_validation, baby_strats_forward, aggregated_picks)`, `asset_class = CRYPTO`

**Exclude:** `quan_engine` (WR=30.4%, PF=0.41), `rapid_fire` (WR=29%, PF=0.16), `luxalgo_filters` (WR=43.5%, PF=1.00), `battleground` (WR=43.7%, PF=0.57)

| Source | n | WR | PF | Notes |
|---|---|---|---|---|
| mega_mutation | 94 | 60.6% | 2.61 | ✅ T2, MDD watch (44.6%) |
| kimi_riseoftheclaw | 89 | 58.4% | 1.65 | ✅ T2 |
| claude_gainer_st | 110 | 56.4% | 1.48 | ✅ T2 borderline |
| dna_winner_picks | 132 | 52.3% | 1.88 | ✅ T2 |
| signal_validation | 26 | 53.8% | 2.08 | ✅ Building (n<100) |
| baby_strats_forward | 539 | 51.9% | 1.65 | ✅ T2 (largest sample) |
| aggregated_picks | 52 | 50.0% | 1.77 | ✅ T2 borderline |
| **ELITE COMBINED** | **1,042** | **53.7%** | **1.85** | |

| Metric | Value |
|---|---|
| Raw Kelly | 24.7% |
| **0.25× Kelly** | **6.2% of account** |
| **$ per pick at $10k** | **$618** |

**How to apply on `/audit`:**
1. Filter: Asset Class = Crypto → Source = [any of 7 elite sources above]
2. Exclude any pick where `source_system` is quan_engine / rapid_fire / luxalgo_filters / battleground
3. Size at **6.2%** per pick, max 4 concurrent CRYPTO positions = 24.8% total CRYPTO exposure
4. Prefer picks with `elite_score ≥ 55` and `confidence ≥ 0.6`

---

## BOND — Accumulating (No Sizing Yet)

n=11 all-time, WR=54.5%, PF=0.66 — PF<1 means it's currently losing money.  
**Action:** No sizing. Monitor `signal_validation` (BOND component) for 20-trade accumulation milestone.

---

## FOREX — Hard Disabled

FOREX PF=0.85 — disabled via `FOREX_HARD_DISABLE=1`. Do not size.  
**Rescue path in progress:** carry-factor scaffold (`tools/research/forex_carry.py`) + ATR mutation Axis 4 registration.

---

## Summary: Position Size Table ($10,000 Account)

| Class | Filter | Size/pick | Max concurrent | Max exposure |
|---|---|---|---|---|
| EQUITY | kimi_riseoftheclaw | $738 (7.4%) | 3 picks | $2,214 (22.1%) |
| COMMODITY | SHORT only, multi_asset_cot/copytrader | $500 (5.0%) | 3 picks | $1,500 (15.0%) |
| ETF | kimi_riseoftheclaw | $394 (3.9%) **paper only** | 3 picks | paper only |
| CRYPTO ELITE | 7-source elite basket | $618 (6.2%) | 4 picks | $2,472 (24.7%) |
| **TOTAL MAX LIVE** | | | | **$6,186 (61.9%)** |

**Remaining 38.1% = cash reserve / DD buffer**

---

## Risk Controls

- **Max per-pick live:** 7.4% (EQUITY cap, most conservative class with proven OOS)
- **Daily soft-stop:** −2% total PnL triggers review pause
- **DD halt:** if rolling 30-day drawdown > 20%, pause all new sizing
- **COMMODITY cap:** 5% hard cap per pick regardless of Kelly output (basis/gap risk)
- **ETF:** paper-trade only until n_all_time ≥ 100
- **Never size FOREX or BOND** until next formal filter review shows PF>1.3 and WR>50%
- **mega_mutation MDD watch:** MDD=44.6% — size at 0.5× (3.1%) until MDD trend improves

---

## Next Formal Review Triggers

| Trigger | Action |
|---|---|
| ETF all-time n hits 100 | Promote ETF to live sizing at 3.9% |
| EQUITY OOS WR < 55% over next 30d | Pause EQUITY sizing |
| COMMODITY PF drops below 2.0 over 30d rolling | Revert to paper-trade |
| mega_mutation MDD < 25% over 60d | Restore to full 6.2% size |
| BOND n hits 20 and PF > 1.3 | Add BOND to filter at 2% paper size |

---

## Daily Ideas Top Action Items (Priority Queue)

From cross-agent synthesis 2026-05-16 (15 ideas ranked). Top 3 unimplemented:

1. **M-034 CRYPTO Confidence Inversion Gate** — enable `CRYPTO_CONF_INVERSION_GATE=1` (coded, shadow-logging). Expected lift: CRYPTO WR 46.8% → ~55%+ for filtered subset. Complexity: LOW (env-var flip after shadow log review).
2. **PCG-5 Portfolio Gate Stack enforce mode** — flip `PCG5_ENFORCE=1` (shadow log in `audit_dashboard/data/pcg5_log.json`). Prevents correlated blowups, concentration, fight-the-regime picks. Complexity: LOW.
3. **COMMODITY SHORT-only tier gate** — add explicit direction gate in `quality_gates.py` blocking COMMODITY LONG from cta_replicator. Complexity: LOW (3-line gate).

---

*Reproducibility: `python tools/money_maker_readyv2_runner.py --date 2026-05-17` (forthcoming)*  
*Not financial advice. All stats are historical; past performance does not guarantee future results.*
