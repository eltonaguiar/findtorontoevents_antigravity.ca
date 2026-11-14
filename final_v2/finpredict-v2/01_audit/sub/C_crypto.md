# Subagent C — Crypto Per-Symbol Audit (live findtorontoevents.ca/audit)

**Verdict: `FAIL` — crypto data integrity + accuracy**

Crypto counts and the one fresh per-symbol PnL (NEARUSDT) reconcile with Binance, but the crypto book is dominated by never-resolved "zombie" re-emissions, zero/null entry rows, duplicate IDs, and status/PnL contradictions. The headline "flat 0%" mass is a stale-data artifact, not true flat performance.

- Audit time: **2026-11-14T16:03–16:10Z** (host clock `Sat Nov 14 04:03:50 PM UTC 2026`).
- Payload `generated_at`: **2026-11-14T14:30:07.135931+00:00** (`payload_lag_seconds = 4586.14`, `repo_sha = 1b2c98e225f8de2bd860f4165a3476f659723796`).
- Archive: `2026-11-14/finpredict-v2_20261114-1602/` (this report in `sub/C_crypto.md`, raw evidence in `raw/`).

---

## 0. Data sources / evidence (exact)

Downloaded (curl -sL, HTTP 200; full files kept, never dumped):

| File | URL | bytes | sha256 |
|---|---|---|---|
| `raw/live_data_dashboard_data.json` | `https://findtorontoevents.ca/audit/data/dashboard_data.json` | 25,099,200 | `71e8add438e0606cf1d5ad9d2f2123a7a29e087f80d3e03e3a1f84d817e81954` |
| `raw/live_data_dashboard_payload.json` | `https://findtorontoevents.ca/audit/data/dashboard_payload.json` | 34,385,688 | `9a3c6a410902bc71b25261f30d3aa1026cc57132f738b39c647f599f0aa19f32` |

> Path correction: `https://findtorontoevents.ca/audit/dashboard_data.json` and `/audit/dashboard_payload.json` return **HTTP 404** (992-byte Apache "Object not found"). The live payloads are under `/audit/data/`. Both downloaded files were parsed with Python `json.load` and only sampled/aggregated; nothing whole was printed.

External market sources (all fetched 2026-11-14T16:03–16:06Z):

- Binance ticker: `https://api.binance.com/api/v3/ticker/price?symbol=<SYM>` (HTTP 200)
- Binance klines: `https://api.binance.com/api/v3/klines?symbol=<SYM>&interval=1d&startTime=<ms>&limit=400` (287 daily bars 2026-02-01→2026-11-14)
- Binance 1h: `https://api.binance.com/api/v3/klines?symbol=<SYM>&interval=1h&startTime=<2026-11-14T00:00Z ms>&limit=100`
- Coinbase spot: `https://api.coinbase.com/v2/prices/BTC-USD/spot`, `.../ETH-USD/spot`
- CoinGecko: `https://api.coingecko.com/api/v3/simple/price?ids=near,xrp,bitcoin,ethereum,solana&vs_currencies=usd&include_last_updated_at=true`
- FX: `https://open.er-api.com/v6/latest/USD`

Binance last daily close (2026-11-14 UTC day, still forming): NEAR **3.197**, XRP **0.9716**, BTC **65,672.05**, ETH **1,837.15**, SOL **73.64**.
Cross-source agreement: CoinGecko 16:05Z (BTC 65,624 / ETH 1,836.13 / NEAR 3.20 / SOL 73.61) and Coinbase (BTC 65,576.55 / ETH 1,833.68) within ~0.15% of Binance. **Price feed is sound; the problem is the dashboard's cached/pick data.**

Schema note: `picks = {active:20, active_raw:4148, recent_closed:3500, ueps_kpi, smart_picks}`; crypto asset_class only. `active` is a strict subset of `active_raw` (all 3 crypto ids present in `active_raw`).

---

## 1. Crypto inventory (scope)

