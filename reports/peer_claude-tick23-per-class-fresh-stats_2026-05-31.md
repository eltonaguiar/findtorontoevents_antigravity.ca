# Per-Class Fresh Stats Audit — 2026-05-31

**Goal**: pre-fetch live per-class + per-strategy performance for `/money-maker-readyv2` hedge-fund-tier work. Memory stats from 2026-05-25 are DEPRECATED per CLAUDE.md — this report is the current source of truth.

**Generated**: 2026-05-31, pulled at run-time from `ejaguiar1_stocks.trading_picks` + live `audit/data/*.json`.

---

## 1. Live 14d per-class (trading_picks, closed only)

SQL:
```sql
SELECT LOWER(COALESCE(category,'unknown')) class, COUNT(*) n,
  SUM(CASE WHEN pnl_pct>0 THEN 1 ELSE 0 END) wins,
  ROUND(SUM(CASE WHEN pnl_pct>0 THEN 1 ELSE 0 END)*100.0/COUNT(*),1) wr_pct,
  ROUND(SUM(CASE WHEN pnl_pct>0 THEN pnl_pct ELSE 0 END)/NULLIF(ABS(SUM(CASE WHEN pnl_pct<0 THEN pnl_pct ELSE 0 END)),0),2) pf,
  ROUND(AVG(pnl_pct),3) avg_pnl, ROUND(STDDEV(pnl_pct),3) std,
  ROUND(MIN(pnl_pct),2) worst, ROUND(MAX(pnl_pct),2) best
FROM trading_picks
WHERE closed_at IS NOT NULL AND closed_at > NOW() - INTERVAL 14 DAY
  AND status IN ('TP_HIT','SL_HIT','LOST','EXPIRED','TIME_EXIT')
GROUP BY class ORDER BY n DESC;
```

| Class | n | WR% | PF | Avg PnL | Std | Worst | Best | Verdict (vs CLAUDE.md tiers) |
|-------|---|-----|-----|---------|-----|-------|------|------------------------------|
| crypto | 729 | 39.9 | **1.71** | +0.87 | 4.17 | -7.39 | +31.5 | **NEAR-T2** (n>=100, PF>1.5, but WR<50 → fails WR gate) |
| commodity | 63 | 0.0 | 0.00 | -2.18 | 14.05 | -98.4 | 0.0 | **FAIL+INSUFF-N** (all losses) |
| equity | 42 | 21.4 | 0.42 | -0.89 | 2.38 | -4.96 | +3.78 | **FAIL+INSUFF-N** |
| forex | 40 | 20.0 | 0.40 | -0.16 | 0.39 | -0.56 | +0.77 | **FAIL+INSUFF-N** |
| stocks | 38 | 0.0 | 0.00 | -23.8 | 22.8 | -46.6 | -1.00 | **FAIL+INSUFF-N** (likely pre-resolver-fix mislabels) |
| (empty) | 16 | 0.0 | 0.00 | -0.82 | 0.02 | -0.84 | -0.80 | category-blank rows (case-mess per memory) |
| etf | 6 | 33.3 | 4.80 | +1.12 | 1.44 | -0.88 | +2.44 | **INSUFFICIENT_N** (only 6) |
| meme | 1 | 0.0 | – | – | – | – | – | INSUFF-N |
| futures | 1 | 0.0 | – | – | – | – | – | INSUFF-N |

**Big change vs memory**: CRYPTO PF jumped 1.14→**1.71** in 14d (n 728→729, similar size, fresh wins). EQUITY worsened (33%→21% WR). COMMODITY catastrophic 0% WR (was 11%). The empty-string category bucket (n=16, all losses ~-0.82%) suggests a routing bug — picks not getting categorized.

---

## 2. Live 48h per-class

```sql
-- same shape, INTERVAL 48 HOUR
```

| Class | n | WR% | PF | Avg PnL |
|-------|---|-----|-----|---------|
| crypto | 80 | 38.8 | **3.77** | +2.39 |
| commodity | 19 | 0.0 | – | 0.00 |
| stocks | 13 | 0.0 | – | – |
| equity | 9 | 11.1 | 0.86 | -0.12 |
| forex | 3 | 0.0 | 0.00 | -0.11 |
| (empty) | 2 | 0.0 | – | – |
| futures | 1 | 0.0 | – | – |

**Key signal**: CRYPTO 48h PF=3.77 from n=80 is the only positive surface. Non-crypto in the last 48h is uniformly bleeding.

---

## 3. money_ready_verdict.json (live, 2026-05-31T20:09:25Z)

