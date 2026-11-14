# Subagent D — Non-Crypto Asset-Class Audit (EQUITY / FOREX / ETF / BOND / FUTURES / COMMODITY / MUTUAL FUNDS / STOCKS)

**Audit target:** `https://findtorontoevents.ca/audit` (payload `.../audit/data/`)
**Audit clock:** 2026-11-14T16:05Z (Saturday)
**Payload `generated_at`:** 2026-11-14T14:30:07.135931+00:00 → payload was **~1.6 h old** when captured (`metadata.payload_lag_seconds = 4586.14`; `data_freshness.last_dashboard_build = 14:34:54Z`, stale_warning=false)
**Repo SHA in payload:** `1b2c98e225f8de2bd860f4165a3476f659723796`
**Archive path:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/finpredict-v2/2026-11-14/finpredict-v2_20261114-1602/`
(raw files in `raw/`, this report in `sub/D_non_crypto.md`)
**Method:** streaming Python / `json.load` + targeted passes; never printed whole files. Live UI verified with Playwright 1.58.2.
**Age convention:** "Age" values are the payload's own `age_hours`, computed at `generated_at` (14:30:07Z). Add **~1.6 h** for the age at the 16:05Z capture (e.g. ADBE payload 1.8 h → ~3.3 h at audit; FOREX curated 0.1 h → ~1.7 h).

---

# OVERALL VERDICT: **FAIL — non-crypto data integrity**

Non-crypto surfaces are **not internally consistent, not fully priced, and not resolvable to a single class taxonomy**. Every non-crypto class fails at least one of: pricing, staleness, status/PNL consistency, or class labelling. No fabricated numbers are used below; every figure is traceable to the archived files or the named external source.

## Top findings (evidence-first)

1. **Four different class inventories inside one payload.** `asset_class_summary` = 7 classes; `money_ready_verdict` / `audit_surface_truth` = 9; `summary_picks` = 11; `picks.active_raw` = 8 (incl. `SPORTS`); canonical `alpha_engine/asset_class.py` = 7 (`crypto, forex, etf, bond, commodity, futures, equity`). `INDEX`, `MANAGED_FUTURES`, `SPORTS`, `STOCKS` are not canonical; `MEME`/`PENNY_STOCK` are canonicalised to crypto/equity but emitted as separate classes.
2. **Mathematically impossible win rates in `summary_picks.json`.** 6 of 11 classes report `win_rate_pct > 100` because the formula is `wins / resolved * 100` while `wins` comes from a much larger population than `resolved`: BOND **127.8 %** (92 W / 156 L vs `resolved=72`), COMMODITY **240.2 %** (3476/3466 vs 1447), EQUITY **162.4 %** (1332/2148 vs 820), ETF **232.9 %** (170/183 vs 73), FOREX **147.0 %** (8536/8968 vs 5806), FUTURES **363.9 %** (222/357 vs 61), INDEX **1141.2 %** (194/251 vs 17).
3. **89 % of non-crypto `active_raw` rows carry `pnl_pct == 0`** (508 of 569, excluding 2 SPORTS). Of 571 non-crypto rows, **277 (48.5 %) are `_auto_expired` / `expired_no_pnl` zombies** with `pnl=0` and `exit_reason="STALE (auto-expired >NNNNh)"`.
4. **274 non-crypto rows are >30 days stale** (EQUITY 82, FOREX 158, COMMODITY 16, FUTURES 10, ETF 8). Oldest FOREX row is 2026-02-20 (267 d); oldest EQUITY row 2026-03-30 (229 d / 5,490.6 h).
5. **`asset_class_summary.activeCount` understates open positions by up to 59×**: FOREX 2 vs **118 OPEN**, EQUITY 2 vs **94**, ETF 10 vs **30**, BOND 0 vs **15**, COMMODITY 2 vs **27**, FUTURES 1 vs **3**. The curated `picks.active` list is a freshness-filtered subset, not "all active picks".
6. **Triple/quadruple emission.** BOND: 15 rows for 5 instruments from 3 emitters (`alpha_engine`, `bond_scanner`, `orphan_emitter_bond`). FOREX: 277 rows / 210 unique IDs, 67 duplicate `symbol+strategy+direction` groups (198 extra rows). FUTURES: one ES=F ID emitted 3×, one YM=F combo 6×. COMMODITY: GC=F SHORT 4×. Overall `active_raw`: 4,148 rows / 3,851 unique IDs.
7. **Frozen prices prove "never marked to market".** Old FUTURES rows still carry April-2026 prices: ZN=F `current_price=111.015625` = Yahoo 2026-04-02 close **exactly**; CL=F 112.06 vs today 88.56 (**−21.0 %**); GC=F 4702.70 vs 3886.30 (**−17.3 %**); NG=F 2.807 vs 3.23 (+15.1 %). All still `pnl_pct=0.0`.
8. **Status/PNL contradiction** (sample): QQQ LONG entry 677.36 → exit 679.63 = **+0.335 %**, yet `status=LOST`, `exit_reason=SL_HIT` (ETF). CL=F SHORT 87.81 → 86.01 = **+2.049 %**, yet `status=LOST`, `exit_reason=TP_HIT` (COMMODITY). TLT LONG +0.131 % marked LOST/SL_HIT (BOND).
9. **Self-declared mispricing:** `audit_surface_truth.tournament.mispriced_entry_n = 4285 / 7099 = 60.4 %` (`banner: "tournament WR is coin-flip at pool level; not money-ready"`).
10. **No class is money-ready.** `money_ready_verdict.summary.money_ready = []`, `watch=["COMMODITY"]`, n_classes 9. `audit_surface_truth.headline`: *"0/9 asset classes money-ready on policy-clean closed picks."* `db_health` passes its 5 checks, yet still records **22,947 ghost rows** (`ghost_rows.total_ghost_rows`) although the dashboard banner text claims "Ghost rows: 0".

## User-claim verification

| Claim | Verdict | Evidence |
|---|---|---|
| (a) FUTURES shows 1 active pick **with no date** | **NOT REPRODUCED** | `picks.active` has exactly 1 FUTURES row: `multi_asset_futures_connors_rsi2::ES=F::2026-11-14_1306`, `timestamp=2026-11-14T13:06:02.734149+00:00`, `age_hours=1.4`, `status=OPEN`. Live page renders it as `ES=F LONG … Picked (EST) **Nov 14, 8:06 AM**`. Caveat: `signal_time`/`entry_time` are date-only (`"2026-11-14"`), and the pick is on a non-trading Saturday priced at Friday's close. |
| (b) BOND newest pick ~4 days ago | **CONFIRMED** | `recent_closed` BOND newest = `2026-11-10T13:52:26Z` → **98.2 h = 4.09 d** before 16:05Z. Live page shows `⚠ STALE · BOND — no new picks in >72h`. |
| (c) FOREX USDCAD=X / NZDUSD=X flat 0 % — stale? | **PARTLY CONFIRMED; "flat" is an artifact** | Stored `pnl_pct` is `-0.0` for both. Entry == `current_price` (USDCAD 1.4269; NZDUSD 0.5525167), so 0 % is an identity, not an observation. Against `open.er-api.com` (update Sat 14 Nov 2026 00:02:31Z): USDCAD **1.426026** (−0.061 % vs entry), NZDUSD **0.552726** (+0.038 %). Not genuinely unchanged, and not resolved — never repriced. |

---

# 1. Class inventory & canonical mismatch

Canonical source: `alpha_engine/asset_class.py` (`_CAT_MAP`, `_LOWER_TO_UPPER`). Canonical classes: `crypto, forex, equity, etf, bond, futures, commodity` (+`unknown`). `stock/stocks/penny → equity`; `meme → crypto`; **there is no `STOCKS`, `INDEX`, `MANAGED_FUTURES`, `SPORTS`, `PENNY_STOCK` or `MEME` class**.

| Surface | Count | Classes |
|---|---|---|
| `asset_class_summary` / `smart_picks_by_asset` | 7 | BOND, COMMODITY, CRYPTO, EQUITY, ETF, FOREX, FUTURES |
| `money_ready_verdict.classes` | 9 | + MEME, PENNY_STOCK |
| `audit_surface_truth.by_asset_class` | 9 | + MEME, PENNY_STOCK |
| `pf_registry.by_asset_class` | 9 | + MEME, PENNY_STOCK |
| `summary_picks.asset_classes` | 11 | + INDEX, MANAGED_FUTURES |
| `picks.active_raw` | 8 | BOND, COMMODITY, CRYPTO, EQUITY, ETF, FOREX, FUTURES, **SPORTS** |
| `picks.recent_closed` | 6 | BOND, COMMODITY, CRYPTO, EQUITY, ETF, FOREX |

## Per-class canonical mismatches (`active_raw`, 4,148 rows; 51 mismatched)

| Payload label → canonical | n | Example |
|---|---|---|
| COMMODITY → **FUTURES** | **44 (100 % of COMMODITY)** | GC=F, CL=F, SI=F, HG=F, HE=F, NG=F, ZS=F, SB=F, PA=F — all `=F` suffixes |
| FOREX → **CRYPTO** | 5 | `EURUSDT` (top_gainer_predictor, incubator_gainer, volume_spike_breakout) |
| SPORTS → canonical COMMODITY (classifier artifact) | 2 | `"Montreal Canadiens vs Buffalo Sabres"`, strategy `value_bet` |

`recent_closed` adds 26 more: FOREX→CRYPTO 19 (`EURUSDT`), COMMODITY→FUTURES 7.

## Non-canonical / mislabelled classes

| Label | Where | Evidence | Assessment |
|---|---|---|---|
| **STOCKS** | `audit_surface_truth.tournament.closed_by_class[7]` only | `n_closed=1, wr=1.0, avg_pnl_pct=14.885, verdict=INSUFFICIENT_N` | A **single** closed tournament trade labelled STOCKS; not an equity surface. Canonical maps STOCKS→EQUITY. Literal `"STOCKS"` appears **0 times** in `dashboard_payload`, `dashboard_data`, `summary_picks`, `pf_registry`, `money_ready_verdict`. |
| **INDEX** | `summary_picks` only | total 3549, resolved 17, wins 194, losses 251, `win_rate_pct=1141.2`, last 2026-11-14T13:33Z | Phantom: **0** rows in `picks.active`, `active_raw`, `recent_closed`; absent from MRV/truth/pf_registry. |
| **MANAGED_FUTURES** | `summary_picks` only | total 2, resolved 0, last 2026-11-10T13:35Z | Phantom: no picks anywhere else. |
| **SPORTS** | `picks.active_raw` | 2 × `Montreal Canadiens vs Buffalo Sabres`, `value_bet`, `current_price=None`, `pnl=0` | Not an asset class. Live page filters these (file 4,148 → page 4,146). |
| **PENNY_STOCK** | MRV/truth/pf_registry | n=1 policy-clean, WR 0 %, pnl −0.013 | Canonical `penny → equity`; split out as own class. |
| **MEME** | MRV/truth/pf_registry | n=10, WR 10 % | Canonical `meme → crypto`; split out as own class. |

**Class contamination inside nominal classes (`active_raw`):**

- **EQUITY contains ETFs:** XLE, XLK, QQQ, SPY (9 rows; e.g. `SPY cta_golden_cross_200`, `QQQ regime_terminal`).
- **FOREX contains currency ETFs:** 44 rows — UUP 9, FXA 13, FXC 5, CEW 10, FXE 2, FXY 4, FXB 1 — emitted by **equity** strategy names `Quality Compounders` (36), `Value + Quality` (4), `Consecutive Beats` (4). Plus 5 `EURUSDT` crypto rows. **49/277 = 17.7 % of FOREX is not spot FX.**
- **ETF contains a bond fund:** `VCSH` (short-term corporate bond ETF) sits in ETF while HYG/JNK/EMB/TLT/SHY sit in BOND — same economic exposure, split classes.
- **COMMODITY is entirely futures contracts** (44/44 `=F`), while index/rates futures (`ES=F`, `YM=F`, `ZN=F`) sit in FUTURES. The split is "commodity futures vs other futures", not canonical asset class.

**Shared strategy names across classes** (one strategy, many labels): `inverse_luxalgo_confluence` → COMMODITY+CRYPTO+FOREX+FUTURES; `Quality Compounders` → EQUITY+CRYPTO+FOREX; `momentum-factor` → EQUITY+ETF; `MomentumEMA`/`MeanReversionBB` → CRYPTO+FOREX; `non_crypto_consensus` → COMMODITY+FOREX.

---

# 2. EQUITY — **FAIL**

## Active picks (curated `picks.active`, n=2)

| Symbol | Dir | Entry | Current | PnL % | TP | SL | Strategy (source) | Timestamp | Age |
|---|---|---|---|---|---|---|---|---|---|
| ADBE | LONG | 243.0800018310547 | 243.08 | −0.0 | 262.5264 | 230.9260 | magic_formula_x_piotroski_x_acquirers (ueps) | 2026-11-14T12:44:52Z | 1.8 h |
| SNDL | LONG | 1.37 | 1.3700000047683716 | 0.0 | 1.4796 | 1.3015 | regime_terminal (regime_terminal) | 2026-11-14T13:05:09Z | 1.4 h |

## Age / staleness (`active_raw`, n=182)

- Status: **94 OPEN, 85 EXPIRED, 3 SL_HIT** (0 TP_HIT).
- Age: min 1.4 h, **median 107.2 h (4.5 d)**, max **5,490.6 h (228.8 d)**.
- **82 rows >30 d stale (45 %)**; 85 `_auto_expired` with `expired_no_pnl`.
- `current_price` null/0: **110 (60 %)**; `pnl_pct == 0`: **142 (78 %)**.
- Examples: `Quality Compounders_stocks_LIN_2026-03-30` (LIN, EXPIRED, age 5,490.6 h, px None, pnl 0); `Dividend Aristocrats_stocks_PG_2026-03-30` (PG, same); `stocksunify2_V_LONG_…_20260826T220326Z` (V, EXPIRED, px None, pnl 0).

## Closed-recent (`picks.recent_closed`, n=738)

- 347 WON / 390 LOST / 1 CLOSED → **WR 47.0 %**, mean PnL **+0.323 %**, PF **1.154**.
- Newest: 2026-11-13T06:48:03Z (33.3 h); oldest 2026-02-19 (268 d); **649 rows >30 d stale (88 %)**.
- `current_price` is null for **738/738** closed rows (by schema — not a bug per se, but it prevents independent re-pricing from the payload).

## Accuracy cross-reference — Yahoo Finance `query1.finance.yahoo.com/v8/finance/chart/<TICKER>`

Stooq (`stooq.com/q/d/l/?s=…`) returned a JavaScript proof-of-work challenge (HTTP 200, no CSV) from this network, so Yahoo was used.

- Programmatic check of **294** EQUITY/ETF closed picks (01–14 Nov): entry price inside the timestamp-day (or prior session) [low, high] range in **292/294** cases.
- **2 impossible AAPL entries**:
  - `vt_equity_two_day_rsi_reversal::AAPL::2026-11-13`: entry **315.9799**, exit 320.7652, `WON`, closed 2 min later. AAPL on 2026-11-13 traded **355.75–360.83** (close 356.27). Entry is **11.2 % below the day's low**.
  - Second AAPL pick dated 2026-11-03 with entry **316.22**; 2026-11-03 range **325.33–334.50**.
- Spot samples (entry vs actual close):
  - GOOGL LONG entry **298.70** = Yahoo 2026-11-12 close **298.70001** ✓; reported −1.19 % exit 295.155 vs 11-13 close 295.77.
  - ADBE active entry **243.08** = Yahoo 2026-11-13 close **243.0800018** exactly ✓ (live PnL 0.00 % because it was never repriced).
  - AMD momentum-factor 2026-11-12 entry 573.86 vs 11-12 close 585.30 (−1.95 %); exit 529.22 vs 11-13 close 534.06.

## Surface-level metrics (conflicting cohorts)

| Source | n | WR | PF | PnL |
|---|---|---|---|---|
| `recent_closed` (payload) | 738 | 47.0 % | 1.154 | +0.323 %/trade |
| `pf_registry.by_asset_class_policy_clean` | 461 | 42.95 % | 0.722 | −3.208 % total |
| `money_ready_verdict` intrabar truth | 250 | 59.2 % | 0.939 | — |
| `audit_surface_truth` | 249 | 59.0 % | 0.934 | — |
| `summary_picks` | 13,383 total / 820 resolved | **162.4 %** (invalid) | — | −0.06 %/trade |
| `tournament` | 288 closed | 36.8 % | — | −0.40 %/trade |

`intrabar_daily_divergence.flag = true` (daily PF 1.298 vs honest 0.939; `wr_inflation_pp=-11.2`). Readiness: `MONITORING`, **sizing_allowed=false**, `SUB_T2`.

**Verdict: FAIL** — 2 impossible prices, 45 % stale/auto-expired, 60 % no current price, 6 mutually inconsistent performance cohorts.

---

# 3. FOREX — **FAIL**

## Active picks (curated, n=2)

| Symbol | Dir | Entry | Current | PnL % | TP | SL | Strategy (source) | Timestamp | Age |
|---|---|---|---|---|---|---|---|---|---|
| NZDUSD=X | LONG | 0.552517 | 0.5525166988372803 | −0.0 | 0.556937 | 0.549754 | non_crypto_consensus | 2026-11-14T14:24:05Z | 0.1 h |
| USDCAD=X | SHORT | 1.4269 | 1.426900029182434 | −0.0 | 1.417913 | 1.434035 | non_crypto_consensus | 2026-11-14T14:24:05Z | 0.1 h |

Full `active_raw` consensus batch (20 rows, 16:24:05Z) also includes AUDJPY, CADJPY, EURGBP, USDCHF, AUDUSD, GBPUSD, USDJPY, EURUSD, GBPJPY — **all `pnl=0.0`**.

## Age / staleness (`active_raw`, n=277)

- Status: **118 OPEN, 158 EXPIRED, 1 SL_HIT**.
- Age: min 0.1 h, **median 3,932.7 h (163.9 d)**, max **6,413.7 h (267.2 d)** (2026-02-20).
- **158 rows >30 d stale (57 %)** — all `_auto_expired` with `exit_reason="STALE (auto-expired >NNNNh)"` and `pnl=0`.
- `current_price` null/0: **242 (87 %)**; `pnl_pct == 0`: **273 (99 %)**. Only 4 rows have non-zero PnL (2 positive / 2 negative → 0.7 % WR, PF 0.004).
- Stale examples: `sig_20260220_084514_USD-JPY` (USD-JPY SHORT, EXPIRED, 6,413.7 h, px None, pnl 0); `sig_20260220_185343_EUR-USD`; `sig_20260222_065338_USD-CHF`.
- April-2026 frozen set (`2026-04-03T00:06:41Z`, all EXPIRED, `current_price == entry`, pnl 0): EURJPY=X 184.068, AUDNZD=X 1.20874, USDJPY=X 159.472, USDCHF=X 0.79860, AUDUSD=X 0.69144, NZDUSD=X 0.57208.

## Closed-recent (n=187)

- 73 WON / 104 LOST / 10 CLOSED → **WR 39.0 %**, mean PnL **−0.155 %**, PF **0.634**.
- Newest 2026-11-13T02:08:26Z (37.9 h); oldest 2026-02-17 (270 d); **144 rows >30 d stale (77 %)**.

## Structure defects

- **49/277 (17.7 %) not spot FX**: 44 currency-ETF rows + 5 `EURUSDT` crypto rows (see §1).
- **Duplicates:** 40 duplicate-ID groups (67 extra rows); 67 duplicate `symbol+strategy+direction` groups (198 extra rows). Example: `consensus_USDJPY=X_SELL_20261114_1424` appears 2×.
- **Direction conflicts (10 symbols):** USDJPY=X, GBPUSD=X, USDCHF=X, GBPJPY=X, CADJPY=X, USD-JPY, plus 4 more carry both LONG and SHORT rows simultaneously in the same class.

## Accuracy cross-reference — `https://open.er-api.com/v6/latest/USD`