| Section | crypto rows | composition |
|---|---|---|
| `.picks.active` (curated panel) | **3** | NEARUSDT, XRPUSDT, BTCUSDT |
| `.picks.active_raw` (raw feed) | **3,577** | 121 distinct symbols |
| `.picks.recent_closed` | **1,966** | 69 distinct symbols; WON 779 / LOST 1,187 |

`active_raw` crypto statuses: **EXPIRED 3,100 (86.7%)**, OPEN 402 (11.2%), SL_HIT 50, TP_HIT 25 → **only 75 (2.1%) ever resolved**.

Flat/missing mass in `active_raw` crypto:
- `pnl_pct == 0.0`: **3,322 / 3,577 (92.9%)**
- `current_price` null: **3,170 / 3,577 (88.6%)**
- pnl 0 **and** status EXPIRED: 2,995; pnl 0 + EXPIRED + null current: 2,841
- pnl 0 with status OPEN: 327 (329 OPEN rows have null current)

Curated `.picks.active`: **19 / 20 rows have `current_price ≈ entry_price`** (relative diff < 0.01%), i.e. PnL is identically 0 by construction; the only nonzero row is NEARUSDT (+2.74%).

---

## 2. Per-symbol table — top 20 (combined `active_raw` + `recent_closed`)

`n active` = raw-feed rows; `n closed` = recent_closed rows; age from `age_hours`; entry/current medians over positive values; "active nonzero" excludes the 0.0 zombies.

| # | symbol | n active | n closed | newest | median age h | entry med | entry min–max | cur med (dash) | active nonzero med PnL (n) | closed med PnL | zero-PnL | null cur |
|---|--------|---------:|---------:|--------|------------:|----------:|--------------|---------------:|---------------------------:|---------------:|---------:|---------:|
| 1 | BTCUSDT | 215 | 176 | 2026-11-14 14:24 | 1574.5 | 75,654.97 | 0.2608–86,672.82 | 66,300.0 | −3.82 (20) | −0.351 | 195 | 196 |
| 2 | ETHUSDT | 199 | 145 | 2026-11-14 13:08 | 1742.5 | 2,168.71 | 0.092–3,175.53 | 1,883.225 | −1.951 (19) | −0.149 | 180 | 181 |
| 3 | AVAXUSDT | 220 | 118 | 2026-11-14 13:04 | 1634.5 | 8.927 | 0.1544–23.5 | 7.887 | −8.78 (15) | +0.196 | 205 | 206 |
| 4 | LINKUSDT | 186 | 103 | 2026-11-14 12:53 | 1850.5 | 11.474 | 0.1656–15.102 | 9.591 | +5.396 (11) | −1.016 | 175 | 175 |
| 5 | **NEARUSDT** | 179 | 99 | 2026-11-14 13:10 | 2054.5 | 3.638 | 1.246–5.771 | 3.339 | +8.75 (13) | −2.231 | 166 | 166 |
| 6 | STXUSDT | 160 | 111 | 2026-11-14 12:20 | 1898.5 | 0.312 | 0.1187–0.4546 | 0.2733 | −1.44 (5) | −2.361 | 155 | 154 |
| 7 | **XRPUSDT** | 170 | 100 | 2026-11-14 13:54 | 2090.5 | 1.3339 | 0.9842–2.45 | 0.9944 | +29.43 (15) | −1.232 | 155 | 154 |
| 8 | JUPUSDT | 161 | 106 | 2026-11-14 04:29 | 2006.5 | 0.2551 | 0.1541–0.3803 | 0.2574 | +2.88 (1) | −1.579 | 160 | 160 |
| 9 | SOLUSDT | 177 | 90 | 2026-11-14 13:54 | 1478.5 | 96.45 | 69.07–142.5 | 74.38 | −1.505 (16) | −1.087 | 161 | 162 |
| 10 | DOTUSDT | 150 | 116 | 2026-11-14 12:20 | 1802.5 | 1.016 | 0.75–1.524 | 0.769 | −3.27 (6) | −0.732 | 144 | 144 |
| 11 | ARBUSDT | 156 | 105 | 2026-11-14 12:53 | 1874.5 | 0.165 | 0.0729–0.249 | 0.1378 | +6.39 (5) | −1.889 | 151 | 151 |
| 12 | SUIUSDT | 150 | 99 | 2026-11-14 12:53 | 1898.5 | 0.9128 | 0.2608–1.2792 | 0.7705 | −19.84 (11) | −1.824 | 139 | 139 |
| 13 | WIFUSDT | 142 | 102 | 2026-11-14 02:28 | 2042.5 | 0.1924 | 0.1352–0.2654 | 0.1401 | −2.84 (1) | −1.53 | 141 | 141 |
| 14 | ADAUSDT | 153 | 87 | 2026-11-14 12:53 | 1886.5 | 0.2125 | 0.1466–0.98 | 0.1608 | +3.732 (6) | −1.002 | 147 | 147 |
| 15 | RENDERUSDT | 174 | 0 | 2026-11-14 12:53 | 2354.5 | 1.587 | 0.1005–2.206 | 1.486 | −7.18 (11) | — | 163 | 163 |
| 16 | ENAUSDT | 165 | 0 | 2026-11-14 13:10 | 2006.5 | 0.1259 | 0.0758–0.2884 | 0.124 | +19.92 (5) | — | 160 | 160 |
| 17 | BTC-USD | 63 | 30 | 2026-11-13 04:06 | 4722.7 | 77,253.35 | 61,510.37–86,541.5 | 66,814.41 | −2.952 (3) | −2.522 | 60 | 60 |
| 18 | ETH-USD | 63 | 28 | 2026-11-13 17:33 | 4837.5 | 2,257.02 | 1,592.77–2,766.9 | 1,893.1 | −2.152 (4) | −3.155 | 59 | 59 |
| 19 | SOL-USD | 40 | 25 | 2026-11-14 02:33 | 4591.6 | 87.46 | 64.29–121.77 | 75.37 | −0.238 (3) | −4.409 | 37 | 37 |
| 20 | BNBUSDT | 41 | 16 | 2026-11-14 14:24 | 50.2 | 651.38 | 575.69–766.32 | 615.44 | −4.458 (11) | −0.996 | 30 | 30 |

