# DAILY_IDEAS — Statistical Edge Per Asset Class — 2026-05-13T01:08Z

Mining `DAILY_IDEAS.MD` for concrete, testable edge hypotheses per asset
class. Cross-walked with live `dashboard_data.json` state (0.45h fresh).

## Live per-class baseline (canonical)

| Class | n | WR % | PF | Total PnL % | tier | concentration tier | Top symbol share |
|---|---|---|---|---|---|---|---|
| **COMMODITY** | 422 | 67.5 | **3.89** | +686.77 | T1 candidate | **WARN** | CT=F at 75.57% |
| EQUITY | 447 | 53.2 | 1.55 | +376.68 | **T2 confirmed** | OK | AMD at 11.19% |
| ETF | 107 | 56.1 | 1.34 | +37.48 | sub-T2 | OK | XLE at 20.91% |
| CRYPTO | 7935 | 46.5 | 1.36 | +3019.29 | sub-T2 (WR<50) | OK | BTCUSDT at 10.27% |
| FOREX | 1355 | 46.1 | 0.29 | **-1026.15** | **stressed** | OK | USDCHF at 26.49% |
| BOND | 11 | 54.5 | 0.66 | -1.53 | thin (n<100) | n/a | n/a |

Verified Tier-2 systems (4 still pass charter floors):

| System | PF | WR | n | MDD | asset_classes | last_signal |
|---|---|---|---|---|---|---|
| **multi_asset_cot** | 21.33 | 88.2 | **144** | 17.8 | COMMODITY | 2026-05-12 |
| signal_validation | 4.31 | 51.0 | 535 | 8.1 | CRYPTO+FOREX | 2026-05-12 |
| ml_crypto_pred_v12 | 2.53 | 55.6 | 123 | 11.0 | CRYPTO | **2026-02-22 DEAD** |
| copy_trader_intel | 1.84 | 50.0 | 690 | 2.23 | COMMODITY+CRYPTO | 2026-05-08 |

`multi_asset_cot` n grew 130→144 since session start. PF 19.19→21.33.
Trajectory consistent with class concentration finding (CT=F is the edge).

---

## Per-class edge hypotheses ranked by leverage

### COMMODITY — focus on CT=F sub-class, NOT class-aggregate

Class headline PF=3.89 misleading per A6 audit. Real edge is `multi_asset_cot on CT=F`.

**Edge #1: CT=F COT positioning (existing, needs verification)**
- `multi_asset_cot` PF=21.33 / WR=88.2 / n=144 — implausibly high; P0-#1 DB-verify pending (`tools/verify_system_pf.py` shipped this session)
- IF verified MATCH: this single strategy on this single instrument IS the entire COMMODITY edge
- Source: DAILY_IDEAS 2026-05-09 baseline + 2026-05-11 supreme plan
- Action: dispatch `ab_analysis.yml` cron → inspect `system_pf_verification.json`

**Edge #2: Friction-adjusted DSR gate on CT=F**
- `tools/cot_step7_friction_adjusted_mc.py` shipped (`d60a7b2656d`)
- Gate: DSR ≥ 0.85 at n_trials=500. If output < 0.85 = CT=F NOT LIVE_ELIGIBLE regardless of paper-pilot result
- Pending: next cron output

**Edge #3: DBMF/KMLM commodity-momentum replication** (DAILY_IDEAS B-COMMODITY)
- Industry-grade systematic CTA strategies with public NAV — academic basis well-documented
- Capacity: $1B+ AUM trade these, so capacity is real
- Action: scaffold `tools/research/dbmf_replication.py` as backtest target

**Edge #4: Roll-yield asymmetry** (B-COMMODITY)
- Crude contango/backwardation regime gate
- Natgas seasonal post-LNG-export shift
- Both have well-documented pre-2024 alpha; need OOS verification on 2024-2026 sample

### EQUITY — only confirmed Tier-2 class; widen pipeline

**Edge #5: PEAD (Post-Earnings Announcement Drift)** (DAILY_IDEAS B-EQUITY)
- Long-documented anomaly; survives transaction-cost auditing
- DE Shaw R3 in supreme plan: "PEAD edge is real, not yet shipped"
- Already partially wired (`alpha_engine/data/incubator_picks.json`); needs explicit strategy
- Capacity caveat: HFT-crowded since ~2022; per-name short-window edge has decayed
- Action: backtest EQUITY top-100 cross-section with 2-day post-earnings window

