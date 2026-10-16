# Pick Funnel Swarm Verdict — 2026-10-16 04:10 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261016T041013Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day edge analysis

Before the per-class verdicts, three system-wide observations that color everything below:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is firing on **zero** picks across 90 days and ~53k scans. Either the gate is mis-wired, the trust field is never populated above 60, or the score distribution never reaches 80. This is the single biggest finding in the dataset — the "HIGH CONVICTION" funnel stage is dead code in production.
2. **`passed_verified_alpha` is 0 for EQUITY, INDEX, FOREX, COMMODITY, ETF, BOND, UNKNOWN.** Only CRYPTO (1960) and a trickle of MEME/FUTURES (1 each) pass. The verified-alpha stage is effectively a CRYPTO-only gate.
3. **`opened` >> `passed_smart` in most classes** (EQUITY: 5594 opened vs 209 smart; FOREX: 22654 vs 23075 — ok; BOND: 545 vs 2). This means the "opened" counter is not downstream of the smart gate. The funnel is not a funnel — it's two parallel pipelines. Any P&L attribution from "opened" trades is not attributable to the smart gate.

---

### EQUITY
- **Real/noise verdict:** The three "PROVEN" cells are **the same 66 trades** sliced three ways (`trust=UNK & fam=mean_reversion & score_dec=S40` ≡ `conf=C<0.60 & fam=mean_reversion & score_dec=S40` ≡ `fam=mean_reversion & dir=LONG & score_dec=S40`). n=66, WR=98.48%, PF=231. This is not an edge — it is a **leakage signature**. A 98% WR with PF=231 on mean-reversion LONGs is the classic fingerprint of (a) look-ahead in the entry price, (b) exit-at-close-of-signal-bar, or (c) a single-symbol / single-day cluster. The fact that all three "independent" cells collapse to the same 66 trades means the edge-discovery code is not deduplicating overlapping cells — Bonferroni is being applied to a set of correlated hypotheses, so `bonferroni_pass=true` is meaningless here. The holdout (n=24, PF=99) is too small to falsify. **Treat as leakage until proven otherwise.** Also note: `passed_smart=209` but `opened=5594` — the smart gate is filtering 96% of equity picks, yet the "edge" lives in the 209 that passed. That's a 66/209 = 32% concentration in one cell, which is itself a red flag for overfitting the gate to a historical cluster.
- **90d expected P&L (1% risk, $100k):** **$0.** Do not size this. If forced to mark-to-model the cell as-is: 66 trades × 1% × $100k = $66k risked; at PF=231 the model says ~$1.4M profit — which is exactly why you should not believe it. A realistic post-leakage-fix estimate for equity mean-reversion LONG at S40 is WR~52-55%, PF~1.1-1.3, i.e. **$3k–$8k** over 90d, well inside noise.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — currently the smart gate passes only 209/5734 (3.6%). The edge (if real) lives at `score_dec=S40`, i.e. **low** score decile. The gate is likely inverted or the score is not monotonic with edge. Set `SMART_PICKS_MIN_SCORE_EQUITY` to the **S40 boundary value** (whatever score maps to decile 40) rather than a high floor, and add a hard `dedupe_cells=True` in the edge-discovery pass so overlapping cells don't triple-count.
- **Confidence (1-5):** 1

### INDEX
- **Real/noise verdict:** n_closed=5. **No edge. Full stop.** `passed_smart=1598/1941` (82%) but only 5 closed — the class is essentially un-exercised. WR=20% on n=5 is noise. Do not derive anything.
- **90d expected P&L (1% risk, $100k):** **$0** (insufficient sample; any number is fiction).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise it hard. 82% pass rate on a class with 5 closed trades means the gate is not filtering. Set to the 90th percentile of observed index scores so the class stops emitting unvalidated picks.
- **Confidence (1-5):** 1

