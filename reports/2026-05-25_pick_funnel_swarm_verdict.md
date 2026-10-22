# Pick Funnel Swarm Verdict — 2026-10-22 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261022T040955Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

Before per-class verdicts, three structural facts dominate everything below:

1. **`passed_high_conviction = 0` across every single asset class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is *never* satisfied. Either the scoring scale never reaches 80, or `trust>=60` is unreachable (note: every "proven" cell in CRYPTO and EQUITY is `trust=UNK`). This is a dead gate — it is not filtering, it is silently rejecting 100% of flow. That alone is the biggest finding in this dataset.
2. **`opened` >> `passed_smart` in most classes** (EQUITY 5645 opened vs 221 smart; FOREX 23390 vs 23837; BOND 528 opened vs 0 smart). The funnel is not actually gating — the "opened" count is essentially the raw scan count. The gates are decorative.
3. **Closed counts are tiny relative to opened** (EQUITY 135/5645 = 2.4%; INDEX 5/1764 = 0.3%; COMMODITY 63/5831 = 1.1%). Most "edges" are computed on a 1–3% sample of what was actually opened. Survivorship and selection bias are baked in.

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE.** The `fam=mean_reversion & score_dec=S40` cell shows WR=98.44% (63/64), PF=235, holdout PF=99. A PF of 235 is not a trading edge — it is a data artifact. Three red flags: (i) `trust=UNK` on 100% of the cell, (ii) `conf=C<0.60` — the *lowest* confidence bucket producing the *highest* WR, which inverts the entire premise of the scoring model, (iii) n=64 with 63 wins means the loss side of the PF denominator is essentially one trade. This is almost certainly a **stop/target bookkeeping bug** (e.g., mean-reversion exits booked as wins on touch of entry, or PnL sign error on a single symbol). It also matches the pattern of H-001 (single-symbol concentration + timestamp leakage). Do not trade this. The 70.37% headline WR on 135 closed is also suspect given the opened/closed ratio.
- **90d expected P&L (1% risk, $100k):** **$0 — do not deploy.** If forced to model the *headline* 70.37% WR at 1% risk with 1.5:1 avg R:R and 135 trades: 0.7037×1.5R − 0.2963×1R = +0.759R/trade × 135 × $1,000 = **~$102k gross**, minus ~15 bps slippage × 135 × $100k = ~$20k → **~$82k net**. But this number is fiction because the underlying cell is broken. Report it only to show how misleading the headline is.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — currently the funnel passes 221/5780 (3.8%) but opens 5645. The gate is not binding. Set `SMART_PICKS_MIN_SCORE_EQUITY = 55` **and** add a hard `trust != UNK` requirement in `quality_gates.py` (new constant `REQUIRE_TRUST_KNOWN = True`). The mean_reversion/S40 cell must be quarantined pending a PnL-sign audit.
- **Confidence (1-5):** **1**

### INDEX
- **Real/noise verdict:** **NO EDGE — insufficient sample.** 5 closed trades, 1 win, 20% WR. `passed_smart=1430` but `opened=1764` and only 5 closed. This class is not measurable. Any "edge" claim here is noise by definition (n<20). The 1430 smart passes on 1769 scans (81%) means the gate is essentially open.
- **90d expected P&L (1% risk, $100k):** **$0 — no basis.** At 20% WR and unknown R:R, expected value is negative. Do not deploy.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **65** to cut the 81% pass rate, and more importantly fix the *exit* pipeline: 1764 opened / 5 closed means positions are not being closed/resolved. This is an operational bug, not a gate bug. Flag `INDEX_CLOSE_STALE_DAYS = 5`.
- **Confidence (1-5):** **1**

### COMMODITY
- **Real/noise verdict:** **WEAK / NOT PROVEN.** Best cell `rr=RR>=2.0 & source=alpha_engine` has n=20, WR=70%, shrunk WR=60%, PF=4.125, **but `bonferroni_pass=false`** and `wr_z=1.789` (below the ~2.5 threshold for multiple-testing survival). Holdout PF 2.612 on n=10 is encouraging but n=10 is not a holdout, it's a coin flip. Given H-001 (COT leakage, 85% cotton concentration) and H-036 (inventory gate rejected), this class has a documented history of leakage. The `trust=UNK` on the top cell is another warning. Treat as **unproven, watchlist only.**
- **90d expected P&L (1% risk, $100k):** At 60% shrunk WR, 2:1 R:R, 20 trades: 0.60×2R − 0.40×1R = +0.80R/trade × 20 × $1,000 = **$16k gross**, minus slippage (~$3k) → **~$13k net**. But n=20 and bonferroni-fail means the confidence interval spans zero. **Expected value ≈ $0 with high variance.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — currently 3715/5894 = 63% pass. Raise to **70** and add `MIN_RR_COMMODITY = 2.0` as a hard floor (the only cell that even approaches significance is the RR>=2.0 bucket). Also enforce `REQUIRE_TRUST_KNOWN`.
- **Confidence (1-5):** **2**