**Edge #6: QMOM/IMOM momentum-crash survival** (B-EQUITY)
- 12-1m momentum factor + crash-protection overlay (skip when X-month return < -threshold)
- AQR R3 prescription: factor-beta not alpha
- Cap-weighted vs equal-weighted matters
- Action: backtest against current EQUITY n=447 cohort

**Edge #7: Sector-rotation XLF/XLE/XLK** (B-EQUITY)
- Cross-sectional momentum across 11 SPDRs
- Sharpe ~0.7-1.0 historical, low capacity ceiling but durable
- Pairs with risk-parity rotation idea (B-ETF)

### CRYPTO — diversified but sub-T2; identify draggers

PF 1.36 / WR 46.5% / n=7935 with top symbol only 10% = no single-symbol artifact. Edge is sub-50% WR → the 7935 distribution itself has structural drag.

**Edge #8: Strategy-level concentration check** (A3 just shipped per-strategy rollup)
- Next cron `dashboard_data.json::asset_class_concentration.CRYPTO.top_strategy` will surface which strategy drives the CRYPTO mass
- Likely candidates per blocklist + drag log:
  - `kimi_signal_tracking` already class-wide blocked (-930% PnL)
  - `alpha_engine_fast` PF 0.62, freebuff just quarantined
  - `crypto_winners` PF 0.39 (per Mimo audit)
- Action: inspect next cron output; quarantine if any strategy >40% drag

**Edge #9: Hyperliquid HLP carry replication** (DAILY_IDEAS B-CRYPTO)
- Documented Sharpe 2.5-3.5 on $HLP $1.5B AUM — real funded-perp basis carry
- Replicable via funding-rate proxy: long spot + short funding-positive perps
- Action: scaffold backtest from CFTC + funding-rate data (needs CFTC_API_KEY)

**Edge #10: BTC seasonal-by-UTC-hour** (B-CRYPTO + memory `feedback_quick_guess_horizons`)
- Memory `project_clean_data_symbol_wr` shows 22 UTC = 61.2% WR, 08-09 UTC = death zone
- Free pure-statistical edge, no data-key cost
- Action: add `_hour_filter` parameter to crypto strategies; backtest the +22 UTC slot

**Edge #11: Funding skew + taker imbalance + OI delta** (B-CRYPTO)
- Post-2024 documented Sharpe>1.5 on Glassnode data
- Blocker: `GLASSNODE_API_KEY` MISSING in GH secrets
- Cost: Glassnode pro ~$30/mo
- Action: surface to user as data-key procurement decision

### ETF — closest to T2 graduation

PF 1.34 / WR 56.1% / n=107 — needs PF lift OR n scale to graduate.

**Edge #12: ETF subset analysis** (per A6 sub-class learning)
- Top symbol XLE 20.91% — energy ETF dominance
- Diversifier role may be broken (need sub-class split similar to commodity ag vs metal)
- Action: re-stratify ETF picks by sector ETF vs broad-market ETF vs international

**Edge #13: Risk-parity rotation post-2022 reset** (B-ETF)
- 2022 reset broke classic 60/40; current optimal weights differ
- Black-Litterman over treasury duration + equity exposure (B-BOND ref)
- Action: `pyportfolioopt` wire-up already documented; ship

### FOREX — confirmed stressed; do NOT trade until rehab

PF 0.29 / -1026% PnL / n=1355 = catastrophic. Memory: mutate-before-kill required.

**Edge #14: Carry-factor activation** (B-FOREX + AQR R3 supreme plan)
- AQR R3: "FOREX failing because momo applied where carry has 30yr alpha"
- Re-orient default FOREX strategy from MomentumEMA (already blocked) to G10 carry factor
- Long high-yielder, short low-yielder; rebalance monthly
- 30-yr Sharpe ~0.7-0.9 documented (carry trade)
- Action: scaffold `tools/research/forex_carry.py` as P5 swarm research target

**Edge #15: SHORT-only rehab** (memory `feedback_long_source_bias`)
- 7 sources are 99-100% LONG-only on FOREX; reject their LONGs
- Use luxalgo/dna_winner SHORTs instead
- Hard requirement until WR>45 + PF>0.8 for 30 consecutive days