Provider `time_last_update_utc = Sat, 14 Nov 2026 00:02:31 +0000`. Deviation of entry vs latest rate:

| Pair | Dir | Entry | er-api now | Δ entry→now | Stored PnL |
|---|---|---|---|---|---|
| USDCAD=X | SHORT | 1.4269 | 1.426026 | **−0.061 %** | −0.0 |
| NZDUSD=X | LONG | 0.552517 | 0.552726 | **+0.038 %** | −0.0 |
| USDJPY=X | SHORT | 159.875 | 159.799454 | −0.047 % | 0.0 |
| EURUSD=X | LONG | 1.105021 | 1.103809 | −0.110 % | 0.0 |
| GBPUSD=X | LONG | 1.323136 | 1.322019 | −0.084 % | 0.0 |
| AUDUSD=X | LONG | 0.677415 | 0.677928 | +0.076 % | 0.0 |
| AUDJPY=X | LONG | 108.821 | 108.332517 | **−0.449 %** | 0.0 |
| EURJPY=X (Apr zombie) | LONG | 184.068 | 176.388044 | **−4.172 %** | 0.0 |
| AUDNZD=X (Apr zombie) | LONG | 1.20874 | 1.226518 | **+1.471 %** | 0.0 |

**Flat vs unpriced:** the two curated pairs are not "genuinely unchanged" (market moved 0.04–0.06 %); they are unpriced (`current_price` copied from `entry_price`). The April zombies are worse: EURJPY has moved 4.17 % against the position and still reports `pnl=0.0`.