### FOREX
- **Real/noise verdict:** **NOISE — and the "best" cell is a textbook leakage recurrence.** `conf=C>=0.90 & dir=LONG & source=regime_terminal` shows WR=85.71%, PF=8.885, **but `train_pf=0.0` on train_n=4 and `holdout_pass=false`.** A train PF of 0.0 means the training window had *zero* winning trades — the entire "edge" lives in the 24-trade holdout. That is the definition of overfitting to a holdout. `wr_z=3.779` looks strong but with train_n=4 the z-score is meaningless. This is exactly the H-001/H-035 pattern: a regime/terminal source producing a suspiciously clean holdout. **Do not trade.** The class-wide 42.15% WR on 1301 closed is the honest number, and it's a losing class.
- **90d expected P&L (1% risk, $100k):** At the *honest* 42.15% WR and unknown R:R (assume 1:1): 0.4215×1R − 0.5785×1R = **−0.157R/trade × 1301 × $1,000 = −$204k gross**, minus slippage (~$195k at 15bps × 1301 × $100k) → **~−$400k.** This class is a money incinerator at current sizing. The "best cell" P&L if you believed it: 0.857×1R × 28 × $1,000 = +$24k — but it's fake.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — currently 23837/24691 = **96.5% pass rate**. The gate is not a gate. Set to **75** (cut to roughly the top decile) and add `FOREX_MAX_OPEN_PER_DAY = 50` to stop the 23k-opens firehose. Also kill `source=regime_terminal` from the scanner until it passes a proper walk-forward (it currently fails holdout).
- **Confidence (1-5):** **1**

### CRYPTO
- **Real/noise verdict:** **PLAUSIBLY REAL — the only class with a defensible edge.** The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell: n=183, WR=79.23%, shrunk WR=76.35%, PF=4.706, **train PF 5.707 (n=105) / holdout PF 3.534 (n=78), holdout_pass=true, wr_z=7.908, bonferroni_pass=true.** This is the only cell in the entire dataset that survives multiple-testing correction *and* has a real train/holdout split with consistent PF. Caveats: (i) `trust=UNK` on the cell — the trust dimension is not adding information, (ii) the cell is defined by `score_dec=S50` which is a *decile* bucket, so it's a narrow slice (183/2440 = 7.5% of closed), (iii) avg_pnl 1.64% per trade is modest, (iv) the three "proven" cells are the *same 183 trades* re-sliced three ways — not three independent edges. Still: this is the one signal I'd put money behind, at reduced size, with a live-vs-backtest monitor.
- **90d expected P&L (1% risk, $100k):** Using shrunk WR 76.35%, PF 4.706 implies avg win/avg loss ≈ 4.706 × (1−0.7635)/0.7635 ≈ 1.46:1. Per trade: 0.7635×1.46R − 0.2365×1R = +0.878R. At 1% risk ($1,000/trade) × 183 trades = **+$160.7k gross**. Slippage: crypto ~25 bps round-trip × 183 × $100k = ~$45.8k. **Net ≈ +$115k** on the proven cell alone. If you scale to the full 2440 closed at the class-wide 45.2% WR, you lose money — so **size only the proven cell**, not the class.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — currently 3599/13066 = 27.5% pass. The proven cell lives at `conf 0.75-0.80 & score_dec=S50`. Add a **new** constant `CRYPTO_PROVEN_CELL_ONLY = True` that restricts live sizing to `source=alpha_engine & conf in [0.75,0.80] & score_dec==S50`, and set `SMART_PICKS_MIN_SCORE_CRYPTO = 60` for the broader funnel. Also fix the HC gate (see system-wide).
- **Confidence (1-5):** **4**

