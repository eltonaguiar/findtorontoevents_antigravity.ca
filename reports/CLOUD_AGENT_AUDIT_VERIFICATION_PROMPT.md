# Cloud-Agent Prompt — Verify findtorontoevents.ca/audit Performance

Hand the prompt in **§PROMPT** below to a cloud agent (Kimi / Gemini / GPT-5 /
Grok) with repo access. The §CODE MAP is embedded so the agent does not waste
budget rediscovering the layout. Built 2026-05-17 from a 5-subagent
investigation of the live repo.

---

## CODE MAP (verified file:line — give this to the cloud agent)

**Repo:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/

| What | Where |
|---|---|
| Dashboard template (canonical — NOT `index.html`) | `audit_dashboard/template.html` (18,369 lines) |
| Tab bar | `template.html:1322-1335` — Overview `:1322`, **Active Picks** `:1323` (`data-tab="active"`), **Verified Alpha** `:1324` (`data-tab="verifiedalpha"`), **Closed Picks** `:1328` (`data-tab="closed"`) |
| Tab-switch JS | `template.html:12080-12087` (binds every `.tab-btn`) |
| **Smart Picks** (button + filter, not a tab) | pane `#tab-smartpicks` `:1443`; button handler `:12182-12219`; `loadSmartPicks()` `:12540-12601` (`SMART_PICKS_MIN_SCORE=60`) |
| **Verified Alpha** button | `btn-verified-alpha` `:1299`; render `renderVerifiedAlpha()` `:3106`; handler `:12777-12789` |
| Dashboard generator | `audit_trail/dashboard_generator.py` (17,218 lines) — `_normalize_pick` `:7063`; `compute_asset_class_health()` `:5472`/call `:14346`; `by_asset_class` rollup `:14504-14543`; writes `audit_dashboard/data/dashboard_data.json` `:17118-17154` |
| **Quality gate** | `audit_trail/quality_gates.py` — `passes_active_gate` `:5631`; `passes_smart_gate` `:7307`; `meta_label_gate` (SHADOW) `:5543-5605` |
| Pick → asset-class tracing | `alpha_engine/outcome_resolver.py` — `_resolve_asset_class` `:687-726`, stamps `pick["asset_class"]` `:782-791`; `closed_picks.json` `:60`; per-class WIN/LOSS thresholds `classify_outcome` `:663-687` |
| Verified-Alpha gate | `dashboard_generator.py` — `_is_verified_alpha_pick` `:5807-5870`; `_compute_verified_alpha_summary` `:6383-6475` |
| Walk-forward / OOS table | `alpha_engine/walkforward_validator.py` — `walk_forward_by_class()` `:212`/`:542` → `alpha_engine/data/walkforward_results.json` → consumed `dashboard_generator.py:14728-14746` |
| Refresh automation | `.github/workflows/audit-dashboard.yml` — cron `'10 * * * *'` (hourly): runs `walkforward_validator` then `dashboard_generator`, commits `dashboard_data.json` to main with `[skip ci]` |
| TRUTH LAYER banner | `template.html:837-855` — **HARDCODED static HTML**, not computed |
| MySQL `at_raw_picks` | a table in `ejaguiar1_stocks` DB (`audit_trail/mysql_schema.sql`) — NOT a repo file |
| Inverse picks / DNA mutation | `alpha_engine/inverse_edge_system.py`, `dna_mutation_engine.py`, `auto_dna_mutator.py`, `tools/mutation_analysis.py`, `docs/MUTATION_THREE_AXIS_PROTOCOL.md`, `docs/SIGNATURE_FEATURES.md` |

---

## PRE-VERIFIED FINDINGS (state them to the agent; have it independently confirm)

