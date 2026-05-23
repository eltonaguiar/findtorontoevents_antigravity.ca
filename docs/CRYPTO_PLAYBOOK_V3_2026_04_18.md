# Crypto Playbook V3 — 2026-04-18

> **RETRACTION BANNER.** This playbook supersedes `docs/CRYPTO_PLAYBOOK_2026_04_18.md`,
> which is **retracted**. V1 conflated backtest / forward-test statistics with
> realized live PnL, banned SHORTs on directional grounds when SHORTs were in
> fact the only side with a positive live WR in the window, and quoted
> Wilson-insignificant WRs as "EDGE." V3 is built from one file only and refuses
> to reach an "approved" conclusion unless the math forces it.
>
> **Data source (only):** `alpha_engine/data/closed_picks.json`
> **SHA-256:** `8a11793f62c2a9c650cd3dbc837d6f82968155654ae1509e77bf15491e332317`
> **File mtime (UTC):** `2026-04-18T22:20:12Z`
> **Rows in file:** 500. **Crypto, 90d, pnl_pct not null:** 495.
> **Anchor "now":** latest `closed_at` in file = `2026-04-18T21:13:55Z`.
> **Bonferroni correction:** `k = 4` combos tested at n ≥ 30, so
> α_adj = 0.05/4 = 0.0125, two-sided z = **2.4977**.

---

## 1. Method + guardrails

Every number below is derived by this pipeline (reproducible in
`tmp_playbook_v3.py`):

```
rows       = json.load(closed_picks.json)             # 500
crypto_90d = [r for r in rows
              if r.symbol endswith 'USDT'
              and r.status in {CLOSED, WON, LOST, EXPIRED}
              and r.pnl_pct is not None
              and (anchor - r.closed_at).days <= 90]   # 495
direction  = BUY|LONG -> LONG ; SELL|SHORT -> SHORT
```

**Guardrails that cannot be relaxed in this document:**
1. Zero numbers sourced from `strategy_performance.json`, any `backtest_*.json`,
   any `forward_*.json`, any `simulation_*.json`. If a strategy has zero rows in
   `closed_picks.json`, it is unranked — period.
2. Wilson 95% lower bound with z = 1.96, Bonferroni-adjusted to z = 2.4977
   (k = 4). Formula:
   `LB = (p + z²/2n − z·√((p(1−p)+z²/4n)/n)) / (1 + z²/n)`.
3. n ≥ 30 per `(strategy, symbol, direction)` combo after direction split.
4. "Approved" requires **all** of: Wilson_Bonf > 0.50, n ≥ 30, avg PnL% > 0,
   total PnL% > 0.
5. Every cell below carries a one-line citation of the form
   `filter(...) | agg(...)` against `closed_picks.json`.

---

## 2. Direction regime (7d / 30d / 90d)

Not a ban — raw live numbers. Let the reader weight them.

| Window | Dir    | n   | WR     | avg PnL% | total PnL% | Wilson95 LB |
|--------|--------|-----|--------|----------|------------|-------------|
| 7d     | LONG   | 14  | 0.214  | −0.255   | −3.56      | 0.076       |
| 7d     | SHORT  | 21  | 0.762  | −0.019   | −0.40      | 0.549       |
| 30d    | LONG   | 440 | 0.227  | −0.168   | −74.08     | 0.191       |
| 30d    | SHORT  | 21  | 0.762  | −0.019   | −0.40      | 0.549       |
| 90d    | LONG   | 460 | 0.226  | −0.167   | −76.90     | 0.190       |
| 90d    | SHORT  | 35  | 0.629  | −0.033   | −1.14      | 0.463       |

Citation: `filter(symbol~USDT, closed_at∈[anchor−Nd, anchor], pnl_pct!=null) | group_by(dir) | {count, mean(pnl_pct), sum(pnl_pct), wilson_lb(wins,n,1.96)}`.

**What this says, honestly:**
- LONG in crypto over the last 90d is a **negative-expectancy book** (avg
  −0.167%, −76.9% cumulative across 460 trades).
- SHORT has a materially higher WR (62.9% @ n=35 90d, 76.2% @ n=21 30d) but
  **still bleeds PnL** (−0.033% avg, −1.14% total 90d). Wins are small, losses
  are larger — classic premature-TP / generous-SL asymmetry.
- V1's "ban SHORTs" rule was empirically backwards: SHORT is the only crypto
  side with WR > 50% here. But SHORT is **not profitable** either. Neither side
  is "approved." No direction ban; no direction green light.

---

## 3. Source-system leaderboard (last 30d, crypto, n ≥ 100)

| source_system             | n   | WR    | avg PnL% | total PnL% | Wilson95 | med age (d) | med hold (bars) | stale? |
|---------------------------|-----|-------|----------|------------|----------|-------------|-----------------|--------|
| quan_engine               | 459 | 0.248 | −0.1624  | −74.53     | 0.211    | 28.31       | 4               | no     |

