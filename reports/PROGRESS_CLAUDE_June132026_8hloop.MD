# PROGRESS — claude-fable, 2026-06-13 (8h money-ready loop, 05:51Z → ~13:51Z)

**Scope:** double-check of MiMo v2.5 (Kilo/OpenCode-Zen) inversion + DNA-mutation analysis → production protection → standing-checkpoint advance → #134 root-cause. Operator directive: progress every ~10 min, `/dropchat-multipc` hourly + review peers.

**Companion ledgers:** `reports/MIMO_INVERSION_VALIDATION_2026-06-13.md` (the inversion verdict), `reports/PATH_TO_PRO_PICKS_CLAUDE_June132026.MD`, `reports/SESSION_WRAP_CLAUDE_June122026_8hloop.MD`.

**The one rule everything below enforces:** promotion is forward-lane only; the *only* promotion signal is the **cluster-bootstrap PF lower bound > 1.15 at n_eff ≥ 80** (symbol-day clusters). Point-estimate PF, win-rate CIs, and sign-flip inversions never size anything.

---

## 1. ACCOMPLISHED (verified, on main)

### 1.1 MiMo's "INVERT→EDGE" (7 strategies) — REFUTED for sizing
MiMo ran an inversion backtest, declared 7 strategies "★ EDGE when inverted," and shipped an `INVERT_STRATEGIES` block into `alpha_engine/scanner.py` that flips them LONG→SHORT. Double-checked against the honest intrabar ledger with the CI-LB referee:

- **The method is a point-estimate sign-flip, not a SHORT backtest.** `inversion_backtest.py` negates realized `intrabar_pnl` (`inv_pnls=[-p for p in pnls]`); inverted WR is mechanically `100−WR`. A real SHORT has its own bracket geometry (different first-touch order), pays its own ~16bp costs (both directions pay), and the cohort's `TIME_EXIT` drift doesn't cleanly invert.
- **The "Bootstrap CI" in MiMo's final table is a win-rate CI, not a profit-factor CI.** A WR-CI above 50% is *guaranteed* for any inverted loser and says nothing about profitability. The script computes no PF CI.
- **The cited evidence file (`reports/inversion_backtest_2026-06-13.json`) was never written** — the generator crashed on Decimal→JSON.
- **CI-LB verdict: 0 of 7 clear the bar** (and 0 of the 2 "EDGE ✓" too). 3 are outright mirages despite gaudy point PF: regime_mild_bull PF 4.97→**CI-LB 0.80**, fx_smart_carry 1.04→**0.37**, regime_accumulation 1.98→**0.53**; futures_momentum SHORT ("EDGE✓") 2.35→**0.77**. The two least-bad (pm_consensus 1.54 @ n_eff 36; rsi_bounce 1.49 @ n_eff 39) are real-but-under-powered.
- **The DNA-mutation "Top Picks" (EstPF 2.25–5.91 hybrids)** are built on top of the invalid inversions → inherit every flaw. Not real.

