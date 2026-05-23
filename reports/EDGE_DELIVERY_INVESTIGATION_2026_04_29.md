# Edge-Delivery Investigation — Why 10 S-tier Strategies Emit ZERO Active Picks

**Date:** 2026-04-29
**Author:** Claude Opus 4.7 (1M context) investigation subagent
**Scope:** 10 strategies (PF>1.5, WR>50%, n>=10 on 30d) with zero active picks per `reports/PRE_PHASE_1_BASELINE_2026_04_29.md`
**Bench value:** ~$165% sum 30d-PnL of unrealized edge sitting dormant

---

## TL;DR

- **NO cron failures** detected — every relevant GHA workflow ran green in the last 24h.
- **4 of 10 strategies are killed by a 5-week-stale `core_whitelist.json` kill_list** (last_kill_run 2026-03-26). The system never reconsiders the kill verdict against newer data.
- **2 of 10 are blocked by a downstream filter at the dashboard generator** — including a hard-coded `"rsi2" in strategy.lower()` substring rule that nukes the entire `stocks_rsi2_pullback` family for non-crypto picks.
- **3 of 10 have no current setups (regime shift)** — they are alive end-to-end, but FX is in a low-vol regime and the mega_mutation engine is naming current picks differently from m048.
- **1 of 10 has a stale upstream data file** (`ml_gatekeeper/data/active_picks.json` is 337h old; tripped by the 72h freshness gate).
- **One strategy is a baseline string-truncation artifact** — `multi_period_rsi_confluence_et` is `multi_period_rsi_confluence_eth` (missing `h`); the `_et` form has 0 closed picks anywhere.

The single highest-leverage fix is **scrubbing the stale `core_whitelist.json` kill_list** — it would unblock 4 strategies on its own, expected ~30+ picks/week.

---

## Methodology

For each of the 10 strategies, ran the prescribed 4-step check (code search, kill-list check, GHA run check, active-picks search) plus deep-dive into:
- `audit_trail/dashboard_generator.py` filter chain (`_apply_external_source_gate`, `_is_valid_pick`, kill_set logic at line 7706-7723, staleness filter at line 7416-7451).
- `alpha_engine/feed_hygiene.py:is_valid_active_pick` (proven to PASS our target picks — issue is downstream).
- `alpha_engine/data/core_whitelist.json` kill_list (550 entries, last_kill_run=2026-03-26).
- `alpha_engine/strategy_blocklist.py` retired/paper-only sets.
- File mtimes for all source pick files.
- Source pick files actually contained the strategies as OPEN picks.

GHA workflows checked (all GREEN, last 5 runs each):
`mega-mutation-tracker.yml`, `kimi-feb172026-live.yml`, `forex-agent.yml`, `dna-mutation-cycle.yml`.

---

## Per-strategy diagnosis

