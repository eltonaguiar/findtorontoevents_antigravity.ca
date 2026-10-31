# Pick Funnel Swarm Verdict — 2026-10-31 04:06 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261031T040619Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

**Bottom line up front:** The funnel is broken in two directions. (1) The "PROVEN" cells are almost certainly artifacts — the EQUITY `mean_reversion` cell at PF=175 and the CRYPTO `alpha_engine` cell at PF=4.18 both smell like leakage or single-symbol concentration, and the FOREX "best" cell fails holdout. (2) The funnel itself is leaking: `opened` >> `passed_smart` in every class (e.g. EQUITY 5,716 opened vs 234 passed_smart; FOREX 23,140 opened vs 23,656 passed_smart but only 3 verified_alpha). The gates are not actually gating. **Zero classes have a defensible real-money edge today.**

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE.** The `conf=C<0.60 & fam=mean_reversion` cell (n=64, WR=98.44%, PF=174.9) is not a real edge — it is a data-integrity failure. A 98% WR with PF=175 on 64 trades means the "loss" leg is essentially absent; that is the signature of (a) look-ahead in the mean-reversion signal (entry priced at the reversion bar, not the signal bar), (b) a single-symbol or single-day cluster, or (c) a P&L sign bug on the losing side. The fact that `trust=UNK` is the dominant dimension is a red flag: the "edge" lives entirely in the bucket where trust scoring failed. Train PF 87 / holdout PF 99 is *too* stable — real edges decay, this one doesn't, which is what leakage looks like. **Do not trade this.** Also note the funnel: 5,847 scanned → 234 passed_smart → 0 passed_HC → but 5,716 opened. The gate is decorative.
- **90d expected P&L (1% risk, $100k):** **$0** (do not deploy). If you naively sized the "proven" cell at 1% risk × 64 trades × 1.55% avg P&L you'd book ~$99k — that number is fiction and I will not present it as an estimate.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — raise from current floor to **≥ 70** AND add a hard `trust != UNK` requirement in `quality_gates.py`. The current floor lets 234 through but the *opened* count (5,716) proves the floor isn't wired to the execution path. Fix the wiring first, then raise the floor.
- **Confidence (1-5):** **1** (that the edge is real). 4 that it's leakage.

---

### COMMODITY
- **Real/noise verdict:** **NOISE.** No PROVEN cells. Best cell `trust=UNK & dir=LONG & source=alpha_engine` (n=31, WR=58%, shrunk 54.9%, PF=1.93) **fails holdout** (holdout PF 1.07, holdout_pass=false) and fails Bonferroni. This is exactly the pattern H-001 warned about — a `trust=UNK` LONG-only alpha_engine cluster that looks fine in-sample and collapses out-of-sample. 3,657 passed_smart out of 6,008 scanned (61% pass rate) is not a gate, it's a turnstile. Treat as no edge.
- **90d expected P&L (1% risk, $100k):** **$0** (holdout-failed; expected value ≈ 0 after slippage).
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — raise to **≥ 65** and require `holdout_pass=true` before a cell is eligible for HC. Currently 61% of scanned names pass "smart" — that's the bug.
- **Confidence (1-5):** **1**.

---

### INDEX
- **Real/noise verdict:** **NOISE / INSUFFICIENT SAMPLE.** n_closed=4. WR 25%. 1,444 of 1,809 passed_smart (80% pass rate!) — the gate is effectively open. No edge, no sample, no conclusion possible. Do not trade.
- **90d expected P&L (1% risk, $100k):** **$0**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — raise to **≥ 70**; 80% pass rate is indefensible. Also cap INDEX exposure until n_closed ≥ 30.
- **Confidence (1-5):** **1**.

---

### FOREX
- **Real/noise verdict:** **NOISE.** No PROVEN cells. The "best" cell `trust=UNK & fam=regime & dir=LONG` (n=29, WR=82.8%, shrunk 69.4%, PF=5.22) **fails holdout** (holdout_pass=false) and **fails Bonferroni**. Train n=7 vs holdout n=22 — the train set is too small to mean anything, and the holdout PF of 8.15 on 22 trades is exactly the kind of small-n blowout that vanishes on the next 22. The `regime_terminal` source with `trust=UNK` is a single-source, single-family cluster — classic single-strategy concentration. **Do not trade.** Note also: 23,656 of 24,436 passed_smart (96.8%!) — the FOREX gate is not a gate, it's a rubber stamp. 1,296 closed, WR 45.3% — that's the true base rate, and it's below breakeven after costs.
- **90d expected P&L (1% risk, $100k):** **$0** (holdout-failed; base-rate WR 45% is negative-EV after spread).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — raise from current to **≥ 75** (biggest single lift available; 96.8% pass rate is the worst offender in the funnel). This alone would cut FOREX opened from 23k to a few hundred and let the real signal (if any) surface.
- **Confidence (1-5):** **1**.

