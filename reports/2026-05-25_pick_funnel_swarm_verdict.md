# Pick Funnel Swarm Verdict — 2026-11-18 04:41 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261118T044131Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

**Bottom line up front:** The funnel is broken. `passed_high_conviction = 0` across **every** asset class means the HC gate (`score>=80, conf>=0.75, trust>=60`) is effectively dead code — nothing reaches the dashboard's "high conviction" tier. Meanwhile `opened` ≈ `scanned` in most classes (FOREX: 25,897 opened of 27,258 scanned = 95%), so the "Smart" gate is barely filtering. The only class with a defensible, holdout-passing, Bonferroni-passing edge is **CRYPTO**, and even that edge is thin (PF 1.6, not the 14x/135x monsters). The 135x and 14x PFs are **artifacts**, not edges — see below.

---

### CRYPTO
- **Real/noise verdict:** **Real but modest.** The PROVEN cell `trust=UNK & conf=C0.75-0.80 & score_dec=S50` has n=193, WR_shrunk=63.4%, PF=1.616, train_pf=1.234 / holdout_pf=2.525 (holdout_pass=true), wr_z=4.10, **bonferroni_pass=true**. This is the only cell in the entire report that survives multiple-testing correction with a holdout. It is a genuine, if small, edge. The `best_pf_overall` cells (PF 1.849) are the *same 182 trades* re-sliced three ways — they are not independent confirmations, and they fail Bonferroni. Do not double-count them. **No leakage flag** on the PROVEN cell, but note `trust=UNK` dominates — the trust dimension is not doing work; the edge is really "conf 0.75–0.80 + score_dec S50 + alpha_engine." Class-level WR is 44.8% (losing), so the edge is *concentrated*, not broad.
- **90d expected P&L (1% risk, $100k):** Apply edge only to the 193-trade PROVEN cell. At 1% risk ($1,000/trade), avg_pnl_pct=0.6358% of notional → but with 1% risk sizing and PF 1.616, expected net per trade ≈ +0.30% of $1,000 risk unit ≈ **+$3/trade** net of the modeled edge, ×193 ≈ **+$580**. If you instead size the full 2,206 closed trades at class WR 44.8%, you lose money. **Realistic estimate: +$400 to +$700** on the isolated cell; **negative** if you trade the class broadly. Slippage assumption: 5 bps round-trip on crypto (generous); fees 10 bps taker. At 1% risk the edge is real but tiny in dollars.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — raise from current (effectively ~50, since 3,853/11,969 = 32% pass) to **65**, and add a hard `conf >= 0.75` requirement in `production_scanner.py` for CRYPTO. This kills the 44.8%-WR bulk and keeps the 0.75–0.80 conf band that carries the edge.
- **Confidence (1-5):** **3** — real but thin; one holdout window only.

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE.** The PROVEN cell `rr=RR>=2.0 & fam=mean_reversion` shows WR 97.4%, **PF 135.9**, holdout_pf=99.0 on n=25. A PF of 135 with 97% WR is not a trading edge — it is a **data artifact**. Prime suspects: (1) `holdout_pf=99.0` is a sentinel/cap value, meaning zero losing trades in holdout — impossible for 25 real trades; (2) `avg_pnl_pct=1.5971` with RR>=2.0 and 97% WR implies the "loss" leg is never hit, i.e. **look-ahead in exit logic** (trade marked win before stop could trigger) or **survivorship** (only winners recorded). This is the same failure signature as **H-001 (COT look-ahead)** and **H-009/H-011 (killed equity options)**. Treat as **leakage recurrence**, not edge. Also note `opened=5,673` but `closed=105` — 98% of equity trades never close in the window, so the 105 closed are a non-random, likely cherry-picked subset.
- **90d expected P&L (1% risk, $100k):** **$0 — do not trade.** If you naively trusted the 135x PF you'd "expect" absurd returns; that is the tell. Realistic forward P&L on this cell is **unknown and probably negative** once leakage is fixed. Estimate **-$200 to +$100** (i.e., noise around zero) with honest fills.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — **raise to 75** (from ~50; 226/5,778 = 3.9% pass is already tight, but the closed sample is 105 — the gate isn't the problem, the **exit/close pipeline is**). The real fix is not a gate constant: **halt EQUITY promotion until `closed/scanned` ratio > 20%** and the 97%-WR cell is re-audited for exit look-ahead. If forced to name one constant: set `SMART_PICKS_MIN_SCORE_EQUITY = 75` and add `MIN_CLOSED_TRADES_FOR_PROMOTION = 200` in `quality_gates.py`.
- **Confidence (1-5):** **1** — almost certainly leakage.

---

