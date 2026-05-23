# IDEA-A: Proven COMMODITY Criteria Research — Academic + Practitioner

## Context

We run a multi-asset algorithmic trading system. COMMODITY asset class is currently sub-Tier-2:
- WR=46.9%, PF=1.78, n=750
- PF is already Tier-2 quality — the constraint is WR below 50% floor
- Primary instruments: commodity futures ETFs — USO (crude oil), UNG (natural gas),
  DBA (agriculture), DBB (base metals), CT=F (cotton futures)
- CT=F dominates volume at ~87% concentration (CT=F concentration cap is an active gate)
- Target: WR>50%, PF>1.5 (Tier-2), long-run: WR>55% / PF>2.0 (Tier-1)
- Hold period: 5–30 days forward returns

We need to enumerate **proven, academically-grounded criteria** for COMMODITY futures/ETFs
that can be wired into `calculate_smart_score()`, applied as pick gates, or used as filters.

## Existing criteria to EXCLUDE (already implemented)

Do NOT suggest any of the following — they are already wired:
- Roll yield / term structure slope (already in CO-1 hypothesis)
- COT (Commitment of Traders) — H-004 LIVE, COT net_z field populated for CT=F
- EIA inventory surprise (already wired, H-004 adjacent)
- Price/volume momentum (already in multiple strategies)
- ML gradient boost score (already in pipeline)
- Confidence threshold gates (M-034, M-035 live)

## Research Task

Enumerate the **top 10 proven criteria** from academic literature and practitioner research
that predict 5–30 day forward returns for COMMODITY futures ETFs (USO/UNG/DBA/DBB/CT=F),
where:

1. Data is available via FREE public sources:
   - yfinance: ETF price/volume history, futures front-month prices (CT=F, CL=F, NG=F)
   - FRED (Federal Reserve): free economic data (PMI, CPI components, USD index DXY)
   - Quandl/Nasdaq Data Link free tier: some commodity series
   - EIA.gov API (free): crude oil, natural gas production/inventory data
   - USDA free data: crop reports, acreage estimates (agriculture commodities)
   - Alternative free sources acceptable if publicly accessible

2. NOT already in our system (see exclusion list above)

3. Ranked by: (expected WR lift × data availability × implementation simplicity)
   - Top 3 MUST be immediately implementable with free APIs, complexity ≤ 3

For each criterion provide:

### Criterion Format

**Name**: [criterion name]
**Mechanism**: [1–2 sentence explanation of why this predicts returns]
**Academic Reference**: [paper/author/year — if none, cite practitioner source]
**Data Source**: [exact API endpoint or free data source]
**Implementation Complexity**: [1=trivial, 2=easy, 3=moderate, 4=hard, 5=research-grade]
**Expected WR Lift**: [estimate in percentage points vs baseline, cite source if known]
**Wire-In Point**: [smart_score boost | gate | filter | signal source | new strategy]
**Free API Feasibility**: [yes/partial/no — explain if partial]

## Wire-In Architecture (for reference)

Our system's pick scoring pipeline (most relevant hooks):
- `alpha_engine/quality_gates.py` → `passes_active_gate()` / `passes_smart_gate()` — binary gates
- `alpha_engine/smart_picks_engine.py` → `calculate_smart_score()` — composite score 0–1
- `alpha_engine/production_scanner.py` — upstream signal generation
- `audit_trail/quality_gates.py` → gate registry with shadow mode support
- New hypothesis slots: H-009 through H-018 available in hypothesis registry
- DXY booster already wired (`alpha_engine/dxy_booster.py`) — do not re-suggest

## Focus Areas (prioritized)

Research especially these underexplored COMMODITY-specific factors:

1. **Weather/climate signals**: temperature anomaly forecasts → agriculture/energy demand
2. **Dollar strength orthogonal signals**: beyond DXY — trade-weighted dollar vs commodity-specific
3. **Cross-commodity momentum spillover**: crude oil leads base metals leads agriculture?
4. **Seasonal demand cycles**: not calendar month but end-use demand cycles (heating, planting)
5. **Production cost floor**: breakeven cost analysis → price floor support level
6. **Currency pairs for commodity-exporting nations**: AUD, CAD, BRL correlation to commodity
7. **Equity market stress**: VIX regime → commodity safe-haven vs risk-off behavior
8. **Index rebalancing pressure**: commodity index (GSCI, BCOM) rebalancing creates predictable flows
9. **Supply chain disruption proxies**: freight rates (Baltic Dry Index) → commodity price lead
10. **Macro regime indicators**: PMI expansion/contraction → industrial commodity demand

## Instrument-Specific Notes

- **USO (crude oil)**: seasonal summer driving demand, refinery utilization, OPEC+ compliance
- **UNG (natural gas)**: extreme seasonality (heating demand), storage injection/withdrawal cycle
- **DBA (agriculture)**: USDA crop reports, weather, currency of major exporters
- **DBB (base metals)**: China PMI driven, global capex cycle, inventory at LME warehouses
- **CT=F (cotton futures)**: USDA acreage + crop condition reports, China import demand, USD

## Output Format

Rank all 10 by (expected edge × data availability × implementation simplicity).
Top 3 must be immediately free-API implementable (complexity ≤ 3).
For criteria 4–7: acceptable if complexity ≤ 4.
For criteria 8–10: may require moderate engineering (complexity ≤ 5).

After the ranked list, provide a **consensus recommendation**: if you had to pick ONE
criterion to implement first for maximum WR lift with minimum implementation cost, which
would it be and why?

Also note: CT=F represents ~87% of our COMMODITY picks. Any criterion that applies
specifically to cotton futures (CT=F) should be flagged with [CT=F PRIORITY] as it will
have outsized impact on our WR.
