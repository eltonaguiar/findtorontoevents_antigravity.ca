# Near-Miss Deep Dive — 3 strategies just below tier-promotion thresholds

**Date**: 2026-04-29
**Investigator**: Claude (read-only diagnostic)
**Data source**: `audit_dashboard/data/dashboard_data.json` (3,500 closed picks, 13 active)
**Cohort**: `luxalgo_confluence`, `rs-breakout-scout`, `atr_percentile_gate`
**AI panel**: Cerebras qwen-3-235b-instruct, Cerebras gpt-oss-120b, Ollama gpt-oss:20b-cloud
  (DeepSeek v3.2 cloud returned reasoning-only — see `near_miss_deep_dive_2026_04_29/ollama_deepseek-v3.2-cloud.md`)

---

## TL;DR

| # | Strategy | n | WR | PF | sum_pnl | Active | Verdict |
|---|----------|---|----|----|---------|--------|---------|
| A | luxalgo_confluence | **205** | 52.2% | **1.66** | +93.7% | 0 | **Promote — only blocker is stale config** |
| B | rs-breakout-scout | 23 | 78.3% | 7.49 | +59.8% | 0 | **Hold — let n grow naturally** |
| C | atr_percentile_gate | 22 | 95.5% | 13.51 | +9.27% | 0 | **Watch — score-gate is gating, but n & burst pattern need more data** |

**AI panel consensus**: prioritize **A** — it is the only strategy already past
the proven-floor (n>=200) and Tier-2 metric thresholds, and the only blocker is
stale config (paper-only flag + kill-list entry). B & C are sample-starved
(n<30 candidate floor) and should not be force-promoted this cycle.

---

## Per-strategy diagnostic table

| Field | A: luxalgo_confluence | B: rs-breakout-scout | C: atr_percentile_gate |
|---|---|---|---|
| n (closed) | 205 | 23 | 22 |
| WR | 52.2% | 78.3% | 95.5% |
| PF | 1.66 | 7.49 | 13.51 |
| sum_pnl_pct | +93.7% | +59.8% | +9.27% |
| avg_win | +2.21% | n/a | +0.48% |
| avg_loss | -1.45% | -1.84% | -0.74% |
| Asset class | CRYPTO | EQUITY 18 / ETF 4 / BOND 1 | CRYPTO (BTCUSDT only) |
| Direction mix | LONG 103 / SHORT 102 | LONG only | LONG only |
| Top symbol | STXUSDT 60% n=20 | SOXX 80% n=5 | BTCUSDT 95.5% n=22 |
| Worst symbol | SOLUSDT 31% n=13 | TLT/COIN/XLI 0% n=1 each | n/a (BTC only) |
| Source system | luxalgo_filters (RELIABLE) | kimi_riseoftheclaw (UNTRUSTED) | baby_strats_forward + battleground (WATCH) |
| Trust tier | RELIABLE | UNTRUSTED | WATCH |
| WF verdict | VIABLE | STRONG | STRONG |
| Score (avg / max) | 45.5 / 53 | 56.2 / 65 | 44.7 / 45 |
| Confidence (avg / min) | 0.63 / 0.48 | 0.55 / 0.35 | 0.40 / 0.00 |
| RR ratio (avg) | 1.71 | 1.62 | 1.67 |
| Exit mix | TP 73 / SL 73 / FORCE 57 / TIME 2 | TP 14 / TIME 6 / SL 3 | TP 16 / TIME 5 / SL 1 |
| Latest emit (age) | **3.0h** (still firing) | 123.5h (5.1d) | 68.9h (2.9d) |
| Closed last 7d | 159 | 5 | 22 (entire history) |
| Closed last 30d | 205 (entire history) | 14 | 22 |
| Currently active | 0 | 0 | 0 |
| Near-miss losses (-0.05 to -0.5%) | 2 (1.0%) | 1 (4.3%) | 0 (0.0%) |
| Near-miss losses (-0.05 to -2.0%) | 82 (40.0%) | 2 (8.7%) | 1 (4.5%) |

---

## A. luxalgo_confluence — diagnosis

**Status**: emitting upstream every few minutes (latest 3h ago); blocked at
the dashboard active gate.

### Why no active picks

Two independent blockers, both stale:

1. **`alpha_engine/strategy_blocklist.py:174`** — added to `_PAPER_ONLY_STRATEGIES`
   on 2026-04-19. Rationale in source comment:
   > "Kimi Code fact-check — luxalgo_confluence appears in every toxic consensus
   > combo with n>=5. luxalgo_confluence + st_obv_support_divergence = 8.3% WR n=12."

   But `st_obv_support_divergence` is now `_RETIRED` (2026-04-20). The "toxic
   combo" partner is gone. The rationale is stale.

2. **`alpha_engine/data/core_whitelist.json` kill_list** (origin/main) — both
   `luxalgo_confluence` and `luxalgo_filters::luxalgo_confluence` are present.
   The `audit_trail/dashboard_generator.py:7720-7724` filter strips killed
   strategies from `picks.active` regardless of source.
   - PR #519 added `kill_list_max_age_days=21` auto-expiry, but
     `last_kill_run=2026-03-26` (34d stale) means the entire kill_list
     auto-expires on next dashboard run. The luxalgo entries are scheduled
     to clear via that mechanism — but until `tools/strategy_killer.py`
     refreshes the list, the explicit entry still wins.

### Per-direction profitability

Symmetric. **LONG: 52.4% WR / +51.4%, SHORT: 52.0% WR / +42.3%**. Equal
TP/SL count (73/73) is genuinely 50/50 — argues that the 1.66 PF comes
from the **win-magnitude > loss-magnitude** asymmetry (avg_win 2.21% vs
avg_loss -1.45%), not directional bias. AI panel unanimous: this argues
**FOR** a real signal, not a directional curve-fit.

### Symbol-level edge

Top performers: STXUSDT 60%/+17%, ARBUSDT 71%/+21%, ADAUSDT 71%/+14%,
WIFUSDT 70%/+14%. Drag: SOLUSDT 31%/-3.7%, JUPUSDT 36%/-3.7%, BTCUSDT 38%/-2.8%.
A symbol-blacklist on the worst-3 (SOL/JUP/BTC) would lift PF measurably
(removes ~10% of trades and ~10% of net loss).

### Quick-win

**Single-line action**: remove `"luxalgo_confluence"` from `_PAPER_ONLY_STRATEGIES`
in `alpha_engine/strategy_blocklist.py` AND remove both kill_list entries from
`alpha_engine/data/core_whitelist.json`. Update kill_list `last_kill_run` so the
auto-expiry doesn't blow away the rest of the list.

**Estimated weekly volume restored**: ~110 picks/wk (159 closed in last 7d).
**Estimated edge contribution**: at 1.66 PF / 52% WR / +0.46% avg-pnl-per-trade,
~+50%/wk gross PnL contribution at 1× position sizing.

### Fragility

- **Low** — n=205, 10-day window, symmetric direction, balanced TP/SL.
- Caveat: 10 days is a short observation window. Re-validate at n=400 (~3 weeks
  more emission) before promoting from candidate to PROVEN.
- Symbol concentration: top-4 symbols carry ~40% of trades. Single-symbol
  failure (e.g. STX delisting) would cost ~10% of net edge.

---

## B. rs-breakout-scout — diagnosis

**Status**: trickle emission; last pick 5 days ago. Pre-existing in
`smart_picks_engine.py:253` PROVEN_STRATEGIES with `boost=8 wr=69.2`. NOT in
kill_list, NOT paper-only.

### Why no active picks

- n=23 < candidate floor (30). 8 more picks needed to clear floor.
- Source `kimi_riseoftheclaw` carries `trust_tier=UNTRUSTED` schema-wide
  (regardless of strategy quality). Picks won't be promoted to active until
  trust escalates.
- Setup is genuinely rare. Daily entry counts: April had 13 picks across
  roughly 1-2 per day, with 5 days emitting nothing.
- The strategy is in the equity allowlist in `smart_picks_engine.py:382` —
  i.e. the engine *would* surface it if the upstream emitted, the pipeline
  isn't blocking it.

### Per-direction & symbol-level

LONG-only. Strong on tech/sector ETFs (SOXX 80% n=5, XLK 100% n=3) and
energy (XOM/CVX 75-100%). Single-trade losses on TLT, COIN, XLI — too few
to act on.

### Quick-win

**No 1-line fix is appropriate**. n=23 is genuinely below the candidate floor
and the AI panel agrees forcing promotion is unwarranted. Two passive options:

1. **Wait** — at 1-2 emits/day, candidate floor reached in ~7-10 days
   naturally. Re-evaluate then.