---

### CRYPTO
- **Real/noise verdict:** **SUSPICIOUS — likely leakage or single-symbol concentration.** The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell (n=174, WR=78.2%, shrunk 75.3%, PF=4.18, holdout PF 2.74, holdout_pass=true, Bonferroni pass) is the *only* cell in the entire report that survives holdout AND Bonferroni. That deserves respect — but three red flags: (1) the cell is defined by `score_dec=S50`, a *decile* bucket, which is a post-hoc binning choice; (2) `trust=UNK` is the dominant trust dimension (same pattern as EQUITY leakage); (3) PF 4.18 with avg P&L 1.59% on 174 trades is high but not impossible — however the train PF 6.29 vs holdout 2.74 shows the expected decay, which is *good* (real edges decay). **Verdict: plausibly real but unverified — needs symbol-level concentration check before sizing.** If the 174 trades are >40% one coin (e.g. BTC or a memecoin), it's concentration, not edge. The `ml` cells you flagged aren't in this report's PROVEN list — but the `alpha_engine` cell is the one to interrogate. **Do not size up until you've run a per-symbol breakdown.**
- **90d expected P&L (1% risk, $100k):** If the cell is real and you'd sized 1% risk × 174 trades × 1.59% avg P&L ≈ **$27.7k gross**, minus ~0.1% round-trip slippage × 174 × $1k ≈ $1.7k → **~$26k net**. **But I do not recommend deploying this number** until symbol concentration is ruled out. Treat as $0 deployable today.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — raise to **≥ 70** AND add a `max_single_symbol_share ≤ 0.25` constraint in `quality_gates.py`. The gate change that lifts edge most is the concentration cap, not the score floor — because the score floor is already letting 3,755 through and the edge (if real) is in a narrow conf band the floor doesn't isolate.
- **Confidence (1-5):** **2** (that it's real; 3 that it's worth investigating).

---

### BOND
- **Real/noise verdict:** **NOISE.** n_closed=31, WR 38.7%, 1 of 786 passed_smart. No edge. The 755 "opened" vs 1 passed_smart is a funnel bug — almost nothing should be opening here.
- **90d expected P&L (1% risk, $100k):** **$0**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — set to **≥ 80** (effectively disable until sample grows). 1/786 pass rate is correct; the 755 opened is the bug.
- **Confidence (1-5):** **1**.

---

### ETF
- **Real/noise verdict:** **NOISE.** n_closed=9, WR 11.1%. 300 of 352 passed_smart (85%!). No edge, tiny sample, gate wide open.
- **90d expected P&L (1% risk, $100k):** **$0**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — raise to **≥ 70**; 85% pass rate is indefensible.
- **Confidence (1-5):** **1**.

---