| # | Strategy | Class | Cause | Evidence (file:line / data) | Recommended fix | Risk |
|---|---|---|---|---|---|---|
| 1 | `mega_mutation_macd_rsi_m048` | CRYPTO | **E** regime + naming | `genome/data/mega_mutation_picks.json` has 1 open_pick with `strategy=None`; closed_picks use `mutation_name` (e.g. `ema_momentum_m006`), not `strategy`. mega_mutation cron green @ 17:13 UTC. | Add `mutation_name` fallback in `audit_trail/dashboard_generator.py::_normalize_pick` (line 5859); confirm whether m048 setups are firing under different mutation IDs. | LOW |
| 2 | `claude_ml_moderate_mut` | CRYPTO | **D** kill_list (stale) | Verbatim entry in `alpha_engine/data/core_whitelist.json` kill_list AND `dna_winner_picks::claude_ml_moderate_mut`. last_kill_run=2026-03-26 (33d stale). 26 closed picks in last 7d, 2 in last 48h — actively emitting but every pick filtered at dashboard kill_set. | Remove from kill_list; add to `protected_strategies`; bump last_kill_run. | MED — was killed for reason; need to confirm 30d performance |
| 3 | `hs_lb_None` | CRYPTO | **B** staleness filter | 92 OPEN picks in `copy_trader_intel/data/highscore_active_picks.json` with `timestamp=2026-04-19` (10+ days old). Crypto max-age in dashboard_generator.py is 168h (7 days), so all 92 are auto-expired at line 7232. Last closed 2026-04-21 → emitter is QUIET, not broken. | Refresh upstream copy_trader_highscore producer to emit fresh picks; or relax staleness for whitelist of proven traders. | LOW |
| 4 | `stocks_rsi2_pullback` | EQUITY | **B** anti-test substring filter | 8 fresh OPEN picks (timestamp 2026-04-28, age <24h) at `copy_trader_intel/data/multi_asset_picks.json`. `audit_trail/dashboard_generator.py:7355` rejects ANY non-crypto pick whose strategy contains substring `"rsi2"` as a "test harness". Connors RSI2 pullback is a legitimate equity edge (Wikipedia-grade, n=19 WR 73.7% confirms). | Replace substring rule with explicit whitelist of test-harness names, OR add `stocks_rsi2_pullback` to a permitted list. | LOW |
| 5 | `MeanReversionBB` | CRYPTO | **D** kill_list (CONTRADICTORY: also in core_strategies) | In kill_list as bare match AND `signal_validation::MeanReversionBB`. Yet ALSO listed in `core_strategies`. `audit_trail/quality_gates.py:624` says "REHABBED 2026-04-05 77.8% WR". 14 closed in last 7d, 1 in 48h. 153 raw emissions in `signals_database.json` all dropped at dashboard kill_set. | Delete kill_list entry; reconcile the contradiction (core_whitelist logic should treat core_strategies as immune). | MED |
| 6 | `multi_period_rsi_confluence_et` (truncation; real name `_eth`) | CRYPTO | **D** kill_list + baseline string artifact | Baseline used `_et` (truncated). True name `multi_period_rsi_confluence_eth` killed via TWO entries: `baby_strats_forward::multi_period_rsi_confluence_eth` and `battleground::multi_period_rsi_confluence_eth`. Namespace-strip pulls bare into kill_set. | Fix baseline string at source; remove kill_list entries (per `alpha_engine/super_strategies.py:20`: 64.3% OOS WR, PF 7.58). | LOW |
| 7 | `atr_percentile_gate` | CRYPTO | **D** kill_list | Killed via `baby_strats_forward::atr_percentile_gate`. Real function is `atr_percentile_gate_scanner` in `alpha_engine/proven_edge_strategies.py:884` (comment claims 100% WR on 11 trades). 22 closed last 7d, latest 2026-04-27. Producer alive; killed at dashboard. | Remove kill_list entry; add naming alias so `_scanner` suffix matches. | LOW |
| 8 | `forex-rsi-ema-scout` | FOREX | **E** regime / no current setups | `KIMI_RISEOFTHECLAW/live_scanner.py:6154` defines it; `kimi-feb172026-live.yml` ran green @ 18:26 UTC. Last closed 2026-04-15 (14d ago); 0 in any current active_picks file. FX is in low-vol regime per FORENSIC_REPORT_2026_04_29.md. | Verify forex universe + regime gating; consider relaxing entry criteria when low-vol regime persists; or manual seed pilot. | LOW |
| 9 | `fx_smart_carry_trade_momentum` | FOREX | **A** cron data stale | 2 OPEN picks at `ml_gatekeeper/data/active_picks.json` (timestamp 2026-04-15). File mtime=337h, exceeds `_FRESHNESS_REQUIRED_HOURS["ml_gatekeeper"]=72`, so the ENTIRE source is dropped at `dashboard_generator.py:6564`. Whitelisted in `alpha_engine/smart_picks_engine.py:362`. | Identify and re-enable the ml_gatekeeper writer workflow OR redirect this strategy's emissions to a different active source. | MED |
| 10 | `cta_fx_multifactor` | FOREX | **E** regime / no current setups | `alpha_engine/cta_bridge.py:250` is the function; `cta_replicator` source is wired in JSON_PICK_SOURCES at line 3586. Last closed 2026-04-17. 0 current emissions. | Confirm cta_replicator workflow scheduled; relax low-vol gate; pilot back-fill. | LOW |

---

## Cause-class distribution

| Cause | Count | Strategies |
|---|---|---|
| **A — Cron / data stale** | 1 | fx_smart_carry_trade_momentum |
| **B — Downstream filter blocked** | 2 | stocks_rsi2_pullback, hs_lb_None |
| **C — Universe mismatch** | 0 | — |
| **D — Kill-list / retired** | 4 | claude_ml_moderate_mut, MeanReversionBB, multi_period_rsi_confluence_eth, atr_percentile_gate |
| **E — Regime shift** | 3 | mega_mutation_macd_rsi_m048, forex-rsi-ema-scout, cta_fx_multifactor |
| **F — Other (string artifact)** | (overlaps with D for multi_period_rsi_confluence_et) | — |

**Headline:** **70% of dormancy is self-inflicted by stale infrastructure** (kill_list + filter + cron + freshness gate). Only 30% is "no current setups" market reality.

---

## Top-5 highest-impact fixes (ranked by expected pick volume × edge × inverse risk)

