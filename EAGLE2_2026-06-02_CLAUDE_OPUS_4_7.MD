# EAGLE-2 Enhancement Plan — 2026-06-02 (Claude Opus 4.7)

**Author**: Claude Opus 4.7
**Date**: 2026-06-02
**Predecessor**: `EAGLE_JUNE2_CLAUDE_OPUS_4_7.MD` (commit `a2bc178ad`)
**Trigger**: Second-opinion quant review. Verdict accepted with corrections logged below.

---

## Concessions to the second quant

The second review pushed harder than mine in three places. Accepted:

1. **Portfolio "empty" was a URL/cache artifact, not data.** Live `pf_portfolios.json` shows 81 portfolios, 66 with open positions. `deepseek_v4__aggressive` has 11 open names right now. The earlier "empty" screenshot was bad URL input or stale cache. My EAGLE-1 diagnosis ("no source picks today") was wrong for the cited case — that explanation is reserved for the genuinely-empty subset (~15 of 81).
2. **EQUITY is honest failure, not just methodology.** EAGLE-1 was too easy on EQUITY. The live PF 0.90 / WR 33% / n=33 post-policy-clean is bad deployed strategy quality, not just a measurement artifact. Recency 37→67% over 14d is signal but n is tiny.
3. **Methodology fix alone won't ship money-ready strategies.** Even if EAGLE-1's MC-null fix lands, the **production scanner still emits from a noisier universe than the lab tests**. Closing the lab/production gap is a separate problem from closing the methodology gap.

The second review's clearest contribution: **"research-to-production translation problem"** — the lab has real sleeves, but those are not what dominates live picks. That distinction matters and EAGLE-1 missed it.

---

## Where edge actually lives (corrected)

| Surface | Edge state | Use for |
|---|---|---|
| `/audit/` aggregate money-ready layer | **No deployable edge** — 0/6 classes pass Tier-2 post-policy-clean | Sanity dashboard only. Never size from green cells here. |
| `/audit/ai-tournament.html` + `pf.html` | **Best current paper edge** — deepseek_v4 leads; gpt4o + grok3 secondary | Paper-only learning lab. **Different universe than production Smart Picks.** |
| `/audit/pick_funnel.html` | Discovery surface | Filter R&D. **Not a sizing source** — concentration / dispute / holdout flags reject most surface wins. |
| Lab `verified_strategies/` (VWAPReversion, BollingerMR, ETF Verified DM, Faber TAA) | **Best future production candidates** — all currently shadow tier | Promote via the bridge below. None are ready for capital yet. |

**Capital allocation today: zero outside paper.** Until the bridge is built, nothing on /audit aggregate is sizeable.

---

## The actual root cause: research → production translation gap

The second quant nailed it. The chain breaks here:

```
Lab WF-survivor (e.g. VWAPReversion OOS Sharpe 3.10, n=516, shadow tier)
        ↓
    [GAP — no promotion gate exists]
        ↓
Production scanner (alpha_engine/production_scanner.py) emits from
the FULL strategy universe — includes weak/contaminated emitters
        ↓
Live PF 0.98 on 1085 CRYPTO picks, PF 0.56 on 74 FOREX picks
```

**Two distinct fixes required:**

1. **Lab-side**: EAGLE-1 methodology fixes (MC null, DSR N_trials, PBO, purged WF) so the gate can correctly identify edge.
2. **Production-side (the new thing)**: promotion gate between lab survivors and production emission. Until a strategy clears the gate, its source_system stays out of the live pick pool — regardless of how attractive it looks in the funnel.

---

## EAGLE-2 Enhancement Plan — 4 pillars, 14 actions

### Pillar 1 — Stop the bleeding (this week)

Goal: prevent live sizing from broken classes while fixes land.

| # | Action | File / mechanism | Owner | Status |
|---|---|---|---|---|
| 1 | **Freeze FOREX emission** | `BLOCKED_ASSET_CLASSES += {"FOREX"}` in `audit_trail/quality_gates.py:1725` | code | Was set 2026-05-28, **verify still active**; if reverted, re-add |
| 2 | **Freeze COMMODITY emission** until COT lag forensics complete | `BLOCKED_ASSET_CLASSES += {"COMMODITY"}` + remove CT=F from universe | code | New |
| 3 | **Freeze FUTURES emission** (n=2 is not a class) | `BLOCKED_ASSET_CLASSES += {"FUTURES"}` | code | New |
| 4 | **Run zoo's 367-row sign-flip purge** in staged order: luxalgo 6 → ml 15 → battleground 63 → mega 141 → kimi 142 | `audit_trail/sign_flip_purge.py --apply` (PR #433 already shipped the tool) | operator | Pending |
| 5 | **Set `SIGN_FLIP_BASELINE=0`** repo variable after purge | GitHub repo settings | operator | Pending |
| 6 | **Land PR #437** (tournament resolver chunked executemany) → unfreezes `/audit/ai-tournament.html` mark-to-market | already open | merge | CI pending |

### Pillar 2 — Lab-side methodology (next 2 weeks)