2. **Trust-tier escalation** — review whether `kimi_riseoftheclaw` source
   should escalate from UNTRUSTED to DEVELOPING for strategies with
   `wf_verdict=STRONG` and PF>2. (Schema-wide change; not a 1-line fix.)

**Estimated weekly volume**: ~5 picks/wk (current cadence). No restoration
needed — the cadence is real.

### Fragility

- **Medium-high** — n=23, single TLT loss = 1/23 = 4.3% of trades; bad luck
  could swing WR by 5-10pp.
- LONG-only on EQUITY makes it regime-dependent (will lag in a sustained
  bear market — see TLT bond loss as canary).
- The `boost=8 wr=69.2` baseline in `smart_picks_engine.py` is from a
  separate window — current 78.3% may not persist.

---

## C. atr_percentile_gate — diagnosis

**Status**: burst pattern then silence. 20 picks Apr 26 alone, 2 picks Apr
25, NOTHING since Apr 27.

### Why no active picks

1. **PR #519 (b218cb7ba2 merged Apr 29)** removed
   `baby_strats_forward::atr_percentile_gate` from kill_list on origin/main.
   Local feat-branch still has it (untracked). After dashboard regen on main,
   this blocker clears.
2. **Score floor blocks all picks**: 100% of closed picks have score < 50
   (avg 44.7, max 45). Any active gate using `score >= 50` cuts every pick.
   Most likely the strategy never produces score >= 50 because the scoring
   formula penalises BTC-only single-symbol strategies.
3. **Confidence floor**: 27% of picks have confidence < 0.50; 100% < 0.55.
4. **trust_tier=WATCH** (not RELIABLE/PROVEN).
5. **The strategy module name mismatch** noticed in `proven_edge_strategies.py:990`
   — emits `strategy: "atr_percentile_gate_scanner"` (with `_scanner` suffix),
   but closed picks are tagged `atr_percentile_gate`. The mapping is
   happening somewhere in the resolver chain. Worth confirming the live
   emission path is consistent (otherwise PR #519's whitelist fix may not
   match the actual emit name).

### Per-direction & symbol-level

100% BTCUSDT LONG. Tight 2.5x ATR TP / 1.5x ATR SL — small edge per trade,
but consistent. Avg win 0.48%, avg loss -0.74%, R:R 1.67.

### Why the burst-then-silence?

Likely volatility regime dependent — the strategy fires only when ATR
percentile is in 35-97 range and EMA9 > EMA21 etc. (`proven_edge_strategies.py:931+`).
When BTC volatility flatlines outside the goldilocks band, the gate stays
closed. This is **correct behaviour**, not a bug.

### Quick-win

**No 1-line fix is appropriate** — multiple AI panelists urged caution. n=22
is below candidate floor; the burst-pattern means the n we have is from a
single 2-day vol regime. Forcing promotion now would expose us to
regime-shift fragility.

Conditional fix worth queueing (not this week):
- After n>=30 organic emission (likely 3-5 weeks at burst cadence), revisit
  whether to add a `score_gate_exempt` for strategies meeting (n>=30, WR>=80,
  PF>=3) — Cerebras gpt-oss-120b's suggested rule.

**Estimated weekly volume**: unpredictable (regime-dependent). Recent burst
was 20 picks in 1 day; could be 0 picks for 2 weeks.

### Fragility

- **High** — n=22, single asset (BTCUSDT), single direction (LONG), single
  2-day window (Apr 25-27). Effectively **one regime, one symbol**.
- Burst pattern is the largest red flag. The strategy may have produced
  20 correlated picks during one BTC ATR-band crossing — the n=22 is closer
  to **n=2 independent regimes** statistically.
- Tight TP/SL means a single SL_HIT represents -0.74%, but the small avg_win
  +0.48% means even a small WR drop (95% → 75%) inverts profitability.

---

## AI panel verdicts (3-AI consensus)

### Q1: Which to prioritize for promotion intervention?

| AI | Priority order |
|----|----------------|
| Cerebras qwen-3-235b | A (only) |
| Cerebras gpt-oss-120b | A only — focus there |
| Ollama gpt-oss:20b | A > C > B |

**Consensus**: **A first, alone**. C is borderline (gpt-oss:20b suggested
score-gate relaxation, but qwen and gpt-oss-120b both said small-n + burst-
pattern fragility argues for waiting).

### Q2: Highest-leverage 1-line fix per strategy

