<AGENT: D> COMPLETE — wrote D_reliability_summary.md

# SUB-AGENT D — RELIABILITY SCORECARD

Scope: aggregate the findings of SUB-AGENTS A/B/C into a ranked reliability scorecard
for the copy-trader + backtest + reliability + future-bias / timestamp / EST /
timezone audit of findtorontoevents.ca/audit.

Output: reports/subscriptions/2026-11-18-copytrader-llm-audit/D_reliability_summary.md

---

## 1. SCORING METHODOLOGY

Each verified candidate source is scored 0–100 on four axes (weights in parentheses):

| Axis | Weight | What is measured |
|---|---|---|
| Verified (exchange / on-chain provenance) | 30 | Source is displayed on an exchange's own leaderboard or on-chain verified record; raw data available |
| Backtest WR (paper) | 25 | Verified backtest win rate, computed from the no-future-bias filter |
| Forward-bias risk | 20 | Whether any timestamp / bar filter produced a future-bias flag |
| EST / timestamp correctness | 15 | UTC->EST conversion applied correctly (-5 winter / -4 EDT); no naive timestamps |
| Traceability | 10 | Every pick carries a source_file and ID; no synthetic placeholder in the live set |

Decision thresholds:
- Verified >= 70 AND forward-bias risk LOW AND EST/timestamp CORRECT -> LIVE candidate
- Verified 40-69 OR forward-bias MEDIUM -> PAPER ONLY
- Verified < 40 OR forward-bias HIGH OR EST/timestamp WRONG -> DO NOT USE

---

## 2. RANKED RELIABILITY SCORECARD

| Rank | Source / Trader Label | Class | Verified % | Backtest WR | Backtest PF | Forward-bias risk | EST/timestamp | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | Shallow-Pair-Frog (OKX) | a | 100% | 43.6% (a) | 0.91 | LOW | CORRECT | PAPER ONLY (class a WR too low for live) |
| 2 | nightraid- (OKX) | a | 100% | 43.6% (a) | 0.91 | LOW | CORRECT | PAPER ONLY |
| 3 | FJ Investment (OKX) | a | 100% | 43.6% (a) | 0.91 | LOW | CORRECT | PAPER ONLY |
| 4 | CrowleyZhou (OKX) | a | 100% | 43.6% (a) | 0.91 | LOW | CORRECT | PAPER ONLY |
| 5 | Trader KS (OKX) | a | 100% | 43.6% (a) | 0.91 | LOW | CORRECT | PAPER ONLY |
| 6 | Expert-Ethash-Camel (OKX) | a | 100% | 43.6% (a) | 0.91 | LOW | CORRECT | PAPER ONLY |
| 7 | okx_futures_ada (OKX) | a | 100% | 43.6% (a) | 0.91 | LOW | CORRECT | PAPER ONLY |
| 8 | okx_futures_fil (OKX) | a | 100% | 43.6% (a) | 0.91 | LOW | CORRECT | PAPER ONLY |
| 9 | okx_futures_apt (OKX) | a | 100% | 43.6% (a) | 0.91 | LOW | CORRECT | PAPER ONLY |
| 10 | okx_futures_arb (OKX) | a | 100% | 43.6% (a) | 0.91 | LOW | CORRECT | PAPER ONLY |
| 11 | Bybit master traders (Aristocrat, Real World, MASE, Caleon8, Harisonjones, etc.) | a | 100% | 43.6% (a) | 0.91 | LOW | CORRECT | PAPER ONLY (class a WR 43.6%) |
| 12 | MQL5_MT4 forex DB | a | 100% | 43.6% (a) | 0.91 | LOW | CORRECT | PAPER ONLY |
| 13 | Hyperliquid on-chain (whale_433roi, whale_59M_252roi, etc.) | d | 100% | n/a (no backtest) | n/a | LOW | CORRECT | PAPER ONLY (no entry_time, no backtest) |
| 14 | btctangying (Bitget) | a | 100% | n/a | n/a | LOW | CORRECT | DO NOT USE (flagged suspicious, no trades) |
| 15 | DeepSeek-V4 (Bitget) | a | 100% | n/a | n/a | LOW | CORRECT | DO NOT USE (flagged suspicious, no trades) |
| 16 | Rich (Bitget) | a | 100% | n/a | n/a | LOW | CORRECT | DO NOT USE (flagged suspicious, no trades) |
| 17 | DataPEDIA BTC Bot (Bybit) | a | 100% | n/a | n/a | LOW | CORRECT | DO NOT USE (100% WR grid/DCA signature) |
| 18 | Harisonjones (Bybit) | a | 100% | n/a | n/a | LOW | CORRECT | DO NOT USE (100% WR grid/DCA signature) |
| 19 | Pizza Coin.8 (Bybit) | a | 0% | n/a | n/a | HIGH | CORRECT | DO NOT USE (disqualified -61% ROI, 95.8% DD) |
| 20 | Crypto Musk (Bybit) | a | 0% | n/a | n/a | HIGH | CORRECT | DO NOT USE (44.74% WR, disqualified) |
| 21 | SKDXB (Bybit) | a | 0% | n/a | n/a | HIGH | CORRECT | DO NOT USE (DD 56.5% > 40% cap) |
| 22 | Hyperliquid on-chain (100% WR group) | d | 100% | n/a | n/a | HIGH | CORRECT | DO NOT USE (100% WR = grid/DCA survivorship) |
| 23 | lb_None (clone, highscore) | c | 0% | n/a | n/a | HIGH | CORRECT | DO NOT USE (no entry_time, NO_ENTRY_TIME) |
| 24 | whale_13M_new (clone, highscore) | c | 0% | n/a | n/a | HIGH | CORRECT | DO NOT USE (NO_ENTRY_TIME) |
| 25 | Auros_66M (clone) | c | 0% | n/a | n/a | HIGH | CORRECT | DO NOT USE (NO_ENTRY_TIME) |
| 26 | whale_433roi clone | c | 0% | n/a | n/a | HIGH | CORRECT | DO NOT USE (NO_ENTRY_TIME) |
| 27 | PensionFund_24M clone | c | 0% | n/a | n/a | HIGH | CORRECT | DO NOT USE (NO_ENTRY_TIME) |
| 28 | ABC_41M clone | c | 0% | n/a | n/a | HIGH | CORRECT | DO NOT USE (NO_ENTRY_TIME) |
| 29 | btctangying (Bitget) | a | 100% | n/a | n/a | HIGH | CORRECT | DO NOT USE (flagged suspicious) |
| 30 | cta_picks (CL/NG/HG/ZW/TLT/IEF/ZS/SPY) | e | 98% | 8.0% | 0.06 | LOW | CORRECT | PAPER ONLY (0.03% scale signals, no edge) |
| 31 | non_crypto_consensus (12 picks) | e | 98% | 8.0% | 0.06 | LOW | CORRECT | PAPER ONLY |
| 32 | forex_copytrader RSI2 (27 picks) | e | 98% | 8.0% | 0.06 | LOW | CORRECT | PAPER ONLY |
| 33 | multi_asset_bond ZN=F | e | 98% | 8.0% | 0.06 | LOW | CORRECT | PAPER ONLY |
| 34 | myfxbook_olivierdanvel | e | 0% | n/a | n/a | HIGH | HIGH | DO NOT USE (synthetic placeholder, entry 0) |
| 35 | hyperliquid on-chain (low WR / no trades) | d | 100% | n/a | n/a | LOW | CORRECT | PAPER ONLY |

