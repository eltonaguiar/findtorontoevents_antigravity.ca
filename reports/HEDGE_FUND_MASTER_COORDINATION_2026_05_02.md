# Hedge-Fund Master Coordination — 2026-05-02

**Purpose:** Single navigation index over the avalanche of peer-AI work that landed today on the hedge-fund-quality push. Eight independent agents (Kimi PRs #658/#660/#661, Cursor playbook, Copilot 14-section action plan, Grok feedback, Gemini Antigravity resolved plan, ChatGPT Codex action plan, plus 4 internal subagents and 2 DeepSeek-Reasoner external reviews) converged on the same problem in parallel. This doc is the **decisive synthesis + reference index**, not a 50-page rewrite.

---

## TL;DR (read this first)

1. **Do NOT auto-merge Kimi PRs #660 + #661.** Both silently revert PR #659 (which merged 8 minutes earlier), PR #660's configs are wired to a dead module (zero runtime effect), PR #661 has a fatal `ImportError` on first import, and PR #661 falsely claims to add `statistical_rigor.py` (already shipped in PR #626). REQUEST_CHANGES posted on both. Authoritative reviews: `reports/KIMI_PR660_REVIEW_2026_05_02.md`, `reports/KIMI_PR661_REVIEW_2026_05_02.md`, `reports/DEEPSEEK_PR660_661_REVIEW_2026_05_02.md`.
2. **PR #658 (Kimi 36k-word audit) → MERGE-AS-DOCS, DO-NOT-AUTO-ACTION.** The PR is a faithful mirror of the docx, but the docx itself derives all numbers from a stale `n=506` snapshot (current repo: `n=7,445+` to `n=10,674` per Codex). Three-AI gap synthesis on PR #662. PNG bytes ship via PR #663 (Kimi attachment ZIP — PR #658 has 0-byte placeholders).
3. **Phase 0 is mostly already done.** Per Gemini Antigravity's line-by-line audit, **9 of 13** recommended emergency items are already implemented in current `main`. Only **4 actions remain**, all small, all with default-OFF + 14-day shadow envelope. Authoritative implementation plan: `C:\Users\zerou\.gemini\antigravity\brain\92f5efae-b91b-4433-9010-06a333c30147\implementation_plan.md.resolved` (10 KB, includes line-precise code patches). Do not re-derive — point at this and ship.
4. **Highest-ROI immediate fix:** the kill-list **enforcement** is decorative. `quan_engine_scalp` is on `BLACKLISTED_STRATEGIES` since 2026-04-02 but still appears 6+× in `closed_picks.json` (per Copilot §14 of `reports/HEDGE_FUND_ACTION_PLAN_2026_05_02.md`). Fix the filter that's supposed to apply the blacklist before pick emission. **30-minute change.**
5. **Where users should click on `/audit`:** CRYPTO/EQUITY/FOREX → **High Conviction** button; COMMODITY → **Verified Alpha**; BOND → wait (n<30); ETF/FUTURES → don't trade (PF<1). Detail in subagent report `reports/AUDIT_UI_SURFACE_GUIDANCE_2026_05_02.md`.
6. **TP/SL "ideal" via Kimi PRs alone? NO.** Use ATR formula via the orphan `alpha_engine/adaptive_stops.py` (509 lines, MFE/MAE-calibrated) behind an env flag with 14-day shadow. Gemini verified the file exists; my orphan-hunt subagent ranked it as a top wire-up. Full protocol: `reports/DEEPSEEK_INTERVENTION_PROTOCOL_2026_05_02.md` Section D.

---

## 1. Cross-AI Verdict Matrix

Every reviewer reached compatible verdicts on the load-bearing questions. Where they diverged, the resolution column gives my final call backed by file:line evidence.

| Question | Kimi (PR #658) | Cursor (playbook) | Copilot (action plan) | Grok | Gemini Antigravity | Codex | DeepSeek (×2) | My subagents (×4) | **Verdict** |
|---|---|---|---|---|---|---|---|---|---|
| Kimi PR #660 mergeable? | (self-yes) | n/a | n/a | (silent) | (silent) | "live code disagrees" | **FORCE-REWRITE** | **REQUEST_CHANGES** | **REQUEST_CHANGES** |
| Kimi PR #661 mergeable? | (self-yes) | n/a | n/a | (silent) | (silent) | (silent) | **FORCE-REWRITE** | **REQUEST_CHANGES** | **REQUEST_CHANGES** |
| Suspend Crypto C-Tier | TRUE (P0) | TRUE | TRUE | TRUE | **NOT IMPLEMENTED yet** + line-precise patch | TRUE | flagged: n=50 statistically thin | NOT IMPLEMENTED today | **DO IT** behind `HF_CRYPTO_CTIER_ENABLED` env flag default-off |
| Disable `SMART_PICKS_CRYPTO_LONG_ONLY` | (silent) | (silent) | YES (verified line 534) | YES | YES (line 534, with `CRYPTO_SHORT_REGIME_GATE_ENABLED` safety net) | YES | (silent) | confirmed line 534 | **FLIP** with regime-gate safety net |
| Replace `elite_score` w/ `ml_score` | TRUE | (caution) | (with addendum) | TRUE | already disabled; **add dual-path gate** behind `use_ml_score_gate=false` | TRUE | flagged: -0.17 corr needs DSR | already disabled at line 256 | **DUAL-PATH SHADOW** per Gemini's patch |
| ATR-based SL/TP | (silent) | YES | YES | YES | YES — `adaptive_stops.py` exists, 509 lines, orphan | YES | YES (Section D) | top orphan goldmine | **WIRE** `adaptive_stops.py` behind env flag |
| Toxic-strategy enforcement bug | (silent) | (silent) | YES (§14: blacklist is decorative) | (silent) | (silent — assumed working) | (silent) | (silent) | n/a | **FIX FILTER** (highest ROI) |
| UNKNOWN reclassification | (silent) | (silent) | YES | YES | YES — line-precise patch sketched | YES | YES (Section E.5) | n/a | **DO IT** symbol-pattern router |
| `WINNER_FILTER` recommendation | TRUE (abolish) | (uses) | (uses) | inherits | **Never existed** — full ripgrep returns zero matches | n/a | flagged: data-snooping risk | confirmed never exists | **NO-OP** — claim is from stale corpus |
| Score floor 40 | (silent) | (uses) | (uses) | YES | already set at `hc_filter.js:24` | YES | (silent) | n/a | **already done** |
| Best UI surface for trading | (silent) | Active+HC, then Verified Alpha | (mentions HC) | HC + Verified Alpha | (silent) | n/a | (silent) | per-class table | **per-class** (see §3) |

---

## 2. The 4 Remaining Phase-0 Items (per Gemini's surgical plan)

Gemini Antigravity verified the codebase line-by-line. Of the 13 items everyone has been recommending all day, only 4 remain. Their resolved plan has copy-pasteable code patches. **Do not re-derive these** — use Gemini's plan as the implementation spec.

| # | Action | Effort | File:line | Env-flag default | Safety net |
|---|---|---|---|---|---|
| 1 | **Suspend Crypto C-Tier** | ~1 h | `alpha_engine/hedge_fund_quality_gate.py:238` (block before banned-symbol check) | `HF_CRYPTO_CTIER_ENABLED=0` (off) | flip env to re-enable; 48 h shadow log clean = done |
| 2 | **Disable `SMART_PICKS_CRYPTO_LONG_ONLY`** | ~10 min | `audit_trail/quality_gates.py:534` flip `True → False` | n/a (one-line flip) | `CRYPTO_SHORT_REGIME_GATE_ENABLED=1` blocks shorts in bull regime; `CRYPTO_SHORT_DISABLED=1` is full kill-switch |
| 3 | **Add `ml_score` gate (shadow mode)** | ~2 h | `alpha_engine/hf_quality_gate.py:100-102` dual-path | `use_ml_score_gate=false` | flip after 14-d shadow proves ≥5% WR improvement vs elite_score |
| 4 | **UNKNOWN reclassification** | ~4 h | `signal_aggregator/picks_router.py` (new function) or `audit_trail/quality_gates.py` | — | symbol-pattern: `*USDT/*USDC` → CRYPTO; `*=X` → FOREX; `*=F` → COMMODITY; 1-5 uppercase + ETF list → ETF; fallback UNKNOWN |

**Plus Copilot's §14 finding (highest ROI of all):** the **toxic-strategy kill-list enforcement filter is broken** — `quan_engine_scalp` is on `BLACKLISTED_STRATEGIES` since Apr 2 but still appears in live `closed_picks.json`. Fix the filter that's supposed to apply the blacklist (verify in `alpha_engine/scanner.py` or `production_scanner.py`). **30-minute change, biggest single PnL lift in the repo.**

## 3. Per-Asset-Class Action Verdict (today)

| Class | HC-pass status today | Triage verdict | Concrete next action |
|---|---|---|---|
| **EQUITY** | PF 4.05, WR 68.1% n=72 (post `scoreFloorEquity` 55→45 on 2026-04-30) | **SCALE** to 30-40% allocation | Continue lowered floor; wire `consensus_tier.py` (orphan goldmine #1) for cross-system confirmation |
| **CRYPTO (S/B/A)** | FWD 60%, n=562 validated edge | **HOLD + selective SCALE on B-Tier L20** | Suspend C-Tier (Gemini Action 1, default-off flag); wire `adaptive_stops` ATR SL/TP; flip `LONG_ONLY=False` (Gemini Action 2) |
| **FOREX** | WR 65.8% (HC pass with auto-relax) | **HOLD + paper-trade-recovery validation** | Verify `outcome_resolver.py` v2.1 deployed; 14-day forward check; pre-register "trusted filter" criteria before any capital |
| **COMMODITY** | PF 1.28 inconclusive | **HOLD via Verified Alpha only** | No new strategy deployment; collect 30 more trades; check CFTC COT free data |
| **BOND** | n=8 insufficient | **HOLD — insufficient_data** | Lower elite_score floor 30→15 behind flag; collect to n=30 |
| **ETF** | PF 0.28 (DEAD) | **KILL or SHRINK** | Suspend new ETF picks; investigate filter-starvation root cause |
| **FUTURES** | WR 5.9% n=2 | **NEW_STRATEGY_DEPLOY** | Triple-screen rebuild from scratch; no capital until n>=30 with PF>=1.2 |

## 4. Direct Answers to Operator's Specific Questions

### Q: "Are you SURE the Kimi PRs make TP/SL ideal?"

**No.** PR #660's configs are wired to a dead module → $0 net runtime effect; PR #660 + #661 silently revert PR #659; "ideal" TP/SL requires per-asset ATR calibration + 14-day shadow + automated rollback — none of which are in Kimi's PRs. Use `alpha_engine/adaptive_stops.py` (already exists, orphan, 509 lines, MFE/MAE-calibrated) behind env flag with 14-day shadow. See DeepSeek Section D for the full ATR / structural-level / Kelly-sized variants.

### Q: "Where on `/audit` should users find investables?"

Per UI subagent (`reports/AUDIT_UI_SURFACE_GUIDANCE_2026_05_02.md`):

- **CRYPTO** → click **High Conviction** (WR 60.3%, n=562 validated)
- **EQUITY** → click **High Conviction** (WR 68.1%, n=72, strongest edge)
- **FOREX** → click **High Conviction** + age≤48 h filter (WR 65.8%, smaller sample; auto-relax 70→65 if n<20)
- **COMMODITY** → click **Verified Alpha** (HC rejects as "WEAK"; PF 1.28 inconclusive)
- **BOND** → do not trade yet (n=8)
- **ETF / FUTURES** → do not trade (PF<1)

UI honesty disclosure: **Smart Picks** claims 62% score-profit correlation but cannot be validated on closed-trade data (6-dimension fields missing from historical records). Use it as a **live overlay only**, not a primary execution surface, until the historical-field gap closes.

### Q: "Do we have orphan code that's literally a goldmine?"

Top 5 ranked by (impact ÷ wire-up effort), per `reports/ORPHAN_GOLDMINE_HUNT_2026_05_02.md`:

| Rank | Module | Effort | Expected lift | Wire-up sketch |
|---|---|---|---|---|
| 1 | `alpha_engine/consensus_tier.py` | 1.2 h | +3-5 pp smart_picks WR | `quality_gates.calculate_smart_score()` after the trust component (line 4337); continuous-gradient bonus |
| 2 | `alpha_engine/dsr_pick_filter.py` | 2.5 h | filters ~15% noise; +0.8 pp aggregate Sharpe | pre-`passes_active_gate()` in `dashboard_generator.py:13397` |
| 3 | `ml_gatekeeper/gatekeeper.py` | 2 h | +2-3 pp WR (ML model trained on 3,500+ real closed picks) | `quality_gates.calculate_smart_score()` — multiply `pick_quality_prob` into `elite_score` |
| 4 | `alpha_engine/kelly_position_sizer.py` | 1.5 h | +2 pp Sharpe via risk normalization | scale existing 1-call site in `production_scanner.py` to also run in `dashboard_generator.py` final write |
| 5 | `alpha_engine/regime_flip_detector.py` | 2.75 h | +1-2 pp WR via adaptive thresholds | start of `dashboard_generator.main()`; widens stops in choppy regime |

Plus Gemini's flagged `alpha_engine/adaptive_stops.py` for the SL/TP wire-up. All wire-ups must ship default-OFF behind their own env flag with 14-day shadow per CLAUDE.md. Total wall-clock to wire top 5 in parallel: **~9 hours**.

## 5. Free-Data + GH-Library Stack (operator picks 5+5)

Per `reports/FREE_DATA_AND_LIB_CATALOG_2026_05_02.md`:

**Top 5 free APIs to add ($0):**
1. **CoinGlass** — funding rates (Binance perp arb gate)
2. **DeFiLlama** — TVL + on-chain liquidity (memecoin liquidity gate)
3. **CFTC COT** — commercials net positioning (commodity bias)
4. **CEFConnect** — NAV + discount Z-score (CEF mean-reversion sleeve, replaces mutual-fund interest)
5. **Alpaca free tier** — IEX intraday equity bars (penny stock liquidity gate; beats Polygon free which is EOD-only)

**Top 5 GH libraries** (most already pinned in `requirements-hedge-fund.txt` / `requirements-validation.txt`):
1. **`vectorbt`** — primary backtester (already pinned)
2. **`bashtage/arch`** — block bootstrap (StationaryBootstrap) for CI estimation; already in `requirements-validation.txt`
3. **`statsmodels`** — FDR multiple-testing correction (Benjamini-Hochberg)
4. **`PyPortfolioOpt`** (HRP allocator) — already in `requirements-hedge-fund.txt`
5. **`timeseriescv`** — CPCV / purged k-fold (already in `requirements-validation.txt`; AGPL-free alternative to mlfinlab)

**Do NOT add** mlfinlab (AGPL conflict per repo's own `requirements-validation.txt` rationale), `zipline-reloaded` (wrong fit), `Backtrader` (slow + maintenance-stalled), or generic `ta` (violates Wire-Up Rule).

## 6. Niche Playbooks (one-liner each)

- **Penny stocks (sub-$5 equities):** Alpaca IEX free intraday + ADV $500k filter + spread 50bps + float 5M + no S-1-in-5d gate; momentum-after-50-SMA-cross with 1.5×ATR SL.
- **Meme coins:** LunarCrush (already wired) + Santiment + CoinGlass funding + DeFiLlama TVL; mcap $50M floor + AltRank top-100 + funding < +0.1%/8h + 3 CEX listings + $5M 24h vol; cap allocation 5% of book.
- **Mutual funds → CEFs:** CEFConnect Z-score mean-reversion (enter when discount > 2σ below 60-day mean; exit at mean or +1σ); academic basis Berk & Stanton + MDPI 2023 ARDL paper.
- **Toxic-strategy autopsy:** grep last 30 days of `closed_picks.json` for kill-list strategies; if any appear, the enforcement filter is broken — fix that **before** anything else.
- **UNKNOWN reclassification:** 410 picks deliver 45.37% WR + best avg PnL — likely mis-classified equities/ETFs in crypto pipeline; Gemini Action 4 has the symbol-pattern router sketch.

## 7. Foolproof Intervention Protocol (8 sections)

Full 17 KB protocol at `reports/DEEPSEEK_INTERVENTION_PROTOCOL_2026_05_02.md`. One-line orientation per section:

- **A — Edge Diagnosis (Day 1, ~4 h):** SQL/grep recipe → per-asset edge report (WR, PF, Sharpe, n, DSR, MDD, current gate effectiveness)
- **B — Triage Decision Tree (Day 2):** KILL / SHRINK / HOLD / SCALE / NEW_STRATEGY_DEPLOY pseudocode with burden-of-proof to flip state
- **C — Backtest → Paper → Live Promotion Gates (Weeks 1-12):** 5-fold CPCV CI lower bound, walk-forward instability < 0.5, PBO < 0.30, 30-day paper, $1M → $5M → $25M ramp with auto-demotion on -5% day
- **D — TP/SL Determination Protocol:** ATR (SL = -1.5×ATR(14), TP = +2×ATR(14)) + structural-level + Kelly-sized variants, all gated through `forward_validator.py`
- **E — Niche playbooks:** penny stocks, meme coins, CEFs, toxic-strategy autopsy, UNKNOWN reclassification
- **F — Top 5 free APIs + top 5 GH libs**
- **G — 12-step algorithm an autonomous IDE agent can copy-paste**
- **H — 5 NEVERs + 5 ALWAYSes guard rails**

## 8. Five NEVERs + Five ALWAYSes (operator guard rails)

**NEVER:**
1. Merge a "P0 emergency" PR that hasn't shown a `git diff origin/main` line count matching the PR body's claimed file count.
2. Flip an `enabled: false → true` config without `git log -p` on the file (false may be deliberate safety, not accident).
3. Auto-action a recommendation derived from a stale data snapshot — refresh against current `audit_dashboard/data/dashboard_data.json` first.
4. Skip the Wire-Up Rule (CLAUDE.md): every new module needs a production caller path or `## Wiring Plan` section.
5. Expand the whitelist without a 60-day forward-WR sanity check.

**ALWAYS:**
1. Ship production-behavior changes default-OFF + 14-day shadow + automated rollback (revert if PF<1.0 on rolling 20-trade window).
2. Run `git stash && git pull --rebase origin main && git stash pop` before any push (CLAUDE.md rule; chaotic peer-coordination pattern in this repo demands it).
3. Cross-AI-verify any "kill X immediately" recommendation against actual current code state (multiple peers have inherited Kimi's stale claims uncritically).
4. Treat orphan modules as evidence wiring is the highest-leverage work — wire 5 existing orphans before writing 1 new module.
5. Refresh the headline dataset metric (`n=506 → n=7,445+`) at the start of every audit document so future readers don't act on stale snapshots.

---

## 9. Reference Index — All Contributing AI / Peer Reviews

### My subagent + DeepSeek output (this session)
- `reports/KIMI_DOCX_VS_PR658_GAPS_2026_05_02.md` — Kimi PR #658 doc-fidelity gap inventory
- `reports/KIMI_PR658_THREE_AI_GAP_SYNTHESIS_2026_05_02.md` — 3-AI verdict on the docx (PR #662)
- `reports/KIMI_PR660_REVIEW_2026_05_02.md` — silent-revert + dead-config review
- `reports/KIMI_PR661_REVIEW_2026_05_02.md` — fatal ImportError + duplicate `statistical_rigor.py`
- `reports/DEEPSEEK_PR660_661_REVIEW_2026_05_02.md` — DeepSeek's external view on the two CODE PRs
- `reports/DEEPSEEK_INTERVENTION_PROTOCOL_2026_05_02.md` — 17 KB foolproof 8-section protocol
- `reports/AUDIT_UI_SURFACE_GUIDANCE_2026_05_02.md` — UI tab/filter audit
- `reports/ORPHAN_GOLDMINE_HUNT_2026_05_02.md` — top 10 orphan goldmines + wire-up sketches
- `reports/FREE_DATA_AND_LIB_CATALOG_2026_05_02.md` — per-asset-class API + library catalog
- `reports/GROK_PLAN_CROSSCHECK_2026_05_02.md` — cross-check of Grok's two MDs against current state

### Peer-AI side
- `reports/HEDGE_FUND_QUALITY_INTERVENTION_PLAYBOOK_2026_05_02.md` — Cursor (17 KB, well-structured per-asset playbook + UI workflow)
- `reports/HEDGE_FUND_ACTION_PLAN_2026_05_02.md` — Copilot/Claude Opus (with §14 addendum: blacklist enforcement is decorative)
- `reports/HEDGE_FUND_PHASE0_ACTION_PLAN_2026_05_02.md` — newer Phase 0 v2 from peer
- `reports/HEDGE_FUND_UPLIFT_ROADMAP_2026_05_02.md` — peer roadmap doc
- `reports/HEDGE_FUND_ENHANCEMENT_PR_2026_05_02_VERBATIM.md` — Cursor (docx-to-MD verbatim)
- `reports/HEDGE_FUND_ENHANCEMENT_DOCX_CODEBASE_REVIEW_2026_05_02.md` — Cursor (codebase comparison, on PR #663 branch)
- `updates/2026-05-02-hedge-fund-enhancement-pr-feedback.md` — Grok feedback (light, inherits some stale claims; Codex updated same file later)
- `updates/2026-05-02-hedge-fund-foolproof-intervention-plan.md` — Grok plan (light)
- `C:\Users\zerou\.gemini\antigravity\brain\92f5efae-b91b-4433-9010-06a333c30147\implementation_plan.md.resolved` — **Gemini Antigravity 4-action surgical plan with line-precise code patches (canonical Phase 0 spec)**

### Original Kimi corpus
- PR #658 — master 36k-word audit (MERGE-AS-DOCS verdict)
- PR #660 — P0 emergency gate fixes (REQUEST_CHANGES posted)
- PR #661 — infra v2.0 modules (REQUEST_CHANGES posted)
- PR #662 — my 3-AI gap synthesis on PR #658
- PR #663 — Kimi 47-file ZIP attachments (incl. .docx + 18 PNGs that PR #658 has as 0-byte placeholders)

---

**Author:** Claude Opus 4.7 (1M context) — synthesizing 4 internal subagents + 2 DeepSeek-Reasoner external reviews + 6 peer-AI submissions + the original Kimi corpus.

**Recommended operator next-actions (in order):**
1. Ship the **toxic-strategy enforcement-bug fix** (Copilot §14, 30 min, single highest-ROI change in the repo).
2. Ship Gemini's **4 Phase-0 actions** as 4 separate small PRs with default-OFF env flags (~7.5 hours total).
3. Wire the **top 5 orphan goldmines** in parallel (consensus_tier, dsr_pick_filter, gatekeeper, kelly, regime_flip_detector — ~9 hours wall-clock).
4. **REQUEST_CHANGES** on Kimi PRs #660/#661 (already posted; needs author rebase + cleanup).
5. Wait for **14-day shadow data** on every flag flip before any second-order action.

---

## §11. v2.1 Update — Kimi Self-Correction Verified + Cross-Checked (08:30Z)

After this doc's first publish, Kimi shipped PR #660 v2.1 (`f9ae07bbac9`) with their own internal verification (`quant_verification.md`) catching errors in their original PR. Then a 5th internal subagent cross-checked Kimi's v2.1.

### Kimi's self-corrections (good — they caught the right things)

| Original (broken) | Corrected |
|---|---|
| R:R floor 1.5 → 1.25 | KEEP 1.5, ADD ceiling 2.0 (1.25–1.5 band: PF 1.01, Kelly −1.6%) |
| ml_score >= 0.82 | >= 0.90 (0.8–0.9 band: 39.3% accuracy) |
| 24h tracking | 120h (72.7% of picks unresolved at 24h) |
| C-Tier hard suspend | 5% allocation |
| Uniform Kelly 25% | Dynamic by R:R band (11.8% for 1.5–2.0, 0% outside) |

### My subagent's findings on the v2.1 corrections (`reports/KIMI_V2_PLAN_CROSSCHECK_2026_05_02.md`, EDIT_BEFORE_USE verdict)

1. **Headline "PF 5.81 / Kelly +47.2% in R:R 1.5–2.0" rests on n=99 with 49.4% ghost rate and 72.7% unresolved at 24h** — same methodological flaws Kimi used to disqualify the original numbers. No bootstrap CI, no PSR/DSR, no multiple-testing across 5 bands. **Use as A/B-test hypothesis, not a hardcoded threshold.**
2. **MEME class split (n=32, avg PnL −12.96%) is empirically supported.** PENNY (n≈0) and CEF (n=0 in shadow data) are aspirational — move to research backlog, not 12-week timeline.
3. **"16 orphan goldmines" repeats the Grok 2026-04-22 mistake on at least 3 of top 5:** `ml_consensus` is wired at `audit_trail/dashboard_generator.py:3871-3873`, `audit_impact_tracker` has its own `.github/workflows/audit-impact-tracker.yml`, `signal_quality_ml` producer wired at `alpha_engine/scanner.py:2637/:4483`. Re-grep before scheduling any integration work.
4. **"Foolproof 7-step Protocol" cannot run on Day 1** — all 4 cited scripts (`scripts/daily_edge_report.py`, `scripts/audit_unresolved.py`, `scripts/gate_performance_review.py`, `alpha_engine/decay_tracker.py`) don't exist; §9.1 sketch has a `total` NameError. Rewrite around existing tooling.
5. **Config drift confirmed in PR #660 v2.1**: `config/hf_quality_gates.json` still has `min_risk_reward: 0.8` and `enabled: false`. The v2.1 commit (`f9ae07bbac9`) only modified `config/per_asset_thresholds.json`. **One-file follow-up commit needed to align both configs** — comment posted on PR #660.
6. **Don't add yfinance calls** until `outcome_resolver.py:97/:384-405` resolver bug is fixed (independently mandated).

### Bible Designation

Per operator: **`FOOLPROOF_ACTION_PLAN.docx`** (in `kimi_attachments_v2_2026_05_02/planning/`, also persisted as PR #667) is now the canonical reference for any per-asset performance issue. If a class falls below T2 thresholds (PF<1.5, WR<50, MDD>20%), follow that doc's 7-step protocol — but with the corrections from `reports/KIMI_V2_PLAN_CROSSCHECK_2026_05_02.md`:
- Treat the headline numbers (PF 5.81, Kelly +47.2%, +173% killed alpha) as **hypotheses to A/B-test**, not deploy-ready thresholds.
- Use existing tooling (`forward_validator.py`, `walkforward_validator.py`, `quality_gates.py`) for the 7-step loop, not the script names cited (which don't exist yet).
- Re-grep orphan-goldmine claims before integration; 3 of top 5 are already wired.

### Recommended Merge Order (cross-AI agreed)

1. **PR #659** (per-class walkforward UI) — ✅ MERGED 07:36Z
2. **PR #662** (3-AI gap synthesis) — docs-only, mergeable now
3. **PR #663** (Kimi v1 attachments) — docs-only, mergeable now
4. **PR #666** (master coordination v1) — docs-only, mergeable now
5. **PR #667** (Kimi v2 attachments + FOOLPROOF) — docs-only, mergeable now (this is the one with the Bible)
6. **PR #668** (Cloud Agent feature-flag enablement) — surgical 1-file change, enables `ml_gatekeeper`, `what_if_analysis`, `smart_picks_explainability` flags with explicit `## Wiring Plan` per CLAUDE.md Wire-Up Rule + bumps `policy_version` → v4 so `FeatureFlagManager.reload()` picks them up. Opt-in sidecar, no production behavior change until wiring follow-ups land. **Mergeable now** (the three flags' consumers are all in flight per the wiring plan)
7. **PR #660 + #661** — HOLD until Kimi pushes the follow-up commits per my coordination comment + REQUEST_CHANGES list
8. **Phase-0 code PRs** (Gemini's 4 actions) — ship as 4 separate small PRs, each default-OFF + 14-day shadow

### GHA Pipeline Health (08:30Z)

GHA Hourly Health Monitor (commit `7f680b668da`) reports **GREEN**:
- PR #665: 5/5 checks pass (08:08Z)
- PR #659: 4/4 checks pass (07:36Z merged)
- Open PRs #615 + #597: pre-existing test failures (HELD/known)
- No chronic workflow cancellations

Next monitor fire: 09:00 UTC.

### Open peer activity worth tracking
- **GitHub Cloud Agent** task `7cd68a65-0527-4bf0-bfdd-c7eef3d3535b` — proceeding (operator informed)
- **`copilot/enable-feature-flags-and-fix-gate-config`** branch — pushed 08:25Z; aligns with Copilot's §14 finding (kill-list enforcement bug) — review before merge

---

**Author note:** all subsequent peer-AI work today (Kimi v2 self-correction, Gemini Phase-0 v3, Cloud Agent feature-flag PR, Mercury/Codex repeated docx-read attempts) has been folded into this single navigation doc. Operator should treat this MD + the FOOLPROOF Bible (PR #667) + Gemini's 4-action plan (`reports/HEDGE_FUND_PHASE0_ACTION_PLAN_2026_05_02.md`) as the canonical 3-document set for the hedge-fund-quality push. Everything else is supporting evidence.
