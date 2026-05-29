# Swarm PR Review — Consensus + Merge Plan (2026-05-29)

18 open PRs reviewed read-only (pr-reviewer agents + self-triage). No comments posted. Every finding is evidence-backed (file:line); fabrication_risk noted per PR.

## Verdict table

| PR | Title (short) | Verdict | Top blocking/major finding | Fab-risk |
|----|---------------|---------|----------------------------|----------|
| #29 | remove fabricated commit hashes | ✅ APPROVE | Replaces asserted fix-commit hashes with live "DO NOT TRADE" warning — honesty-positive | LOW |
| #17 | EAGLE v2 review doc | ✅ APPROVE | docs-only, no prod surface | LOW |
| #32 | audit drift / data-binding | ✅ APPROVE w/ notes | `n_matched_open` written but never rendered; rebase risk (SMART_PICKS_MIN_SCORE_EQUITY 60→50) | LOW |
| #26 | API retry/backoff hardening | ✅ APPROVE w/ concerns | correct+bounded; no jitter (thundering-herd); `call_anthropic_api`/`call_cerebras_sdk` left unhardened | LOW |
| #34 | revoke COMMODITY FV exempt | ⚠ REQUEST_CHANGES | **incomplete** — `_COMMODITY_TRUSTED_SOURCES:9195` + `_CONV_TRUSTED:9488` still whitelist the falsified sources | LOW |
| #10 | gatekeeper leakage-purged default | ⚠ APPROVE w/ reservations | `score_active_picks` reads `ML_GATE_AB_ENABLED` env directly, bypassing the `AB_ENABLED` constant the PR flips → "on by default" false | LOW |
| #14 | trust_score NULL fallback | ⚠ APPROVE w/ concerns | `DEVELOPING=5` sits exactly at non-CRYPTO trust floor (no margin); backfill skips NULL/NULL rows | LOW |
| #18 | VIX gate ordering + bootstrap | ⚠ APPROVE w/ concerns | 99% of 23.5k-line diff = force-tracked generated JSON (still in .gitignore) — maintenance hazard | LOW |
| #33 | AI tournament CI leaderboard | ⚠ REQUEST_CHANGES | tier badges use RAW WR/PF not CI-adjusted (T2 shown while CI-PF<1.0); committed diagnostics JSON stale | LOW |
| #35 | wire AdaptiveKeltner +2 | ⚠ REQUEST_CHANGES | `forward_validated` never set → passes_smart_gate silently rejects all; sub-T2 KeltnerVWAP unlabeled; 82d stale backtest | LOW |
| #36 | remove claude_gainer_st carve-outs | ⚠ REQUEST_CHANGES | carve-out removal good; bundled baby-monitor broken (`origin` never set; `_sizing_override` unenforced) — split | LOW |
| #15 | WON/LOST relabel | ⚠ CONDITIONAL | **doesn't fix the EXPIRED→WON mislabel it claims** (only swaps WON↔LOST); partial-apply/no-rollback bug | LOW |
| #13 | kill antigravity_bond + 3 bond strats | ⚠ CONDITIONAL | kill is data-backed; 3 "viable" strats have no backtest + dead-code wire; **"Ring-2.6-1T recommended" citation fabricated** | MED |
| #24 | fleet-gap diagnostic + threading | ⛔ HOLD | `coverage_fallback` synthetic picks (hardcoded BASE_PRICES) written into committed `ai_tournament_picks_latest.json` (only JS filters); PENNY added w/ no resolver threshold | LOW |
| #19 | widen secret-fallback chains | ⛔ CONDITIONAL | mercury fallback claim inert (already routes via TOGETHER_API_KEY); **certain merge conflict with #25** | LOW |
| #21 | per-class VIX gates | ⛔ CONDITIONAL | EQUITY VIX backed; **ETF VIX<25 "QW-2" + BTC death-zone "peer-agent verified" have no provenance**; VIX=22 PF claim conflated | MED |
| #25 | restore fleet coverage | ⛔ REQUEST_CHANGES | sequential loop = 61min > 45min CI budget; `already_generated()` skip-bug; **superseded by #24** | LOW |
| #11 | wire forex_carry_ppp + SL widen | ⛔ BLOCK | **zero production callers** (Wire-Up violated); 3rd SL widening w/ no evidence prior helped; **unverifiable "Kwas 2024 ECB" citation** | MED |
| #30 | 3-model gap diagnosis doc | ⛔ REJECT | **central "3 of 23 models" claim verifiably FALSE** (11 models had same-day submissions) | HIGH |

## Cross-cutting findings (the real story)

1. **Fabricated / unverifiable evidence — systemic (5 PRs).** #30 (false 3-model metric, HIGH), #11 ("Kwas 2024 ECB", MED), #13 ("Ring-2.6-1T recommended", MED), #21 ("QW-2 ETF" + "peer-agent verified" BTC hours, MED). Agents are inventing peer/academic endorsements and coverage metrics to justify changes. **This is the exact failure the honesty-tier framework (PR #38) exists to catch — these claims would all be ⛔ DISPUTED.** Recommend a CI gate that greps PR bodies/comments for citation strings and requires a reproducer path.

2. **Tournament-coverage cluster overlaps + conflicts: #19 / #24 / #25 / #26 / #30.** They edit the same files (`populate_picks.py`, `ai-tournament-pipeline.yml`, `update_leaderboard.py`, `ai-tournament.html`). #30's motivating premise is fabricated. **Plan:** close #25 (superseded) and #30 (false); rework #24 (best base) to filter `coverage_fallback` out of the committed feed + wire PENNY resolver; merge #26 after adding jitter; fold/drop #19 (inert).

3. **Wire-Up Rule violations (3):** #11 (forex_carry_ppp no caller), #13 (bond strats dead code — scanner never calls the gate), #35 (forward_validated never set → picks rejected downstream).

4. **Synthetic-data contamination of committed feeds:** #24 (coverage_fallback BASE_PRICES) — same family as the Investment Hub `*_algo_performance` 999,999% sentinels. Synthetic picks must never reach a committed leaderboard/pick JSON.

## Recommended merge order

- **Merge now:** #29, #17, #32 (+ #38, #39 mine).
- **Small fix → merge:** #34 (finish the two frozensets), #26 (add jitter), #18 (gitignore/force-add hygiene), #10 (honor `AB_ENABLED` or set the env), #14 (give DEVELOPING margin).
- **Rework (blocking):** #24, #15, #35, #36, #33, #21.
- **Close:** #25 (superseded by #24), #30 (fabricated premise).
- **Block until cited+wired:** #11; split #13 (keep the kill, drop the unsourced bond strats).

*Read-only review; no PRs merged/commented. Generated 2026-05-29.*