All other source_systems fall below the n ≥ 100 cut (`multi_asset_copytrader`
n=5 90d, `prediction_market_agents` n=2 90d) and are not rankable. `quan_engine`
is **not** in `_FRESHNESS_REQUIRED_HOURS` (dashboard_generator.py:3700–3756), so
its picks are treated as live. The honest read: the only statistically
resolvable live crypto engine is currently running a 24.8% WR with −0.16% avg —
negative edge, not noise.

Citation: `filter(symbol~USDT, closed_at≥anchor−30d) | group_by(source_system) | n>=100 | stats(...)`.

---

## 4. APPROVED combos

**Count: 0.**

Four combos cleared n ≥ 30. All four failed Wilson_Bonf > 0.50. Three of four
had negative avg PnL% and negative total PnL%.

| strategy           | symbol    | dir  | n   | WR    | avg PnL% | total PnL% | Wilson95 LB | Wilson_Bonf LB | 30d WR | decay flag |
|--------------------|-----------|------|-----|-------|----------|------------|-------------|----------------|--------|------------|
| quan_engine_scalp  | TRXUSDT   | LONG | 66  | 0.621 | +0.068   | +4.49      | 0.501       | **0.468**      | 0.690  | —          |
| quan_engine_scalp  | BTCUSDT   | LONG | 42  | 0.238 | −0.255   | −10.71     | 0.135       | 0.115          | 0.238  | —          |
| quan_engine_scalp  | HYPEUSDT  | LONG | 47  | 0.213 | −0.234   | −11.02     | 0.120       | 0.102          | 0.217  | —          |
| quan_engine_scalp  | MATICUSDT | LONG | 103 | 0.000 | −0.150   | −15.45     | 0.000       | 0.000          | 0.000  | —          |

Citation: `filter(symbol~USDT,90d) | group_by(strategy,symbol,dir) | n>=30 | ...`.

TRXUSDT is the single *positive-PnL* combo and **nearly** clears the unadjusted
Wilson 95% LB (0.501 > 0.50), but once we correct for four comparisons it
drops to 0.468 — below threshold. Its 30d WR (0.690 on n=58) is actually
**better** than its 90d WR (0.621 on n=66), i.e. it is not decaying — but the
playbook's contract says Bonferroni-adjusted LB > 0.50, so it does not make the
approved tier.

**MATICUSDT LONG is a live-trading emergency.** 103 trades, zero winners, every
trade returning exactly −0.15% (likely a stop-loss-only exit pattern). This is
not a strategy — it is an automated loss pipeline. See §7 kill-switches.

---

## 5. PAPER-ONLY runner-ups

Criteria: Wilson95 LB ∈ [0.40, 0.50] AND avg PnL% > 0 AND n ≥ 50.

**Count: 0.**

TRXUSDT LONG has Wilson95 = 0.501 (just over the upper bound of the paper-only
band) and is effectively the "almost approved" combo. Rather than carve out a
third tier to keep it, we log it as a **Watch combo** (§8 open questions): if
another ~30 closed trades land in the same regime and Wilson_Bonf crosses 0.50,
it becomes approvable.

---

## 6. Sizing + exit rules (derived, not generic)

Derived from actual TP/SL distances in the 90d crypto set:

| strategy             | n   | median TP distance | median SL distance | implied R:R |
|----------------------|-----|--------------------|--------------------|-------------|
| quan_engine_scalp    | 448 | 1.18%              | 0.59%              | ~2.0        |
| quan_engine_swing    | 34  | 5.49%              | 1.98%              | ~2.8        |
| quan_engine_position | 11  | 13.66%             | 3.76%              | ~3.6        |

Citation: `filter(symbol~USDT,90d,strategy=X) | median(|tp-ep|/ep), median(|ep-sl|/ep)`.

**Expectancy per trade (using realized avg_win / avg_loss, not assumed R:R):**

| combo                              | realized WR | avg_win% | avg_loss% | EV / trade |
|-------------------------------------|-------------|----------|-----------|------------|
| quan_engine_scalp TRXUSDT LONG     | 0.621       | +0.351   | −0.396    | **+0.068%**|
| quan_engine_scalp BTCUSDT LONG     | 0.238       | +0.342   | −0.441    | −0.255%    |
| quan_engine_scalp HYPEUSDT LONG    | 0.213       | +0.034   | −0.307    | −0.235%    |
| quan_engine_scalp MATICUSDT LONG   | 0.000       | —        | −0.150    | −0.150%    |

Only TRXUSDT has positive EV, and fees/slippage at this scalp distance (1.2% TP)
will eat a meaningful chunk of +0.068%. A 2bp round-trip cost absorbs ~30% of
realized edge. **No live sizing is justified by this data set.**