| Strategy | Convergent fix |
|----------|----------------|
| A | Remove from `_PAPER_ONLY_STRATEGIES` and from `core_whitelist.json` kill_list (all 3 AIs agreed) |
| B | No 1-line fix — wait for n>=30 (qwen, gpt-oss-120b); manual emit-trigger (gpt-oss:20b — minority view) |
| C | Score-gate exemption (gpt-oss:20b, gpt-oss-120b) OR wait for n>=30 (qwen) |

### Q3: Fragility ranking

All 3 AIs ranked: **C most fragile (BTC-only, burst, n=22) > B (LONG-only,
small-n) > A (low-fragility, n=205, symmetric)**.

### Q4: Should 0.55 conf / 50 score floors be relaxed?

| AI | Position |
|----|----------|
| qwen | Keep rigid; relax only with n>=200 + WR>=55 + MDD<15 |
| gpt-oss-120b | Keep conf rigid; relax score to 45 if WR>=50 AND PF>=1.5 |
| gpt-oss:20b | Keep rigid in general; case-by-case relaxation only with operator approval |

**Convergence**: keep rigid for now. Conditional relaxation (n>=200 + WR>=50 + PF>=1.5
→ score floor 45) would help A but doesn't matter for B/C (sample-starved).

### Q5: Symmetric LONG/SHORT + 50/50 TP/SL — argues FOR or AGAINST trusting A's edge?

| AI | Verdict |
|----|---------|
| qwen | FOR — balanced, non-noise edge |
| gpt-oss-120b | FOR (mostly) — non-directional signal, but caveat that modest 1.66 PF could still be chance over 205 trades |
| gpt-oss:20b | FOR — systematic, not lucky direction-pick |

**Convergence**: **FOR**. Edge comes from win-magnitude > loss-magnitude
asymmetry (2.21% / 1.45% = 1.52x), not direction selection — that's a
genuine signal, not a directional bet.

---

## Recommended next-actions (ranked)

1. **A — luxalgo_confluence: unblock at config layer** (this week, separate PR)
   - Remove from `_PAPER_ONLY_STRATEGIES` (alpha_engine/strategy_blocklist.py)
   - Remove `luxalgo_confluence` AND `luxalgo_filters::luxalgo_confluence` from
     core_whitelist.json kill_list
   - Refresh `last_kill_run` to today so the 21d auto-expiry doesn't fire on
     unrelated entries
   - Add anti-regression test pinning the strategy to active-eligible
   - Investigate symbol blacklist for SOL/JUP/BTC (separate PR; do not gate
     the unblock on this)
   - Expected weekly impact: ~110 picks/wk restored, +1.66 PF contribution

2. **B — rs-breakout-scout: passive monitor**
   - No code change. Re-evaluate at n>=30 (~Apr 30 - May 7 at current cadence)
   - Consider `kimi_riseoftheclaw` source-tier escalation review (separate
     P2 task)

3. **C — atr_percentile_gate: passive monitor + integrity check**
   - Verify the strategy-name resolver chain: emitter writes
     `atr_percentile_gate_scanner`, dashboard tags `atr_percentile_gate`.
     If a regression strips the `_scanner` suffix asymmetrically, PR #519's
     fix may not match. (~30 min investigation; not a code change.)
   - Re-evaluate at n>=30 organic emission. Could take 2-5 weeks given
     burst regime dependency.

---

## Red flags & fragility summary

- **A**: low fragility, BUT 10-day observation window is short. The 1.66 PF
  could be partly transient. Treat as Tier-2 candidate, NOT Tier-2 PROVEN
  until n>=400 (or 3+ weeks at current cadence).
- **B**: medium-high fragility, n=23 is too small. Don't force.
- **C**: HIGH fragility. **DO NOT promote this week**. Single asset, single
  direction, two-day burst. Statistically closer to 1-2 independent
  observations than 22.

---

## Path

- Diagnostic: `tmp/diag_output.txt` (per-strategy raw output)
- AI panel responses: `reports/near_miss_deep_dive_2026_04_29/`
  - `cerebras_qwen-3-235b.md`
  - `cerebras_gpt-oss-120b.md`
  - `ollama_gpt-oss-20b-cloud.md`
  - `ollama_deepseek-v3.2-cloud.md` (reasoning-only)
- Prompt: `reports/near_miss_deep_dive_2026_04_29/_PROMPT.md`
- This synthesis: `reports/NEAR_MISS_DEEP_DIVE_2026_04_29.md`