1. **TRUTH LAYER banner is a hardcoded stale snapshot.** `template.html:840,850`
   hard-codes `55,510 / 11.13% WR / −3.56% avg / Sharpe −2.34 / PF 0.46`. No JS
   computes it. The local closed-pick ledger
   (`closed_picks.json` 8,421 + `closed_picks.archive.jsonl` 44,384 = 52,805)
   actually shows **WR 32.2% raw / 36.5% deduped, avg −15.3%, PF 0.40** — every
   headline number in the banner is wrong, though the *thesis* (DB reality is
   worse than the rosy tiles, no class passes real-money thresholds) is
   directionally true. The "55,510" is a DB `at_raw_picks` count, not the repo.
2. **CT=F / cot_positioning "DSR=1.0" claim is FALSIFIED by the repo's own
   audits.** `alpha_engine/cot_positioning.py:40-54` cites
   `cot_timing_leakage_audit_2026-05-13.md` (look-ahead leakage halves WR) and
   `cot_paper_pilot_overemission_falsified_20260513.md` (WR 90%→40%, PF 2.73→0.17,
   n=101→5 real releases). The banner's lone real-money candidate is debunked.
3. **The per-class tiles are FRESH, not stale.** `asset_class_health` +
   `walkforward.by_class` are recomputed hourly by `audit-dashboard.yml`. Only
   the template's hardcoded date strings (`generated 2026-05-05T01:37Z`
   `:952`, `Static data updated 2026-05-16` `:894`) are stale prose — the data
   underneath is current.
4. **41–87% of the closed-pick ledger is duplicate re-emissions** (depends on
   dedup key strictness). A9 `emitter_dedup.py` now blocks future dups; existing
   dups are stripped at read time by `tools/build_pf_registry.py`.

---

## §PROMPT — paste this to the cloud agent