The four mandated symbols are rows 1, 2, 5, 7. Note the median `age_h` is ~1,500–2,400 h (2–3 months) even though `newest` is today — each symbol carries a long tail of old OPEN/EXPIRED zombies plus a few fresh rows.

---

## 3. External cross-check — dashboard vs Binance actual

### 3A. Fresh OPEN picks (entry → now; Binance 1h closes 2026-11-14)

Binance 1h closes used as entry-time reference (hour bucket ending): 13:00Z NEAR 3.315 / XRP 0.9955 / BTC 66,839.18 / SOL 75.52 / ETH 1,893.80; 16:00Z NEAR 3.197 / XRP 0.9716 / BTC 65,666.23 / SOL 73.62 / ETH 1,837.05.

| symbol | pick (strategy) | dir | dash entry | dash cur | dash PnL | Binance entry-hour close | Binance now (16:03Z) | ACTUAL entry→now | Δ vs dash |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| NEARUSDT | `tsmom_volscaled` (13:10Z) | SHORT | 3.324 | 3.233 | **+2.74%** | 3.315 @13:00 | 3.197 | **+3.82%** (from 3.324) / +3.56% (from 3.315) | +1.08 pp |
| XRPUSDT | `kalshi_mtf_consensus` (13:53Z) | SHORT | 0.9842 | 0.9842 | **0.00%** | 0.9955 @13:00 | 0.9716 | **+1.28%** | +1.28 pp |
| BTCUSDT | `kalshi_mtf_consensus` (13:53Z) | SHORT | 66,300.0 | 66,300.0 | **0.00%** | 66,839.18 @13:00 | 65,672.05 | **+0.95%** | +0.95 pp |
| SOLUSDT | `kalshi_mtf_consensus` (13:53Z, active_raw only) | LONG | 74.38 | 74.38 | **0.00%** | 75.52 @13:00 | 73.64 | **−0.99%** | −0.99 pp |