Goal: make the gate correctly identify edge. From EAGLE-1, in priority order.

| # | Action | File:line | Effort |
|---|---|---|---|
| 7 | **Fix MC null hypothesis** — bootstrap-with-replacement → block bootstrap for trend strategies; random-trade-entry on same price series for mean-reversion | `verified_strategies/strategy_verification_engine.py:243-245` | 1 day |
| 8 | **Wire DSR `n_trials` to real hypothesis-registry count** | `alpha_engine/rigorous_backtest_harness.py:61` + read from `reports/hypothesis_registry.json` | 0.5 day |
| 9 | **Fix PBO to use real parameter-grid k-fold partitions** — the 8-fold purged WF at `rigorous_backtest_harness.py:249-320` is already coded but never called. Wire it. | `rigorous_backtest_harness.py:391-395` + wire 249-320 | 1 day |
| 10 | **Walk-forward: 8-fold purged + embargoed** — embargo = max hold period, purge gap = lookback window | `verified_strategies/walkforward_suite.py:50-62` | 1 day |
| 11 | **Per-class realistic slippage** — futures micro-contract spread, FX pip-cost, crypto taker tier | `verified_strategies/strategy_verification_engine.py` cost block + per-class config | 0.5 day |

### Pillar 3 — Build the promotion bridge (NEW — the second quant's contribution)

Goal: lab survivors flow into production scanner under a controlled gate. No more "interesting cell = sizeable."

| # | Action | Detail |
|---|---|---|
| 12 | **Promotion gate spec** — a strategy enters the production scanner ONLY when ALL of: (a) Lab passes corrected MC + DSR + PBO + purged WF, (b) Block-tier verdict in CLAUDE.md asset-class table moves from FAIL → INSUFF-N or better, (c) 30-day shadow paper PF stays within 30% of OOS lab PF, (d) Concentration index (HHI on source_system) < 0.30, (e) `sign_coherence_check.py` returns 0 flips for the strategy's rows. | New doc: `docs/STRATEGY_PROMOTION_GATE.md`. Encode gate as a function `is_admissible_for_production(strategy_key) -> bool` in `audit_trail/quality_gates.py`. Wire `production_scanner.py` to call it before adding a strategy's emissions to the live pool. |
| 13 | **Decouple research vs production stats surface** — `/audit/` shows production-emitted picks only. Lab/tournament results go to a separate `/audit/lab.html`. Stop using funnel green cells as proof. | Dashboard split. Tournament edge → `/audit/ai-tournament.html` stays paper-only until promotion. |
| 14 | **Capital-staging ladder** — every promoted strategy moves shadow → 0.5× sizing → 1× sizing in 14-day steps, contingent on forward PF holding. Automatic revert to shadow on PF<1 over rolling 14d. | New: `tools/portfolios/capital_staging.py`. Operator approval required at each step initially. |

### Pillar 4 — Per-class action plan

Synthesizing both reviews, the cleanest per-class actions:

| Class | EAGLE-1 + 2 verdict | Concrete next 30 days |
|---|---|---|
| **ETF** | **Best deployable candidate** (Verified DM PF 1.60, n=104, WR 53.8%). Sample too small. | Run full sector universe (XLE/XLU/XLV/XLI/XLF/XLK/XLY/XLP/XLC) for 30d shadow. If forward PF holds, this becomes the first production-promoted strategy. |
| **CRYPTO** | Live aggregate is breakeven (PF 0.98). Lab VWAPReversion + BollingerMR + DualMomentum pass WF. | (a) Fragment VWAPReversion: 10% cap per symbol. (b) Run 30d shadow paper alongside production. (c) Diagnose 1864 duplicate signal-ts + EXPIRED→WON mislabels in `feed_hygiene.py`. (d) Audit `claude_gainer_st` 91.7% concentration. |
| **EQUITY** | Honest failure. PF 0.90 / WR 33% / n=33. Faber TAA SPY is decent but small n (=11). | Sector-gate Faber TAA on XLE/XLU/XLV/XLI/XLK. Backtest cumulative n target >50. Run shadow paper. |
| **FOREX** | Freeze. kimi sign-flip evidence (142/367 = 38.7%). USDJPY 55% concentration. 8× vol mismatch with crypto. | (a) Freeze emission. (b) Sign-flip purge (action #4). (c) Rebuild with ATR-normalized thresholds + per-pair vol scaling. (d) Inverse-test kimi only after #4 completes. (e) 30d paper before any live resume. Floor: PF>1, WR>45% on 30d paper. |
| **COMMODITY** | Kill until COT lag forensics complete. CT=F 57% concentration. `cot_positioning` post-dedup PF dropped 4.6 → 0.51. | (a) Enforce 3-day COT publication lag at signal receipt. (b) Remove CT=F from universe. (c) Rebuild commodity scanner with broadened symbol set (GC=F, SI=F, NG=F, HG=F, ZC=F). (d) 60d post-fix live test. |
| **BOND** | Cold start. n=11 since FRED 2026-05-03. Resolver risk on fixed-income sign convention. | Paper-only 60d on HYG/LQD. Check `sign_coherence_check.py` BOND subset. Parameter grid on credit-spread thresholds. |
| **FUTURES** | Not a class (n=2). | Freeze. No revival without COT lag fix + slippage-adjusted BT + 50 paper trades. |

---

## Anti-pattern checklist (avoid going forward)

The second quant's "what you are doing wrong" list — encoded as **rules**:

1. **Never size from `/audit/` aggregate green cells.** Money-ready policy-clean layer only.
2. **Never confuse tournament edge with production edge.** Different universes. Different admissibility pipelines.
3. **Never promote a strategy where one source_system contributes >30% of picks.** HHI gate enforced at `quality_gates.py`.
4. **Never trust raw funnel green cells without dispute-flag check.** The "78.9% CRYPTO Smart-Picks" banner exists for a reason.
5. **Never invert a strategy blanket-wide.** Inversion only after explicit OOS proof on the specific signal. FOREX kimi may qualify after sign-flip purge; nothing else.
6. **Never widen the emitter pool to compensate for weak signal.** Breadth ≠ edge.
7. **Never accept high-WR + low-PF as edge.** Classic mean-reversion catches-falling-knives pattern (cf. ConnorsRSI2 confirmed dead: WR 60-69%, PF 0.95).
8. **Never run sign-coherence with non-zero baseline.** Set `SIGN_FLIP_BASELINE=0` after purge.

---

## Capital sequencing — what gets size when

| Strategy | Asset class | Today | After Pillar 2 (lab fixes) | After 30d shadow | After 60d sized paper |
|---|---|---|---|---|---|
| ETF Verified Dual Momentum | ETF | shadow | shadow + tighter gate | 0.5× live | 1× live if forward PF in [1.4, 1.8] |
| Faber TAA (sector-gated) | EQUITY | not yet | shadow | 0.5× live if WR holds | 1× live |
| VWAPReversion (symbol-fragmented) | CRYPTO | shadow | shadow + symbol caps | 0.5× live if 30d PF >1.2 | 1× live |
| BollingerMR | CRYPTO | shadow | shadow | 0.5× live cautiously (n=126 still small) | 1× live |
| DualMomentumCrypto | CRYPTO | shadow | shadow | 0.5× live | 1× live |
| HYG/LQD Credit Momentum | BOND | not started | paper 60d | sized after 60d clean | — |
| Anything FOREX / COMMODITY / FUTURES | — | frozen | frozen | frozen | only after class-specific forensics complete |

---

## Operator decision points (you, this week)

1. **Approve Pillar-1 actions #1–#3 (freeze FOREX + COMMODITY + FUTURES emission).** Reversible config change.
2. **Approve PR #433 staged purge** (action #4) and set `SIGN_FLIP_BASELINE=0` (action #5).
3. **Merge PR #437** (action #6).
4. **Approve Pillar 3 promotion gate** — needs your sign-off because it changes how strategies reach capital. The doc + gate function are a 1-PR change.
5. **Pick a single strategy for the first capital-staging run.** EAGLE-2 recommendation: **ETF Verified Dual Momentum** — best risk-adjusted (Sharpe 1.91, MDD acceptable, n=104), simplest universe (8 ETFs), cleanest data feed (yfinance), no resolver/sign-flip risk.

---

## Why this plan beats EAGLE-1

EAGLE-1 was right on methodology but light on the production-translation question. EAGLE-2 keeps the methodology fixes (Pillar 2) and adds:

- **Pillar 1** — explicit freeze to stop bleeding while fixes land
- **Pillar 3** — the promotion bridge, which is what actually stops lab/production drift
- **Pillar 4** — per-class action plan, not just per-class diagnosis
- **Anti-pattern rules** — codified into the gate so they don't re-emerge
- **Capital sequencing table** — shows exactly when each survivor moves and on what evidence

If both pillars 1+2 land, the noise floor on `/audit/` drops materially within 14 days. If Pillar 3 lands, the divergence between lab and production stops growing. If Pillar 4 executes, the first money-ready strategy reaches 0.5× capital in ~45 days.

**No part of this is "wait longer." Every action is mechanical, time-bounded, and verifiable.**

---

## Companion artifacts

- `EAGLE_JUNE2_CLAUDE_OPUS_4_7.MD` — methodology review (commit `a2bc178ad`)
- PR #435 — Binance 451 failover (merged)
- PR #437 — tournament resolver chunked executemany (open, fixes May-30 stale mark)
- PR #434 — nightly sign-coherence gate (open, regression detector for purge)
- PR #433 — sign-flip purge tool (merged, awaiting staged operator run)
- `reports/asset_class_backup_plans_2026-06-02.md` — grok-gx10 session backup plans per class
- `reports/hypothesis_registry.json` — H-102 (Connors crypto), H-103 (symbol-quality filter) pre-registered

**Filed**: `EAGLE2_2026-06-02_CLAUDE_OPUS_4_7.MD`
