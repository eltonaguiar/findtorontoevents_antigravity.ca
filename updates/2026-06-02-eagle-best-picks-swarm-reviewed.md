# EAGLE Best Picks — Swarm-Reviewed Summary (2026-06-02)

## What was broken / missing

- No single updates-page entry tied **production money-ready**, **AI tournament paper edge**, and **lab shadow sleeves** with explicit “why we cite each stat.”
- `ai_tournament_picks_latest.json` export has **null outcomes** on rows — symbol/direction stats cannot be recomputed from that file alone.
- Prior swarm run rejected claims because evidence pack lacked leaderboard + EAGLE3 directional table.

## What changed

1. **`tools/verify_best_picks_swarm.py`** — enriched evidence: `money_ready_verdict.json`, `ai_tournament_leaderboard.json`, EAGLE3 directional/symbol tables, lab sleeve metrics, tournament export null-outcome note.
2. **`tools/generate_eagle_best_picks_guide.py`** — generates `updates/eagle-best-picks-guide-2026-06-02.html` with full + ELI5 explanations, EAGLE file index, recent planning docs.
3. **`updates/index.html`** — new card (before `AUTO-INJECTED:INCIDENTS-ENHANCEMENTS:START`) linking to the HTML guide.
4. **`reports/best_picks_swarm_review_2026-06-02.json`** — LiteLLM swarm artifact.

## Verification

```bash
python3 tools/verify_best_picks_swarm.py
python3 tools/generate_eagle_best_picks_guide.py
python3 -c "import py_compile; py_compile.compile('tools/verify_best_picks_swarm.py', doraise=True)"
```

Deploy (updates FTP):

```bash
python3 tools/deploy_audit_files.py --only updates
curl -sI 'https://findtorontoevents.ca/updates/eagle-best-picks-guide-2026-06-02.html'
```

## Best picks verdict (evidence-bound)

| Pick | Tier | Source |
|------|------|--------|
| deepseek_v4, gpt4o | PAPER WATCH | `ai_tournament_leaderboard.json` |
| CRYPTO SHORT | PAPER WATCH | `EAGLE3_2026-06-02_minimax-m3-free.MD` |
| EEM, IWM, GLD | PAPER WATCH | EAGLE3 symbol table |
| BAC, JPM, MSFT, NVDA | PAPER WATCH | EAGLE3 LONG bias; prod EQUITY fails |
| etf_verified_dual_momentum | SHADOW PILOT | lab + WF; live ETF n=3 |
| /audit production | DO NOT SIZE | `money_ready: []` |
