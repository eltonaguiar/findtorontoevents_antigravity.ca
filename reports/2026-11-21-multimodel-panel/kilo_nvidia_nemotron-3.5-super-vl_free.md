
> code · nvidia/nemotron-3.5-super-vl:free

1. Panel B's commodity recommendation ("T+3 COT embargo and dedup by signal date") is statistically wrong: commodity n=48 sits below the n>=100 forward-rows promotion floor and PF 0.29 is far from IR>=0.5, so no embargo or dedup can make it promotable regardless of cost assumptions.

2. It is a category error for EQUITY and ETF. CRYPTO (CI[-0.647,-0.114] excludes zero, negative) and the n<100 classes are correctly blocked, and FOREX (WEAK, n>=100) is appropriately blocked, but EQUITY CI[-0.516,+0.720] and ETF CI[-0.420,+0.450] both include zero, so they are inconclusive, not blocked; a class-level CI including zero cannot rule out a subset edge the aggregate dilutes.

3. Run an EQUITY mid-cap quality factor test: 20-60 day holds, matched cap/style benchmark, 2x slippage, collect >=100 forward rows, require IR>=0.5 with CI excluding zero. It targets the inconclusive equity class, launches within a week, and is falsifiable in 90 days given <=60-day holds.

4. Confidence 80%. It falls if forward equity CI includes zero or IR<0.5 at 2x slippage; it rises if a forward equity subset shows CI excluding zero with IR>=0.5.