> You are a quant auditor. Repo: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/ — clone it. Your job: independently verify the findtorontoevents.ca/audit dashboard's per-asset-class performance claims and find real, defensible edge. Use the CODE MAP above to navigate; do not rediscover it.
>
> **Task 1 — Verify every stat on the page.** Open `audit_dashboard/data/dashboard_data.json`. For each asset class (EQUITY/CRYPTO/COMMODITY/ETF/FOREX/BOND) recompute WR, PF, avg pnl, n DIRECTLY from the closed-pick ledger (`alpha_engine/data/closed_picks.json` + `closed_picks.archive.jsonl`) and compare to `performance.asset_class_health`. Report every mismatch. Critically: dedup the ledger first (key = strategy|symbol|direction|entry_date|entry_price|exit_date) — report raw AND deduped numbers. Confirm or refute the 4 PRE-VERIFIED FINDINGS above with your own evidence.
>
> **Task 2 — Trace picks end to end.** Pick one strategy per asset class. Trace: where does it emit a pick → how does it get an `asset_class` (`outcome_resolver._resolve_asset_class:687`) → which gate decides Active Picks (`quality_gates.passes_active_gate:5631`) vs Smart Picks (`passes_smart_gate:7307`) vs Verified Alpha (`_is_verified_alpha_pick:5807`) → how it lands in `closed_picks.json` after resolution. Document the data flow.
>
> **Task 3 — Audit each UI surface for edge vs anti-edge.** For each of: Active Picks tab, Closed Picks tab, Verified Alpha tab, Smart Picks button, "Best Score" preset — determine what filter/gate it applies and whether the cohort it surfaces actually has positive realized edge (recompute its WR/PF). Flag any button that surfaces an ANTI-edge cohort (e.g. high-`confidence` picks, which the repo's own audit shows invert: conf≥0.9 → 14.4% WR).
>
> **Task 4 — Find edge.** Hunt for: (a) strategies with excellent PF but tiny n (<30) — promising but unproven; (b) consistent losers that are inverse-edge candidates (WR<40%, PF<0.9, n≥20 — see `inverse_edge_system.py`); (c) mutation candidates per `MUTATION_THREE_AXIS_PROTOCOL.md`. Rank the top 10 highest-expected-edge actions with file:function targets.
>
> **Task 5 — Real-money readiness.** For any class claiming Tier-2 (PF>1.5/WR>50/MDD<20), check it against Lopez de Prado gates: DSR>0.95, PBO<0.05, walk-forward decay≥0 across 3+ folds, n≥100 clean (post-dedup, post-resolver-v2.1) trades. State per class: REAL-MONEY-READY / ACCUMULATING / BLOCKED.
>
> **Hard rules:** every numeric claim must cite a file + a reproducible computation. Treat the TRUTH LAYER banner as untrusted (it is hardcoded). Do not trust cumulative-since-inception stats — use rolling post-resolver-v2.1 windows. Distinguish raw vs deduped ledger everywhere. Output: a per-class verdict table + the ranked top-10 edge actions + a list of every dashboard stat that did NOT reconcile.

---

## SWARM-OPTIMIZATION NOTE (answers "do our swarms need optimization for large text")

YES — one concrete bug. The ~2000-char truncation seen in swarm reviews is
**not** a token/schema limit — it is a parse-fail fallback: `tools/swarm/
worker_runner.py:1196` does `raw[:2000]` when the engine emits non-JSON
(fenced ```json or a reasoning preamble). Full output IS saved uncapped to
`<out>.raw.txt`. Fix: add a JSON-recovery ladder (strip fences / extract first
balanced `{...}`) before the fallback, and change `raw[:2000]` → full `raw`.
Neither swarm v1 nor v2 chunks large prompts/responses or auto-continues a cut
answer — the caller must pre-split. Full audit: `reports/swarm_largetext_audit_2026-05-17.md`.

For a large task/prompt: pre-split into ≤1 question per engine call, or use the
v2 `pr_review_swarm` role fan-out — do NOT send one giant multi-part prompt and
expect a complete multi-part answer back.

---

## §PROMPT v2 REFINEMENTS (Xiaomi MiMo peer review, 2026-05-17)

Append these tightenings to the cloud agent's instructions:

1. **Dedup key — add a tolerance band.** The key
   `strategy|symbol|direction|entry_date|entry_price|exit_date` misses
   re-emissions with rounding/feed-jitter on `entry_price`. Use the CANONICAL
   key from `alpha_engine/emitter_dedup.py` (`compute_dedup_key` — buckets
   `entry_price` to 2dp); if computing independently, apply a ±0.5% `entry_price`
   tolerance band, and prefer a `pick_id`/`emission_id`/`dedup_key` field if the
   schema has one. Have the agent confirm its key matches `emitter_dedup.py`.

2. **Inverse-edge needs a stability check, not just a low WR.** Before flagging
   any cohort (e.g. `conf≥0.9 → 14.4% WR`) as an inverse candidate the agent must:
   (a) check the WR is stable across ≥3 time windows, not concentrated in one;
   (b) confirm n is large enough that the WR is not noise; (c) run a binomial
   test — WR significantly below 50% at **p<0.01**. Matches
   `inverse_edge_system.py` (both history halves <40%).

3. **DSR = Deflated Sharpe Ratio** (Bailey & López de Prado 2014) — NOT Dynamic
   Sharpe. The agent MUST compute it with the deflator = number of
   trials/strategies tested. Without the trial count, DSR is meaningless.

4. **Walk-forward bar raised.** Require **≥5 folds** (not 3), a monotonicity
   test (is performance degrading over time?), and **OOS Sharpe ≥ 70% of
   in-sample Sharpe**. Combinatorially-symmetric CV preferred.

5. **Task 3 must be a standalone Python script, not prose.** Auditing every UI
   surface (load `dashboard_data.json` + `closed_picks.json` + archive, filter
   by each gate fn, recompute per-cohort stats) exceeds single-call output
   limits. Instruct the agent: WRITE A PYTHON SCRIPT that does this and emits a
   comparison table — let code do the heavy lifting, not the LLM context.

6. **New Task 6 — verify the data path.** Grep `template.html` for `fetch(` /
   `XMLHttpRequest` / `dashboard_data` to confirm the page actually consumes
   `audit_dashboard/data/dashboard_data.json` from that exact path — not a CDN,
   cache, or alternate source. Closes the "is the audited file the live file"
   gap.


---

## §0 PROOF-OF-ACCESS GATE (MANDATORY — read FIRST, prepend to the agent prompt)

Some cloud agents cannot clone the repo and will CONFABULATE — they adopt this
prompt's structure and invent file paths, strategy names, pick IDs, and stats
that look authoritative but do not exist (observed: an Ernie/Baidu run invented
`alpha_engine/emitters/*.py`, strategies `mom_breakout_v3` / `vol_arb_vix_es` /
`momentum_bonds_tlt`, and pick IDs `cp_88471` — NONE exist in the repo).

**The agent MUST pass this gate before ANY finding is accepted. Paste, verbatim,
at the TOP of the report:**

1. `git rev-parse HEAD` — the real current commit SHA of the cloned repo.
2. `git log -1 --format=%ci` — the real date of that commit.
3. **Three real strategy names** copied from `alpha_engine/data/strategy_performance.json`
   (top-level keys) — NOT invented. Real examples that DO exist:
   `multi_asset_cot`, `kimi_signal_tracking`, `alpha_engine_fast`,
   `signal_validation`, `copy_trader_intel`. If the agent's three names are not
   in that file, the whole report is rejected.
4. **One real line quoted with its line number** from `audit_trail/quality_gates.py`
   around the `passes_active_gate` definition (~line 5631).
5. The real total row count of `alpha_engine/data/closed_picks.json`.

**Rejection rule:** if the agent cannot produce items 1-5 from a real clone, it
MUST say so explicitly ("I could not access the repo") and STOP. Any report that
contains strategy names, file paths, or pick IDs absent from items 1-5's
verifiable sources is to be discarded in full. Cite a file:line for EVERY
numeric claim; an uncitable number is a fabricated number.


---

## §0b INVERSE-PROJECTION RULE (MANDATORY — anti-fantasy-edge)

When the agent flags a consistent loser as an inverse-edge candidate, it MUST
NOT project the inverse PF as `1 / base_PF` (or any naive flip). Observed
failure: a GLM run claimed "inverse of forex_rsi2_mean_reversion → PF ~2.7" by
inverting a PF-0.16 strategy — pure fantasy.

Why the naive flip is wrong: flipping direction flips win-rate roughly
symmetrically (12% WR → ~88%), but PF does NOT invert symmetrically. Stop-loss
/ take-profit geometry is asymmetric, and transaction cost + slippage + spread
are paid on BOTH the original and the inverted trade. An inverted loser
typically nets PF ~1.0–1.5 at best, often still < 1 after costs.

**Required:** any inverse-edge claim must come from a friction-costed backtest
of the ACTUAL inverted trades through `alpha_engine/inverse_edge_system.py`
(double the per-trade cost; re-derive SL/TP for the flipped direction) — never
a `1/x` projection. Until that backtest runs, an inverse candidate is
ACCUMULATING, not deployable. Also cite the candidate's real base stats from
`alpha_engine/data/strategy_performance.json` (or state "not in
strategy_performance.json — base stat unverified") — do not invent n / WR / PF.

## §0c RECENCY-WINDOW RULE (anti-cherry-pick)

Do NOT quote "last 10 / last 50 picks" win-rate as edge. A short trailing
window is a cherry-pick — it inflates WR/PF and ignores the resolver-v2.1 fix +
the 41–87% duplicate re-emission problem. Observed failure: an Ernie run
reported "CRYPTO last-50 = 68% WR / PF 5.1 → elite, go make money" — pre-dedup,
pre-resolver-fix, recency-cherry-picked. Use only **rolling 30-day,
post-resolver-v2.1, deduped** windows with n ≥ 100. Cumulative-since-inception
and short trailing windows are both inadmissible.
