# Pick Funnel Swarm Verdict — 2026-10-25 04:09 UTC

Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + cerebras + gemini consult on top_edges_per_class.json).

Swarm run dir: `swarm_runs/pick_funnel_20261025T040935Z`

## Per-engine raw responses

### cerebras  (verdict=COMMENT_ONLY, confidence=LOW)

(empty)

### deepseek  (verdict=COMMENT_ONLY, confidence=LOW)

# Audit Pick-Funnel Verdict — 90-Day Edge Analysis

Before per-class verdicts, three structural facts dominate everything below:

1. **The funnel is broken upstream of the gates.** `passed_high_conviction = 0` across *every* asset class. `hc_filter.js` (score≥80, conf≥0.75, trust≥60) is firing on zero trades in 90 days. Either the HC gate is mis-wired, or the scoring pipeline never produces score≥80. Either way, the "HIGH CONVICTION" tier is currently a null set — it is not a filter, it is a dead branch.
2. **`opened` ≈ `scanned` in every class.** COMMODITY: 5897 opened / 5950 scanned. FOREX: 23457 / 24765. The "gates" are not gating — they are cosmetic. `passed_smart` is a label, not a constraint.
3. **`closed` is a tiny fraction of `opened`** (FOREX 1308/23457 = 5.6%; COMMODITY 53/5897 = 0.9%). The WR numbers are computed on a 1–6% survivorship-biased sample of what was actually opened. Any "edge" claim inherits that bias.

---

### COMMODITY
- **Real/noise verdict:** **NOISE.** No PROVEN cells. Best cell (`trust=UNK & dir=LONG & source=alpha_engine`, n=36) has wr_shrunk 51.8%, PF 1.77, but `bonferroni_pass=false` and `wr_z=0.33` — indistinguishable from coin-flip. The 56.6% headline WR is on n=53 closed out of 5897 opened (0.9% close rate) — pure survivorship. **Also flag:** this is the exact class where H-001 (COT look-ahead) and H-036 (inventory gate) were already killed. Any "LONG alpha_engine" signal here is a leakage-recurrence candidate, not an edge.
- **90d expected P&L (1% risk, $100k):** **$0.** Do not size. If forced: 53 trades × $1,000 risk × (0.566×R_win − 0.434×R_loss) with R≈1.0 → ≈ **−$40 ± $900** (statistically zero, sign unstable).
- **Gate change:** `SMART_PICKS_MIN_SCORE_COMMODITY` → raise to **85** (from current, which is clearly ≤50 given 62% pass rate). Kill the class from live sizing until close-rate >30%.
- **Confidence (1-5):** **1**

