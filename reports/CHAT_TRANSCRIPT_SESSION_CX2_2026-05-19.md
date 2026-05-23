# Session CX2 Chat Transcript — 2026-05-19

**Session type:** Autonomous continuation (prior context compacted)
**Date:** 2026-05-19
**Branch:** main
**Agent:** claude-sonnet-4-6-desktop

---

## Session Goals (from prior session mandate)

"Ask agent swarm for ideas, then proceed to your discretion." Autonomous continuation. Prior session (CW) concluded with hypothesis research track exhausted and dropchat sent. The one remaining actionable item was implementing `fetch_form4_purchases()` in H-028 research script.

---

## Work Done This Session

### 1. Implemented H-028 Form 4 XML Fetch (`tools/e1_insider_cluster_buy_research.py`)

**Problem:** `fetch_form4_purchases()` was a documented scaffold that returned an empty list. The module comment described the EDGAR path but didn't walk it.

**Root cause discovered during implementation:**
The submissions API (`data.sec.gov/submissions/CIK{cik}.json`) lists only the company's OWN filings (10-K, 8-K, etc.). Form 4 filings are stored under each individual INSIDER's CIK, not the issuer's CIK. So querying the issuer's submissions API returns 0 Form 4s for most companies.

**Correct approach:** EDGAR's EFTS full-text search API (`efts.sec.gov/LATEST/search-index`) finds Form 4s by issuer CIK because the issuerCik field (zero-padded 10 digits) is indexed in the full text of every Form 4 XML.

**EFTS response structure (discovered via debugging):**
- `_id` = `"{accession_no}:{document_name}"` (e.g., `0001654708-23-000017:primary_doc.xml`)
- `_source.adsh` = accession number (NOT `accession_no`)
- `_source.ciks[0]` = filer's (insider's) CIK, `ciks[1]` = issuer's CIK
- `_source.file_date` = filing date

**Three functions added:**
1. `_http_text(url)` — GET text/HTML/XML helper
2. `_parse_form4_xml(xml, filing_date)` — Extract code-P transactions from ownership XML using `xml.etree.ElementTree`; walks `nonDerivativeTransaction` elements, filters `transactionCode == 'P'`
3. `_form4_xml_for_accession(filer_cik_int, acc_no, primary_doc)` — Fetches ownership XML; tries primary doc name from EFTS `_id` suffix first, falls back to `{acc_no}.xml`, `form4.xml`, `xsForm4.xml`, and finally scans filing index HTML for `.xml` links