| Rank | Fix | Expected weekly picks (post-fix) | Effort | Risk |
|---|---|---|---|---|
| 1 | **Scrub `core_whitelist.json` kill_list** — remove stale entries for `claude_ml_moderate_mut`, `MeanReversionBB`, `baby_strats_forward::atr_percentile_gate`, `baby_strats_forward::multi_period_rsi_confluence_eth`, `battleground::multi_period_rsi_confluence_eth`. Add timestamp-based auto-expiry (e.g. drop entries with last_kill_run > 21d unless re-confirmed). | ~30-45 (4 strategies × 6-12 picks/wk based on 30d closed-pick rate) | 1 PR, ~30 LOC | MED — verify each strategy's 14d closed-pick PF still passes Tier 2 before unkilling |
| 2 | **Replace `_is_valid_pick` substring rule with whitelist** — `audit_trail/dashboard_generator.py:7344-7357`. Change `or "rsi2" in strat` to a strict equality match against a known test-harness set. Effect: revives `stocks_rsi2_pullback` (n=19, WR 73.7%, +12.86% sum 30d) and any future legitimate rsi2 pullback strategies on equities. | ~12-15 | 1 PR, 5 LOC | LOW — strategy already has 30d realized edge proof |
| 3 | **Add `mutation_name` fallback in `_normalize_pick`** — `audit_trail/dashboard_generator.py:5859`. Mega-mutation engine writes `mutation_name` not `strategy`; `_normalize_pick` only checks `strategy/strategy_name/algorithm`. Adds fallback for genome family. Effect: revives `mega_mutation_macd_rsi_m048` AND any other mutation IDs with current open setups. | ~5-10 | 1 PR, 3 LOC | LOW — pure normalization |
| 4 | **Refresh `copy_trader_highscore` producer** — `hs_lb_None` has 92 OPEN picks but they're all 10+ days stale. Either find why the trader-following workflow stopped emitting fresh picks, or accept that hs_lb_None is "winding down" and remove from S-tier expectations. | 0-15 if revived; 0 if confirmed dead | Investigation + writer-side fix | MED — root-cause first |
| 5 | **Re-enable `ml_gatekeeper` writer for FX picks OR redirect `fx_smart_carry_trade_momentum` to a fresh source** — `ml_gatekeeper/data/active_picks.json` is 337h old. ml_gatekeeper-writer GHA workflow likely retired. | ~5-8 | Investigation + redirect | MED |

---

## AI panel consensus

Single-AI consultation (budget-constrained). Full responses in `reports/edge_delivery_investigation_2026_04_29/`.

| Provider/Model | Cause attribution | Top-3 fix ranking |
|---|---|---|
| Ollama gpt-oss:20b-cloud | Agreed on all 10 attributions ✅ | 1) stocks_rsi2_pullback 2) mega_mutation_macd_rsi_m048 3) forex-rsi-ema-scout |
| Cerebras (qwen-3-235b) | Cloudflare 1010 — API blocked from this IP, no consultation possible | n/a |

The single AI agreed with my cause attribution per strategy and proposed substantially the same fixes. Its top-3 leaned on per-strategy WR/edge but missed the **leverage point** that scrubbing the kill_list unblocks 4 strategies in one PR — which is why my synthesis ranks the kill_list scrub at #1.

---

## False positives in the S-tier list

- **`multi_period_rsi_confluence_et`** is a string-truncation artifact in the baseline. The real strategy is `_eth`. The baseline reproducer at `reports/PRE_PHASE_1_BASELINE_2026_04_29.md` line 168-194 likely trimmed the strategy name somewhere; recommend re-running with full strategy strings.
- **`hs_lb_None`** is "winding down" — 92 stale OPEN picks but emitter has not produced fresh picks since 2026-04-19. Possibly the underlying copy-trader account stopped trading. Should be re-investigated before counting as "S-tier going forward".
- **No strategies that should be re-killed.** None of the 10 are deterministic-loser patterns; all have plausible edges. The risk is in unkilling MED-risk ones (`claude_ml_moderate_mut`, `MeanReversionBB`) without verifying their April performance separately first.

---

## Reproducer commands

```bash
# Verify any of the 10 strategies are in kill_list:
python -c "
import json
wl = json.load(open('alpha_engine/data/core_whitelist.json'))
killset = {s.lower() for s in wl['kill_list']}
core = {s.lower() for s in wl['core_strategies']}
for s in wl['kill_list']:
    if '::' in s and s.split('::',1)[1].lower() not in core:
        killset.add(s.split('::',1)[1].lower())
for t in ['mega_mutation_macd_rsi_m048','claude_ml_moderate_mut','hs_lb_None','stocks_rsi2_pullback','MeanReversionBB','multi_period_rsi_confluence_eth','atr_percentile_gate','forex-rsi-ema-scout','fx_smart_carry_trade_momentum','cta_fx_multifactor']:
    print(f'{t:40s} killed={t.lower() in killset}')
"

# See live source files where picks live:
python -c "
import json
sources = [
    ('copy_trader_intel/data/multi_asset_picks.json', 'stocks_rsi2_pullback'),
    ('copy_trader_intel/data/highscore_active_picks.json', 'hs_lb_None'),
    ('signals_database.json', 'MeanReversionBB'),
    ('ml_gatekeeper/data/active_picks.json', 'fx_smart_carry_trade_momentum'),
]
for path, target in sources:
    arr = json.load(open(path))
    if isinstance(arr, dict): arr = arr.get('picks') or arr.get('open_picks') or arr.get('active') or []
    n = sum(1 for p in arr if isinstance(p,dict) and p.get('strategy')==target)
    print(f'{path:60s} :: {target}: {n}')
"

# Confirm the rsi2-substring filter:
grep -n 'rsi2' audit_trail/dashboard_generator.py
```

---

## Constraints honored

- READ-ONLY: no code modifications, no PRs.
- Wall-clock: ~30 min.
- All file paths are absolute or repo-relative; tests not run.