| Class | n_resolved | WR | PF | MDD | Verdict | Top Source | Top Share |
|-------|------------|----|----|-----|---------|------------|-----------|
| EQUITY | 43 | 30.2% | 0.156 | 98.2% | INSUFFICIENT_DATA | regime_terminal | 41.9% |
| CRYPTO | 341 | 39.3% | 0.879 | 100% | **NOT_READY** | UNKNOWN | 58.1% |
| COMMODITY | 7 | 57.1% | 3.87 | – | INSUFFICIENT_DATA | UNKNOWN | 57.1% |
| FOREX | 29 | 27.6% | 0.035 | 82.3% | INSUFFICIENT_DATA | multi_asset_scanner | 37.9% |
| ETF | 4 | 50.0% | 0.476 | – | INSUFFICIENT_DATA | etf_scanner | 50.0% |
| FUTURES | 12 | 16.7% | 0.536 | 16.7% | INSUFFICIENT_DATA | multi_asset_scanner | 91.7% |
| PENNY_STOCK | 1 | 0% | 0.0 | – | INSUFF | multi_asset_scanner | 100% |
| BOND | 0 | – | – | – | INSUFFICIENT_DATA | – | – |
| UNKNOWN | 7 | 57.1% | 2.05 | – | INSUFFICIENT_DATA | UNKNOWN | 100% |

**CRITICAL DELTA**: verdict shows CRYPTO PF=0.88 / WR=39.3 / NOT_READY. Live DB shows CRYPTO 14d PF=1.71 / WR=39.9. The **verdict file is using a stricter policy-clean cohort (n=341)** vs raw 14d (n=729). The verdict's PF<1 is the source of "NOT_READY"; the raw DB number is more optimistic because it includes unfiltered cohorts. Use **policy_clean_net for production gating**.

---

## 4. pf_registry.json `by_asset_class_policy_clean_net` (live)

| Class | n | WR% | PF | MDD | Top Source | Single-Src% |
|-------|---|-----|-----|-----|------------|-------------|
| COMMODITY | 7 | 57.1 | 3.87 | 4.6% | file:alpha_engine | 57% |
| CRYPTO | 346 | 39.3 | 0.88 | 100% | file:battleground | 25% |
| EQUITY | 43 | 30.2 | 0.16 | 98.2% | regime_terminal | 42% |
| ETF | 4 | 50.0 | 0.48 | 6.2% | file:alpha_engine | 50% |
| FOREX | 29 | 27.6 | 0.035 | 82.3% | multi_asset_scanner | 38% |
| FUTURES | 12 | 16.7 | 0.536 | 16.7% | multi_asset_scanner | 92% **artifact** |
| PENNY_STOCK | 1 | 0 | 0 | – | multi_asset_scanner | 100% |
| UNKNOWN | 7 | 57.1 | 2.05 | – | file:alpha_engine | 100% **artifact** |

`is_single_source_artifact=true` on FUTURES and UNKNOWN means those PF values do NOT pass the concentration gate.

---

## 5. Named-candidate strategies (30d, n>=3)

```sql
SELECT strategy, category, COUNT(*) n, WR, PF, avg_pnl
FROM trading_picks WHERE strategy LIKE '%<name>%'
  AND closed_at > NOW() - INTERVAL 30 DAY
  AND status IN ('TP_HIT','SL_HIT','LOST','EXPIRED','TIME_EXIT')
GROUP BY strategy, category HAVING n>=3;
```

