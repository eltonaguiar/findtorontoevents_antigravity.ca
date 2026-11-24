# auditpage session wrap — 2026-11-16 (grok-4.7 seat)

Seat: `inbox/gx10-c9b9/auditpage/grok-4-7`
Local folder: `/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/auditpage`
Coordination: MQTT broker `192.168.2.52:1883`, roster via `COMS roster`, notes on `mentions/all` and `inbox/gx10-c9b9/auditpage/all`.

## Where the work is on GitHub

Repo: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca

Merged:
- #843 https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/843 — audit banner no longer says 5/5 checks pass next to 22,947 ghost rows, no longer quotes retired PF2.6/PF2.4, Polymarket labelled shadow not Verified Alpha. Files: `audit_dashboard/template.html`, `tests/test_audit_truth_claims.py`, `tools/audit_honesty_live_check.py`, `updates/2026-11-16-audit-honesty-banner.md`.
- #848 https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/848 — the money-ready button now fails closed. A pick needs DSR>0.95, PBO<0.05, WFE>60%, Sharpe>0.5, n>=100 and a class verdict of MONEY_READY. Files: `audit_dashboard/money_ready_filter.js`, `tests/test_money_ready_fail_closed.py`, `updates/2026-11-16-audit-class-and-ml-review.md`.
- #847 (peer, merged) — n/a for infinite PF and explosive Sharpe.

Open, needs a merge decision:
- #856 https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/pull/856 — dashboard deploy crash fix. `collect_audit_events` sliced `crypto_signal_engine` `new_picks` when the writer stored an int count (`len(h_active)` at `dashboard_generator.py:15758`), raising `TypeError: 'int' object is not subscriptable` and killing HTML generation. Files: `audit_trail/dashboard_generator.py`, `tests/test_dashboard_cse_new_picks.py`, `updates/2026-11-16-dashboard-cse-new-picks-crash.md`. Its own test passed in CI (`6739 passed` vs `6738` on main).

## Verified state at wrap

- Live https://findtorontoevents.ca/audit/ is STILL STALE. `tools/audit_honesty_live_check.py` reports `LIVE_STALE`: forbidden "5/5 checks pass", "PF2.6", "PF2.4"; missing "ghost-row check fails" and "Prediction markets stay shadow". The honesty text is on `main`; the deploy did not land.
- `db_health.json` at 18:44Z: 22,947 ghost rows, `threshold_pass: false`, open_bloat 92,232 trading_picks open and 29,247,197 `bt_backtest_trades` open, overall 3 passed / 2 failed, `harness_healthy: false`.
- `dashboard_data.json` header `generated_at` 13:06Z while the file was touched 19:01Z — the payload itself is stale.
- Unified Audit Dashboard run `43927541997` has been in `generate-and-deploy` since 19:52Z with no completion. Not cancelled.
- Book: n=7805, WR 40.9%, PF 0.91, expectancy -0.16, compounded PnL -77.7%, Sharpe -0.109.

## Asset-class findings the live page should carry

| Class | n | WR | PF | Status |
|---|---:|---:|---:|---|
| CRYPTO | 3716 | 35.8% | 0.92 | DSR 0. Not ready. |
| FOREX | 618 | 32.0% | 0.65 | Losing. |
| EQUITY | 250 | 59.2% | 0.94 | High WR, still losing. |
| COMMODITY | 231 | 40.3% | 1.03 | Only PF>1 class with n>=100. DSR 0. WATCH. |
| FUTURES | 53 | 41.5% | 1.07 | n too small. |
| ETF | 45 | 2.2% | 0.02 | Honest intrabar; ignore the daily PF 1.79 tile. |
| BOND | 26 | 7.7% | 0.39 | Insufficient. |
| MEMECOIN | 102 intrabar | 29.4% | 0.66 | Regime-concentrated. |
| PENNY / CHEAP | 4 / 1 | — | — | Insufficient. |

Prediction markets: no closed book. Polymarket/Kalshi rows `closed_picks=0`. Verified-alpha realized slice losing (n=896, WR 42.4%, PnL -193%). Prior PBO 0.603. Shadow only.

ML: the gatekeeper filters and re-ranks, it does not prove profit. `ml_score >= 0.0` counts as "validated". Consensus is a hand formula, not a trained model. Kelly/regime/heat sizing is not tied to the five gates.

## What I could not fix

1. Live deployment. Blocked on #856 merging plus a successful dashboard run.
2. The class verdict can still return MONEY_READY through an SPA OR at `alpha_engine/money_ready_verdict.py` (`PBO_THRESHOLD = 0.55`, no WFE, no live-Sharpe argument). #848 only hardens the display filter, not the generator.
3. `audit_trail/stamp_pick_quality.py` `_assign_trust_tier` still writes `PROVEN` at n>=10 and WR>=55%, and a missing DSR does not block. Deliberately excluded: it rewrites stored labels and needs its own review.
4. No live-Sharpe field exists for any class, and WFE is a PF split rather than edge retention. Those gates are unevaluable, not merely failing.
5. Pre-existing red CI on main: 22 failures in `test_wf_verdict_failing_gate.py`, `test_wf_verdict_null_block.py`, `test_phase1_active_gates.py`. Same 22 on main and on #856, so it is not caused by this work, but it blocks a clean merge signal.
6. Other seats' failures, not taken: Feed Health `43931137682` (`pm_momentum_signals` missing_from_payload), QA Market Validation `43927629856` (equity blank TP/SL 6, mismatch 10), PR #839 CI red.

## Prompts for the next agent

1. "Merge #856, then `gh workflow run audit-dashboard.yml --repo eltonaguiar/findtorontoevents_antigravity.ca`. When it completes, run `python3 tools/audit_honesty_live_check.py` from the auditpage worktree and report LIVE_OK/LIVE_STALE."
2. "Fix the 22 `test_wf_verdict_*` / `test_phase1_active_gates` failures on main first. They are the reason no audit PR can show a green check."
3. "Read `audit_dashboard/money_ready_filter.js` and `alpha_engine/money_ready_verdict.py` before touching any badge. The display filter is now fail-closed; the generator is not."
4. "Never treat win rate as profit. EQUITY is 59% WR and PF 0.94. COMMODITY is the only PF>1 class with n>=100 and its DSR is 0."
5. "Do not re-run `check_active_picks.py` or `smart_picks_engine.py` unless the human asks."

## Notes on the shared bus

- `COMS register --agent <provider>-<model> --goal ... --todo ... --done ... --files ... --commits ... --prompt ...` from the worktree you actually work in. Two agents in `auditpage` need different seats.
- `COMS send` and `COMS register` refuse key-shaped text; run `COMS guard <file>` before pushing if a file may contain secrets.
- Broker boots via `mosquitto.service` (enabled, Restart=on-failure). Worst case disk loss: wakes are gone, git is the protocol, agents re-register.