Curated entries match Yahoo's weekend FX snapshot exactly (`USDCAD=X` 1.4269, `NZDUSD=X` 0.552517), so the entry is a weekend snapshot, not a live tick.

Conflicting cohorts: `recent_closed` WR 39.0 %/PF 0.634 vs `pf_registry` policy-clean n=438 WR 35.6 %/PF 0.866 vs MRV intrabar n=612 WR 32.2 %/PF 0.660 vs `summary_picks` WR **147.0 %** (invalid) vs `tournament` 262 closed WR 50.8 %.

**Verdict: FAIL** — 17.7 % contaminated class, 57 % auto-expired, 87 % unpriced, duplicate/direction-conflicted rows, no non-zero PnL for 273/277.

---

# 4. ETF — **FAIL**

## Active picks (curated, n=10; all timestamped 2026-11-14T12:17:32–33Z, age 2.2 h)

| Symbol | Dir | Entry | Current | PnL % | TP | SL | Strategy |
|---|---|---|---|---|---|---|---|
| USO | LONG | 145.58 | 145.5800018310547 | 0.0 | 158.8965 | 137.5901 | etf_dual_momentum |
| KWEB | SHORT | 22.93 | 22.93000030517578 | −0.0 | 21.6193 | 23.7164 | etf_dual_momentum |
| XLF | LONG | 58.68 | 58.68 | 0.0 | 60.9077 | 57.3434 | etf_sector_momentum |
| EFA | LONG | 104.17 | 104.16999816894531 | −0.0 | 110.058 | 102.698 | etf_faber_tactical |
| XOP | SHORT | 184.8 | 184.8000030517578 | −0.0 | 177.408 | 188.496 | etf_rsi2_pullback |
| VCSH | LONG | 77.25 | 77.25 | 0.0 | 80.34 | 75.705 | etf_rsi2_pullback |
| XLV | LONG | 188.85 | 188.85000610351562 | 0.0 | 197.1497 | 183.8702 | etf_sector_dual_momentum |
| XLE | LONG | 64.96 | 64.96 | 0.0 | 68.9142 | 62.5875 | etf_cross_sectional_momentum |
| VLUE | LONG | 189.18 | 189.17999267578125 | −0.0 | 198.0385 | 183.8649 | etf_cross_sectional_momentum |
| XLK | LONG | 170.28 | 170.27999877929688 | −0.0 | 184.1118 | 161.9809 | etf_cross_sectional_momentum |

