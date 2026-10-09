# Pick Funnel Swarm Verdict — 2026-10-09 04:12 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261009T041232Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-day Edge Analysis

Before the per-class verdicts, three structural facts dominate everything below:

1. **`passed_high_conviction = 0` in every single class.** The HC gate (`score>=80, conf>=0.75, trust>=60`) is firing on **zero** picks across 90 days and ~52k scans. Either the gate is mis-wired, or the scoring pipeline never produces a pick that satisfies all three simultaneously. This is the single biggest finding in the dataset.
2. **`passed_verified_alpha` is 0 for 7 of 10 classes.** Only CRYPTO (1921) and a token trickle in FOREX/FUTURES/MEME pass. The "verified alpha" stage is effectively a CRYPTO-only filter.
3. **`opened` >> `passed_smart` in every class** (e.g. EQUITY: 240 passed_smart → 5559 opened). The funnel is not gating what actually gets traded. The dashboard is showing a filter that the execution layer ignores.

That last point means the "edge cells" below describe a **counterfactual book**, not the book you actually ran. Treat every P&L number as "if the funnel had been the only gate."

---

### EQUITY
- **Real/noise verdict:** **NOISE / LEAKAGE.** The `fam=mean_reversion & score_dec=S40` cell shows WR=98.46% (64/65), PF=210.8, holdout PF=99.0. A 98% win rate on 65 trades with PF >200 is not an edge — it is a **labeling or exit-logic bug**. Most likely causes: (a) mean-reversion trades being marked "win" on any touch of a limit that is inside the entry, (b) `score_dec=S40` selecting a decile that correlates with a post-hoc favorable close, or (c) the "closed" set being conditioned on a filter that drops losers. The `wr_z=7.81` and `bonferroni_pass=true` are meaningless when the underlying P&L distribution is degenerate. **Do not trade this.** Also note EQUITY `opened=5559` vs `closed=149` — 97% of equity picks never closed in 90d, so the WR is computed on a 2.7% survivor sample.
- **90d expected P&L (1% risk, $100k):** **$0.** I will not size a 98% WR / PF 210 cell. If forced to mark-to-model with the observed avg_pnl of +1.29% on 65 trades at 1% risk: ~$840 gross, but the number is not credible and I'd expect it to revert to negative once the labeling bug is fixed.
- **Gate change:** `SMART_PICKS_MIN_SCORE_EQUITY` — **raise from current to 65** AND add a hard `MIN_CLOSED_TRADES_FOR_EDGE = 200` guard in `quality_gates.py` so EQUITY cannot be promoted on n=149. The real fix is upstream: audit why 5559 opened → 149 closed.
- **Confidence (1-5):** **1**

### INDEX
- **Real/noise verdict:** **NOISE.** n_closed=5. WR=20%. `passed_smart=1588` on 1895 scanned (84% pass rate) — the Smart floor for INDEX is doing nothing. No edge cells exist. This class should not be in the funnel at all until it has ≥200 closed trades.
- **90d expected P&L (1% risk, $100k):** **-$1,600** (extrapolating 20% WR at 1:1 R:R on the 5 closed trades; statistically meaningless).
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` — **raise to 75** (currently effectively ~0 given 84% pass). Better: disable INDEX in `production_scanner.py` until n_closed ≥ 200.
- **Confidence (1-5):** **1**

### FOREX
- **Real/noise verdict:** **NOISE, and the "best" cell is a textbook leakage recurrence.** The `trust=UNK & conf=C>=0.90 & fam=regime` cell has **train_pf=0.298 (n=17)** and **holdout_pf=14.149 (n=37)**. That is the signature of a regime-terminal source that was **retro-fitted after the regime was known** — i.e. the `regime_terminal` source is emitting picks whose "confidence" is derived from the outcome window. `holdout_pass=false`, `bonferroni_pass=false`. This is exactly the H-001 pattern (COT look-ahead) re-appearing under a different name. **Flag as leakage recurrence, do not trade.** The class-level WR of 42% on n=533 is the honest number, and it is below breakeven at typical FX spreads.
- **90d expected P&L (1% risk, $100k):** **-$3,000 to -$5,000.** 533 decisive trades at 42% WR with ~1:1 R:R and 0.5–1.0 pip slippage on 22k opened picks is a losing book. The `regime_terminal` cell would show +$X on paper but I refuse to size it.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` — **raise to 70** AND add `BANNED_SOURCES = {"regime_terminal"}` in `quality_gates.py`. The 96% pass rate (22647/23558) is the real problem: the FOREX floor is a no-op.
- **Confidence (1-5):** **1** (on the class), **5** (that `regime_terminal` is leakage)