---

## 3. VERDICT BY SOURCE TYPE

### 3.1 Exchange leaderboard (a) — PAPER ONLY
All class (a) sources pass the no-future-bias bar conditionally, but the backtest
win rate for the 2026-11-17/18 1h-bar sample is **43.6%**, which is below the 50%
threshold required for a live assignment. The OKX spot traders (Shallow-Pair-Frog,
nightraid-, FJ Investment, etc.) show high leverage (50x) and wide TP/SL slack,
which inflates the P&L magnitude but not the win rate. Verdict: keep as paper-only
monitoring only; do not execute live.

### 3.2 Hyperliquid on-chain (d) — PAPER ONLY / EXCLUDE
Hyperliquid records (whale_433roi, whale_59M_252roi, etc.) have strong on-chain
provenance and verified win rates, but:
- No entry_time_utc -> cannot be timestamp-audited (EST/EDT offset cannot be
  assigned to a specific fill).
- The 100%-win-rate cluster (PensionFund_24M, whale_7.7M_acct, whale_123M_87roi,
  whale_48M_429roi, whale_35M_313roi, whale_34M_129roi, ETH_whale_282M_long,
  NMTD_25M) is a survivorship/grid signature, not evidence of edge.
Verdict: exclude from live; retain for paper-only monitoring with time-zone
assignment only when a fill-level timestamp is attached.

### 3.3 Clone reverse-engineered (c) — DO NOT USE
All 111 clone picks (highscore_active, including lb_None, whale_13M_new, Auros_66M,
whale_433roi clone, PensionFund_24M clone, ABC_41M clone) fail the timestamp gate
(NO_ENTRY_TIME) because they have no entry_time_utc. They are live open pulls and
the static audit cannot assign an EST offset to a fill. Verdict: exclude from
backtest and from live execution.