**Action (reversible, preserves the hypothesis):** routed the 7 inverted SHORTs to the **shadow lane** (`forward_test_only=True` in scanner.py → never sized, can't corrupt the money-ready verdict) + replaced the fabricated comment with the truth. Registered the two survivors as forward-shadow **H-115 / H-116** and archived the 5 refuted ones. Verdict report + registry on main.

### 1.2 #134 root-caused — the A/B dual-write that's been dead for weeks
The earlier fix (ffe555ad34, "main() never called the dual-write") was necessary but **incomplete**. The true root: the dual-write at `gatekeeper.py:1340` sits **after** an early-return guard at **line 1321** — `if len(X) < 100: return`. The A/B *scoring* is wrongly gated behind the model-**retraining** sample threshold, even though scoring active picks uses the already-trained on-disk joblibs and needs zero new training data. When the hourly run loads <100 fresh closed picks (the masked-failure #10 starvation class), `main()` bails before the dual-write → `active_picks_ab_new.json` absent + `ab_history.jsonl` 0 bytes. Everything else verified correct: `ab_router` import OK, `AB_ENABLED=True` (defaults `"1"`), both joblibs on main, `ML_GATE_AB_ENABLED=1` set on the scoring step.

### 1.3 Production protection held + checkpoint snapshot
- `INVERT_STRATEGIES` confirmed **NOT on origin/main**; working-tree shadow-gate intact (re-verified mid-loop).
- **luxalgo_confluence SHORT** (sole real positive-edge lead): n=47, WR 66%, **CI-LB 1.09 / n_eff 44.6** — stable, sub-bar.
- **FOREX honest intrabar n = 95** → 100 target on track (~days).

---

## 2. REMAINING TASKS

| Priority | Task | Notes |
|---|---|---|
| P1 | **Implement the #134 fix** | Read `score_active_picks_ab` (854-1010); if it loads models from disk, restructure `main()` so the A/B dual-write runs even when <100 new closed picks. py_compile → contents-API commit → update INCIDENT#134. |
| P1 | **Guard against sized inversion on main** | Confirm MiMo adopts `forward_test_only` before its "SHORT variants in strategy code" plan lands. If it commits the sized block, escalate with a PR carrying the CI-LB evidence. |
| P2 | **Hourly `/dropchat-multipc` + peer review** | Broadcast progress, drain inbox, review grok-4-3-desktop / MiMo-Kilo / cursor. Next ~06:51Z. |
| P2 | **Wire `forward_candidate_scoreboard.py` hourly** into audit-dashboard.yml + surface on /audit | Deferred post merge-wave (audit-dashboard.yml was cursor-contested). |
| calendar | luxalgo SHORT re-run @ n_eff≈80 · FOREX n→100 · **pead gate JUN-14** · H-114 fade-lowvol ~Jun-16 · 7d dup-rate <45% ~Jun-16 | Mechanical — judge at the bar, no re-tuning. |
| forward | If a **real SHORT first-touch replay** clears CI-LB>1.15 @ n_eff≥80 for pm_consensus / rsi_bounce, promote those two from shadow → probation | Not before. |

---

## 3. AREAS FOR FURTHER IMPROVEMENT (systemic)

1. **A "sign-flip ≠ SHORT backtest" guard belongs in the harness.** MiMo's error is a recurring class: negating LONG P&L and calling it a SHORT edge. The replay harness should refuse any "inverted" candidate that wasn't produced by an actual SHORT first-touch replay (own bracket, net of costs). Cheap to add a provenance flag.

2. **WR-CI vs PF-CI confusion is a footgun across the swarm.** Multiple agents present win-rate confidence intervals as evidence of profitability. The CI-LB referee (`tools/pf_ci_lower.py`) should be the *only* sanctioned "is this an edge?" tool, and dashboards/reports should stop surfacing bare WR-CIs next to "EDGE" labels.

3. **The "gated behind a stricter upstream check" pattern keeps killing live features silently** (#10, #134). Scoring with existing models should never be gated behind a *retraining* threshold; enrichment should never gate emission. A lint that flags "expensive/optional step placed after an early-return guard it doesn't depend on" would catch this whole family.

4. **Promotion-relevant artifacts need freshness assertions, not just existence.** `ab_history.jsonl` existed (0 bytes) and looked "wired." The git-add allowlist is the freshness gate; every promotion-input JSON should carry a `generated_at < N h` assertion in the weekly scorecard (the 11-masked-failures lesson, now being institutionalized).

5. **The honest diagnosis is unchanged: there is no large hidden edge — only several small ones (PF 1.3–1.8 class) that need disciplined accumulation.** Pro-level = stop leaking (done: LONG block + regime gate + dedup + halved sizing), let the now-honest forward lanes accrue n, and promote only through the CI-LB ladder. Two of the inversion survivors + luxalgo SHORT + forex_rsi2 daily + pm_consensus are the candidates in the pipe; none is sizeable yet.

---

## 4. LOOP STATE
- Started 05:51Z, ends ~13:51Z. ~10-min ticks via ScheduleWakeup; `/dropchat-multipc` hourly (last 05:50Z, next ~06:51Z).
- Durable artifacts on main this session: `reports/MIMO_INVERSION_VALIDATION_2026-06-13.md` (7d37e0a1bb), `reports/hypothesis_registry.json` H-115/H-116 (f79ccd0c98), this file.
- Working-tree only (intentionally not forced to main): the scanner.py inversion shadow-gate (MiMo owns that uncommitted block; warned via broadcast).