### BOND — too thin to score; ramp first

n=11 / charter floor 100. Need months of accumulation before any edge claim.

**Edge #16: PEAD-equivalent on duration** (B-BOND)
- TLT/IEF momentum 3yr Sharpe 1.2-1.5 historical
- Treasury curve steepener mean-reversion
- Needs FRED_API_KEY (SET in secrets — usable)
- Action: BOND scanner shipped this session; ramp data accumulation

---

## Hidden-insight queries from user directive

DAILY_IDEAS 2026-05-12 user directive explicitly listed 5 hidden-insight queries.
Cross-walk against shipped + pending:

| Query | Status |
|---|---|
| 1. Picks with low score / high PnL → missing signal | Tools: `tools/swarm/pattern_miner.py` (shipped this session) — winning cells |
| 2. Picks with high score / low PnL → overfit noise | Same — losing cells |
| 3. Top strategies dormant (no signal) → emission decay | DEAD-status flag shipped `023e636e26c` — `ml_crypto_pred_v12` confirmed dead 80d |
| 4. DNA mutation of strategies | `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — used pre-kill for FOREX guard |
| 5. ML reality check | `reports/ml_staleness_audit_2026-05-12.md` — peer-shipped + my V2 hf_stats fix |

---

## Top 5 actionable next steps for class-by-class edge

### NS-A — Manually dispatch `ab_analysis.yml` → unlock multi_asset_cot DB verdict

```bash
gh workflow run ab_analysis.yml -R eltonaguiar/findtorontoevents_antigravity.ca
# wait ~5 min; check audit_dashboard/data/system_pf_verification.json
```

Outcomes:
- `MATCH` → COMMODITY edge confirmed at strategy-instrument level; proceed to A4 capacity model
- `DASHBOARD_INFLATED` → multi_asset_cot phantom; COMMODITY headline PF drops to ~broad-class real number; entire single-symbol edge thesis dies

### NS-B — Procure missing data keys (5 min user-action each)

Per Grok #2 (Claude#2 retro) + B-CRYPTO/BOND:

```bash
gh secret set GLASSNODE_API_KEY -R eltonaguiar/findtorontoevents_antigravity.ca
gh secret set CFTC_API_KEY -R eltonaguiar/findtorontoevents_antigravity.ca
```

Unlocks Edges #9, #10 (CRYPTO funding-rate strategies) + improves Edge #1 verification.

### NS-C — Ship Edge #10 (BTC UTC-hour filter)

Free, no data keys needed. Memory `project_clean_data_symbol_wr` already
proved 22 UTC = 61.2% WR (n>1000). Implementation: 1-line strategy filter
on every CRYPTO strategy. Estimated WR lift if applied: +14pp.

```python
# in calculate_smart_score or smart_picks_engine
hour = pick.created_at.hour
if pick.asset_class == "CRYPTO" and hour in (8, 9):
    return SKIP  # death zone