**`fetch_form4_purchases()` rewrite:**
- Hits EFTS at `?q="{cik_padded}"&forms=4&dateRange=custom&startdt=2020-01-01&enddt=2026-06-01`
- Processes up to 40 hits (rate-limit cap, well under SEC's 10 req/sec guidance)
- 0.12s sleep between XML fetches
- Degrades gracefully: missing hits → empty purchases → caller logs UNTESTED-data-gap

### 2. H-028 Test Results

**UNIVERSE_QUICK (8 tickers — meme stocks):** 1/8 tickers produced real data
- TLRY: offline=False, clusters=1, price_bars=1968

**UNIVERSE_FULL (30 tickers):** Same — only TLRY got real clusters

**Root cause of UNTESTED-data-gap:**
- AMC's first 20 Form 4 XMLs: 0 code-P transactions. Confirmed via direct API walk.
- SOFI: 4 code-P from 2 insiders (too few, too sparse to cluster ≥3 distinct within 10 days)
- CLF: 6 code-P from 5 insiders (scattered across years — no 10-day clustering period detected)
- The meme/volatile universe (AMC, GME, BBBYQ, RIDE, NKLA, GOEV, etc.) does not have insider open-market purchases. These insiders receive options/RSUs and prefer to sell, not buy on the open market.

**Verdict correctly remains:** UNTESTED-data-gap (universe mismatch, not code failure)

**What would actually test H-028:** A broader Russell-2000-style sample across financials, industrials, energy — sectors where management does buy shares on the open market. Would require a new M-107 pre-registration as a distinct hypothesis.

### 3. Commits This Session

| SHA | Subject |
|---|---|
| `144ec7ef3a` | feat(H-028): implement Form 4 code-P XML fetch via EDGAR EFTS API |
| `2452f0cd25` | feat(IDEA-A+H-004): earnings surprise PEAD factor + H-004 CI workflow (pulled from remote) |

### 4. hypothesis_registry.json Updated

H-028 status changed from `UNTESTED` → `UNTESTED-DATA-GAP` with full result record documenting:
- Code status: IMPLEMENTED
- Root cause: universe mismatch
- Next step: new pre-registration with diverse Russell-2000-style universe

---

## OpenRouter Swarm Input Received (FYI)

User forwarded a swarm response to the prompt: "11/11 pre-registered causal hypotheses killed by walk-forward harness. Name ONE retail-accessible strategy that could survive."

The swarm (at $0.01, 11% score) recommended:

**BTC Miner Capitulation / Hash Ribbon Signal (CRYPTO)**

Key elements:
- **Signal:** Go LONG BTC when estimated daily miner profit margin (revenue/TH - electricity cost/TH) drops below zero AND 30d MA hash rate < 60d MA hash rate
- **Exit:** When 30d MA hash rate crosses back above 60d MA hash rate
- **Data:** CoinGecko/Binance (BTC price), mempool.space (hash rate), EIA (electricity cost) — all free, no key
- **Causal mechanism:** Mining has a hard electricity cost floor (~60-80% of OpEx). When unprofitable, miners MECHANICALLY sell BTC to pay utility bills. This is involuntary supply pressure, not speculative behavior. Hash rate decline = selling cohort shrinking. When hash recovers, forced supply is exhausted.
- **Sign-stability argument:** The causal direction CANNOT flip. Miners always sell when underwater. This is structural, not behavioral.
- **Cost:** <15bps round-trip on major spot exchanges. Well within 30bps budget.
- **Historical:** Signal has fired 4-5 times in 2014-2024 (BTC bottoms of 2015, 2018, 2020, 2022), each followed by 80-250% moves over 3-6 months.

**NOT on the forbidden list:** Not COT, not funding-rate directional, not roll-yield, not on-chain counts (hash rate is an economic/physical metric, not an address count).

---

## State at Session End

### Hypothesis Registry Status

| ID | Family | Status |
|---|---|---|
| H-001 | COT_positioning (CT=F) | LIVE_TESTING — 2/3 windows stable |
| H-002 | PEAD daily | SHADOW_IMPLEMENTATION |
| H-003 | Funding-rate cross-timeframe | SHADOW_LIVE |
| H-004 | Pending | PENDING_IMPLEMENTATION |
| H-005 | Realized_vol_z | FAILED_ARCHIVED |
| H-009 | Order-flow delta | KILLED |
| H-011 | Stablecoin_flow_ratio | KILLED |
| H-019 | Vol_cluster CRYPTO | REJECTED |
| H-020-H-025 | Free API batch | Mixed (H-021 NEAR_ADMISSIBLE 2/3 windows) |
| H-027 | CO-1 inventory surprise | UNTESTED (needs EIA_API_KEY) |
| H-028 | E-1 insider cluster buy | UNTESTED-DATA-GAP (code works, universe wrong) |
| H-029 | Vol-cluster CRYPTO v2 | TESTED_KILL |
| H-030 | Small-cap liq-shock EQUITY | TESTED_KILL |
| H-031 | Agricultural harvest seasonality | UNTESTED (density gap) |

### Open Items (Not Fixed This Session)

1. **H-021 re-run (~2026-05-26):** COT small-spec harness at 2/3 windows with strong same-sign eff (1.48, 1.21). Needs ~7 more days of COMMODITY picks resolving for window 3.
2. **H-027:** Needs EIA_API_KEY (free registration at eia.gov).
3. **H-028v2 (new pre-reg):** Would need M-107 pre-registration of a diverse Russell-2000-style universe to actually test the insider-cluster-buy signal.
4. **BTC Miner Capitulation hypothesis:** Swarm recommends this as the most causally-grounded surviving CRYPTO strategy. Would need M-107 pre-registration as a new hypothesis if pursued.
5. **B10 UEPS gate:** Auto-resolves ~2026-05-22 when ≥10 UEPS closed picks accumulate.
6. **MySQL dedup fix:** Requires MySQL access (not locally fixable).