## Age / staleness (`active_raw`, n=38)

- Status: **30 OPEN, 8 EXPIRED**.
- Age: min 1.6 h, **median 13.0 h**, max **5,414.4 h (225.7 d)**; **8 rows >30 d stale (21 %)**.
- `current_price` null/0: 11 (29 %); `pnl_pct == 0`: **32 (84 %)**.
- Stale example: `sector_rotation_enhanced::XLE::2026-04-03` (EXPIRED, 5,414.4 h, px 59.25, pnl 0); `dual_momentum::SPY::2026-04-03`.

## Closed-recent (n=567)

- 250 WON / 317 LOST → **WR 44.3 %**, mean PnL **+0.040 %**, PF **1.036**.
- Newest 2026-11-13T14:07:06Z (26.0 h); oldest 2026-02-19 (268 d); **490 rows >30 d stale (86 %)**.

## Accuracy cross-reference — Yahoo Finance

- **All 10 curated entries equal the Yahoo 2026-11-13 close to full float precision** (USO 145.58, XLF 58.68, XLE 64.96, EFA 104.17, XLK 170.28, XLV 188.85, VLUE 189.18, XOP 184.80, KWEB 22.93, VCSH 77.25). The 0.00 % PnL is therefore `entry == current` on a Saturday, i.e. **never repriced**, not a flat market.
- **Contradiction:** `super_signals_QQQ_LONG_strong_consensus_(alpha_engine,_kimi)_20261111T145156Z` — entry 677.359985, exit 679.63, `pnl_pct=+0.3351`, but `status=LOST`, `exit_reason=SL_HIT`, `closed_at=2026-11-13T15:07:19Z`. PnL arithmetic is correct (exit > entry for a LONG); the **status/reason is wrong**.
- QQQ entry 677.36 vs Yahoo 11-11 close 690.38 / 11-12 close 688.17 (entry ≈1.6–1.9 % below both); exit 679.63 vs 11-13 close 679.89.