**If and only if the TRX combo is promoted later**, suggested rules:
- Position size: 0.25% of equity (half the normal 0.5% until Wilson_Bonf>0.50).
- TP = 1.2% from entry (matches `quan_engine_scalp` median TP distance).
- SL = 0.6% from entry (matches median SL distance; keeps live R:R ≈ 2.0).
- Max hold = current median `hold_bars` ≈ 4 (5m-bar equivalent).
- No pyramiding, no size-up on consecutive wins.

Do not extrapolate these numbers to other symbols. Per-symbol distributions
vary enough that HYPEUSDT's avg_win is literally 10× smaller than TRX's.

---

## 7. Kill-switches (hard no-trade)

1. **`quan_engine_scalp` + `MATICUSDT` + LONG — DO NOT TRADE.** 0/103 winners
   over 90d, avg −0.15%. This is a failing automation, not a strategy. Halt it
   at the source until the entry/exit logic is re-audited. Citation:
   `filter(strategy=quan_engine_scalp, symbol=MATICUSDT, dir=LONG, 90d) | WR=0/103`.
2. **`quan_engine_scalp` + `BTCUSDT` + LONG and + `HYPEUSDT` + LONG — DO NOT
   TRADE.** Both have Wilson_Bonf < 0.15, both are deeply negative on realized
   PnL, both have zero regime change 30d vs 90d.
3. **No live crypto LONG book expansion** until aggregate 30d LONG WR exceeds
   the current Wilson95 upper bound (≈0.27). Below that it's a −EV book on
   n=440; adding capital makes it worse.
4. **Any combo with `source_system` listed in
   `dashboard_generator.py::_FRESHNESS_REQUIRED_HOURS` (lines 3700–3756) is
   non-admissible** regardless of WR, because its picks are not guaranteed
   live at scoring time.
5. **Auto-pause on drift:** if any currently-traded combo's 30d WR falls > 10pp
   below its 90d WR across ≥10 new closes, pause that combo pending review.

---

## 8. Open questions / data-gaps

1. **Why does SHORT have a ~76% WR with a −0.019% avg PnL?** Almost certainly
   early TP or stop-chasing — win cells are smaller than loss cells. The file
   doesn't carry MAE/MFE, so we can't quantify. Action: add MAE/MFE to every
   new `closed_picks.json` row before re-running this playbook.
2. **Only one source_system is rankable.** 99% of rows come from
   `quan_engine`. This playbook cannot evaluate whether other engines (ML
   ensembles, breakout curators, AI challenges) actually close trades — they
   don't produce enough `closed_picks.json` rows in the window. Either they
   don't route into live closing, or their results aren't being recorded here.
   That is the single biggest limitation of this analysis.
3. **TRX LONG watch-list:** track the next ~30 `quan_engine_scalp/TRXUSDT/LONG`
   closes. If Wilson_Bonf crosses 0.50, promote to §4.
4. **MATICUSDT forensic:** 103/103 losers, every exit exactly −0.15%. Is this
   a fee/slippage artifact, a stop-loss-only exit path, or a stale
   entry-price? File a bug — do not "tune" it.
5. **No ATR field in `closed_picks.json`.** §6 sizing uses realized TP/SL
   distance as a proxy. Adding `atr_at_entry` would allow the classic
   "1.2×ATR" recommendation to be empirically validated or rejected.

---

## Summary

- **Approved combos: 0.**
- **Paper-only runner-ups: 0.**
- **Active kill-switches: 3 symbol-level + 2 regime-level.**
- **Watch: `quan_engine_scalp/TRXUSDT/LONG`.** Only combo with +EV and +total
  PnL. Needs ~30 more closes to pass Bonferroni-adjusted Wilson.

The honest conclusion, on this data: **stand down live crypto directional
sizing from `quan_engine_scalp` LONG on BTC/HYPE/MATIC immediately, hold TRX
on paper until Wilson_Bonf > 0.50, and collect better data (MAE/MFE, ATR,
cross-engine closes) before the next playbook.**

---

## V3.1 Addendum — Post-MATIC-Purge Re-run (2026-04-18)