### FUTURES
- **Real/noise verdict:** **NOISE.** n_closed=18, WR 38.9%, no PROVEN cells, no best_pf_overall. Consistent with H-005 (futures momentum anti-signal — inversion doesn't fix it). Do not trade.
- **90d expected P&L (1% risk, $100k):** **$0**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — raise to **≥ 75**; 150/206 (73%) pass rate is too loose.
- **Confidence (1-5):** **1**.

---

### UNKNOWN
- **Real/noise verdict:** **NOISE / DATA BUG.** n_closed=3, WR 0%. 1,386 opened from 1,389 scanned with 146 passed_smart. This bucket should not exist — it means the classifier is failing on ~1,400 names. Fix the classifier before analyzing.
- **90d expected P&L (1% risk, $100k):** **$0**.
- **Gate change:** Not a score constant — fix the asset-class classifier so UNKNOWN → 0. If forced to name one: `SMART_PICKS_MIN_SCORE_UNKNOWN = 999` (hard block).
- **Confidence (1-5):** **1**.

---

### MEME
- **Real/noise verdict:** **NOISE.** n_closed=9, WR 33.3%. 15/31 passed_smart. No edge, tiny sample. Do not trade.
- **90d expected P&L (1% risk, $100k):** **$0**.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — raise to **≥ 80** (effectively disable).
- **Confidence (1-5):** **1**.

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: NONE.** Not one class has a defensible, concentration-checked, holdout-passing edge. The only cell that survives holdout + Bonferroni is CRYPTO `alpha_engine` conf 0.75–0.80 / S50 — and it carries the same `trust=UNK` fingerprint as the EQUITY leakage cell. **The correct action today is zero new capital deployment.**

**If forced to pick one to investigate for scaling:** CRYPTO — but only after a per-symbol concentration breakdown of those 174 trades. If >40% is one coin, kill it. If it's spread across ≥10 coins with no single coin >25%, it's the only candidate worth a small ($10k) pilot.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**

1. **FOREX — demote first.** 96.8% pass_smart rate is the single worst funnel failure in the report. Mutate `SMART_PICKS_MIN_SCORE_FOREX` upward (≥75) and re-run 90d. If WR stays <50% after the gate tightens, kill.
2. **EQUITY — demote second, but quarantine the `mean_reversion` cell immediately.** PF=175 is a data bug, not an edge. Mutate: add `trust != UNK` requirement + audit the P&L sign on losing trades. If the cell survives a leakage audit, re-evaluate; if not, kill the family.
3. **COMMODITY — demote third.** Holdout-failed, and the `trust=UNK & LONG & alpha_engine` pattern is the H-001 recurrence signature. Mutate the gate, re-run; expect it to die.

**Do not re-derive:** H-001 (COT), H-005 (futures momentum), H-009/H-011 (equity options), H-035 (crypto funding), H-036 (commodity inventory). None of the cells above are those hypotheses — but the COMMODITY `trust=UNK & LONG & alpha_engine` cell is close enough to H-001's fingerprint that I'd flag it as a **potential leakage recurrence** and audit timestamps before trusting it.

**The single highest-leverage fix across the whole funnel:** the `opened` counts are 10–100× the `passed_smart` counts in EQUITY, BOND, UNKNOWN, and INDEX. The gates in `quality_gates.py` are not wired to the execution path in `production_scanner.py`. Fix that wiring before touching any threshold — otherwise every threshold change is cosmetic.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### CRYPTO**
- Real/noise verdict: Statistically real (n=174, WR_shrunk 75.26%, PF 4.184, holdout_pass + bonferroni_pass both true). PF is high but passes walk-forward and multiple-testing correction; not obviously single-symbol leakage.
- 90d expected P&L (1% risk, $100k): $2,760 (174 trades × $1,000 risk × 1.59% avg edge after 0.2% slippage/commissions).
- Gate change: `hc_filter.js` MIN_SCORE = 50
- Confidence (1-5): 4

**### EQUITY**
- Real/noise verdict: Sample-noise / leakage (n=64, WR 98.44%, PF 174.9). Impossible in live equity markets; almost certainly single-symbol concentration or timestamp error.
- 90d expected P&L (1% risk, $100k): $0 (edge is spurious)
- Gate change: `quality_gates.py` SMART_PICKS_MIN_SCORE_EQUITY = 65
- Confidence (1-5): 5

**### FOREX**
- Real/noise verdict: Noise (no PROVEN cells; all best_pf cells fail holdout and bonferroni).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `hc_filter.js` MIN_CONF = 0.80
- Confidence (1-5): 5

**### COMMODITY**
- Real/noise verdict: Noise (no PROVEN cells; best_pf cells fail holdout).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `quality_gates.py` SMART_PICKS_MIN_SCORE_COMMODITY = 70
- Confidence (1-5): 5

**### FUTURES / BOND / ETF / INDEX / UNKNOWN / MEME**
- Real/noise verdict: Noise (all n_closed < 50 and zero PROVEN cells).
- 90d expected P&L (1% risk, $100k): $0
- Gate change: `quality_gates.py` SMART_PICKS_MIN_SCORE_{CLASS} = 75
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up **CRYPTO** today (only class with a verified, multi-test-passing edge).  
Demote **EQUITY** per MUTATION_THREE_AXIS_PROTOCOL (clear leakage signature; kill the mean_reversion cell immediately). All other classes have no actionable edge.