### COMMODITY
- **Real/noise verdict:** **NOISE.** No PROVEN cells. Best PF 1.779 on n=29 with holdout_pf=1.389 but **wr_z=0.928** (not significant) and bonferroni_pass=false. The n=21 and n=20 cells fail holdout (0.72). Class WR 65.8% on only 38 closed trades — far too few to conclude anything. **H-001 (COT look-ahead) and H-036 (inventory gate) are both already killed** — do not re-derive. The `trust=UNK & dir=LONG & source=alpha_engine` cell is the same shape as the killed COT signal; flag as **potential leakage recurrence** if it ever passes holdout.
- **90d expected P&L (1% risk, $100k):** **$0.** n=38 closed is below any promotion threshold. If you traded the best cell (n=29, PF 1.78, avg 0.61%): 29 × $1,000 × 0.61% × (edge fraction ~0.3) ≈ **+$50**, within noise. Not tradeable.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — **raise to 80** (from ~65; 3,747/5,794 = 65% pass is far too loose). This is the single biggest funnel leak in the system: 65% of commodities pass "Smart."
- **Confidence (1-5):** **1** — no edge.

---

### FOREX
- **Real/noise verdict:** **NOISE / LEAKAGE.** The `conf=C>=0.90 & fam=regime` cell shows WR 89.5%, **PF 14.4**, but **holdout_n=2** and holdout_pf=99.0 (sentinel). n=38 with 34 wins and PF 14.4 means the loss leg is ~0.07% — physically implausible for FX. This is the **same signature as the killed H-035 (funding/settlement timing)** and the EQUITY leakage: a regime/terminal source with near-zero losses = **look-ahead in the regime label or exit**. `bonferroni_pass=true` is misleading because the test was run on a leaked series. Class WR 51.6% on 446 decisive trades is a coin flip — **no class-level edge**. Also: 26,607/27,258 = **97.6% of FOREX passes Smart** — the gate is not filtering at all.
- **90d expected P&L (1% risk, $100k):** **$0 — do not trade.** The 14x PF is fake. Honest forward estimate on 446 trades at 51.6% WR with 1% risk and ~1.2 R:R: **-$300 to +$300** (noise). The `regime_terminal` source should be quarantined.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — **raise to 70** (from ~50; 97.6% pass is the worst funnel in the system). Additionally **disable `regime_terminal` source** in `production_scanner.py` until the 89%-WR cell is re-audited for exit look-ahead.
- **Confidence (1-5):** **1** — leakage.

---

### INDEX
- **Real/noise verdict:** **NO EDGE / INSUFFICIENT DATA.** n_closed=1. 1,557/2,061 = 75.5% pass Smart, 2,060 opened, **1 closed**. The close pipeline is broken for INDEX — you cannot evaluate an edge on one trade. WR 100% on n=1 is meaningless.
- **90d expected P&L (1% risk, $100k):** **$0.** Untradeable — no closed sample.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — **raise to 75** (from ~50; 75.5% pass too loose), but the binding fix is **`MIN_CLOSED_TRADES_FOR_PROMOTION = 200`** — INDEX must not be promoted to the dashboard at all until it closes trades.
- **Confidence (1-5):** **1** — no data.

---

### BOND
- **Real/noise verdict:** **NO EDGE.** n_closed=31, WR 38.7%, PF implied <1. Only 1/1,162 passes Smart (0.09%) — the gate is *too tight* here, not too loose, but the 31 closed trades are a losing sample. No PROVEN cells.
- **90d expected P&L (1% risk, $100k):** **-$150 to -$250** (31 trades × 1% risk × ~-0.5% edge). Negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — **lower to 55** to actually let bond trades through (0.09% pass is starving the class), but **do not promote** until n_closed > 100. The class is under-sampled, not over-gated.
- **Confidence (1-5):** **2** — small losing sample, but directionally clear.

---

### ETF
- **Real/noise verdict:** **NO EDGE.** n_closed=8, WR 12.5% (1 win, 7 losses). 271/309 = 87.7% pass Smart — gate is wide open, results are terrible. No PROVEN cells.
- **90d expected P&L (1% risk, $100k):** **-$400 to -$600** (8 trades, 1% risk, ~-6% avg edge). Negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — **raise to 80** (from ~50; 87.7% pass is indefensible given 12.5% WR). This is the single most urgent gate fix in the system.
- **Confidence (1-5):** **2** — tiny sample but WR is so bad it's directionally real.

---

### FUTURES
- **Real/noise verdict:** **NO EDGE.** n_closed=16, WR 37.5%. 116/163 = 71% pass Smart. No PROVEN cells. **H-005 (futures momentum anti-signal) already killed** — do not re-derive.
- **90d expected P&L (1% risk, $100k):** **-$200 to -$300** (16 trades, 1% risk, ~-1.5% edge). Negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — **raise to 75** (from ~50; 71% pass too loose).
- **Confidence (1-5):** **2** — small sample, negative.

---

### UNKNOWN
- **Real/noise verdict:** **NO EDGE / DATA HYGIENE FAILURE.** n_closed=4, WR 0%. 1,245 opened, 4 closed. 110/1,249 pass Smart. The existence of an "UNKNOWN" class with 1,249 scanned is a **classification bug** — these should be routed or dropped, not traded.
- **90d expected P&L (1% risk, $100k):** **$0.** Do not trade unclassified assets.
- **Gate change:** Not a score constant — **add a hard `asset_class != UNKNOWN` filter** in `production_scanner.py` before Smart scoring. Route to a `quarantine` bucket.
- **Confidence (1-5):** **1** — data bug.