### CRYPTO
- **Real/noise verdict:** **PARTIALLY REAL — the only class with a defensible edge.** The `conf=C0.75-0.80 & dir=LONG & score_dec=S50` cell: n=174, WR_shrunk=68.0%, PF=2.83, **train_pf=3.38 / holdout_pf=1.71 (holdout_pass=true)**, `bonferroni_pass=true`. The train→holdout degradation (3.38→1.71) is exactly what a real edge looks like — it decays but stays >1.5. The `source=alpha_engine` variant (n=244, holdout PF=2.11) is the more robust version. **Caveat:** `trust=UNK` on the top cell means the trust dimension is not actually filtering — the edge is carried entirely by `conf` + `dir=LONG` + `score_dec=S50`. That's fine, but it means the trust gate is dead weight. **No `ml` cell appears in the PROVEN list** — the prompt's concern about "CRYPTO ml cells with suspiciously high PF" is not borne out by this data; the high-PF cells are `alpha_engine`, not `ml`. If an `ml` cell exists elsewhere with PF>5, treat it as leakage until proven otherwise.
- **90d expected P&L (1% risk, $100k):** Using the `alpha_engine` cell (n=244, avg_pnl=+1.055%, WR_shrunk=62.5%): **~$2,570 gross** on the 244 trades in that cell. Scaling to the full 2422 closed CRYPTO trades at the class WR of 45% would be **negative** — so the edge is **cell-specific, not class-wide**. Realistic deployable estimate: **+$1,800 to +$2,500** after 0.15% round-trip slippage on 244 trades.
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` — **raise to 72** AND add a `REQUIRE_DIRECTION_LONG_FOR_CRYPTO_EDGE = True` flag, because every proven CRYPTO cell is LONG-only. The current floor (3515/12957 = 27% pass) is too loose; tightening to ~10% pass rate would concentrate on the `conf 0.75–0.80 & LONG & S50` pocket.
- **Confidence (1-5):** **4**

### COMMODITY
- **Real/noise verdict:** **NOISE / possible leakage.** The `rr=RR>=2.0 & dir=LONG & source=alpha_engine` cell: n=21, WR=80.95%, PF=9.49, **train_pf=5.32 (n=11) / holdout_pf=49.6 (n=10)**. A holdout PF of 49.6 on 10 trades is not an edge — it's one or two outsized winners. `bonferroni_pass=false`. n=21 is below the n≥20 threshold only barely, and the holdout n=10 is far too small. **Also: H-001 (COT leakage) and H-036 (inventory gate) are both COMMODITY kills.** Any COMMODITY "edge" should be presumed leakage until it survives a fresh out-of-sample window with n≥100. This cell does not.
- **90d expected P&L (1% risk, $100k):** **$0.** I will not size n=21 with holdout n=10. If forced: +$2,100 on paper, but the honest answer is "uninvestable."
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` — **raise to 75** AND add `MIN_HOLDOUT_N_FOR_PROMOTION = 30` in `quality_gates.py`. The 58% pass rate (3475/5941) is too loose.
- **Confidence (1-5):** **1**

### ETF
- **Real/noise verdict:** **NOISE.** n_closed=9, WR=22%. No edge cells. `passed_smart=297/346` (86% pass) — floor is a no-op.
- **90d expected P&L (1% risk, $100k):** **-$700** (extrapolated, meaningless).
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` — **raise to 75**, or disable ETF in `production_scanner.py` until n_closed ≥ 200.
- **Confidence (1-5):** **1**

### FUTURES
- **Real/noise verdict:** **NOISE.** n_closed=15, WR=33%. H-005 already killed the futures momentum signal. No edge cells. `passed_smart=129/184` (70% pass).
- **90d expected P&L (1% risk, $100k):** **-$1,000** (extrapolated).
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` — **raise to 75**, or disable until n_closed ≥ 200.
- **Confidence (1-5):** **1**

### BOND
- **Real/noise verdict:** **NOISE.** n_closed=30, WR=43%. `passed_smart=3/560` — the BOND floor is so tight it's effectively disabled, yet `opened=530`. The funnel and execution are completely decoupled here.
- **90d expected P&L (1% risk, $100k):** **-$400** (extrapolated).
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` — **leave at current tight value**, but fix the `opened` path so it respects the gate. The bug is in `production_scanner.py`, not the floor.
- **Confidence (1-5):** **1**

### UNKNOWN
- **Real/noise verdict:** **NOISE / data hygiene failure.** n_closed=5, WR=0%. 1371 scanned, 1366 opened. This class should not exist — it means the classifier in `production_scanner.py` is failing to assign an asset class to ~2.6% of picks. Fix the classifier before analyzing.
- **90d expected P&L (1% risk, $100k):** **-$500** (extrapolated).
- **Gate change:** Add `REJECT_UNKNOWN_CLASS = True` in `quality_gates.py`. Do not trade unclassified picks.
- **Confidence (1-5):** **1**

### MEME
- **Real/noise verdict:** **NOISE.** n_closed=4, WR=25%. No edge cells. n=24 scanned total.
- **90d expected P&L (1% risk, $100k):** **-$300** (extrapolated).
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` — **raise to 80**, or disable. n=24 is not a class.
- **Confidence (1-5):** **1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO only, and only the `conf=C0.75-0.80 & dir=LONG & source=alpha_engine` pocket.** That is the only cell in the entire dataset that has (a) n≥200, (b) holdout_pass=true, (c) bonferroni_pass=true, (d) a train→holdout PF ratio that looks like decay rather than leakage. Expected 90d P&L at 1% risk on $100k: **+$1,800 to +$2,500**. Size at half-Kelly initially (0.5% risk) until the next 90d window confirms.

