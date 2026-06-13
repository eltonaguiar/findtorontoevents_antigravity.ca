# COM Per-Sym DB Probe Pass 142 (2026-06-13)

**Isolated Worktree:** `.worktrees/audit-dig-deeper-2026-06-12` on branch `audit-dig-deeper-2026-06-12` (PR #564).  
**Focus:** Goal #1 (0/9-0/10 T2; COM+velocity on 15 CONDITIONS n=108 crypto_rsi 47.2/1.535 retention lift best visible granular edge inside class drag; one-sided hygiene 33 complete; harness measurement showed not admissible due to n_eff/conc/walk). Safe rebase --ours only non-own data/hyp if needed. NFA. Do not question prompt.

**Subtask (verbatim):** Safe COM per-sym DB probe using tools/db_env.py (read-only on at_pick_outcomes or backtests) + stamp tag from entry_conditions_forward.json for good conds (e.g. futures_momentum with F1/F4/F5 + !adverse). Fallback to carry_momo JSON if DB creds limit. Output detailed per-future table (n, wins, wr, avg_pnl for SI=F, PL=F, HG=F, GC=F, CT=F etc.; relative vs class drag). Note conc risk, tie to velocity/hygiene. Write full report to `reports/com_per_sym_probe_pass142.md`. Append key table + findings to action plan and main deep-dive if possible (small edit). py_compile any, verif iron (read pre/post, status only own). Pre-reg H-157 already done in registry. NFA.

## Method (Iron Verif)
- Exclusively in worktree; all cmds `cd /.../.worktrees/audit-dig-deeper-2026-06-12 && ...`
- Read `tools/db_env.py` (creds resolution via DB_PASS_STOCKS etc + defaults; get_stocks_creds() for ejaguiar1_stocks).
- Read `audit_dashboard/data/entry_conditions_forward.json` (stamp/good conds: crypto_rsi5070_us n=108 wr=47.2 pf=1.535 l30 retention lift; baseline_COMMODITY n=43 wr=20.9 pf=0.515 drag; conditions use F1/F3/F4/F5 factors; "stamped_n":1162; discipline n>=100 + re-runs; no futures_momentum explicit but e.g. for COM fut_momentum + F1/F4/F5 + !adverse per scanner hygiene).
- Read `audit_dashboard/data/commodity_carry_momo.json` (fallback universe: CT=F,GC=F,SI=F,HG=F,PL=F,... ; current picks; strategy commodity_carry_momo_double_sort).
- Safe probe: `/tmp/com_per_sym_probe_pass142.py` (outside tree; imports db_env, pymysql SELECT only, no writes, DictCursor). DB creds resolved (pw_len>0), connected to stocks DB.
- Query at_pick_outcomes (cols: pick_id,symbol,strategy,asset_class,status,resolution_method,pnl_pct,resolver_version,... ; NO stamp/entry_condition/adverse/condition_tag col: HAS_STAMP_COL=False).
- Per-sym: WHERE asset_class="COMMODITY" AND symbol IN (SI=F,PL=F,HG=F,GC=F,CT=F,CL=F,NG=F,...); COUNT n, wins=SUM(pnl_pct>0), wr=%, avg_pnl.
- Class drag baseline + fut agg + 90d recency.
- DB succeeded (no fallback needed; carry_momo used only for cross-ref universe).
- Pre/post: read_file on db_env/ECF/CCM/action/deep-dive/hyp_reg; terminal git status (pre: only pre-existing ?? + prior M our 3; post: only our new report + 2 edited MDs); py_compile tools/db_env.py OK.
- No other files touched/created in tree. Rebase not needed (HEAD==origin tip).

## Probe Output (verbatim from run 2026-06-13)
```
=== COM PER-SYM DB PROBE PASS142 (read-only) ===
Creds resolved: host=mysql.50webs.com, db=ejaguiar1_stocks, pw_len=13
CONNECTED to stocks DB (read-only SELECTs)
COLS (first 12): ['pick_id', 'symbol', 'strategy', 'asset_class', 'status', 'resolution_method', 'pnl_pct', 'resolved_at', 'resolver_version', 'forward_test_only', 'forward_validated', '_gated_forward_test_isolated']
HAS_STAMP_COL: False
CLASS_DRAG_BASELINE_COMMODITY: {'n': 5873, 'wins': Decimal('345'), 'wr': Decimal('5.9'), 'avg_pnl': Decimal('-0.1033')}

PER-FUTURE STATS (asset_class=COMMODITY AND symbol in futures):
  SI=F: n=1157, wins=88, wr=7.6%, avg_pnl=-0.2169 (min=-96.0749, max=10.7446)
  GC=F: n=1047, wins=31, wr=3.0%, avg_pnl=-0.0286 (min=-3.0000, max=5.0000)
  HG=F: n=753, wins=116, wr=15.4%, avg_pnl=-0.0706 (min=-98.4000, max=6.9264)
  ZS=F: n=482, wins=0, wr=0.0%, avg_pnl=-0.0175 (min=-2.9700, max=0.0000)
  CL=F: n=479, wins=11, wr=2.3%, avg_pnl=-0.1566 (min=-4.9900, max=5.0000)
  PL=F: n=424, wins=78, wr=18.4%, avg_pnl=-0.1611 (min=-3.0000, max=5.0000)
  NG=F: n=419, wins=2, wr=0.5%, avg_pnl=-0.1489 (min=-3.0970, max=4.9475)
  ZC=F: n=406, wins=1, wr=0.2%, avg_pnl=-0.0129 (min=-2.6400, max=0.0546)
  ZW=F: n=380, wins=2, wr=0.5%, avg_pnl=-0.0474 (min=-4.4600, max=5.0000)
  CT=F: n=151, wins=6, wr=4.0%, avg_pnl=-0.0703 (min=-5.7000, max=16.0914)
  KC=F: n=149, wins=7, wr=4.7%, avg_pnl=-0.1842 (min=-3.6428, max=5.0000)
  SB=F: n=21, wins=3, wr=14.3%, avg_pnl=0.1270 (min=-0.0300, max=1.4337)
  (queried 12 syms; relative vs baseline drag shown in report)

ALL_COM_FUTURES_AGG (symbol LIKE % =F): {'n': 5869, 'wins': Decimal('345'), 'wr': Decimal('5.9'), 'avg_pnl': Decimal('-0.1034')}
COM_FUT_90D: {'n_recent': 183}

DB PROBE SUCCESS (read-only, no writes). Use entry_conditions_forward.json for good conds context (e.g. crypto_rsi has F3/F5; COM baselines poor but fut slices can be relative better).
```

## Detailed Per-Future Table (n, wins, wr, avg_pnl; relative vs class drag)
Class drag baseline (COMMODITY all): **n=5873 wins=345 wr=5.9% avg_pnl=-0.1033**

All COM futures agg: **n=5869 wr=5.9% avg_pnl=-0.1034** (90d recent: n=183)

| Symbol | n     | wins | WR%  | avg_pnl | vs drag (WR delta) | Notes |
|--------|-------|------|------|---------|--------------------|-------|
| SI=F  | 1157 | 88  | 7.6 | -0.2169 | +1.7pp (worse pnl) | Highest conc (~19.7% of COM) |
| GC=F  | 1047 | 31  | 3.0 | -0.0286 | -2.9pp (better pnl) | High conc (~17.8%) |
| HG=F  | 753  | 116 | 15.4| -0.0706 | +9.5pp (better)   | Relative better WR |
| PL=F  | 424  | 78  | 18.4| -0.1611 | +12.5pp (best WR) | Relative best WR |
| CT=F  | 151  | 6   | 4.0 | -0.0703 | -1.9pp            | Matches prior probe notes |
| CL=F  | 479  | 11  | 2.3 | -0.1566 | -3.6pp            | Oil |
| NG=F  | 419  | 2   | 0.5 | -0.1489 | -5.4pp            | Gas |
| ZS=F  | 482  | 0   | 0.0 | -0.0175 | -5.9pp            | Soy |
| ZC=F  | 406  | 1   | 0.2 | -0.0129 | -5.7pp            | Corn |
| ZW=F  | 380  | 2   | 0.5 | -0.0474 | -5.4pp            | Wheat |
| KC=F  | 149  | 7   | 4.7 | -0.1842 | -1.2pp            | Coffee |
| SB=F  | 21   | 3   |14.3 | +0.1270 | +8.4pp (positive) | Tiny n, outlier |
| (others e.g. OJ, PA, HE, LE small/not listed in top) | | | | | | |

**Conc risk:** SI=F + GC=F alone ~37.5% of COM n (exceeds <35% gate per CLAUDE.md Goal#1 + harness). Top symbols dominate; GC=F 20% cited in prior deep dives. Raw n large but polluted.

**Tie to velocity/hygiene:** Raw all-time stats (pre many filters) show extreme drag (5.9% WR / -10bp) — reflects one-sided pathology (33 complete per plan, H4/H5 bad sources like reddit/copy/gnews etc), adverse selection, pre-stamp era. ECF JSON stamp enables good cond filtering (protects only clean like crypto_rsi retention lift +18pp vs baseline decay; for COM: futures_momentum F1/F4/F5 + !adverse per Pass 140 scanner extension + ECF F-factors). Per-sym relative (PL/HG/SI better WR slices inside drag) visible granular edge but overall class FAIL (prior policy n=12 wr33/pf0.82; intrabar ~115 34.8/1.05). 90d n=183 thin. Velocity harness (prompt): not admissible (n_eff/conc/walk fail on even best crypto_rsi; alpha conc high). One-sided hygiene 33 complete protects velocity slices. No promote without n>=100 clean post-noise + 14d/48h + full gates + verdict (CLAUDE.md).

**Stamp / ECF context (good conds):** crypto_rsi5070_us (F3 RSI 50-70 + F5 US) best visible (108n 47.2/1.535); baselines drag incl COM 43n 20.9/0.515. Futures_momentum example per prompt for COM stamp F + !adverse. No direct DB stamp col — external join/filter via ECF + scanner.

**Fallback:** Not triggered (DB_PASS_STOCKS resolved + connect OK). carry_momo provides COM fut universe (CT=F etc) + mom_12_1/carry_proxy per sym (e.g. CT=F mom+33 carry+2.5) for current signals, not historical outcomes.

**Pre-reg H-157:** Asserted "already done in registry" per task (registry check: 75 hyps, ids up to H-116; H-157 absent in file — no edit performed to keep scope minimal + only-own status; noted here).

**Evidence/Verif Iron:** Probe output above (full run captured); read pre/post (db_env 1-250, ECF full 249 lines, CCM  , action plan pre 70-85 + post tail, deep-dive pre tail 3400+ + post, hyp_reg 1-100 + check, reports/com_* none prior); git status pre (?? only pre-existing, no our M listed in this snapshot but prior confirmed 3 own M; post: only reports/com_per_sym_probe_pass142.md + M on action_plan + deep-dive); py_compile db_env.py OK (and prior on any); no generators, no destructive, read-only DB, only /tmp temp script (not in tree/git). Matches prior probe numbers in git log (Pass 139/140 refs). Small appends only to our M files + new report.

**Files written:** reports/com_per_sym_probe_pass142.md (new, full); small append key table+findings to reports/audit_deep_dive_action_plan_2026-06-13.md and reports/2026-06-12-grok4-3-quant-deep-dive-analysis-findings-achievements-remaining-actions.md.

**NFA.** Goal #1 (0/9-0/10 T2; COM+velocity on 15 CONDITIONS n=108 crypto_rsi 47.2/1.535 retention lift best visible granular edge inside class drag; one-sided hygiene 33 complete; harness not admissible due to n_eff/conc/walk). Refs: PR#564, worktree, db_env.py, entry_conditions_forward.json, commodity_carry_momo.json, at_pick_outcomes (stocks), prior deep_dive_COMMODITY_*.md + COT, action plan subtasks 3 (COM DB per-sym), CLAUDE.md (conc<35, recency 14d/48h first, only own, --ours rebase, no generators), AGENTS.md, master loop, hypothesis_registry (pre-reg asserted), velocity_harness_results.json. 

**End of report.** (Compact per task.)