### FOREX
- **Real/noise verdict:** `top_edges_proven = []`. The best cell (`trust=UNK & fam=regime & dir=LONG`, n=31, WR=77.4%, PF=4.08) **fails holdout** (`holdout_pass=false`, train_n=5, train_pf=0.0). This is the textbook "train on 5, test on 26" overfit — the train set is too small to have a PF at all, and the holdout is the same regime window. `bonferroni_pass=false`. **No proven edge.** The class-level WR=42.3% on n=527 decisive is a **losing** class (needs ~52%+ at 1:1 R:R to break even after costs). The `consensus` cell you flagged isn't in the top-3 here, but the `regime_terminal` source is — and it's the same 31 trades sliced three ways, same leakage pattern as EQUITY.
- **90d expected P&L (1% risk, $100k):** Negative. 527 decisive trades × 1% × $100k = $527k risked; at WR=42.3% with typical 1:1 R:R and ~1.5 pip spread cost on majors, expect **–$15k to –$40k** over 90d. This class is a net drag.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — currently passes 23075/23982 = **96.2%**. The gate is doing nothing. Raise to the 70th percentile of forex scores (roughly the value that would cut pass rate to ~30%), and add a `MIN_DECISIVE_N=50` requirement before any forex cell is allowed to be labeled "proven."
- **Confidence (1-5):** 2 (confident it's noise; less confident on exact P&L magnitude)

### CRYPTO
- **Real/noise verdict:** This is the **only class with a defensible edge**, and even here the top cell is suspicious. `conf=C0.75-0.80 & dir=LONG & score_dec=S50`: n=177, WR=72.3%, shrunk WR=70.1%, PF=3.25, train PF=3.34 (n=117), holdout PF=3.03 (n=60), `holdout_pass=true`, `bonferroni_pass=true`, `wr_z=5.94`. That is a **real, out-of-sample-confirmed** signal — the train/holdout PF ratio (3.34 → 3.03) is the hallmark of a stable edge, not an overfit one. The second cell is the same 177 trades with `trust=UNK` prepended (again, correlated-cell double-counting — the dedup bug is systemic). The third cell (`source=alpha_engine`, n=247, PF=2.29, holdout PF=1.53) is a **different, weaker** signal — holdout PF dropped 46% from train, which is the edge decaying but still positive. **Caveat:** you flagged the `ml` cells as suspiciously high — they're not in the top-3 shown, but if any `ml`-sourced cell shows PF>5 with n<100, treat it as leakage (feature computed post-entry). The `alpha_engine` cell at PF=2.29 is the one I'd actually trade.
- **90d expected P&L (1% risk, $100k):** Using the `conf=C0.75-0.80 & dir=LONG & score_dec=S50` cell: 177 trades × 1% × $100k = $177k risked. At PF=3.25, gross profit ≈ $177k × (3.25/(3.25+1)) × 2 ≈ **$270k gross**, minus ~0.15% round-trip slippage+fees on $17.7M notional ≈ $26k costs, minus funding on 90d holds. **Net ≈ $180k–$220k.** Using the more conservative `alpha_engine` cell (PF=2.29, n=247): 247 × 1% × $100k = $247k risked, net ≈ **$120k–$150k**. I'd underwrite to the lower number.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — currently passes 3586/13162 = 27%. The edge lives at `score_dec=S50` (mid-decile) and `conf=0.75-0.80` (a **narrow** band). The gate should be a **band**, not a floor: `SMART_PICKS_MIN_SCORE_CRYPTO = S50_lower_bound` AND `SMART_PICKS_MAX_SCORE_CRYPTO = S50_upper_bound`, plus `SMART_PICKS_CONF_BAND_CRYPTO = (0.75, 0.80)`. The current floor-only gate is letting in S90 picks that have no edge and excluding the S50 band that does.
- **Confidence (1-5):** 4

### COMMODITY
- **Real/noise verdict:** `top_edges_proven = []`. Best cell (`trust=UNK & rr=RR>=2.0 & source=alpha_engine`, n=21, WR=76.2%, PF=5.73) has `bonferroni_pass=false` and n=21 — below your own n>=20 threshold's spirit. Train n=11, holdout n=10; a 10-trade holdout cannot confirm anything. **No proven edge.** Note the rejected hypothesis H-001 (COT look-ahead) and H-036 (inventory direction) both live in this class — the class has a documented history of leakage. Treat any new commodity "edge" with extreme suspicion.
- **90d expected P&L (1% risk, $100k):** Class-level WR=58.8% on n=68 decisive. At 1:1 R:R and ~0.1% commodity spread, expect roughly **+$2k to +$6k** over 90d — inside noise, not a business.
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — passes 3653/6007 = 61%. Raise to cut pass rate to ~25%, and add `MIN_HOLDOUT_N=30` before any commodity cell can be labeled proven (the current n=10 holdout is the failure mode).
- **Confidence (1-5):** 2

### MEME
- **Real/noise verdict:** n_closed=6. **No edge.** WR=16.7% on n=6 is noise. The class is too small to evaluate and should not be in the funnel at all.
- **90d expected P&L (1% risk, $100k):** **$0** (do not trade).
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — set to a value that passes **zero** picks until n_closed>=50. Effectively disable the class.
- **Confidence (1-5):** 1

### ETF
- **Real/noise verdict:** n_closed=9. **No edge.** WR=22.2% on n=9. Same as INDEX/MEME.
- **90d expected P&L (1% risk, $100k):** **$0**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to disable until n_closed>=50.
- **Confidence (1-5):** 1

### UNKNOWN
- **Real/noise verdict:** n_closed=3, WR=0%. **No edge, and a data-quality bug.** 1427 scans landing in UNKNOWN means the asset-class classifier is failing on ~2.7% of the universe. Fix the classifier before evaluating.
- **90d expected P&L (1% risk, $100k):** **$0**.
- **Gate change:** Not a gate — fix the classifier in `production_scanner.py` so UNKNOWN routes to the correct class. Until then, `SMART_PICKS_MIN_SCORE_UNKNOWN = infinity` (block).
- **Confidence (1-5):** 1

### FUTURES
- **Real/noise verdict:** n_closed=13. **No edge.** WR=38.5% on n=13. Rejected hypothesis H-005 (futures momentum anti-signal) lives here — the class has a documented failure. Do not re-derive.
- **90d expected P&L (1% risk, $100k):** **$0**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to disable until n_closed>=50.
- **Confidence (1-5):** 1

### BOND
- **Real/noise verdict:** n_closed=33, WR=39.4%. **No edge.** `passed_smart=2/578` — the smart gate is essentially blocking the entire class, which is correct given the WR. `best_pf_overall=[]` — no cell even qualifies for ranking.
- **90d expected P&L (1% risk, $100k):** Negative. 33 trades × 1% × $100k = $33k risked; at WR=39.4% expect **–$3k to –$6k**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — keep at current (effectively blocking). No change needed; the gate is already correct.
- **Confidence (1-5):** 3 (confident it's a loser)

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO only.** Specifically the `conf=C0.75-0.80 & dir=LONG & score_dec=S50` cell (n=177, holdout PF=3.03, bonferroni_pass=true) and the broader `source=alpha_engine` cell (n=247, holdout PF=1.53). Size at 0.5% risk per trade for the first 30 days to validate live slippage against the backtest, then step to 1%. Expected 90d P&L at 1% risk: **$120k–$220k**. This is the only class where the holdout confirms the train.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill): FOREX.** It is the largest class by scan volume (23982) and the largest by opened trades (22654), yet it has **zero** proven cells, a class-level WR of 42.3% (a loser), and a smart gate that passes 96% of picks — i.e. the gate is not a gate. Mutate the three axes before killing: (1) **score axis** — replace the floor with a band around the 30th-50th percentile; (2) **trust axis** — require `trust != UNK` (currently the only "best" cell is `trust=UNK`, which is a data-quality smell); (3) **source axis** — drop `regime_terminal` (its train_n=5 is not a train set). If after mutation the class still shows WR<48% on n>=200 decisive, kill it.

**Secondary demotions (mutate, then kill if no improvement):** EQUITY (leakage-suspect, gate passes 3.6% but the "edge" is a 66-trade cluster), COMMODITY (rejected-hypothesis graveyard, n=21 best cell), BOND (already correctly blocked).

**Do not trade:** INDEX, MEME, ETF, FUTURES, UNKNOWN — all have n_closed < 15 and no statistical basis.

**Two bugs to fix before the next audit, regardless of class:**
1. **`passed_high_conviction = 0` everywhere.** The HC gate is dead. Either `hc_filter.js` is not being invoked server-side, or `trust` is never >=60, or `score` never reaches 80. This is the highest-leverage fix in the entire system — you have a "HIGH CONVICTION" funnel stage that has never fired in 90 days.
2. **Correlated-cell double-counting in edge discovery.** Every "top 3" list contains the same trades sliced by different dimension prefixes (EQUITY: 3 cells = 1 trade set; FOREX: 3 cells = 1 trade set; CRYPTO: 2 of 3 cells = 1 trade set). Bonferroni is being applied to non-independent hypotheses, so `bonferroni_pass=true` is not a real multiple-testing correction. Add a dedup step keyed on the trade-ID set before ranking cells.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### EQUITY
- Real/noise verdict: noise (leakage); n=66 with 98.5% WR and PF=231 is statistically impossible without single-symbol concentration or look-ahead bias; shrunk WR still unrealistically high.
- 90d expected P&L (1% risk, $100k): $0 (edge invalid; do not trade).
- Gate change: SMART_PICKS_MIN_SCORE_EQUITY = 85
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: noise; n=5 closed, zero proven cells, WR=20%.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: none (no edge exists)
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: noise; top cells fail holdout and Bonferroni; n=31 too small for claimed PF=4.077; no proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: HC_MIN_CONF = 0.82
- Confidence (1-5): 4

### CRYPTO
- Real/noise verdict: real but modest; n=177 cell has credible shrunk WR=70%, PF=3.25, holdout pass, and Bonferroni pass; volume supports it.
- 90d expected P&L (1% risk, $100k): $12400 (177 trades × ~1.36% avg edge after 0.15% slippage, 1% risk sizing).
- Gate change: SMART_PICKS_MIN_SCORE_CRYPTO = 72
- Confidence (1-5): 4

### COMMODITY
- Real/noise verdict: noise; n=21 cells fail Bonferroni; no proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: none (no edge exists)
- Confidence (1-5): 5

### MEME
- Real/noise verdict: noise; n=6 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: none (no edge exists)
- Confidence (1-5): 5

### ETF
- Real/noise verdict: noise; n=9 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: none (no edge exists)
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: noise; n=3 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: none (no edge exists)
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: noise; n=13 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: none (no edge exists)
- Confidence (1-5): 5

### BOND
- Real/noise verdict: noise; n=33 closed, zero proven cells.
- 90d expected P&L (1% risk, $100k): $0.
- Gate change: none (no edge exists)
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale CRYPTO today (only class with volume + statistically validated edge). Demote EQUITY per MUTATION_THREE_AXIS_PROTOCOL.md (mutate the mean_reversion S40 path immediately; the metrics indicate leakage recurrence). All other classes have no actionable edge.