**DEMOTE per `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill):**

1. **FOREX** — demote to paper-only. The `regime_terminal` source is a **leakage recurrence of H-001** (train_pf=0.298 → holdout_pf=14.149 is the tell). Mutate: ban the source, re-run with `conf>=0.90` removed, and require n≥200 per cell. If it still fails, kill.
2. **EQUITY** — demote to paper-only. The 98% WR / PF 210 cell is a **labeling bug**, not an edge. Mutate: audit the mean_reversion exit logic and the `score_dec=S40` definition. Do not promote until the 5559→149 open/close gap is explained.
3. **COMMODITY** — demote to paper-only. Two prior kills (H-001, H-036) plus a holdout PF of 49.6 on n=10. Mutate: require `MIN_HOLDOUT_N_FOR_PROMOTION = 30` and re-test.
4. **INDEX, ETF, FUTURES, BOND, UNKNOWN, MEME** — **kill from the live funnel.** n_closed < 30 in every case. These are not classes; they are noise buckets. Re-admit only when n_closed ≥ 200.

**The single most important fix is not a gate constant — it is the `opened` vs `passed_smart` decoupling.** In every class, `opened` is 10–100× `passed_smart`. The dashboard is showing a filter that the execution layer ignores. Until that is fixed, every "edge" number above describes a book you did not run. Fix the funnel wiring in `production_scanner.py` before tuning any floor in `quality_gates.py`.

**On the HC gate:** `passed_high_conviction = 0` across 52k scans is not a finding about edges — it is a **broken gate**. Either `score>=80` is unreachable given the scoring distribution, or `trust>=60` is never satisfied, or `hc_filter.js` is not being invoked server-side. Debug this before any further edge analysis; it is the highest-leverage 30 minutes in this audit.

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

**### CRYPTO**
- Real/noise verdict: The three listed cells show holdout_pass + bonferroni_pass and decent shrunk WR/PF, but n=174–244 is still modest; the identical metrics across overlapping cells and extreme PF suggest possible single-symbol concentration or alpha_engine leakage rather than robust multi-symbol edge.
- 90d expected P&L (1% risk, $100k): $2,800 (uses observed 1.05–1.23 % avg win size, 1 % risk, 0.15 % slippage, ~240 trades; net expectancy ~2.8 % after costs).
- Gate change: `audit_trail/quality_gates.py:SMART_PICKS_MIN_SCORE_CRYPTO` = 55
- Confidence (1-5): 3

**### EQUITY**
- Real/noise verdict: 98 % WR on 65 trades with PF=210 is statistically impossible without leakage or single-name concentration; flagged as noise / data artifact.
- 90d expected P&L (1% risk, $100k): -$1,400 (expect mean-reversion edge to collapse to ~45 % WR once leakage removed).
- Gate change: `audit_dashboard/hc_filter.js:HIGH_CONVICTION_MIN_TRUST` = 75
- Confidence (1-5): 2

**### FOREX**
- Real/noise verdict: All top cells fail holdout_pass and bonferroni; n=54 with train/holdout PF inversion is classic overfitting / noise.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: `audit_trail/quality_gates.py:SMART_PICKS_MIN_CONF_FOREX` = 0.92
- Confidence (1-5): 1

**### COMMODITY**
- Real/noise verdict: n=21 cells fail bonferroni; PF=9.5 collapses under any realistic slippage or symbol diversification; noise.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: `audit_trail/quality_gates.py:SMART_PICKS_MIN_RR_COMMODITY` = 2.5
- Confidence (1-5): 1

**### INDEX / ETF / FUTURES / BOND / UNKNOWN / MEME**
- Real/noise verdict: All have n_closed ≤ 30 and zero proven cells; every “best_pf” entry fails statistical gates or has n<20 → pure sample noise.
- 90d expected P&L (1% risk, $100k): $0 (no deployable edge).
- Gate change: `audit_dashboard/hc_filter.js:HIGH_CONVICTION_MIN_SCORE` = 85
- Confidence (1-5): 1

**SYSTEM-WIDE CONCLUSION**  
Scale up **CRYPTO** today only after raising the score floor (edge is marginal but the only one that survived basic holdout checks). Demote **EQUITY** and **COMMODITY** per MUTATION_THREE_AXIS_PROTOCOL.md — both show clear leakage signatures and should be mutated (or killed) before any further capital allocation. All other classes have no actionable edge.