### ETF
- **Real/noise verdict:** **NO EDGE — n=9.** 2 wins, 7 losses, 22% WR. Not measurable. `passed_smart=304/356` = 85% pass — gate is open.
- **90d expected P&L (1% risk, $100k):** **$0 — negative EV.** At 22% WR, 1:1: −0.56R/trade × 9 × $1,000 = **−$5k** (and that's generous).
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **70** (from effectively 0). Also `ETF_MIN_CLOSED_FOR_SIZING = 30` — do not size this class until it has 30 closed trades.
- **Confidence (1-5):** **1**

### UNKNOWN
- **Real/noise verdict:** **NO EDGE — n=3, 0 wins.** This is a data-quality bucket, not an asset class. 1404 scanned, 152 smart, 1401 opened, 3 closed, 0 wins. The fact that 1401 "UNKNOWN" positions were opened is a **classification bug** — these should never reach the scanner. This is the single most alarming operational finding after the dead HC gate.
- **90d expected P&L (1% risk, $100k):** **$0 — do not trade.** 0/3 wins.
- **Gate change:** Add `REJECT_UNKNOWN_ASSET_CLASS = True` in `quality_gates.py` — hard-reject at scan time. This alone removes 1401 phantom opens.
- **Confidence (1-5):** **1**

### FUTURES
- **Real/noise verdict:** **NO EDGE — n=16.** 7W/9L, 43.75% WR. `best_pf_overall=[]` (empty). H-005 already killed the momentum inversion. Not measurable.
- **90d expected P&L (1% risk, $100k):** **$0 — negative EV.** 0.4375×1R − 0.5625×1R = −0.125R × 16 × $1,000 = **−$2k**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **70**; add `FUTURES_MIN_CLOSED_FOR_SIZING = 30`.
- **Confidence (1-5):** **1**

### BOND
- **Real/noise verdict:** **NO EDGE — and the gate is fully open.** `passed_smart=0` but `opened=528`. The smart gate rejects 100% of bonds, yet 528 were opened anyway. 13W/20L, 39.39% WR. This class should not be in the funnel at all until the gate is wired correctly.
- **90d expected P&L (1% risk, $100k):** **$0 — negative EV.** 0.3939×1R − 0.6061×1R = −0.212R × 33 × $1,000 = **−$7k**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — the fact that 0 pass but 528 open means the gate is bypassed. Set `BOND_ENABLED = False` in `quality_gates.py` until the bypass is fixed and n>=30 closed is achieved.
- **Confidence (1-5):** **1**

### MEME
- **Real/noise verdict:** **NO EDGE — n=7.** 1W/6L, 14.29% WR. Not measurable. `passed_verified_alpha=2` on 29 scanned is noise.
- **90d expected P&L (1% risk, $100k):** **$0 — strongly negative EV.** 0.1429×1R − 0.8571×1R = −0.714R × 7 × $1,000 = **−$5k**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to **75**; add `MEME_MIN_CLOSED_FOR_SIZING = 30`. Given the 14% WR, consider `MEME_ENABLED = False` per the mutation protocol.
- **Confidence (1-5):** **1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only the proven cell.**
The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell is the *only* signal in this entire 90-day dataset that survives Bonferroni correction, has a real train/holdout split with consistent PF (5.7 → 3.5), and has n=183. Expected net P&L on that cell alone at 1% risk is **~+$115k over 90d** after slippage. Size it at **0.5% risk per trade** (not 1%) for the first 30 live trades as a live-vs-backtest monitor, then step to 1% if live WR stays within 5pp of the 76.35% shrunk estimate. Do **not** size the broader CRYPTO class (45.2% WR on 2440 closed is a loser) — the edge is in the cell, not the class.

**Demote per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill): FOREX.**
FOREX is the worst offender on every axis: 96.5% smart-pass rate (gate is open), 23,390 opens, 42.15% WR on 1301 closed (honest losing class), and its "best" cell has `train_pf=0.0` / `holdout_pass=false` — a textbook leakage recurrence matching H-001/H-035. Mutate first: (1) raise `SMART_PICKS_MIN_SCORE_FOREX` to 75, (2) kill `source=regime_terminal` from the scanner, (3) cap `FOREX_MAX_OPEN_PER_DAY=50`. If after 30 days the class-wide WR is still <48% on n>=200, kill it. Do not skip the mutation step — the protocol exists precisely because FOREX has produced fake edges before.



### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Noise — n=183 is decent but PF=4.7 and WR_shrunk=76% on alpha_engine cells are implausibly high; likely single-symbol concentration or leakage (similar to rejected H-035 patterns). Holdout still strong but suspicious.
- 90d expected P&L (1% risk, $100k): $0 (edge not trusted; slippage + overfit would erase gains).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 65
- Confidence (1-5): 2

### EQUITY
- Real/noise verdict: Noise — 98% WR and PF=235 on mean_reversion S40 cells with n=64 screams data leakage or single-name concentration; impossible in live trading.
- 90d expected P&L (1% risk, $100k): $0 (edge is artifact).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 70
- Confidence (1-5): 1

### FOREX
- Real/noise verdict: Noise — top cells have holdout_pass=false, tiny train_n=4, and PF inflated by small sample; no proven edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: HC_MIN_CONF = 0.85
- Confidence (1-5): 1

### COMMODITY
- Real/noise verdict: Noise — n=20 borderline, bonferroni_pass=false, PF=4.1 not stable; matches rejected inventory/COT leakage patterns.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_COMMODITY = 75
- Confidence (1-5): 1

### FUTURES
- Real/noise verdict: Noise — n_closed=16 too small for any conclusion; no proven edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_FUTURES = 80
- Confidence (1-5): 1

### BOND
- Real/noise verdict: Noise — n=33, no proven edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_BOND = 80
- Confidence (1-5): 1

### ETF
- Real/noise verdict: Noise — n=9, no edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_ETF = 80
- Confidence (1-5): 1

### INDEX
- Real/noise verdict: Noise — n=5, no edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_INDEX = 80
- Confidence (1-5): 1

### UNKNOWN
- Real/noise verdict: Noise — n=3, no edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 1

### MEME
- Real/noise verdict: Noise — n=7, no edges.
- 90d expected P&L (1% risk, $100k): $0
- Gate change: SMART_PICKS_MIN_SCORE_MEME = 80
- Confidence (1-5): 1

**SYSTEM-WIDE CONCLUSION**  
Scale up TODAY: none (zero classes have trustworthy edges after scrutiny).  
Demote per MUTATION_THREE_AXIS_PROTOCOL.md: EQUITY and CRYPTO (highest leakage risk and inflated metrics); tighten all SMART_PICKS_MIN_SCORE_* first.