## Divergence / cohort conflict

| Source | n | WR | PF |
|---|---|---|---|
| `recent_closed` | 567 | 44.3 % | 1.036 |
| `pf_registry` policy-clean | 15 | 73.33 % | 1.8406 |
| MRV intrabar truth | 45 | **2.22 %** | **0.0216** |
| `audit_surface_truth` | 44 | 2.3 % | 0.0219 |
| `summary_picks` | 1002 / 73 resolved | **232.9 %** (invalid) | — |

`intrabar_daily_divergence`: daily PF 1.8358 vs honest 0.0216 → **`pf_inflation_x = 84.99`**, `wr_inflation_pp = +71.1`, `flag = true`. This is the largest daily-vs-intrabar inflation in the payload. Readiness `INSUFFICIENT_SAMPLE`, sizing_allowed=false.

`VCSH` is a short-term **corporate bond** ETF placed in ETF while HYG/JNK/EMB are BOND — economic mislabel.

**Verdict: FAIL** — status/PNL contradiction, 85× PF inflation, 84 % zero-PnL, 86 % of closed rows >30 d old.

---

# 5. BOND — **FAIL**

## Active picks

Curated `picks.active`: **0 rows** (`asset_class_summary.BOND = {activeCount: 0, smartCount: 0, avgScore: 0, thresholdPass: true}` — a vacuous pass because n=0).

`active_raw`: **15 rows, all `OPEN`**, but only **5 unique instruments** (SHY, TLT, HYG, JNK, EMB) from 3 emitters:

| Emitter run (UTC) | Rows | Instruments | Pricing |
|---|---|---|---|
| `alpha_engine_*` 2026-11-13T13:39:53Z | 5 | HYG, EMB, JNK, SHY, TLT | HYG/JNK/TLT/SHY `px=None, pnl=0`; EMB priced (91.13, +0.23 %) |
| `bond_scanner_*` 2026-11-13T14:08:24Z | 5 | HYG, EMB, JNK, SHY, TLT | **all `px=None, pnl=0`** |
| `orphan_emitter_bond_*` 2026-11-13T14:34:18Z | 5 | HYG, JNK, SHY, TLT | all priced (HYG 76.94, JNK 92.32, SHY 81.17, TLT 79.38) |

- **15 rows → 9/15 (60 %) `current_price=None` and `pnl=0`**; 6/15 priced.
- Duplicates: 6 `symbol+strategy+direction` groups, 9 extra rows. TLT SHORT emitted **3×** with *different* entries (79.72, 79.72, 79.20).
- Ages 23.9–24.8 h. Newest row 2026-11-13T14:34:18Z (25.5 h).

## Closed-recent (n=35)

- 12 WON / 23 LOST → **WR 34.3 %**, mean PnL **−0.221 %**, PF **0.586**.
- **Newest: 2026-11-10T13:52:26Z = 98.2 h = 4.09 d** → confirms claim (b). Oldest 2026-02-19 (268 d); **27/35 >30 d stale (77 %)**.
- Newest row: `super_signals_TLT_LONG_strong_consensus_(alpha_engine,_kimi)_20261110T135226Z`, TLT LONG entry 82.115 → exit 81.10, −1.236 %, SL_HIT.