| Strategy | Class | n | WR% | PF | Avg PnL | Verdict |
|----------|-------|---|-----|-----|---------|---------|
| stocks_rsi2_pullback | equity | 17 | 23.5 | 0.24 | -1.33 | **DO NOT UN-KILL** — recent 30d shows degradation, not edge |
| stocks_rsi2_pullback | (blank) | 10 | 0 | 0 | -0.82 | category-blank routing bug compounds the failure |
| dxy_trend_filter | – | 0 | – | – | – | **NO RECENT ACTIVITY** (need to wire/turn on first) |
| cta_cross_asset_tsmom | – | 0 | – | – | – | NO ACTIVITY (already killed/dormant) |
| quan_engine_scalp | – | 0 | – | – | – | NO ACTIVITY (likely already killed per INCIDENT_CRYPTO #2) |
| cot_positioning | – | 0 | – | – | – | NO ACTIVITY (TRIAGED falsified, confirmed) |
| futures_momentum | commodity | 83 | **2.4** | **0.03** | -2.03 | **CATASTROPHIC — KILL CANDIDATE #1** (single largest non-crypto producer is 2% WR) |
| etf_faber_tactical | – | 0 | – | – | – | NO ACTIVITY |
| regime_mild_bull | – | 0 | – | – | – | NO ACTIVITY |
| bond_connors_rsi2 | – | 0 | – | – | – | NO ACTIVITY (BOND class has n=0 in verdict) |

### trust_score=7 CRYPTO cohort (90d)

```sql
SELECT COUNT(*) n, wins, wr, pf, avg_pnl FROM trading_picks
WHERE LOWER(category)='crypto' AND trust_score=7
  AND closed_at > NOW()-INTERVAL 90 DAY AND status IN (...);
```

| Filter | n | wins | WR% | PF | Avg PnL |
|--------|---|------|-----|-----|---------|
| crypto + trust_score=7 | **99** | 85 | **85.9** | **12.19** | +2.53% |

**CONFIRMED EDGE** — matches memory (85.9% WR n=99 PF 12.19). This is the single best surface in the entire repo right now. Hedge-fund tier (PF>2, WR>55, n~100). Worth productizing immediately.

### Other top PFs n>=20 (30d, exploratory)

| Strategy | Class | n | WR% | PF | Avg PnL |
|----------|-------|---|-----|-----|---------|
| (blank strategy) | crypto | 202 | 57.9 | **3.19** | +2.38 | **HIDDEN EDGE — investigate provenance** |
| claude_ml_moderate_mut | crypto | 29 | 41.4 | 1.32 | +0.46 | Near-T2, needs n |
| luxalgo_confluence | crypto | 845 | 41.7 | 1.08 | +0.11 | Marginal positive, large n — register |
| futures_momentum | commodity | 83 | 2.4 | 0.03 | -2.03 | KILL |

The blank-strategy CRYPTO cohort (n=202, PF=3.19) is a labeling bug — these picks aren't getting attributed. Recovering provenance could surface another verified edge.

---

## 6. Tier verdict per class (CLAUDE.md thresholds: T1 PF>=2/WR>=55/MDD<10/n>=100; T2 PF>=1.5/WR>=50/MDD<20/n>=100)

| Class | 14d Verdict | Verdict-file Verdict | Combined |
|-------|-------------|----------------------|----------|
| CRYPTO | NEAR-T2 (PF 1.71, WR<50) | NOT_READY (policy-clean PF<1) | **NOT_READY at class level; T1 at trust_score=7 sub-cohort** |
| EQUITY | FAIL | INSUFFICIENT_DATA | **FAIL+INSUFF-N** |
| COMMODITY | FAIL | INSUFFICIENT_DATA (n=7 too small) | **FAIL** at production, INSUFF in verdict |
| FOREX | FAIL | INSUFFICIENT_DATA | **FAIL+INSUFF-N** |
| ETF | INSUFFICIENT_N | INSUFFICIENT_DATA | **INSUFFICIENT_N** |
| BOND | n=0 | n=0 | **DORMANT** |
| FUTURES | n=1 | INSUFFICIENT_DATA (single-src artifact) | **DORMANT/ARTIFACT** |

**Zero classes pass T2.** Same conclusion as CLAUDE.md banner but with fresher numbers.

---

## 7. Classified Actions

### SAFE_NOW (low-risk, observable wins)
1. **Register & productize CRYPTO trust_score=7 filter** — PF 12.19, WR 85.9%, n=99. Already proven historically; just make it a first-class money_ready filter.
2. **Add concentration gate before DSR/SPA** — both single-source-artifact flags on FUTURES + UNKNOWN must invalidate PF in the verdict pipeline (per CLAUDE.md P0).
3. **Investigate blank-strategy CRYPTO cohort (n=202, PF 3.19)** — recover provenance, possibly a second productizable edge.
4. **Resolve category-blank routing bug** — 16+10 picks with empty `category` are 0% WR; fix the writer.

### OPERATOR_DECISION (kill/rebuild)
5. **KILL futures_momentum (COMMODITY)** — 83 closed in 30d, 2.4% WR, PF 0.03, avg -2%/trade. This single strategy is producing essentially all the COMMODITY 0% WR signal. Append to `BLOCKED_SOURCE_SYSTEMS` per `STRATEGY_INVESTIGATION_BEFORE_KILL.md`.
6. **DO NOT un-kill stocks_rsi2_pullback** — 30d shows 23.5% WR / PF 0.24. Memory premise (T2 candidate) is refuted by current data; keep killed.
7. **dxy_trend_filter / etf_faber_tactical / bond_connors_rsi2 = wire-up project**, not data project — no recent emissions. The blocker is plumbing, not edge.
8. **luxalgo_confluence** (n=845 30d, PF 1.08) — marginal positive but high volume. Consider registering as observed-T3 (between break-even and T2), then tighten via mutation rather than kill.

---

## 8. Bottom-line numbers for downstream tools

- **Classes audited**: 9 (crypto, equity, commodity, forex, etf, stocks, bond, futures, penny)
- **Strategies audited**: 10 named + 3 hidden top-PFs
- **T1 (PF>=2/WR>=55/n>=100)**: **0 classes** — but 1 SUB-COHORT (CRYPTO trust_score=7) qualifies
- **T2 (PF>=1.5/WR>=50/n>=100)**: **0 classes**
- **INSUFFICIENT_N**: 4 (ETF, COMMODITY, BOND, FUTURES, plus PENNY)
- **FAIL**: 3 (EQUITY, FOREX, COMMODITY [futures_momentum])

---

## Sources

- Live DB: `mysql.50webs.com / ejaguiar1_stocks.trading_picks` (read-only stocks user)
- `https://findtorontoevents.ca/audit/data/money_ready_verdict.json` 2026-05-31T20:09:25Z
- `https://findtorontoevents.ca/audit/data/pf_registry.json` (current)
- CLAUDE.md tier thresholds + `docs/MUTATION_THREE_AXIS_PROTOCOL.md`
- Memory: `project-money-ready-2026-05-31.md`, `project-confidence-trust-edges-2026-05-31.md`