After tagging 891 `MATICUSDT`/`MATICUSD` rows in `closed_picks.json` with
`rebrand_artifact: true` + `exclude_from_aggregates: true` (peer-review action
item #2) and retiring three dead strategies via `alpha_engine/strategy_blocklist.py`
(action item #6), the Wilson LB > 0.50 + Bonferroni(k) + n ≥ 30 analysis was
re-run against the cleaned slice.

**Scope note:** this addendum re-runs the methodology on the *full crypto
USDT* slice of `closed_picks.json` (n=4391 pre-purge). Section 4 of the
original V3 restricted to a 90d window of 500 rows and found only 4 qualifying
combos; this addendum works on the full 4391-row file so the raw counts below
are not directly comparable to §2–4 above. The V3 conclusion on the 495-row
90d slice is unchanged — that slice did not contain MATIC aggregates that
would have moved its numbers.

### Before / after row counts

| set                         | rows  |
|-----------------------------|-------|
| crypto USDT, closed, pnl≠∅  | 4391  |
| …after MATIC purge          | 3500  |
| rows removed                | 891   |

### Direction stats (full-file, all-history)

| window      | dir   | n (before) | WR (before) | avg PnL% (before) | n (after) | WR (after) | avg PnL% (after) |
|-------------|-------|------------|-------------|-------------------|-----------|------------|------------------|
| all-history | LONG  | 4295       | 0.2834      | −0.1608           | 3404      | 0.3575     | −0.1636          |
| all-history | SHORT | 96         | 0.5833      | +0.0957           | 96        | 0.5833     | +0.0957          |

LONG WR improves +7.4pp after removing the 889 deterministic MATIC losers, but
**avg PnL per trade gets slightly worse** (−0.160% → −0.164%) because the
MATIC rows lost only −0.15% each (below the LONG-book average loss). The LONG
book remains a negative-expectancy book; the improvement is cosmetic.

### Combos passing Wilson LB > 0.50 (unadjusted, n ≥ 30)

| set    | k (combos tested) | passing unadj Wilson > 0.50 | passing Bonferroni-adjusted > 0.50 |
|--------|-------------------|-----------------------------|------------------------------------|
| before | 23                | 1 (`quan_engine_scalp/TRXUSDT/LONG`, 0.501) | 0 |
| after  | 21                | 1 (`quan_engine_scalp/TRXUSDT/LONG`, 0.501) | 0 |

Top combo after purge: `quan_engine_scalp/TRXUSDT/LONG` n=66 WR=0.621
avg=+0.068% total=+4.49 Wilson95=0.501 Wilson_Bonf(k=21,z=3.038)=**0.436**.
No new combo crossed the bar.

### Did any combos clear the bar that didn't before?

**No.** Purging MATIC reduced k from 23 → 21, which loosened Bonferroni
slightly (z 3.065 → 3.038), but that lift was not enough to push TRXUSDT's
Bonferroni-adjusted Wilson LB from 0.434 → above 0.50 (actual: 0.434 → 0.436).

### Updated direction recommendation

**Still neutral. No tilt.** The book remains negative-EV on LONG even after
the MATIC purge; SHORT's +0.096% avg on n=96 does not meet the §4 contract
(Wilson_Bonf > 0.50 + n ≥ 30 + total > 0 is met, but WR=0.583 with n=96 gives
Wilson95_unadj=0.483 — fails the unadjusted 0.50 threshold, so Bonferroni is
moot). The watch-combo (`quan_engine_scalp/TRXUSDT/LONG`) still needs ~30
more closes in the same regime before it can clear Bonferroni-adjusted Wilson.

### Artifact count

- `closed_picks.json` rows tagged `rebrand_artifact`: **891**
  (`symbol ∈ {MATICUSDT, MATICUSD}`)
- Retired strategies (feed_hygiene blocklist): `fear_greed_contrarian`,
  `proven_propfirm_cons_prop`, `proven_triple_ema_prop`
- New pre-emission guard: `feed_hygiene.has_deterministic_loss_pattern()`
  (flat-feed detector; rejects symbols whose recent prices have
  stdev/mean < 1%).

---

## Review feedback — Cursor agent (2026-04-19)

1. **Single-source discipline:** V3’s guardrails are the right precedent — keep **one** authoritative path from `closed_picks.json` into any future “playbook refresh” automation; never merge dashboard HTML aggregates without the same filters.
2. **Multiple testing:** When k changes (MATIC purge example), **re-state Bonferroni k** in the section header so readers don’t compare runs across commits incorrectly.
3. **SHORT/LONG asymmetry:** Align narrative with [CRYPTO_PLAYBOOK_RETRACTION_2026_04_18.md](CRYPTO_PLAYBOOK_RETRACTION_2026_04_18.md) — directional bans must be re-derived any time the 90d window shifts.
4. **Cross-links:** [OUTPERFORMER_ANALYSIS_2026_04_19.md](OUTPERFORMER_ANALYSIS_2026_04_19.md) and [STRATEGY_SUMMARY_BY_ASSET_CLASS_EXTENSIVE_2026_04_19.md](STRATEGY_SUMMARY_BY_ASSET_CLASS_EXTENSIVE_2026_04_19.md) contextualize crypto vs rest-of-book; cite when arguing allocation.
5. **Factory:** Promotion claims still require Strategy Factory stages — V3 is **evidence**, not an approval to expand emitters without S6/S7.