## Accuracy cross-reference — Yahoo Finance + FRED

- **Yahoo TLT:** 2026-11-12 close **79.72**, 2026-11-13 close **79.38**.
  - Run 1/2 SHORT entry **79.72 = 11-12 close** → one-session lag; never repriced (px None).
  - Run 3 entry **79.20** (intraday 14:34Z ≈ 09:34 ET), `current_price` 79.379997 = **11-13 close** ✓, pnl −0.23 %.
- **Same lag confirmed on all run-1 entries:** HYG 76.98 = 11-12 close, JNK 92.42 = 11-12 close, EMB 91.34 = 11-12 close, SHY 81.14 = 11-12 close.
- **FRED reachable:** `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10` → 2026-11-06 4.86, 11-09 4.88, 11-10 4.98, 11-12 **5.10** (11-11 blank). Picks carry no yield field, so **yield-level reconciliation is UNVERIFIED**; only ETF prices can be reconciled.

## Cohort conflict (severe)

| Source | n | WR | PF / PnL |
|---|---|---|---|
| `recent_closed` | 35 | 34.3 % | PF 0.586, −0.221 %/trade |
| `pf_registry` policy-clean | **1** | 0 % | PF 0, −0.011 % |
| `money_ready_verdict` | 26 intrabar / 1 resolved | 7.69 % intrabar, 0 % resolved | PF 0.3915 / 0 |
| `summary_picks` | 1,603 total / 72 resolved | **127.8 %** (invalid) | −0.02 %/trade |
| `audit_surface_truth.tournament` | **503 closed** | **58.1 %** | avg **+1.066 %**, verdict WATCH |

Tournament (503, +1.07 %/trade) vs policy-clean (1, −0.01 %) is a 500× sample discrepancy for the same class. Readiness `BLOCKED`, `sizing_allowed=false`.

**Verdict: FAIL** — triple-emission, 60 % never priced, newest data 4.1 d old (live banner STALE), one-session entry lag, irreconcilable n=1 vs n=503 cohorts.

---

# 6. FUTURES — **FAIL**

## Active picks (curated, n=1)

| Symbol | Dir | Entry | Current | PnL % | TP | SL | Strategy (source) | Timestamp | Age |
|---|---|---|---|---|---|---|---|---|---|
| ES=F | LONG | 7583.0 | 7583.0 | 0.0 | 8039.642857 | 7354.678571 | futures_connors_rsi2 (multi_asset_copytrader) | 2026-11-14T13:06:02.734149Z | 1.4 h |

Live page row (verified): `ES=F LONG 56 SANDBOX multi asset copytrader futures connors rsi2 … +0.00% $7583.0 $8039.6 $7354.7 **Nov 14, 8:06 AM**` → **date is displayed**; claim (a) not reproducible.

## Age / staleness (`active_raw`, n=13)

- Status: **3 OPEN, 10 EXPIRED**; **`pnl_pct == 0` for 13/13 (100 %)**.
- Age: min 1.4 h, **median 2,342.5 h (97.6 d)**, max **5,414.4 h (225.7 d)**; **10/13 >30 d stale (77 %)**.
- `current_price` null/0: 8 (62 %).
- Duplicates: `multi_asset_futures_connors_rsi2::ES=F::2026-11-14_1306` emitted **3×** (same ID); `YM=F + inverse_luxalgo_confluence + SHORT` emitted **6×** (daily, 2026-08-07 → 08-12).

## Closed-recent

**0 FUTURES rows in `picks.recent_closed`** → the main feed provides **no resolved sample**. All FUTURES performance claims come from other surfaces.

## Accuracy cross-reference — Yahoo Finance (futures symbols)