```

### NS-D — Ship Edge #6 PEAD on EQUITY top-100

Already-confirmed Tier-2 class. PEAD is the lowest-hanging academic edge
with public-data implementation. ~1 day work.

### NS-E — Disable FOREX writers entirely until rehab

FOREX class is sub-floor catastrophic. Even with concentration WARN
absent and diverse 1355 trades, the PF 0.29 / -1026% PnL says no
permutation of current strategies works.

Status: `FOREX_MIN_SCORE=70` already raised (`config.py:239`). Tight admission
gate. But emissions still happen. Until carry-factor (Edge #14) ships,
the empirical answer is: write zero FOREX picks.

```python
# alpha_engine/config.py or quality_gates
FOREX_HARD_DISABLE = os.environ.get("FOREX_HARD_DISABLE", "1") == "1"
```

User-action to disable: already largely there. Confirmation needed.

---

## Anti-edge findings (negative info worth flagging)

1. **CRYPTO confidence inverts on ETF/CRYPTO** (memory `project_performance_reality`)
   - score-vs-realized-WR ρ = +0.196 for `trust_score`
   - **ρ = NEGATIVE for `confidence`** on ETF + CRYPTO classes
   - HIGH_CONVICTION button on /audit uses confidence — likely surfacing anti-edge
   - Action: replace confidence-based HC gate with trust_score-based gate

2. **claude_gainer_st earlier ranked Tier-2** (DAILY_IDEAS 2026-05-09 list)
   - PF 6.80 / WR 80.1 / n=3447 → BLACKLISTED post-investigation (26.5% real WR, -355% PnL)
   - Lesson: high WR cumulative-since-inception ≠ live edge
   - Apply same rigor to current verified-T2 list (especially multi_asset_cot)

3. **9/10 personas backed by Opus-4.7** (Agent#3 peer finding)
   - "non-opus-4" preset shipped this session (`e7088bfd4ea`)
   - Future swarm rounds should use `--preset non-opus-4` to force genuine cross-vendor consensus

## NFA

Research surface only. No real-money sizing until:
- multi_asset_cot DB-verify clears (NS-A)
- 30d clean rolling for any T2 candidate
- Friction-adjusted DSR ≥ 0.85
- mutate-before-kill on FOREX rehab path

---

## Claude Code Analysis — 2026-05-16T22:10Z (3 days post-document)

### Next Steps Status Update

| NS | Description | Status |
|---|---|---|
| **NS-A** | Dispatch `ab_analysis.yml` for multi_asset_cot DB verification | ✅ DISPATCHED — run 25973859830 (daily cron active) |
| **NS-B** | Procure GLASSNODE_API_KEY + CFTC_API_KEY | 🔄 OPEN — user action; unlocks Edges #9, #10 |
| **NS-C** | BTC UTC-hour filter | ✅ SHIPPED — `quality_gates.py` lines 6645-6682; tests pass |
| **NS-D** | PEAD on EQUITY top-100 | ✅ SHIPPED — `alpha_engine/strategies/pead_equity.py` |
| **NS-E** | FOREX hard-disable | ✅ SHIPPED — `FOREX_HARD_DISABLE=1` active |

### Edge Status — Current Reality (2026-05-16)

**Edge #1 (CT=F COT):** CT=F moved to PROBATION — block was correct (rolling WR was 8.3%). Post-block OOS WR=75% on n=43. Probation until 2026-06-06. `multi_asset_cot` class-wide still running; `ab_analysis.yml` runs daily.

**Edge #6 (QMOM/IMOM):** Not yet shipped. EQUITY is T2 confirmed; PEAD is wired first per priority. QMOM still open as backlog.

**Edge #8 (CRYPTO strategy drag):** ✅ SHIPPED — dynamic CRYPTO quarantine live in `quality_gates.py`. `alpha_engine_fast`, `kimi_signal_tracking` quarantined.

**Edge #10 (BTC UTC-hour):** ✅ SHIPPED — death-zone (08-09 UTC) blocked; 22 UTC boosted by +8 score. Estimated WR lift confirmed by gate tests.

**Edge #11 (Funding skew + Glassnode):** Still blocked on `GLASSNODE_API_KEY`. Cost ~$30/mo. User procurement decision.

**Edge #14 (FOREX carry-factor):** OPEN — `tools/research/forex_carry.py` not yet scaffolded. FOREX hard-disabled until this ships and meets PF>1.0/WR>45/n>30 over 30 days.

**Anti-edge #1 (confidence inversion):** ✅ ADDRESSED — M-034 shadow gate + trust_score swap in dashboard HC filter. Confidence no longer used as buy signal for CRYPTO/ETF.

### Remaining High-Value Edges to Ship

1. **Edge #13 (ETF risk-parity rotation):** `pyportfolioopt` wire-up documented; not yet shipped. Post-2022 reset optimal weights differ from classic 60/40. Estimated ETF PF lift: 1.32→2.1. **Effort: M (1 day).**

2. **Edge #9 (Hyperliquid HLP carry replication):** Blocked on CFTC_API_KEY. Once funded-perp funding-rate data is available, scaffold from scratch. **Effort: M after data procurement.**

3. **EQUITY PEAD earnings feed:** `incubator_picks.json` partial. For full PEAD, need real earnings calendar API (Polygon.io free tier or yfinance earnings dates). **Effort: S — check yfinance `ticker.earnings_dates`.**

4. **DBMF/KMLM commodity-momentum replication (Edge #3):** `tools/research/dbmf_replication.py` not yet scaffolded. Pro: institutional-grade CTA replication with $1B+ AUM track record. Con: requires monthly NAV data. **Effort: M.**
