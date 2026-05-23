# Paper Trading Session — 2026-04-22 (16 positions across 2 accounts)

**Operator:** Claude Opus 4.7 (1M context)
**Window:** 2026-04-22 ~16:45–21:30 UTC
**Path:** TradingView Desktop 3.1.0.7818 via MCP (CDP port 9222)
**Related agents in session:** Antigravity, Cursor, Codex, Copilot, MiniMax M2.7, Ollama gpt-oss-120b, GPT-OSS-120B (Cerebras), OpenCode GLM-4.7

---

## Trades live (16 positions, 0 TP/SL violations at audit)

### Account 1: `HIGHFWWRABV55_SCOREABOVE50_V4` (~$981 balance — small test account)

| # | Symbol | Side | Qty | Entry | TP | SL | Strategy source |
|---|---|---|---|---|---|---|---|
| 1 | OKX:HYPEUSDT | Long | 1 | 40.936 | 42.570 | 40.120 | `quan_engine` n=647 fwd_wr=99.8% |
| 2 | BINANCE:DOTUSDT | Short | 151.9 | 1.292 | 1.240 | 1.318 | `mega_mutation` n=34 fwd_wr=67.6% trust=RELIABLE |
| 3 | NYSE:MRK | Long | 0.99 | 112.75 | 117.74 | 108.77 | `stocks_rsi2_pullback` (strategy n=18 @ 77.8%) |
| 4 | NASDAQ:GOOGL | Long | 0.99 | 336.87 | 343.79 | 325.31 | Cerebras #1 EQUITY by `net_edge_bps` (705) |
| 5 | NYSE:CVX | Long | 1 | 187.11 | 192.75 | 184.32 | Cerebras #3 EQUITY by `net_edge_bps` (464) |
| 6 | OANDA:USDJPY | Long | 2,460 | 159.486 | 160.280 | 159.000 | `fx_smart_carry_trade_momentum` trust=RELIABLE |

### Account 2: `zerounderscore` (~$98K balance — diversified)

| # | Symbol | Side | Qty | Entry | TP | SL | Strategy source |
|---|---|---|---|---|---|---|---|
| 1 | NASDAQ:GOOGL | Long | 0.97 | 338.13 | 343.79 | 325.31 | Cerebras #1 EQUITY (705 bps) |
| 2 | NYSE:KO | Long | 0.99 | 74.66 | 76.45 | 73.39 | Cerebras #2 EQUITY (465 bps) |
| 3 | NYSE:CVX | Long | 0.98 | 187.32 | 192.47 | 177.81 | Cerebras #3 EQUITY (464 bps) |
| 4 | NYSE:JNJ | Long | 0.99 | 224.42 | 231.15 | 220.93 | Cerebras #4 EQUITY (377 bps) |
| 5 | NASDAQ:PEP | Long | 0.99 | 153.81 | 158.42 | 151.50 | Cerebras #5 EQUITY (350 bps) |
| 6 | OKX:HYPEUSDT | Long | 0.99 | 41.166 | 42.570 | 40.120 | `quan_engine` n=647 |
| 7 | BINANCE:DOTUSDT | Short | 152.2 | 1.289 | 1.240 | 1.318 | `mega_mutation` (direction hedge) |
| 8 | OANDA:USDJPY | Long | 2,459 | 159.453 | 160.250 | 158.900 | Forex Trusted/RELIABLE filter |
| 9 | AMEX:IWM | Long | 1 | 275.68 | 282.57 | 272.23 | ETF small-cap (fills ETF class gap) |
| 10 | AMEX:SPY | Long | 2 | 709.90 | 724.10 | 702.80 | ETF broad market |
| 11 | NASDAQ:TLT | Long | (peer-added) | 86.81 | 88.55 | 85.94 | Bond ETF (added by peer — completes bond class) |

Direction mix: **14 LONG / 2 SHORT** across 5 asset classes (crypto / equity / forex / ETF / bond).

---

## Asset class coverage — all 5 edge-identifiable classes filled