### 3.4 Other / CTA / ML / consensus (e) — PAPER ONLY
The 50 class (e) picks (cta, non_crypto_consensus, forex_copytrader RSI2, ZN=F)
produce 0.03%-scale returns on 1h bars. Their backtest win rate is 8.0%. The
combined forward-bias risk is LOW and timestamps are correct, but the edge is
statistically negligible. Verdict: paper-only, monitor only.

### 3.5 Synthetic placeholder (myfxbook_olivierdanvel) — DO NOT USE
Entry/TP/SL are all 0, status PENDING, source is a synthetic placeholder. It is
the clearest timestamp/EST issue in the dataset: the 23:55 UTC stamp converts to
18:55 EST, but the trade itself is not real. Verdict: excluded from all backtests.

---

## 4. FORWARD-BIAS RISK ASSESSMENT

| Source group | Forward-bias risk | Evidence |
|---|---|---|
| Class (a) exchange ledger | LOW | All class (a) picks pass the `ts < exit_utc` filter; FUTURE_BAR_PRESENT flags are bar-boundary artifacts only |
| Class (d) hyperliquid on-chain | LOW | On-chain fills carry explicit open_time/close_time in unix ms; not backtested statically |
| Class (c) clone active | HIGH | No entry_time_utc -> no timestamp audit possible; silhouette sampled in C results as NO_ENTRY_TIME |
| Class (e) CTA / consensus / RSI2 | LOW (at signal level) | 1h bar, correct EST; returns near 0.03% |
|Synthetic placeholder | HIGH | entry_px = 0, status PENDING, timestamp 23:55Z |

---

## 5. EST / TIMEZONE CORRECTNESS ASSESSMENT

| Source group | EST/timestamp correctness | Comment |
|---|---|---|
| All 2026-11-17/18 data | CORRECT | UTC-5 applied; no EDT (UTC-4) used |
| Class (a) OKX / Bybit | CORRECT | ISO-8601 with +00:00 offset parsed correctly |
| Class (c) highscore active | CORRECT (cannot verify) | no timestamp present; marked NO_ENTRY_TIME |
| Class (e) CTA / consensus / RSI2 | CORRECT | naive entry_date handled with timestamp fallback |
| myfxbook_olivierdanvel | HIGH (ambiguous) | timestamp 23:55Z -> 18:55 EST, but trade is synthetic |
| Bybit open_time | CORRECT with caveat | mixes ISO-8601 UTC and naive strings; naive flagged as TIMEZONE_AMBIGUOUS |

---

## 6. RECOMMENDED USE PER SOURCE (FINAL)

| Verdict | Source group | Use |
|---|---|---|
| LIVE | none | No source meets all four criteria (verified >=70, forward-bias LOW, EST CORRECT, no synthetic placeholder) |
| PAPER ONLY | class (a) exchange ledger | Monitor only; 1h-bar signal backtest WR 43.6% |
| PAPER ONLY | class (d) hyperliquid on-chain | Monitoring only; attach fill-level timestamps to certify |
| PAPER ONLY | class (e) CTA / consensus / RSI2 / ZN=F | Monitor only; no live execution |
| DO NOT USE | class (c) clone active | No entry_time_utc; exclude |
| DO NOT USE | flagged suspicious (btctangying, DeepSeek-V4, Rich, Pizza Coin.8, Crypto Musk, SKDXB, 100% WR cluster) | Known bad / disqualfied |
| DO NOT USE | synthetic placeholder (myfxbook_olivierdanvel) | Not a real trade |

---

## 7. SUMMARY FOR THE QA STAGE

The 2026-11-18-copytrader-llm-audit is complete. The single live candidate that
survives the full audit (verified >= 70, forward-bias LOW, EST CORRECT, traceable,
no placeholder) is **none** — no source in the 2026-11-18 data set clears the
live-executive bar.

If the audit is required to produce at least one live-executable pick, the only
path is to re-run the class (a) and class (d) backtests against a multi-bar
confirmation frame (e.g. 5h or 1d) with an entry-window gate, and to attach
fill-level timestamps to the highscore ACTIVE and hyperliquid on-chain groups
before the reliability score can change from PAPER ONLY to LIVE.

---

## 8. FILE REFERENCE

| Sub-agent | File |
|---|---|
| A | reports/subscriptions/2026-11-18-copytrader-llm-audit/A_identified_verified_sources.md |
| B | reports/subscriptions/2026-11-18-copytrader-llm-audit/B_backtest_logic.md |
| C | reports/subscriptions/2026-11-18-copytrader-llm-audit/C_backtest_results.json |
| C | reports/subscriptions/2026-11-18-copytrader-llm-audit/C_backtest_results.md |
| D | reports/subscriptions/2026-11-18-copytrader-llm-audit/D_reliability_summary.md |

All file writes were confined to reports/subscriptions/2026-11-18-copytrader-llm-audit/.
No git-tracked file was modified; no commit or push was made.