- ES=F entry **7583.0** = Yahoo 2026-11-13 close **7583.0** exactly ✓ (so the pick is Friday's close, emitted Saturday).
- **Frozen/stale prices prove no mark-to-market:**
  - ZN=F `current_price=111.015625` = Yahoo **2026-04-02** close **111.015625** exactly; today 105.1875.
  - CL=F `current_price=112.05999755859375` (Apr 2 evening electronic) vs today **88.56** → **−21.0 %**; pnl still 0.0.
  - GC=F `current_price=4702.7001953125` (Apr 2–3 range) vs today **3886.30** → **−17.3 %**; pnl 0.0.
  - NG=F `current_price=2.806999921798706` ≈ Apr 2 close 2.80; today **3.23** (+15.1 %); pnl 0.0.
- 6 `inverse_luxalgo_confluence::YM=F` rows (2026-08-07…12) have `current_price=None`, `pnl=0`, `EXPIRED`.

## Cohort conflict

| Source | n | WR | PF |
|---|---|---|---|
| `recent_closed` | **0** | — | — |
| `pf_registry` policy-clean | 13 | 23.08 % | 0.911 |
| MRV intrabar | 52 | 42.31 % | 1.0936 |
| `summary_picks` | 945 / 61 resolved | **363.9 %** (invalid) | — |
| `audit_surface_truth` | 52 | 42.3 % | 1.0936 → `INSUFFICIENT_DATA` |
| `tournament` | 22 closed | 50.0 % | avg +1.214 % |

`asset_class_summary.FUTURES.forwardWR = 0.059` (5.9 %) contradicts MRV WR 42.3 % for the same asset class. Readiness `INSUFFICIENT_SAMPLE`, `BLOCKED`, sizing_allowed=false.

**Verdict: FAIL** — 100 % zero PnL, 77 % stale, duplicate emissions, frozen April/August prices, zero closed rows in the primary feed, contradicting WRs.

---

# 7. COMMODITY — **FAIL**

## Active picks (curated, n=2)

| Symbol | Dir | Entry | Current | PnL % | TP | SL | Strategy | Timestamp | Age |
|---|---|---|---|---|---|---|---|---|---|
| PA=F | SHORT | 1006.0 | 1006.0 | 0.0 | 975.82 | 1026.12 | commodity_carry_momo_double_sort | 2026-11-14T14:22:03.725422Z | 0.1 h |
| SB=F | LONG | 18.41 | 18.40999984741211 | −0.0 | 18.9623 | 18.0418 | commodity_carry_momo_double_sort | 2026-11-14T14:22:03.725422Z | 0.1 h |

## Age / staleness (`active_raw`, n=44)

- Status: **27 OPEN, 16 EXPIRED, 1 SL_HIT**.
- Age: min 0.1 h, **median 1.6 h**, max **4,054.4 h (169 d)**; **16/44 >30 d stale (36 %)**.
- `current_price` null/0: **32 (73 %)**; `pnl_pct == 0`: **39 (89 %)**.
- Stale examples: `new_equity_commodity_strategies_20::commodity_channel_index_bounce::CT=F::2026-05-29` (EXPIRED, 4,054.4 h, px None); `…::contango_roll_yield::HG=F::2026-05-29`; `inverse_luxalgo_confluence::SI=F::2026-07-02/03/05`.
- Duplicates: GC=F SHORT ×4 (cftc_cot_commercial_signal), CL=F ×2, NG=F ×2; 9 duplicate-ID groups, 13 extra rows.

## Closed-recent (n=7)

- 2 WON / 5 LOST → **WR 42.9 %**, mean PnL **−0.598 %**, PF **0.604**.
- Newest 2026-11-13T14:36:02Z (25.5 h); oldest 2026-11-04.
- **Contradiction:** `feature_commodity_mom::CL=F::2026-11-09` — SHORT entry 87.81, exit 86.0107731, `pnl=+2.049`, but `status=LOST`, `exit_reason=TP_HIT`. A profitable TP is labelled a loss.
- Several resolutions are 7–11 minutes long (NG=F 18:46:10→18:53:37; CL=F 14:47:21→14:58:31), which makes the −6.80 % NG=F "SL hit" a ~7-minute move.

## Accuracy cross-reference — Yahoo Finance

- PA=F entry **1006.0** = Yahoo 2026-11-13 close **1006.0** exactly ✓.
- SB=F entry **18.41** = 2026-11-13 close **18.40999984741211** ✓.
- GC=F `current_price=3886.300048828125` = 2026-11-13 close **3886.300048828125** ✓.
- HE=F closed-pick entry **55.15** = 2026-11-12 close **55.15** ✓ (timestamp 11-13 14:36Z).
- CL=F closed entries 86.23 / 87.81 vs Nov 11/9 closes ~86.53 / ~? — plausible intraday (not enough granularity from daily closes; intraday fill **UNVERIFIED**).

## Canonical mismatch

**44/44 COMMODITY rows use `=F` futures suffixes** (GC=F, CL=F, SI=F, HG=F, HE=F, NG=F, ZS=F, SB=F, PA=F). `alpha_engine.asset_class.normalize_asset_class()` returns **`futures`** for every one of them. The payload's COMMODITY class is therefore a *sub-bucket of futures*, not a distinct canonical class.

## Cohort conflict

| Source | n | WR | PF / PnL |
|---|---|---|---|
| `recent_closed` | 7 | 42.9 % | PF 0.604, −0.598 %/trade |
| `pf_registry` policy-clean | 14 | **14.29 %** | **0.1939**, −0.178 % |
| MRV intrabar | 229 | 40.17 % | 1.0256 |
| `summary_picks` | 19,502 / 1,447 resolved | **240.2 %** (invalid) | +0.07 %/trade |
| `tournament` | 258 closed | 47.7 % | avg +0.770 % |

`audit_surface_truth` verdict `WATCH` but `policy_clean_wr_pct=14.29` and `policy_clean_pf=0.172` — "watch" is driven by the intrabar cohort, not the policy-clean one. Readiness `BLOCKED`, `INSUFFICIENT_SAMPLE`, sizing_allowed=false.

**Verdict: FAIL** — 100 % canonical mislabel, 89 % zero PnL, 36 % stale, one status/PNL contradiction in 7 closed rows (14 %).

---

# 8. MUTUAL FUNDS — **FAIL (absent)**

| Check | Result |
|---|---|
| Class present in `dashboard_payload` / `dashboard_data` / `summary_picks` / `pf_registry` / `money_ready_verdict` / `audit_surface_truth` | **No** — zero occurrences of "mutual" in any payload |
| Any live/active/closed mutual-fund pick | **None** |
| `alpha_engine/mutual_fund_ranker.py` exists | **Yes** (23,931 bytes, 2026-11-02) |
| Does it emit picks/signals? | **No** — produces fund *rankings* only (risk-adjusted return, Sharpe/Sortino/Ulcer, dedupe clones). No `pick`/`signal` writes in the file. |
| Wired into production? | **No** — zero references in `alpha_engine/production_scanner.py`, `alpha_engine/config.py`, `alpha_engine/scanner.py` |
| Output artifact | `OUT_JSON = alpha_engine/data/mutut_fund_rankings.json` (**typo "mutut"**); file **does not exist** on disk |
| Related tooling | `tools/mutual_fund_backtest.py`, `tools/fund_walkforward_backtest.py`, `tools/mf_walkforward_backtest.py`, `tools/tactical_rotation_backtest.py` — **research/backtest only**; `mutual_fund_metadata.csv` exists (5,983 bytes) |
| `recon_uncharted_tables.py` families | `mutual_fund_v1` (`mf_`), `mutual_fund_v2` (`mf2_`) are recognised for DB reconnaissance, not for scoring |

- Active picks: **0**
- Closed-recent: **0**
- Accuracy: **UNVERIFIED / not applicable** (no picks to score)
- External data: none needed

**Verdict: FAIL (absent)** — mutual funds are a research/ranking artefact, not a live pick surface. The planned class does not exist in any dashboard feed; the ranker exists but has never produced its output file (and the output path is misspelled).

---

# 9. Cross-class stale vs unpriced determination (explicit)

The question was whether `0.00 %` means *genuinely unchanged* or *never priced/resolved*. Evidence supports **"never priced" in every non-crypto class**:

| Evidence | Detail |
|---|---|
| Identity pricing | All **17** curated non-crypto active picks have `current_price == entry_price` to full float precision; recomputed `(current-entry)/entry` = 0.0000 % in every case. |
| Non-trading day | 2026-11-14 is a **Saturday**. Equity/ETF/Futures/Commodity timestamps (12:17–14:24Z) are *after* Friday's US close; their "entry" equals Friday 2026-11-13's close exactly (verified for ADBE, SNDL, USO, XLF, XLE, EFA, USO, XLK, XLV, VLUE, XOP, KWEB, VCSH, ES=F, PA=F, SB=F). A Saturday emission cannot observe a Saturday move. |
| FX moved | `open.er-api.com` shows non-zero deviations for every sampled pair (all 10 `non_crypto_consensus` pairs, −0.449 % … +0.076 %) while stored PnL is 0. |
| Frozen zombies | ZN=F price frozen at the exact 2026-04-02 close; CL=F at ~112 vs 88.56 now; GC=F at ~4702 vs 3886 now; EURJPY at 184.07 vs 176.39 now — all still `pnl=0.0`. A genuine "unchanged" would track the price; these prices did not move because the resolver never touched them. |
| Auto-expiry | 277 rows carry `_auto_expired=True` + `expired_no_pnl=True` and exit reason `STALE (auto-expired >NNNNh)`; they were closed by clock, not by price. |
| Denominator bug | `summary_picks` computes `win_rate_pct = wins/resolved*100`, producing >100 % WR for 6 classes — wins and resolved come from different populations. |

---

# 10. Evidence index / archive

**Raw downloads (all HTTP 200):**

| File | Bytes |
|---|---|
| `dashboard_payload.json` | 34,385,688 |
| `dashboard_data.json` | 25,099,200 |
| `summary_picks.json` | 2,736 |
| `pf_registry.json` | 15,178,278 |
| `money_ready_verdict.json` | 42,481 |
| `audit_surface_truth.json` | 10,239 |
| `db_health.json` | 6,462 |

**Derived working files in `raw/`:** `active_table.txt`, `active_raw_stats.txt`, `per_class_detail.txt`, `zombie_examples.txt`, `zombie_flags.txt`, `class_mismatch.txt`, `dedupe_stats.txt`, `bond_detail.txt`, `closed_equity_samples.txt`, `status_pnl_consistency.txt`, `price_range_check.txt`, `crosscheck_active.txt`, `pf_policyclean.txt`, `mislabels_detail.txt`, `class_age_summary.txt`, `audit_index.html`.

**External sources used (named per class):**

| Class | Source | URL |
|---|---|---|
| EQUITY, ETF, BOND, FUTURES, COMMODITY | Yahoo Finance chart API | `https://query1.finance.yahoo.com/v8/finance/chart/<SYMBOL>?range=…&interval=1d` |
| Stooq | attempted, **blocked** by JS proof-of-work | `https://stooq.com/q/d/l/?s=<ticker>.us&i=d` (returned HTML challenge, no CSV) |
| FOREX | open.er-api.com | `https://open.er-api.com/v6/latest/USD` (update Sat 14 Nov 2026 00:02:31Z) |
| BOND (yield) | FRED | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10` (2026-11-12 = 5.10) |
| MUTUAL FUNDS | repo filesystem only | `alpha_engine/mutual_fund_ranker.py`, `alpha_engine/data/mutual_fund_metadata.csv` |

**Live UI verification:** Playwright 1.58.2 → `https://findtorontoevents.ca/audit/` loaded `window.DASHBOARD_DATA.generated_at = 2026-11-14T14:30:07.135931+00:00`, `picks.active=20`, `picks.active_raw=4146` (2 SPORTS rows filtered client-side). Screenshot saved at `/tmp/kilo/d/audit_full.png`.

---

# 11. Per-class verdict roll-up

| Class | Data integrity | Price fresh | Resolved sample | External reconciliation | Verdict |
|---|---|---|---|---|---|
| EQUITY | 2 impossible AAPL prices; 45 % stale | Curated entries = 11-13 close | 738 recent | Yahoo: 292/294 in-range | **FAIL** |
| FOREX | 17.7 % non-FX contamination; 57 % auto-expired | 87 % no price | 187 recent | er-api: all pairs moved, PnL 0 | **FAIL** |
| ETF | status/PNL contradiction; 84.99× PF inflation | 84 % PnL 0 | 567 recent | Yahoo: entries = 11-13 close | **FAIL** |
| BOND | 3× duplicate emission; 60 % unpriced | newest 4.09 d | 35 recent | Yahoo TLT/ETF + FRED reachable | **FAIL** |
| FUTURES | 100 % PnL 0; frozen Apr/Aug prices | 77 % stale | **0** | Yahoo ES=F exact; zombies −21 %/−17 % | **FAIL** |
| COMMODITY | 100 % canonical mislabel (=F→FUTURES) | 89 % PnL 0 | 7 recent | Yahoo PA/SB/GC exact | **FAIL** |
| MUTUAL FUNDS | Class absent everywhere | n/a | 0 | n/a | **FAIL (absent)** |
| STOCKS (label) | 1 tournament row only | n/a | 1 | n/a | **FAIL (phantom)** |
| INDEX / MANAGED_FUTURES | `summary_picks` only; no picks | n/a | 17 / 0 | n/a | **FAIL (phantom)** |

**Non-crypto data integrity: FAIL.**