---

### MEME
- **Real/noise verdict:** **NO EDGE / INSUFFICIENT DATA.** n_closed=6, WR 33.3%. 7/19 pass Smart. No PROVEN cells. Too few trades.
- **90d expected P&L (1% risk, $100k):** **-$100 to -$150** (6 trades, 1% risk, ~-2% edge). Negative.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — **raise to 80** (from ~50; 37% pass on a 33% WR class is too loose). Or **disable MEME entirely** until n_closed > 100.
- **Confidence (1-5):** **2** — tiny sample, negative.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only CRYPTO, and only the narrow cell.**
The `trust=UNK & conf=C0.75-0.80 & score_dec=S50` cell is the **only** signal in the entire 90-day report that passes holdout **and** Bonferroni with a plausible PF (1.6). Size it at 0.5% risk (not 1%) until a second holdout window confirms, cap at ~$50k notional, and route only `alpha_engine` source. Expected 90d P&L: **+$400 to +$700** — small, but real. Do **not** trade the class broadly (44.8% WR loses money).

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**
1. **FOREX** — 97.6% Smart pass rate, 51.6% WR, and a 14x-PF cell with holdout_n=2 that is almost certainly leakage. **Mutate:** raise `SMART_PICKS_MIN_SCORE_FOREX` to 70, quarantine `regime_terminal` source, re-audit exit logic. If next 90d still <52% WR, kill.
2. **EQUITY** — 135x PF with 97% WR and holdout_pf=99.0 sentinel is a **leakage recurrence** (same signature as H-001/H-009/H-011). **Mutate:** halt promotion, audit exit/close pipeline for look-ahead, require `closed/scanned > 20%` before re-promotion. Do not kill yet — the mean_reversion family may be salvageable once leakage is removed.
3. **ETF** — 12.5% WR on 8 trades with 87.7% Smart pass. **Mutate:** raise `SMART_PICKS_MIN_SCORE_ETF` to 80 immediately; if next 30 trades still <40% WR, kill.

**Do not scale:** COMMODITY (no edge, H-001/H-036 already killed), INDEX (n=1), BOND (losing, under-sampled), FUTURES (H-005 killed), UNKNOWN (data bug), MEME (n=6).

**The single most important system fix is not a gate constant — it's the `passed_high_conviction = 0` across all classes.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is unreachable because `trust>=60` is never satisfied (every PROVEN cell is `trust=UNK`). Either the trust score is miscalibrated or the HC threshold is wrong. **Fix `hc_filter.js` trust threshold from 60 → 0 (or recalibrate trust scoring) before any further edge work** — otherwise the dashboard's "high conviction" tier is permanently empty and the funnel is cosmetic.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: noise — 97% WR / PF 135 on n=38 is statistically impossible without leakage or single-symbol concentration; train/holdout split still shows extreme values.
- 90d expected P&L (1% risk, $100k): $0 (edge is artifact, not tradable).
- Gate change: none (disable mean_reversion path until root cause fixed).
- Confidence (1-5): 1

### INDEX
- Real/noise verdict: noise — n_closed=1, no proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: none.
- Confidence (1-5): 1

### COMMODITY
- Real/noise verdict: noise — no proven cells; best_pf cells fail holdout or have n<30 with bonferroni=false.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: none.
- Confidence (1-5): 1

### FOREX
- Real/noise verdict: noise — PF 14.4 on n=38 driven by holdout_n=2; regime_terminal cells flagged as potential leakage recurrence.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: none.
- Confidence (1-5): 1

### CRYPTO
- Real/noise verdict: real — single proven cell (trust=UNK & conf=C0.75-0.80 & score_dec=S50) has n=193, WR_shrunk=63.38, PF=1.616, holdout_pass=true, bonferroni_pass=true; no obvious leakage.
- 90d expected P&L (1% risk, $100k): ~$2,850 (193 trades × 1% risk × 0.6358% avg_pnl, 0.2% slippage, 0.1% commission).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 50.
- Confidence (1-5): 4

### BOND
- Real/noise verdict: noise — n_closed=31, no proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: none.
- Confidence (1-5): 1

### ETF
- Real/noise verdict: noise — n_closed=8, no proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: none.
- Confidence (1-5): 1

### FUTURES
- Real/noise verdict: noise — n_closed=16, no proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: none.
- Confidence (1-5): 1

### UNKNOWN
- Real/noise verdict: noise — n_closed=4, no proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: none.
- Confidence (1-5): 1

### MEME
- Real/noise verdict: noise — n_closed=6, no proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: none.
- Confidence (1-5): 1

**SYSTEM-WIDE conclusion:** Scale CRYPTO today (only class with statistically credible edge). Demote EQUITY and FOREX per MUTATION_THREE_AXIS_PROTOCOL.md (mutate the mean_reversion and regime_terminal paths before any further capital allocation). All other classes have zero actionable edge.
