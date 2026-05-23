# Round 3 Review — Renaissance Technologies lens (2026-05-12)

Re: `reports/quant_swarm_merged_round2_2026-05-12.md`. Terse. No diplomacy.

## 1. Merge OVER-weights: COMMODITY/CT=F as "highest-conviction edge"

Section "STRONG CONVERGENCE #1" treats n=750 / PF 1.78 / DSR 1.0 as bankable. From the Medallion lens this is one instrument, one asset, ~3 years of de facto data and a single COT regime. DSR 1.0 on n=750 single-symbol is barely above the multiple-testing floor once you account for the prior search across 7 asset classes and dozens of strategies — implicit Bonferroni alone eats most of it. The merge also conflates Miffre 2010's *class-wide* carry alpha with our *single-contract* signal; that is a citation laundering move, not a replication. Cap CT=F at curiosity-sized until cross-contract (GC=F, CL=F, HG=F) replication clears CPCV.

## 2. Merge UNDER-weights: execution / market-impact / capacity

The entire merge is silent on slippage, queue position, fill realism and capacity. "1-contract sizing" in the Month-6 table (line 195-201) sidesteps the question — at any size that matters, CT=F COT-driven signals decay on a 1-2 day half-life and the entry mid-to-fill cost is structurally material. There is no `transaction_cost_model.py`, no impact term in `calculate_smart_score`, no fill-latency audit. Edge claims absent a cost model are gross-of-cost theatre.

## 3. Blind spot across ALL 7 personas: the trades are not independent

Every persona reasons over `n=750`, `n=421`, `n=8067` as if those were i.i.d. samples. They are not. Picks share underlying bars, share strategy DNA, share regime windows, and many are near-duplicates emitted minutes apart on the same symbol (the MATIC artifact in memory is a 660-row example). Effective sample size after autocorrelation + cohort overlap is likely 1/5 to 1/20 of nominal. Every DSR, every PF confidence band, every "n≥100 ramp" gate is computed against an inflated denominator. Nobody — Renaissance round-1 included — proposed a block-bootstrap or cluster-robust SE protocol. Fix: ship `effective_n` per cohort using overlap-adjusted Newey-West before any LIVE promotion.

— RenTech

---
NFA. Research surface.