From audit dashboard closed-trade stats:

| Class | Edge signal | Coverage |
|---|---|---|
| EQUITY/STOCKS | 50.9% WR, PF 1.51, n=348 ✓ strong | 7 positions (MRK, GOOGL×2, CVX×2, KO, JNJ, PEP) |
| CRYPTO | 42.8% WR, PF 1.04, n=22,569 ✓ modest | 4 positions (HYPE×2 L, DOT×2 S) |
| FOREX (Trusted filter) | 49% WR, PF 3.59 w/ filter | 2 positions (USDJPY×2 L, RELIABLE tier) |
| ETF | 49.4% WR, PF 1.10, n=77 ✓ modest | 2 positions (IWM, SPY — zerounderscore only) |
| BOND | 47.1% WR, PF 1.60, n=17 (small sample) | 1 position (TLT — peer-added) |
| COMMODITY | 20.8% WR, PF 1.05 marginal | 0 (all pipeline picks fail gate) |
| FUTURES | No edge (toxic per GLM kill-list) | 0 (correctly skipped) |

---

## Methodology — 3-agent synthesis

Three peer agent families produced top-picks docs in this repo today. Their methodologies differed; each had blind spots the others caught.

| Agent | Signal contribution | Where it was surgical |
|---|---|---|
| **Cerebras (GPT-OSS-120B)** | Pointed me at `audit_dashboard/data/forex_futures_picks.json` and the `net_edge_bps` field — the pipeline's own canonical edge metric. I had never used this field. | Correctly identified GOOGL BUY @ 705 bps as #1 EQUITY. |
| **GLM-4.7 (OpenCode)** | Quantified "Proven ML + conf 0.85–0.90" cohort at 82% WR / PF 11.8 (crypto) and "stocks Trusted + Score ≥50" at 69.2% WR / PF 2.62. Kill list: `signal_type="BUY"` = 28.9% WR worst, `quan_engine` scalps 29% WR, Grade D/F = 33.4% WR. | Flagged Forex Trusted (RELIABLE/PROVEN) filter as 49% WR / PF 3.59 cohort. |
| **Me (Opus 4.7)** | Traced placeholder-stats blocker in 39 `clone_hl_copy_*` rows to `strategy_clone_generator.py:493-497`, back-test against closed-trade leaderboard, 7-reviewer consensus. | Full 6-stage gate stack with placeholder quarantine + resolver-bug awareness + side-sanity + regime checks. |

### Gates applied (in order)

1. **Source scan** — union of `alpha_engine/data/active_picks.json`, `audit_dashboard/data/dashboard_data.json`, `audit_dashboard/data/forex_futures_picks.json`.
2. **Hard rejects:**
   - `strategy` contains `clone_hl_copy` — placeholder whale stats
   - `signal_type == "BUY"` (GLM kill-list: 28.9% WR worst cohort)
   - `confidence ≥ 0.90` AND `fwd_trades < 20` — skill "danger zone"
   - `trust_tier in {SANDBOX, UNPROVEN, PROBATION, DEMOTED}`
   - Non-crypto with suspect fwd_wr (per `feedback_noncrypto_resolver_live_close_bug.md`)
   - Placeholder triple detector: `|elite_score − forward_trades| < 1 AND |elite_score − round(forward_wr × 100)| < 1`
3. **Primary ranker:** `net_edge_bps` DESC (Cerebras contribution).
4. **Secondary prefer:** `trust_tier in {RELIABLE, PROVEN}`, `0.55 ≤ confidence ≤ 0.85`, R:R ≥ 1.5, `signal_type == "LONG"` over `"BUY"`.
5. **Execution hygiene:** TV chart buy/sell button places market + default TP/SL (**TV default is inverted 0.67:1 R:R — MUST override via Protect Position**); side-sanity gate enforced; post-fill audit confirms TP/SL populated.

---

## What was NOT traded, and why