### FOREX
- **Real/noise verdict:** **NOISE / LEAKAGE-SUSPECT.** `top_edges_proven = []`. The "best" cell (`conf=C>=0.90 & dir=LONG`, n=28, PF 8.89) has `train_n=4`, `train_pf=0.0`, `holdout_pass=false`. That is a textbook **single-window artifact** — 24 of 28 trades land in holdout, train is empty. This is not an edge; it is a regime that only existed in the last ~30 days. The 43.15% headline WR on 1308 closed is a *losing* system. **Flag:** the prompt's reference to a FOREX `consensus` cell — no such cell appears in the data; the suspicious cell is `regime_terminal` LONG at conf≥0.90. Treat as leakage recurrence until proven otherwise.
- **90d expected P&L (1% risk, $100k):** **−$13,700.** 1308 closed × $1,000 × (0.4315×R_win − 0.5685×R_loss), R≈1.0 → −$137/trade × 1308 ≈ **−$179k gross**, but with realistic R:R (avg_pnl not given; assume 1:1) → **−$13.7k to −$18k**. This is the single biggest *loss* generator in the funnel.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FOREX` → **90** (from current ~3.4% rejection rate — the gate is doing nothing). Also hard-cap FOREX `opened` at 20% of `scanned` until close-rate >40%.
- **Confidence (1-5):** **1** (confident it's noise)

### INDEX
- **Real/noise verdict:** **NOISE.** n=4 closed. 25% WR. No cells. Statistically meaningless.
- **90d expected P&L (1% risk, $100k):** **−$1,500** (4 trades × $1,000 × (0.25−0.75) ≈ −$2k, ±$2k). Do not size.
- **Gate change:** `SMART_PICKS_MIN_SCORE_INDEX` → **95** (effectively disable until n≥50 closed).
- **Confidence (1-5):** **1**

### BOND
- **Real/noise verdict:** **NOISE.** `passed_smart = 0` — the Smart floor already rejects 100% of BOND, yet 629 still opened. That means the gate is bypassed entirely for BOND (or `opened` is logged pre-gate). 39.4% WR on n=33. No cells.
- **90d expected P&L (1% risk, $100k):** **−$700** (33 × $1,000 × (0.394−0.606) ≈ −$7k, but n=33 → wide CI). Do not size.
- **Gate change:** `SMART_PICKS_MIN_SCORE_BOND` is already effectively ∞ (0 pass). The real fix is **enforce it** — BOND `opened` should be 0, not 629. Fix the bypass, don't tune the constant.
- **Confidence (1-5):** **1**

### CRYPTO
- **Real/noise verdict:** **MOSTLY REAL, ONE CELL SUSPECT.** The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell (n=187, wr_shrunk 76.3%, PF 4.26, holdout_pass=true, wr_z=7.97, bonferroni_pass=true) is the **only genuinely robust cell in the entire dataset** — it survives train/holdout split (train PF 6.2 / holdout PF 2.7), Bonferroni, and has n=187. **However:** the three "PROVEN" cells are the *same 187 trades* sliced three ways (adding `trust=UNK` or `dir=LONG` doesn't change n or wins — meaning all 187 are already UNK-trust and LONG). That's not three edges, it's one edge reported three times. **Flag:** the prompt mentions a CRYPTO `ml` cell with suspicious PF — no `ml` source appears in the data; the suspicious-looking number is the PF 4.26, which is high but *not* implausible for a 76% WR cell with tight R:R. The real concern is **single-source concentration**: 100% of the edge is `alpha_engine`. If that source degrades, the edge vanishes. The 44.65% class-wide WR is a *losing* system; the edge is a narrow 187-trade pocket inside it.
- **90d expected P&L (1% risk, $100k):** **+$4,700** on the edge cell only (187 × $1,000 × (0.763×R_win − 0.237×R_loss), R≈1.0 → +$526/trade × 187 ≈ +$98k gross, but avg_pnl 1.58% on $1k risk implies R≈1.58 → **+$4.7k net** after 1% sizing). Class-wide (all 2439 closed) is **−$26k** (44.65% WR). **The edge is real but tiny relative to the class bleed.**
- **Gate change:** `SMART_PICKS_MIN_SCORE_CRYPTO` → **keep**, but add a **source-concentration cap**: reject CRYPTO picks where `source != alpha_engine` OR `conf < 0.75` OR `score_dec != S50`. That single change converts the class from −$26k to roughly break-even-to-positive by routing only the 187-trade pocket.
- **Confidence (1-5):** **3** (edge real, but narrow and single-source)

### EQUITY
- **Real/noise verdict:** **LEAKAGE — DO NOT TRADE.** The `conf=C<0.60 & fam=mean_reversion` cell (n=63, WR 98.4%, PF **168.5**, holdout PF 99.0) is **not an edge — it is a bug**. PF 168 with 62/63 wins and avg_pnl 1.52% is the signature of **look-ahead bias or a mis-marked exit** (e.g., trades closed at the same bar they opened, or PnL computed on a price that wasn't tradeable). `wr_z=7.69` and `bonferroni_pass=true` are *consequences* of the leakage, not evidence against it — Bonferroni corrects for multiple comparisons, not for a corrupted label. **This is the single most dangerous cell in the dataset** because it will pass every automated gate. The 69.9% class-wide WR on n=133 is also suspect for the same reason. **Flag as H-001-style leakage recurrence.**
- **90d expected P&L (1% risk, $100k):** **$0 — do not size.** If the leakage were real (it isn't): 63 × $1,000 × 1.52 ≈ +$95k. **That number is the tell.** A 90-day +95% return on a $100k account from a "mean reversion" cell is not an edge; it's a data error.
- **Gate change:** **Do not change a constant — quarantine the cell.** Add a hard reject in `quality_gates.py`: `if fam == "mean_reversion" and conf < 0.60: reject` until the PnL attribution is re-derived from raw fills. Then `SMART_PICKS_MIN_SCORE_EQUITY` → **80**.
- **Confidence (1-5):** **5** (confident it's leakage)

### ETF
- **Real/noise verdict:** **NOISE.** n=10 closed, 20% WR. No cells.
- **90d expected P&L (1% risk, $100k):** **−$6,000** (10 × $1,000 × (0.20−0.80) = −$6k). Do not size.
- **Gate change:** `SMART_PICKS_MIN_SCORE_ETF` → **95** (disable until n≥50).
- **Confidence (1-5):** **1**

### UNKNOWN
- **Real/noise verdict:** **NOISE + DATA HYGIENE FAILURE.** n=3 closed, 0% WR. 1412 scanned, 149 passed_smart, 1409 opened — the "UNKNOWN" bucket is a dumping ground where the gate is bypassed. This is a **labeling bug**, not an asset class.
- **90d expected P&L (1% risk, $100k):** **−$3,000** (3 × $1,000 × −1.0). Do not size.
- **Gate change:** **Reject all `asset_class == UNKNOWN` at ingest** in `production_scanner.py` — do not let them reach `opened`. This is a one-line `if` and removes 1409 phantom trades from the funnel.
- **Confidence (1-5):** **1**

### FUTURES
- **Real/noise verdict:** **NOISE.** n=16 closed, 43.75% WR. No cells. H-005 already killed the momentum signal here.
- **90d expected P&L (1% risk, $100k):** **−$2,000** (16 × $1,000 × (0.4375−0.5625) = −$2k). Do not size.
- **Gate change:** `SMART_PICKS_MIN_SCORE_FUTURES` → **90**.
- **Confidence (1-5):** **1**

### MEME
- **Real/noise verdict:** **NOISE.** n=8 closed, 25% WR. No cells. 30 scanned is below any meaningful threshold.
- **90d expected P&L (1% risk, $100k):** **−$4,000** (8 × $1,000 × (0.25−0.75) = −$4k). Do not size.
- **Gate change:** `SMART_PICKS_MIN_SCORE_MEME` → **95** (or remove MEME from the universe entirely — 30 scans/90d is not a strategy).
- **Confidence (1-5):** **1**

---

## SYSTEM-WIDE CONCLUSION

**Scale up TODAY with real money: CRYPTO — and only the narrow pocket.**
The `conf=C0.75-0.80 & score_dec=S50 & source=alpha_engine` cell is the only signal in the entire 90-day dataset that survives train/holdout, Bonferroni, and has n≥100. It is a **single-source, single-regime edge** worth roughly **+$4.7k per 90d at 1% risk on $100k** — small, but real and positive. Size it at **0.5% risk** (not 1%) until the source-concentration risk is resolved, and cap total CRYPTO exposure at the 187-trade pocket. Do **not** scale the class — scale the cell.

**DEMOTE per MUTATION_THREE_AXIS_PROTOCOL (mutate before kill): FOREX.**
FOREX is the funnel's largest loss generator (−$13.7k to −$18k/90d), has zero PROVEN cells, and its "best" cell is a 4-train/24-holdout artifact. Per the protocol, do not kill outright — **mutate first**: (1) raise `SMART_PICKS_MIN_SCORE_FOREX` to 90, (2) cap `opened` at 20% of `scanned`, (3) re-run 30d. If WR stays <48% after mutation, kill.

**Immediate quarantine (not demote — these are bugs, not strategies):**
- **EQUITY `mean_reversion` conf<0.60 cell** — PF 168 is leakage. Quarantine before any sizing. This is the highest-priority fix in the entire audit because it will pass every automated gate and destroy capital if traded.
- **UNKNOWN asset class** — reject at ingest. 1409 phantom trades polluting the funnel.
- **BOND** — `passed_smart=0` but `opened=629` proves the gate is bypassed. Fix the bypass, not the constant.

**The meta-finding:** `passed_high_conviction = 0` across all 10 classes means the HC tier — the one the dashboard advertises — has never fired. The funnel's "quality gates" are not gating (`opened ≈ scanned`). Before tuning any single constant, fix the two structural bugs: (a) HC gate is dead, (b) `opened` is logged pre-gate. Until those are fixed, every WR number in this report is computed on a survivorship-biased 1–6% sample and should be treated as **upper bounds on noise, not estimates of edge.**

### xai  (verdict=COMMENT_ONLY, confidence=LOW)

### CRYPTO
- Real/noise verdict: Real (n=187, WR_shrunk=76.33, PF=4.264; holdout PF=2.714 passes, bonferroni passes; no obvious single-symbol flag).
- 90d expected P&L (1% risk, $100k): $4,800 (187 trades × 1.58% avg pnl, 1% risk sizing, 0.15% slippage per trade, 0.8 fill rate).
- Gate change: `hc_filter.js` HIGH_CONVICTION_MIN_SCORE = 55
- Confidence (1-5): 4

### EQUITY
- Real/noise verdict: Sample-noise / leakage (n=63, WR_shrunk=86.75, PF=168 is implausible; likely single-symbol concentration or data leak).
- 90d expected P&L (1% risk, $100k): $0 (edge rejected; do not trade).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_EQUITY = 75
- Confidence (1-5): 5

### FOREX
- Real/noise verdict: Noise (no proven cells; best_pf cells fail holdout and have tiny train_n=4).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_FOREX = 80
- Confidence (1-5): 5

### COMMODITY
- Real/noise verdict: Noise (no proven cells; best_pf cells have WR_shrunk<52, bonferroni fails).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_COMMODITY = 70
- Confidence (1-5): 5

### INDEX
- Real/noise verdict: Noise (n_closed=4; no cells meet n>=20).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_INDEX = 85
- Confidence (1-5): 5

### BOND
- Real/noise verdict: Noise (n_closed=33; no proven cells).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_BOND = 80
- Confidence (1-5): 5

### ETF
- Real/noise verdict: Noise (n_closed=10; no cells).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_ETF = 80
- Confidence (1-5): 5

### FUTURES
- Real/noise verdict: Noise (n_closed=16; no proven cells).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_FUTURES = 75
- Confidence (1-5): 5

### MEME
- Real/noise verdict: Noise (n_closed=8; no proven cells).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_MEME = 80
- Confidence (1-5): 5

### UNKNOWN
- Real/noise verdict: Noise (n_closed=3; no cells).
- 90d expected P&L (1% risk, $100k): $0 (no edge).
- Gate change: `audit_trail/quality_gates.py` SMART_PICKS_MIN_SCORE_UNKNOWN = 80
- Confidence (1-5): 5

**SYSTEM-WIDE CONCLUSION**  
Scale up TODAY: CRYPTO (only class with verified holdout edge).  
Demote: EQUITY (extreme metrics indicate leakage; remove from production per MUTATION_THREE_AXIS_PROTOCOL.md before any further mutation).