Interpretation: NEAR's entry (3.324 @13:10Z) sits between the 12:00 and 13:00 closes (3.332/3.315) → **valid, not fabricated**. XRP/BTC/SOL entries are likewise inside the surrounding hourly range. Their dashboard `current_price` is a frozen copy of `entry_price`, so the displayed 0.00% understates real moves by ~1 pp (XRP/BTC) and hides a −1% SOL loss.

### 3B. Closed picks — dashboard realized PnL vs Binance daily-close reconstruction (entry date → close date)

| symbol | id (strategy) | dir | dash entry | dash PnL | entry-day close | close-day close | Binance recon | note |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| NEARUSDT | `4a0f6d258f8c` (luxalgo_confluence) | SHORT | 3.528 | +4.535% | 3.445 (11-13) | 3.42 (11-14 02:00 1h) | +0.73% | implied exit 3.368 vs TP 3.3751 → plausible intraday TP |
| XRPUSDT | `b90a9e97460a` (luxalgo_confluence) | SHORT | 1.3192 | +4.677% | 1.3052 (11-04) | 1.2072 (11-05) | +7.51% | plausible intraday force-close |
| XRPUSDT | `df4693675515` (luxalgo_confluence) | LONG | 1.0111 | −2.453% | 1.011 (11-13) | 0.9716 (11-14) | −3.90% | plausible intraday force-close |
| BTCUSDT | `76597e45e9e2` (luxalgo_confluence) | LONG | 68,880.68 | −2.343% | 68,314 (11-13) | 65,672.05 (11-14) | −3.87% | plausible intraday force-close |
| BTCUSDT | `super_signals…strong_consensus` | LONG | 78,336.01 | +2.781% | 80,504.01 (11-04) | 80,504.01 (11-04) | 0.00% daily | TP 80,294 hit intraday — but **SL 79,491.18 > entry** (invalid) |
| ETHUSDT | `aggregated_picks…crypto_funding_confluence` | LONG | 1,931.0 | −2.000% | 1,900.06 (12:00 1h) | 1,837.15 | n/a | **entry 1.63% above market at 12:51Z** → stale entry; SL 1,892.38 trigger does match 13:00 close 1,893.8 |
| ETHUSDT | `2dd6b29c2d79` (luxalgo_confluence) | LONG | 1,985.48 | +1.757% | 2,019.74 (11-12) | 2,019.74 (11-12) | 0.00% daily | TP 2,020.01 hit intraday — plausible |
| ETHUSDT | `super_signals…super_consensus` | LONG | 2,047.29 | **+1.188% LOST/SL_HIT** | 2,053.21 (11-10) | 2,056.36 (11-11) | +0.15% | **contradiction**: SL 2,072.80 > entry, implied exit > entry, labelled LOST |
| SOLUSDT | `06eb96db8f60` (luxalgo_confluence) | LONG | 77.76 | −2.726% | 78.19 (11-13) | 76.22 (11-14 02:00 1h) | −2.52% | plausible |
| SOLUSDT | `super_signals…strong_consensus` | SHORT | 96.45 | +3.815% | 89.33 (11-05) | 89.33 (11-05) | 0.00% daily | plausible intraday |

Bottom line: where picks actually resolve, dashboard PnL magnitudes are broadly within Binance intraday ranges (the daily-close reconstruction cannot reproduce intraday exits, so small gaps are expected). The failures are **unresolved/zombie rows, bad entry prices, and status/PnL contradictions** — not a systematically wrong price feed.

---

## 4. NEARUSDT ~3.16% — is it plausible? → YES