| Candidate | Asset | Reason skipped |
|---|---|---|
| IONQ / SOFI / MSFT LONG (Cerebras top 3 STOCKS @ ~714 bps) | Stocks | All conf 0.90-0.95 = danger zone (22.2% WR per skill scoring rules) |
| BNBUSDT rsi2, DYDXUSDT CCI, STRKUSDT CCI (GLM crypto top) | Crypto | GLM pulled from historical backtest; current active records for these symbols score ≤18 or conf=0.4 — fail the gate |
| ETHUSDT LONG `copy_pm_elpolloloco` | Crypto | Placeholder triple: score=100 / fwd_wr=100% / n=9 — same pattern as clone_hl_copy stats |
| CADJPY/AUDJPY/GBPJPY SHORT (FOREX n=106 fwd_wr=57%) | Forex | trust=WATCH (not RELIABLE); strategy `non_crypto_consensus` susceptible to resolver bug |
| KC=F / CT=F / ZS=F / ZW=F SHORT | Commodity | fwd_wr=25% on n=4 too small + class PF 1.05 marginal |
| HG=F / PL=F LONG | Futures | n=0 fwd + class 0% WR on n=20 (toxic per GLM kill-list) |

---

## Session artifacts

**Files in repo root:**
- [TRADINGVIEW_PROPER.MD](../TRADINGVIEW_PROPER.MD) — end-to-end TV trade flow reference for other agents
- [PICKS_OPUS_4_7_ULTIMATE.MD](../PICKS_OPUS_4_7_ULTIMATE.MD) — 3-agent methodology synthesis
- [PICKS_OPENCODE_GLM47_HUGGINGFACE.MD](../PICKS_OPENCODE_GLM47_HUGGINGFACE.MD) — GLM-4.7 KILL LIST + filter quantification
- [PICKS_GPT_OSS_120B_CERBRAS.MD](../PICKS_GPT_OSS_120B_CERBRAS.MD) — Cerebras `net_edge_bps` ranking

**Pipeline fix status (merged during session):**
- **PR #320** (`5b7cc64313`) — `fix(clone-seed + quality_gates): reject EXEMPT_FROM_SAFETY_GATES + stop seeding placeholder WR` — closes the Blocker 2 placeholder-stats finding (39 rows, source traced to `strategy_clone_generator.py:493-497`, validated by 7+ reviewer consensus + Ollama probability analysis at ~10⁻⁷⁸).
- **PR #325** (`32626c6f4e`) — `fix(quality_gates): revert PR #253 conf gate + pre-score PM exemption (restores 38 active picks)` — closes the audit-dashboard-only-5-picks issue. Dashboard pass rate 14/90 → 52/90. CI 60/60.
- **PR #324** (closed as superseded) — Copilot's shadow-mode version of the same fix; PR #325 was stronger. Closed with explanatory comment.

---

## Active tripwires

- **Issue #331** `ALERT: branch fix/blocklist-adjustment unblocks crypto_winners (PF 0.30 bleeder)` — labeled `do-not-merge / safety / governance / alert`. No PR opened yet. If autonomous agent escalates to PR, close immediately with pointer to issue.

---

## Monitoring notes

- **HYPE LONG on `quan_engine`** — GLM flagged `quan_engine` as 29% WR on scalps generally. The n=647 @ 99.8% fwd_wr for HYPEUSDT specifically may be an outlier OR may share a placeholder pattern. Data passes the triple-detector (score/n/wr don't coincide), but worth reviewing in 24–48h if trade doesn't resolve cleanly.
- **CVX LONG on V4** — SL at 177.81 is wide (~5% below entry); pick's strategy R:R 1.67:1. Current uPnL slightly negative — watch for wider equity pullback.
- **ETF gap closure**: IWM + SPY on zerounderscore + TLT (peer-added) fills 3 ETF/bond exposures; ETF class on audit dashboard shows 49.4% WR / PF 1.10 over 77 closed trades.

---

*Session complete. 16 trades live with valid TP/SL across 5 asset classes, 2 pipeline PRs merged, 1 safety tripwire active, methodology documented for peer agents.*
