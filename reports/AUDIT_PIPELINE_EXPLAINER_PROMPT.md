# AUDIT PIPELINE EXPLAINER PROMPT — 2026-05-18

A copy-paste prompt to brief any AI on how `findtorontoevents.ca/audit` is fed,
what the current per-asset-class prediction status is, and whether there is a
real statistical edge. Use it before asking an AI to propose improvements.

---

## PROMPT (give this verbatim to the AI)

> You are reviewing a multi-asset trading-signal system. Here is its exact
> architecture and verified current state. Do not assume anything beyond this.
>
> ### How `findtorontoevents.ca/audit` is fed
>
> 1. **Code**: GitHub repo `eltonaguiar/findtorontoevents_antigravity.ca`.
>    Strategy emitters, scoring (`alpha_engine/score_booster.py`), quality
>    gates (`audit_trail/quality_gates.py`), and the dashboard generator
>    (`audit_trail/dashboard_generator.py`) all live here.
> 2. **Compute**: GitHub Actions (`.github/workflows/audit-dashboard.yml`) runs
>    hourly. Each cycle: resolve open picks → run scanners/emitters → score →
>    apply quality gates → `score_booster` → `dashboard_generator` →
>    `build_pf_registry.py` → commit the regenerated JSON/HTML back to `main`
>    via `[skip ci]`.
> 3. **Data — MySQL `mysql.50webs.com`**:
>    - `ejaguiar1_stocks` — live pick tables (`at_raw_picks` raw emissions;
>      the planned `audit_*` summary tables); paper-trade tables.
>    - `ejaguiar1_backtests` — historical backtest results.
> 4. **Surface**: `audit_dashboard/template.html` renders
>    `audit_dashboard/data/dashboard_data.json` into the `/audit` page. The
>    canonical verdict-grade ledger is `pf_registry.json` →
>    `by_asset_class_policy_clean_net` (deduped, policy-clean, net-of-slippage).
>
> ### Methodology
>
> Picks flow: emitter → 75+ quality gates → score → `score_booster` →
> active pick. Resolution: TP/SL/time-exit closes picks into `closed_picks.json`.
> Verdict: per asset class, `pf_registry` recomputes PF/WR on the deduped,
> policy-clean, net-of-slippage set; `money_ready_verdict.py` runs DSR + PBO +
> SPA + an n>=100 floor + a single-symbol concentration cap.
>
> ### Verified current state — per asset class (canonical net view)
>
> | Class | net PF | n | Verdict |
> |---|---|---|---|
> | CRYPTO | 1.28 | ~1900 | sub-Tier-2. The apparent edge is the post-hoc winning tail of an `ml_enhanced` 149-variant per-symbol mining sprawl (family PF 0.63). Not a real edge. |
> | COMMODITY | 1.17 | 160 | sub-T2. ~85% of it is CT=F (cotton) — see edge verdict below. |
> | EQUITY | 0.72 | 31 | non-functional — below the n>=100 floor. |
> | FOREX | 0.33 | 392 | hard-disabled (correctly). |
> | ETF / BOND / FUTURES | — | ~1-12 | thin-sample; data-integrity bugs; not tradeable. |
>
> **No asset class has a real, real-money-ready statistical edge.**
>
> ### Edge verdict — the cotton (CT=F) case
>
> The system *appeared* to have a strong edge in COMMODITY: `cot_positioning`
> showed 77-78% WR / PF ~4.6. On inspection it was **not a usable edge**:
> - **~85% concentrated in one symbol** (CT=F, cotton). A one-symbol bet is not
>   a class edge — it is single-name risk.
> - The COT (Commitment of Traders) signal used CFTC report data **not
>   available at decision time** — look-ahead leakage.
> - Deduped + leak-corrected + excluding CT=F, `cot_positioning` is
>   n=20 / WR 30% / PF 0.51 — a loser.
>
> So: we briefly believed we had a statistical edge on cotton; it turned out
> to be **too concentrated (single-symbol) and leakage-inflated, therefore too
> risky and not real.** It has been blocked.
>
> ### Known data-integrity issues (now fixed, but they corrupted prior verdicts)
>
> ~41% duplicate re-emissions in the closed ledger; a 100x slippage units bug;
> a resolver that mass-stamped replay SL-hits; mis-tagged asset classes; DSR
> run with `nb_trials` far below the true multiple-testing burden.
>
> ### Your task
>
> Given this honest baseline — **no edge anywhere, the one apparent edge was a
> concentration + leakage artifact** — propose how to find or build a genuine,
> defensible statistical edge per asset class. Be concrete and falsifiable.
> Reject any class where the honest answer is "this will not have a
> retail-accessible edge — stop". Compare your recommendations to how top
> quant funds and AI labs actually validate edge (below).

---

## How top quants / hedge funds / AI labs actually do it — benchmark

Use this to grade any proposal:

| Technique | Who uses it | This system's gap |
|---|---|---|
| **Deflated Sharpe + PBO/CSCV** (López de Prado) | AQR, Two Sigma, academic quant | Present in code; `nb_trials` was under-counted — DSR PASS was inflated. |
| **White's Reality Check / Hansen SPA** — family-wise error control | Renaissance-style multi-strategy shops | Not yet built (M-065). The `ml_enhanced` 149-variant sprawl is exactly what SPA exists to catch. |
| **Combinatorial Purged CV** with embargo | Lopez de Prado practitioners | Not the default validation; walk-forward only. |
| **Pre-registered hypotheses** (decide the test before seeing data) | Disciplined quant research; mirrors clinical-trial pre-registration | Absent — the system mines per-symbol variants post-hoc, the "garden of forking paths". |
| **Economic prior / causal story** before a statistical test | All credible funds — risk premium, structural friction, flow | Absent — patterns mined from price with no thesis. |
| **Net-of-cost, capacity-aware backtests** | Every real desk | Was gross; fixed (M-069). Capacity still unmodelled. |
| **Information-edge budget** — is the signal observable to a small team after latency/crowding? | xAI/quant consensus | Never asked — much "edge" is negative once dissemination lag is priced. |
| **Forward / paper validation before sizing** | Standard | Paper tables exist but under-wired; forward n is thin. |
| **Ensemble of de-correlated edges, risk-parity sized** | Bridgewater-style | Premature — there are no proven edges to ensemble yet. |

**Bottom line for the AI being briefed:** the discipline IS the edge. The
fastest credible path is pre-registered hypotheses (EQUITY post-earnings drift,
ETF momentum, COMMODITY term-structure roll-yield) validated under CPCV +
White's Reality Check + deflated Sharpe + an n>=100 floor — NOT more mining.
See `NO_EDGE_BRAINSTORM_CLOUD.MD` for the multi-cloud-model expansion of this.