- Active pick: `tsmom_strategy_NEARUSDT_SHORT_tsmom_volscaled_20261114T131005.727789+0000`, SHORT, entry **3.324**, timestamp **2026-11-14T13:10:05Z**, TP 2.7106, SL 3.6307, age 1.3 h.
- Exact `3.16%` short return ⇒ price `3.324 × (1 − 0.0316) = 3.21896`. **Binance 15:00Z 1h close = 3.219 → (3.324−3.219)/3.324 = 3.1588% ≈ 3.16%.**
- Same pick at other timestamps: dashboard snapshot 14:30Z price 3.233 → **2.74%** (the dashboard's number); Binance 16:00Z 3.197 → **3.82%**; CoinGecko 16:05Z 3.20 → 3.73%.
- Entry validation: Binance 12:00Z close 3.332, 13:00Z close 3.315; entry 3.324 is inside that range → **entry is real, not fabricated**. The pick is simply very fresh (1.3 h old).
- Verdict: **3.16% is plausible**; it is the mark at ~15:00Z between the dashboard's cached 2.74% and the live 3.82%. No evidence of a fake PnL.

---

## 5. "Everything except NEARUSDT/XRPUSDT/USDCAD=X/NZDUSD=X/BTCUSDT is ~0%/flat" — stale/zombie, not true flat

**Yes, overwhelmingly stale/zombie artifact.**

Crypto evidence:
- 3,322/3,577 raw crypto rows have `pnl_pct == 0.0`; 3,170 have `current_price = null`; 2,995 of the zero-PnL rows are `EXPIRED` (never resolved); 2,841 are EXPIRED **and** null-current.
- In the curated 20-row `.picks.active` panel, **19/20 have `current_price` equal to `entry_price`** (copy, not a live quote) → PnL identically 0. The three crypto rows: NEAR has a live price (2.74%); XRP and BTC are frozen copies (0.00%), while Binance shows +1.28% and +0.95% respectively.
- 158 OPEN crypto rows are `pnl 0.0` + null current + age ≥ 2 days (e.g. `forward_signals` DrawdownRecovery* rows timestamped 2026-11-12 with entry prices but no live price).

FX caveat (outside crypto but part of the user's list): USDCAD=X entry 1.4269 vs er-api USD/CAD 1.426026 → ~0.06%; NZDUSD=X entry 0.552517 vs er-api 1/1.809216 = 0.552727 → ~0.04%. Those two are **genuinely near-flat**, and their dashboard `current_price` is also just the entry copy. So "flat" can mean either "stale copy" (crypto majority) or "real tiny move" (FX). The crypto 0.00% rows are **not** true flat performance.

---

## 6. Zombie factory — `inverse_mutations` / `inverse_luxalgo_confluence`

Quantified from `active_raw`:

- **2,267 rows** match either condition: 2,262 have `strategy == inverse_luxalgo_confluence`, 2,266 have `source_system == inverse_mutations` (the union is 2,267).
- **20 distinct symbols**, **167 distinct emission days**, first **2026-05-23**, last **2026-11-13**.
- Emission rate: median **15 symbols/day**, mode **16**, max 18. Distribution (rows/day: days): 15:34, 16:60, 14:13, 12:11, 13:8, 17:9, etc. → essentially **one row per symbol per day**.
- Status: **EXPIRED 2,231**, OPEN 26, SL_HIT 7, TP_HIT 3. **pnl == 0.0: 2,255; `current_price` null: 2,254.**
- Per-symbol row counts (≈ one emission/day): STXUSDT 157, ENAUSDT 157, JUPUSDT 156, **NEARUSDT 156**, AVAXUSDT 152, RENDERUSDT 150, ARBUSDT 148, WIFUSDT 141, LINKUSDT 141, **XRPUSDT 136**, ADAUSDT 135, DOTUSDT 131, SUIUSDT 130, **SOLUSDT 123**, **BTCUSDT 118**, **ETHUSDT 114**, TIAUSDT 8, VNQ 7, ATOMUSDT 6, ETCUSDT 1.
- NEARUSDT detail: 156 rows across **156 distinct days** (exactly one/day); 152 EXPIRED, 154 PnL 0.0, 154 null current; direction mix 58 SHORT / 98 LONG; entry range 1.246–5.771; as of 2026-11-13 a LONG at 3.675 marked −12.03% SL_HIT, and 11-11/11-12 LONG 3.675 marked 0.0/OPEN.
- These zombies account for **2,254 of the 3,170 null-current crypto rows (71%)**. The remaining null/zero rows come from other dormant strategies (`signal_validation` 314, `kimi_signal_tracking` 132, `incubator_forward` 98, `forward_signals` 77, etc.).

Conclusion: yes — `inverse_mutations`/`inverse_luxalgo_confluence` re-emit the same 16-symbol universe every day since 2026-05-23 as EXPIRED, zero-PnL, null-price rows. This is the dominant source of the "flat" appearance. (It is not literally the same entry value each day — entry/direction vary — but the symbol set and zombie pattern are daily.)

---

## 7. Impossible / garbage rows (flagged)

1. **Zero/null entry price — 85 crypto rows** across `active_raw + recent_closed`: mape_evolver 28, genetic_programmer 21, ensemble_evolver 10, neat_neural 8, hyperparam_dna 8, genome 4, failure_evolver 3, prediction_market_consensus 3. Examples: 9× `BTCUSDT LONG entry=0.0` at `2026-11-14T13:04:27` and 9× `SOLUSDT LONG entry=0.0` at the same timestamp (ensemble/mape evolver).
2. **Absurd-low entries — 12 rows**, all `inverse_luxalgo_confluence`, EXPIRED, PnL 0, null current:
   - BTCUSDT entry **0.2608** (2026-06-12), **1.334** (2026-08-06, 2026-08-07), **0.3322** (2026-10-08 → 2026-10-11, 4 rows)
   - ETHUSDT entry **0.092** (2026-08-06, 2026-08-07)
   - LINKUSDT **0.1656** (2026-07-19); AVAXUSDT **0.1544** (2026-07-20, 2026-07-21)
3. **Status/PnL contradictions — 12 `recent_closed` crypto rows** labelled `LOST` with positive PnL (all `exit_reason=SL_HIT`): ETH 2,047.29 +1.1884; DOT 0.834 +1.5603; LINK 9.79114 +1.934; SUI 0.8119 +2.1062; WIF 0.1548 +0.8398; etc. Separately, **stop-loss above entry for LONG**: BTC `69980.0` SL 77,569 TP 70,028; ETH `2047.29` SL 2,072.80. BTC super also shows `+12.0426%` FORCE_CLOSED ~64 s after entry (08:28:11Z → 08:29:15Z, id `…20261104T082811Z`).
4. **Duplicates**: 218 duplicate `id` values (max 4 repeats); 244 duplicate `(symbol, direction, entry_price, timestamp)` tuples (max 12: HYPEUSDT LONG 39.91 ×12, LINKUSDT LONG 9.1 ×11, NEARUSDT LONG 1.355 ×11, all at `2026-03-19T11:50:50`). **55 ids appear in BOTH `active_raw` and `recent_closed` with conflicting status/PnL**, e.g. `clone_hl_copy_PensionFund_24M::NEARUSDT::2026-03-19_1150` = EXPIRED 0.0 in raw vs WON +3.4483 in closed; `aggregated_picks_ETHUSDT…crypto_funding_confluence` = OPEN −3.71 (cur 1859.42) vs closed LOST −2.0 SL_HIT.
5. **current_price null on old picks**: 2,841 EXPIRED + 329 OPEN; e.g. all 37 `DOT-USD` rows are EXPIRED/null and the symbol's newest row is 2026-10-27. `RENDERUSDT`/`ENAUSDT` have 0 closed rows — their 174/165 raw rows never reach the closed ledger.
6. **pnl exactly 0.0 with OPEN/EXPIRED**: 3,322 total (2,995 EXPIRED + 327 OPEN); 2,841 also null-current — these are the "flat" rows.

---

## 8. Recommendations (data integrity)

1. Quarantine `inverse_mutations` / `inverse_luxalgo_confluence`: stop emitting all 20 symbols daily unless a real signal fires; archive/delete the 2,267 zombie rows. They poison counts, medians and the "active" panel.
2. Reject picks with `entry_price <= 0`, `entry_price` outside a per-symbol sanity band, or `current_price` null at resolution; mark them `INVALID`, never `EXPIRED/pnl=0`.
3. Enforce `SL < entry < TP` for LONG (and inverse for SHORT) at ingestion; block rows where status and PnL sign disagree (`LOST` with pnl>0).
4. Deduplicate by `(symbol, direction, entry, timestamp)` and by `id` across `active_raw`/`recent_closed`; 55 conflicting-id pairs are currently double-counted.
5. Do not publish `current_price = entry_price` as a quote. The curated panel should show `—`/stale badge, as 19/20 rows are frozen copies (XRP/BTC real moves +1.28%/+0.95% are hidden).
6. Freeze or regenerate the ETH 1,931.0 entry (1.63% above market at 12:51Z) and the BTC `69980`/ETH `2047.29` SL-above-entry rows.

---

## 9. Re-run evidence (exact commands)

```bash
# live data (correct paths; /audit/dashboard_*.json are 404)
curl -sL -o raw/live_data_dashboard_data.json    https://findtorontoevents.ca/audit/data/dashboard_data.json
curl -sL -o raw/live_data_dashboard_payload.json https://findtorontoevents.ca/audit/data/dashboard_payload.json

# Binance tickers (2026-11-14T16:03Z)
for s in NEARUSDT XRPUSDT BTCUSDT ETHUSDT SOLUSDT; do
  curl -s "https://api.binance.com/api/v3/ticker/price?symbol=$s"; echo; done

# Binance daily closes 2026-02-01 → 2026-11-14
curl -s "https://api.binance.com/api/v3/klines?symbol=NEARUSDT&interval=1d&startTime=1769904000000&limit=400"
# Binance 1h for 2026-11-14 (entry-hour validation)
curl -s "https://api.binance.com/api/v3/klines?symbol=NEARUSDT&interval=1h&startTime=1763078400000&limit=100"

# cross-source
curl -s "https://api.coinbase.com/v2/prices/BTC-USD/spot"
curl -s "https://api.coingecko.com/api/v3/simple/price?ids=near,xrp,bitcoin,ethereum,solana&vs_currencies=usd&include_last_updated_at=true"
curl -s "https://open.er-api.com/v6/latest/USD"
```

Parsing was done with Python `json.load` + aggregation over `.picks.active`, `.picks.active_raw`, `.picks.recent_closed`; outputs saved in `raw/symbol_stats_final.json`, `raw/crosscheck_rows.json`, `raw/representative_picks.json`.

---

## 10. UNVERIFIED

- **UNVERIFIED:** exact intraday exit prints used by the dashboard resolver (TP/SL/FORCE_CLOSED). I only fetched daily and 2026-11-14 hourly klines; for most closed picks the exit happened intraday on earlier dates, so day-close reconstruction can legitimately differ from the recorded realized PnL.
- **UNVERIFIED:** whether `current_price == entry_price` with `pnl=0.0` is an intentional "no quote" sentinel or a bug. The effect (0% PnL) is confirmed; intent is not.
- **UNVERIFIED:** root cause that produces 0.0 / 0.26 / 1.334 BTC entries in `inverse_luxalgo_confluence` (likely a units/last-price lookup bug in the mutation lab) — not traced into source (repo source left unmodified per task).
- **UNVERIFIED:** FX intraday moves for USDCAD=X / NZDUSD=X; only daily er-api rates were checked (~0.06% / ~0.04%).
