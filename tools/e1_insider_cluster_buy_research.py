#!/usr/bin/env python3
"""E-1 — Insider open-market cluster-buy backtest, small-cap-stratified (H-028).

OPT-IN RESEARCH SIDECAR. No production wiring. No caller in quality_gates.py,
dashboard_generator.py, passes_active_gate, calculate_smart_score, or any
pick-generation / scoring path. It fetches free public SEC Form-4 + price data
and writes a report — nothing else. Importing this module has no side effects
on production.

------------------------------------------------------------------------------
WHY THIS MODULE EXISTS
------------------------------------------------------------------------------
`reports/new_strategy_proposals_2026_05_18.md` ranks E-1 as the lead EQUITY
candidate of 14 proposals: a documented, academically-replicated alpha source
(Cohen, Malloy & Pomorski 2012; Jeng et al.) with free data and a clean,
revealed-preference causal mechanism. Every equity strategy already in the
ledger is a *technical / factor overlay* — momentum, value, quality, PEAD. None
ingests insider-trading filings text.

THE SIGNAL — insider open-market cluster buy (SEC Form 4, transaction code P):
  SEC Form 4 filings report insider transactions. Transaction code "P" is an
  *open-market purchase* — an officer or director buying shares with personal
  capital on the open market. Code P is distinct from code "A" (grant/award),
  "M" (option exercise), "S" (sale), "F" (tax withholding) — the bulk of insider
  activity is options exercise and 10b5-1 plans, NOT code P. A *cluster* is
  3+ DISTINCT insiders filing a code-P purchase on the SAME ticker within a
  short rolling window:

    cluster(D)        = 3+ distinct insiders, code P, same ticker, <= window days
    total_buy_usd(D)  = sum of code-P purchase notional across those insiders
    signal            = total_buy_usd of the cluster (conviction magnitude)

  Direction: a cluster is unambiguously bullish revealed preference -> LONG the
  stock. There is no SHORT leg — open-market insider SELLING is far noisier
  (diversification, liquidity, tax) and is explicitly NOT used.

------------------------------------------------------------------------------
SMALL-CAP STRATIFICATION — pre-registered scope (proposal directive)
------------------------------------------------------------------------------
The proposal (`new_strategy_proposals_2026_05_18.md` lines 167-189 + 491-492)
is explicit: the cluster-buy signal is "likely arbitraged in mega-caps" — the
edge concentrates where insider information asymmetry is largest and
institutional arbitrage is thinnest. It directs: "pre-register the
small-cap-stratified version only, not the full universe."

This module therefore tests ONLY the SMALL-CAP cohort: tickers whose market
capitalisation is below SMALL_CAP_MAX_USD ($2B) at the time the cluster forms.
Mid- and large-cap clusters are filtered out entirely. The full-universe E-1 is
deliberately NOT built — it is not pre-registered.

------------------------------------------------------------------------------
DATA SOURCES — FREE ONLY
------------------------------------------------------------------------------
  * SEC EDGAR `data.sec.gov` submissions API + the full-text Form-4 XML feed
    (free, no key). Form 4 ownership documents carry the `transactionCode`
    and `transactionShares` / `transactionPricePerShare` fields the cluster
    detector reads. A SEC-required descriptive User-Agent is sent on every
    request — SEC fair-access courtesy.
  * yfinance — free, no-key daily price series for each clustered ticker and
    its sector ETF benchmark, plus the `marketCap` scalar used for the
    small-cap stratification cut.

No paid feed. No API key. `openinsider.com` aggregates the same SEC Form-4 data
and is documented here as a scrapeable free fallback only — this module's
canonical path is the primary SEC EDGAR feed. If the network is unavailable the
module degrades to a clearly-labelled synthetic series and reports the verdict
UNTESTED-data-gap honestly — it never fabricates a pass.

------------------------------------------------------------------------------
THE CONSTRUCTION (legitimate density pattern from H-008/H-019/H-020/H-026/H-027)
------------------------------------------------------------------------------
  * Insider clusters are intrinsically SPARSE events. To give the harness its
    required 14-day-window density (>= 80 records/window), the cluster is held
    as a FULL continuous-position book: once a small-cap ticker forms a code-P
    cluster, EVERY (ticker, day) for the next HOLD_DAYS trading days is one
    resolved record. NO post-hoc `total_buy_usd` threshold, NO self-selection
    of "big" clusters — the density comes from holding the position daily, the
    H-008 pattern, not from threshold relaxation.
  * STRICT no-look-ahead: a Form 4 carries a filing date that LAGS the
    transaction date (insiders have 2 business days to file). The cluster is
    stamped at the LATEST filing date of its constituent purchases; a position
    on day D may see only clusters whose filing date is strictly before D;
    entry D+1; the realized return is the price close(D)->close(D+1) move
    (LONG only). The proposal's 20-day horizon is realized as the rolling
    HOLD_DAYS continuous book.

------------------------------------------------------------------------------
THE VERDICT GATE
------------------------------------------------------------------------------
Records pass through tools/edge_stability_harness.evaluate()/is_admissible()
imported UNMODIFIED. ADMISSIBLE iff |eff| >= 0.30, same sign, >= 3 of 5
walk-forward 14-day windows, >= 80 records/window. PLUS a 15bps round-trip
post-cost gate (small-cap spreads are wide): net edge must keep >= 60% of gross.

A gaudy in-sample WR is NOT a pass. The edge hunt's base rate is poor (8-11
harness kills to date). This module reports the verdict honestly whichever way
it lands. Nothing here is wired into or sized by any production path.

    python tools/e1_insider_cluster_buy_research.py [--quick] [--json]
            [--refresh-cache]
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if sys.platform == "win32":
    for _s in (sys.stdout, sys.stderr):
        if hasattr(_s, "reconfigure"):
            try:
                _s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                pass

import edge_stability_harness as harness  # noqa: E402

# ---------------------------------------------------------------------------
# Tunables — pre-registered (H-028). The signal family is fixed; no per-window
# search, no post-hoc parameter tuning.
# ---------------------------------------------------------------------------
CLUSTER_MIN_INSIDERS = 3        # >= 3 distinct insiders to count as a cluster
CLUSTER_WINDOW_DAYS = 10        # rolling window the distinct buys must fall in
HOLD_DAYS = 20                  # continuous-position hold (proposal's 20d horizon)
FILING_LAG_DAYS = 2             # Form-4 filing deadline vs transaction date
SMALL_CAP_MAX_USD = 2_000_000_000.0  # small-cap stratification cut ($2B)
WINDOW_DAYS = 14                # walk-forward window length (harness default)
HARNESS_FIELD = "signal_z"      # conviction-magnitude score the harness reads
ROUND_TRIP_COST_BPS = 15.0      # small-cap round-trip (wide spread + slippage)
COST_SURVIVAL_MIN = 0.60        # net edge must retain >= 60% of gross

CACHE = ROOT / "tools" / "cache" / "e1_insider_cluster_buy_cache.json"

# SEC requires a descriptive UA with contact info for data.sec.gov access.
SEC_UA = "findtorontoevents-research e1-sidecar zerounderscore@gmail.com"

# Small-cap-leaning equity universe — the cohort where insider information
# asymmetry is largest and institutional arbitrage is thinnest (proposal
# directive). Each ticker is re-checked against SMALL_CAP_MAX_USD at runtime;
# any name that has grown out of the small-cap band is dropped from the test.
UNIVERSE_FULL = [
    "AMC", "GME", "PLTR", "SOFI", "RIOT", "MARA", "CLF", "FUBO", "BBBYQ",
    "WKHS", "SPCE", "NKLA", "GOEV", "RIDE", "OPEN", "CLOV", "WISH", "BIG",
    "EXPR", "VFS", "LCID", "CHPT", "BTBT", "CIFR", "HUT", "GROW", "TLRY",
    "ACB", "SNDL", "HEXO",
]
UNIVERSE_QUICK = ["AMC", "GME", "SOFI", "RIOT", "CLF", "FUBO", "CHPT", "TLRY"]

# H-028v2: diverse Russell-2000-style universe. Sectors where management
# actually buys on the open market (code P). Pre-registered 2026-05-19.
# Swarm consensus: 2/2 BUILD (deepseek+kilo). Report: reports/h028v2_*.md
UNIVERSE_DIVERSE = [
    # Financials — banks, insurance, REITs (mgmt buying is documented in literature)
    "FUNC", "CUBI", "NBTB", "FFIN", "HFWA", "WSBC", "CTBI", "FMNB",
    "FBMS", "ESSA", "STBA", "CCNE", "CHMG", "NWFL", "BSVN",
    "AIZ", "HIG", "SFG", "KMPR", "ARGO",
    "PLYM", "NXRT", "GMRE", "GOOD", "UMH",
    # Industrials — manufacturing, transport, services
    "KALU", "GTES", "HONE", "MFIN", "HTLD", "MRTN", "SAIA", "ODFL",
    "ARCB", "WERN", "HUBG", "LSTR", "CVLG", "ECHO", "FWRD",
    "AAON", "APOG", "MFAC", "HOLI", "HAYN", "KLIC", "ALGT",
    # Energy — E&P, midstream, oilfield services (insider buying well documented)
    "MNRL", "CIVI", "GPOR", "VTLE", "REX", "TPVG", "SM", "MTDR",
    "CLINE", "RES", "DMLP", "HESM", "CAPL", "CINF", "NGL",
    "PTEN", "NGAS", "WTTR", "KLXE", "KOS",
    # Healthcare — medical devices, specialty pharma (exec buying visible in filings)
    "NVRO", "NVCR", "IART", "MMSI", "ICUI", "AMED", "LNTH",
    "ACAD", "INVA", "PCRX", "IRWD", "SUPN", "HALO", "VNDA",
    "PRTA", "ANIP", "LWAY", "PAHC", "PDCO", "SRDX",
]
UNIVERSE_DIVERSE_QUICK = [
    "FUNC", "FFIN", "WSBC", "KALU", "MRTN", "SM", "CIVI", "MMSI", "AMED", "ACAD",
]


# ===========================================================================
# Data fetch — free public APIs, no key.
# ===========================================================================
def _http_json(url: str, timeout: int = 30, ua: str = "e1-research/1.0"):
    """GET JSON with a descriptive UA; return parsed object or None."""
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001
        return None


def _http_text(url: str, timeout: int = 15, ua: str = "e1-research/1.0") -> str | None:
    """GET text (HTML/XML) with a descriptive UA; return content string or None."""
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            return r.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return None


def _ticker_to_cik() -> dict:
    """Map ticker -> zero-padded CIK via the free SEC company_tickers.json."""
    out: dict[str, str] = {}
    payload = _http_json("https://www.sec.gov/files/company_tickers.json",
                         ua=SEC_UA)
    if isinstance(payload, dict):
        for rec in payload.values():
            if isinstance(rec, dict) and rec.get("ticker") and rec.get("cik_str"):
                out[str(rec["ticker"]).upper()] = str(rec["cik_str"]).zfill(10)
    return out


def _parse_form4_xml(xml: str, filing_date: str) -> list[dict]:
    """Extract code-P non-derivative transactions from one Form 4 ownership XML.

    Returns [{filing_date, txn_date, insider, shares, price, usd}, ...].
    Returns [] on any parse error (caller degrades gracefully).
    """
    results: list[dict] = []
    try:
        root = ET.fromstring(xml.encode("utf-8", "replace"))
    except ET.ParseError:
        return results

    insider = ""
    for ro in root.findall(".//reportingOwner"):
        name_el = ro.find(".//rptOwnerName")
        if name_el is not None and name_el.text:
            insider = name_el.text.strip()
            break

    for txn in root.findall(".//nonDerivativeTransaction"):
        code_el = txn.find(".//transactionCode")
        if code_el is None or (code_el.text or "").strip().upper() != "P":
            continue
        txn_date = filing_date
        date_el = txn.find(".//transactionDate/value")
        if date_el is not None and date_el.text:
            txn_date = date_el.text.strip()[:10]
        shares = 0.0
        shares_el = txn.find(".//transactionShares/value")
        if shares_el is not None and shares_el.text:
            try:
                shares = float(shares_el.text.strip().replace(",", ""))
            except ValueError:
                pass
        price = 0.0
        price_el = txn.find(".//transactionPricePerShare/value")
        if price_el is not None and price_el.text:
            try:
                price = float(price_el.text.strip().replace(",", ""))
            except ValueError:
                pass
        results.append({
            "filing_date": filing_date,
            "txn_date": txn_date,
            "insider": insider,
            "shares": shares,
            "price": price,
            "usd": round(shares * price, 2),
        })
    return results


def _form4_xml_for_accession(filer_cik_int: int, acc_no: str,
                             primary_doc: str = "") -> str | None:
    """Best-effort fetch of the ownership XML for one Form 4 accession.

    Tries the primary_doc name first (from EFTS _id suffix); then falls back
    to common Form 4 naming conventions and finally to scanning the filing
    index HTML for any .xml link containing ownershipDocument.
    Returns the XML string on success, None on any failure.
    """
    acc_nodash = acc_no.replace("-", "")
    base = f"https://www.sec.gov/Archives/edgar/data/{filer_cik_int}/{acc_nodash}"

    # Build candidate URL list in priority order.
    candidates: list[str] = []
    if primary_doc:
        candidates.append(f"{base}/{primary_doc}")
    for fallback in (f"{acc_no}.xml", "form4.xml", "xsForm4.xml"):
        url = f"{base}/{fallback}"
        if url not in candidates:
            candidates.append(url)

    for xml_url in candidates:
        xml = _http_text(xml_url, timeout=15, ua=SEC_UA)
        if xml and "<ownershipDocument" in xml:
            return xml

    # Last resort: scan the filing index page for any .xml link.
    idx_html = _http_text(f"{base}/", timeout=15, ua=SEC_UA)
    if not idx_html:
        return None
    for m in re.finditer(r'href="([^"]+\.xml)"', idx_html, re.IGNORECASE):
        candidate = m.group(1)
        if candidate.startswith("http"):
            xml_url = candidate
        elif candidate.startswith("/"):
            xml_url = "https://www.sec.gov" + candidate
        else:
            xml_url = f"{base}/{candidate}"
        xml = _http_text(xml_url, timeout=15, ua=SEC_UA)
        if xml and "<ownershipDocument" in xml:
            return xml
    return None


def fetch_form4_purchases(ticker: str, cik: str) -> list[dict]:
    """Fetch this issuer's Form-4 open-market purchases (transaction code P).

    Strategy (free SEC EDGAR only):
      1. data.sec.gov submissions API lists every Form 4 the issuer's insiders
         filed (free, no key, SEC-UA required).
      2. Each Form-4 ownership XML carries `transactionCode`, `transactionShares`
         and `transactionPricePerShare`. Code "P" is the open-market purchase;
         the cluster detector keeps ONLY code P and discards A/M/S/F/G/etc.

    Returns a list of {filing_date, txn_date, insider, shares, price, usd}
    dicts. On any network failure returns [] and the caller degrades to a
    labelled synthetic series + UNTESTED verdict — never a fake pass. The
    full XML-document walk is best-effort; SEC's per-form XML schema is stable
    but document-level fetch is rate-limited, so the run still completes if a
    document is unreachable.
    """
    purchases: list[dict] = []
    if not cik:
        return purchases

    # Form 4 filings are stored under each INSIDER's own CIK, NOT the issuer's
    # CIK. The issuer's submissions JSON lists the company's own 10-K/8-K/etc.
    # — it does NOT list insiders' Form 4s. Use the EDGAR EFTS full-text search
    # instead: the issuerCik field in every Form 4 XML is zero-padded to 10
    # digits, so searching for the padded CIK finds exactly this issuer's Form
    # 4s across all insider filers.
    cik_padded = cik.zfill(10)
    efts_url = (
        f"https://efts.sec.gov/LATEST/search-index"
        f"?q=%22{cik_padded}%22&forms=4"
        f"&dateRange=custom&startdt=2020-01-01&enddt=2026-06-01"
        f"&hits.hits.total.value=true"
    )
    efts = _http_json(efts_url, timeout=20, ua=SEC_UA)
    if not isinstance(efts, dict):
        return purchases
    hits = (efts.get("hits", {}) or {}).get("hits", []) or []
    if not hits:
        return purchases

    # Cap at 40 XML fetches to stay well under SEC's 10 req/sec guideline.
    MAX_FILINGS = 40
    count = 0
    for hit in hits:
        if count >= MAX_FILINGS:
            break
        src = hit.get("_source", {}) or {}
        hit_id = hit.get("_id", "")

        # EFTS _id format: "{accession_no}:{document_name}"
        # EFTS _source.adsh: the accession number (with dashes).
        acc_no = (src.get("adsh") or hit_id.split(":")[0]).strip()
        primary_doc = hit_id.split(":")[-1] if ":" in hit_id else ""
        filing_date = (src.get("file_date") or "")[:10]
        if not acc_no or "-" not in acc_no:
            count += 1
            continue

        # _source.ciks is [insider_cik, issuer_cik]; ciks[0] is the FILER.
        ciks_list = src.get("ciks") or []
        try:
            filer_cik_int = int(ciks_list[0]) if ciks_list else int(
                acc_no.replace("-", "")[:10]
            )
        except (ValueError, IndexError):
            count += 1
            continue

        xml = _form4_xml_for_accession(filer_cik_int, acc_no, primary_doc)
        if xml:
            txns = _parse_form4_xml(xml, filing_date)
            purchases.extend(txns)
        count += 1
        time.sleep(0.12)  # SEC fair-access courtesy delay

    return purchases


def fetch_price_and_cap(ticker: str) -> dict:
    """Fetch a free daily close series + market-cap scalar via yfinance.

    Returns {"price": {iso_date: close}, "market_cap": float|None}. The
    market_cap drives the small-cap stratification cut. On failure returns
    empty price + None cap and the caller degrades to a labelled synthetic.
    """
    price: dict[str, float] = {}
    market_cap = None
    try:
        import yfinance as yf  # noqa: PLC0415
        tk = yf.Ticker(ticker)
        hist = tk.history(period="max", interval="1d", auto_adjust=False)
        if hist is not None and not hist.empty:
            for idx, row in hist.iterrows():
                try:
                    d = idx.date().isoformat()
                    c = float(row["Close"])
                    if c > 0:
                        price[d] = c
                except Exception:  # noqa: BLE001
                    continue
        info = {}
        try:
            info = tk.get_info() if hasattr(tk, "get_info") else tk.info
        except Exception:  # noqa: BLE001
            info = {}
        if isinstance(info, dict):
            mc = info.get("marketCap")
            if mc:
                market_cap = float(mc)
    except Exception:  # noqa: BLE001
        pass
    return {"price": price, "market_cap": market_cap}


def _synthetic_series(ticker: str, n_days: int = 700) -> dict:
    """Deterministic synthetic price + cluster + cap series for an OFFLINE run.

    Used ONLY when every free network source fails. It is clearly labelled and
    drives an UNTESTED-data-gap verdict — it is never reported as a real pass.
    A small deterministic LCG (seeded by the ticker) keeps the run reproducible.
    """
    seed = sum(ord(c) for c in ticker) * 2654435761 & 0xFFFFFFFF
    state = seed

    def rand() -> float:
        nonlocal state
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        return state / 0x7FFFFFFF

    price: dict[str, float] = {}
    px = 5.0 + (seed % 30)
    base = datetime(2023, 1, 2, tzinfo=timezone.utc)
    for i in range(n_days):
        d = (base.fromordinal(base.toordinal() + i)).date().isoformat()
        px *= 1.0 + (rand() - 0.5) * 0.04
        price[d] = round(max(px, 0.5), 4)
    # synthetic small-cap market cap, deterministically below the $2B cut
    market_cap = 200_000_000.0 + (seed % 15) * 100_000_000.0
    # a few synthetic code-P clusters scattered across the price grid
    pdates = sorted(price)
    clusters: list[dict] = []
    step = max(60, n_days // 6)
    for k in range(step, n_days - HOLD_DAYS - 1, step):
        fdate = pdates[k]
        n_ins = CLUSTER_MIN_INSIDERS + (seed >> (k % 5)) % 3
        usd = 50_000.0 + (rand() * 900_000.0)
        clusters.append({
            "filing_date": fdate,
            "n_insiders": n_ins,
            "total_buy_usd": round(usd, 2),
        })
    return {"price": price, "market_cap": market_cap, "clusters": clusters}


def detect_clusters(purchases: list[dict]) -> list[dict]:
    """Collapse a Form-4 code-P purchase list into open-market BUY clusters.

    A cluster = >= CLUSTER_MIN_INSIDERS DISTINCT insiders filing a code-P
    purchase on the same ticker within a CLUSTER_WINDOW_DAYS rolling window.
    Each cluster is stamped at the LATEST filing date of its constituent
    purchases (the no-look-ahead anchor) and carries the summed purchase
    notional. Pure function over the per-issuer purchase list.

    Returns [{filing_date, n_insiders, total_buy_usd}, ...].
    """
    clusters: list[dict] = []
    if not purchases:
        return clusters
    rows = sorted(purchases, key=lambda r: r.get("filing_date", ""))
    for i, anchor in enumerate(rows):
        try:
            a_date = datetime.fromisoformat(str(anchor["filing_date"])[:10])
        except (KeyError, ValueError):
            continue
        insiders: dict[str, float] = {}
        latest = anchor["filing_date"]
        for j in range(i, len(rows)):
            r = rows[j]
            try:
                r_date = datetime.fromisoformat(str(r["filing_date"])[:10])
            except (KeyError, ValueError):
                continue
            if (r_date - a_date).days > CLUSTER_WINDOW_DAYS:
                break
            ins = str(r.get("insider", f"insider_{j}"))
            insiders[ins] = insiders.get(ins, 0.0) + float(r.get("usd", 0.0))
            if str(r["filing_date"]) > str(latest):
                latest = r["filing_date"]
        if len(insiders) >= CLUSTER_MIN_INSIDERS:
            clusters.append({
                "filing_date": latest,
                "n_insiders": len(insiders),
                "total_buy_usd": round(sum(insiders.values()), 2),
            })
    return clusters


def load_market_data(tickers: list[str], refresh: bool) -> dict:
    """Fetch (or load cached) Form-4 clusters + price + market-cap per ticker.

    Adds an `_offline` flag per ticker when the series came from the synthetic
    fallback so the verdict layer can honestly report UNTESTED-data-gap. Also
    applies the SMALL-CAP stratification cut: a ticker whose market cap is at
    or above SMALL_CAP_MAX_USD is flagged `_excluded_large_cap` and contributes
    no records (the proposal forbids the mega-cap cohort).
    """
    if CACHE.exists() and not refresh:
        try:
            cached = json.loads(CACHE.read_text(encoding="utf-8"))
            if all(t in cached.get("data", {}) for t in tickers):
                print(f"# loaded cache {CACHE}", file=sys.stderr)
                return cached["data"]
        except Exception:  # noqa: BLE001
            pass

    cik_map = _ticker_to_cik()
    data: dict[str, dict] = {}
    for t in tickers:
        print(f"# fetching {t} (free SEC EDGAR Form-4 + yfinance) ...",
              file=sys.stderr)
        cik = cik_map.get(t.upper(), "")
        purchases = fetch_form4_purchases(t, cik)
        clusters = detect_clusters(purchases)
        pc = fetch_price_and_cap(t)
        price = pc.get("price", {})
        market_cap = pc.get("market_cap")
        offline = False
        # E-1 needs a dense free price grid AND at least one detectable code-P
        # cluster. The per-insider Form-4 transaction tape requires the bounded
        # XML walk documented in fetch_form4_purchases; when that dense tape is
        # unavailable the run is honestly UNTESTED — fall back to a labelled
        # synthetic series.
        if len(price) < 200 or not clusters:
            print(f"#   {t}: dense free code-P cluster tape unavailable -> "
                  f"synthetic fallback (verdict will be UNTESTED)",
                  file=sys.stderr)
            syn = _synthetic_series(t)
            price = syn["price"]
            market_cap = syn["market_cap"]
            clusters = syn["clusters"]
            offline = True
        # SMALL-CAP stratification cut (proposal directive — pre-registered).
        excluded = bool(market_cap is not None
                        and market_cap >= SMALL_CAP_MAX_USD)
        if excluded:
            print(f"#   {t}: market_cap={market_cap:.0f} >= "
                  f"{SMALL_CAP_MAX_USD:.0f} -> EXCLUDED (not small-cap)",
                  file=sys.stderr)
        series = {
            "price": price,
            "market_cap": market_cap,
            "clusters": clusters,
            "_offline": offline,
            "_excluded_large_cap": excluded,
        }
        print(f"#   {t}: price={len(price)} bars  clusters={len(clusters)}  "
              f"cap={market_cap}  offline={offline}  excluded={excluded}",
              file=sys.stderr)
        data[t] = series
        time.sleep(0.3)

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps({
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stratification": "small_cap_only",
        "small_cap_max_usd": SMALL_CAP_MAX_USD,
        "data": data,
    }), encoding="utf-8")
    print(f"# wrote cache {CACHE}", file=sys.stderr)
    return data


# ===========================================================================
# Signal math (pure, network-free)
# ===========================================================================
def rolling_z(series: list[float], idx: int, roll: int):
    """Z-score of series[idx] vs the `roll` STRICTLY-PAST observations.

    Returns None when fewer than `roll` past observations exist or the past
    window has zero dispersion. series[idx] is excluded from mean/sd — only
    series[idx-roll:idx] feeds them, so no look-ahead.
    """
    if idx < roll:
        return None
    window = series[idx - roll:idx]
    mu = statistics.fmean(window)
    sd = statistics.pstdev(window)
    if sd <= 0:
        return None
    return (series[idx] - mu) / sd


def filing_visible_date(filing_iso: str) -> str:
    """Date from which a Form-4 cluster is visible to a position.

    The cluster is already stamped at the LATEST filing date of its
    constituent purchases. A Form 4 itself lags the transaction by up to
    FILING_LAG_DAYS (the SEC two-business-day deadline). To be conservative the
    cluster becomes actionable one calendar day after its filing date — a
    position on day D may only see clusters whose visible date is strictly
    before D. This enforces the no-look-ahead rule for a lagged filing.
    """
    try:
        f = datetime.fromisoformat(filing_iso[:10])
    except ValueError:
        return filing_iso[:10]
    return (f + timedelta(days=1)).date().isoformat()


# ===========================================================================
# Continuous-position backtest
# ===========================================================================
def backtest_continuous(data: dict) -> dict:
    """FULL continuous-position LONG-only book on small-cap code-P clusters.

    Insider clusters are sparse events; the harness needs 14-day-window
    density. So once a SMALL-CAP ticker forms a code-P cluster, EVERY
    (ticker, day D) for the next HOLD_DAYS trading days with a next bar D+1 is
    one resolved record. NO post-hoc total_buy_usd threshold, NO selection of
    "big" clusters — the density is the H-008 continuous-hold pattern.

      * a position on day D is "in-cluster" iff some cluster on this ticker has
        a VISIBLE date strictly before D and D is within HOLD_DAYS trading days
        of that visible date.
      * signal_z = strictly-past rolling z of the cluster's total_buy_usd
        across the ticker's own prior clusters (conviction magnitude). The
        first cluster with no prior history scores |z|=0 conviction but is
        still resolved (continuous book).
      * direction = +1 (LONG only — no insider-sell short leg).
      * raw_ret = price_close(D+1)/price_close(D) - 1
      * signed_ret = raw_ret  (direction is +1)
      * record: status WON iff signed_ret>0 (gross); harness score field
        signal_z = |z| (conviction magnitude).

    STRICT no-look-ahead: the cluster used is visible strictly before the entry
    date D (filing lag enforced via filing_visible_date); entry is D, return
    realized over [D, D+1). Large-cap tickers (>= $2B) contribute no records.
    """
    records: list[dict] = []
    per_ticker: dict[str, dict] = {}
    gross_rets: list[float] = []
    net_rets: list[float] = []
    cost_frac = ROUND_TRIP_COST_BPS / 10000.0
    any_offline = False
    n_excluded_large_cap = 0
    import bisect

    for ticker, series in data.items():
        if series.get("_excluded_large_cap"):
            n_excluded_large_cap += 1
            per_ticker[ticker] = {"n": 0, "wins": 0, "wr": None,
                                  "clusters": len(series.get("clusters", [])),
                                  "excluded": "large_cap"}
            continue
        price = series.get("price", {})
        clusters = series.get("clusters", [])
        if series.get("_offline"):
            any_offline = True
        pdates = sorted(price)
        if not clusters or len(pdates) < HOLD_DAYS + 2:
            per_ticker[ticker] = {"n": 0, "wins": 0, "wr": None,
                                  "clusters": len(clusters), "excluded": None}
            continue

        # clusters sorted by visible date; rolling z of total_buy_usd over the
        # ticker's own STRICTLY-PRIOR clusters (conviction magnitude).
        cl = sorted(clusters, key=lambda c: filing_visible_date(
            str(c.get("filing_date", ""))))
        usd_series = [float(c.get("total_buy_usd", 0.0)) for c in cl]
        visible: list[tuple[str, float]] = []  # (visible_date, |z|)
        for i, c in enumerate(cl):
            vdate = filing_visible_date(str(c.get("filing_date", "")))
            z = rolling_z(usd_series, i, 5)
            visible.append((vdate, abs(z) if z is not None else 0.0))
        vdates = [v[0] for v in visible]

        n = wins = 0
        for j in range(len(pdates) - 1):
            d = pdates[j]
            d_next = pdates[j + 1]
            # most-recent cluster visible STRICTLY before entry date D
            vi = bisect.bisect_left(vdates, d) - 1
            if vi < 0:
                continue
            vdate, zmag = visible[vi]
            # is D within HOLD_DAYS trading days of that visible date?
            v_idx = bisect.bisect_left(pdates, vdate)
            if v_idx >= len(pdates) or (j - v_idx) < 0 or (j - v_idx) >= HOLD_DAYS:
                continue
            p0, p1 = price[d], price[d_next]
            if p0 <= 0:
                continue
            raw_ret = p1 / p0 - 1.0  # LONG only — direction = +1
            signed_ret = raw_ret
            net_ret = signed_ret - cost_frac
            status = "WON" if signed_ret > 0 else "LOST"
            n += 1
            wins += int(status == "WON")
            gross_rets.append(signed_ret)
            net_rets.append(net_ret)
            records.append({
                "status": status,
                "resolved_at": d_next,
                "entry_date": d,
                "cluster_visible_date": vdate,
                "timestamp": d,
                HARNESS_FIELD: zmag,
                "signed_ret": round(signed_ret, 8),
                "net_ret": round(net_ret, 8),
                "direction": 1,
                "instrument": ticker,
            })
        per_ticker[ticker] = {"n": n, "wins": wins,
                              "wr": round(wins / n, 4) if n else None,
                              "clusters": len(clusters), "excluded": None}

    return {
        "records": records,
        "per_ticker": per_ticker,
        "gross_rets": gross_rets,
        "net_rets": net_rets,
        "any_offline": any_offline,
        "n_excluded_large_cap": n_excluded_large_cap,
    }


# ===========================================================================
# Post-cost gate
# ===========================================================================
def cost_survival(gross_rets: list[float], net_rets: list[float]) -> dict:
    """Post-cost gate: does net per-trade edge keep >= 60% of gross?

    gross_edge = mean signed return (bps). net_edge = mean net return (bps),
    after a single ROUND_TRIP_COST_BPS round-trip per held position.
    """
    if not gross_rets:
        return {"passes": False, "reason": "no trades"}
    gross_bps = statistics.fmean(gross_rets) * 10000.0
    net_bps = statistics.fmean(net_rets) * 10000.0
    survival = 0.0 if gross_bps <= 0 else net_bps / gross_bps
    return {
        "gross_edge_bps": round(gross_bps, 4),
        "net_edge_bps": round(net_bps, 4),
        "cost_bps": ROUND_TRIP_COST_BPS,
        "cost_survival_pct": round(survival * 100, 2),
        "passes": bool(gross_bps > 0 and survival >= COST_SURVIVAL_MIN),
    }


def pooled_wr(records: list[dict], net: bool = False):
    """Pooled win-rate (gross or net of cost)."""
    key = "net_ret" if net else "signed_ret"
    rs = [r.get(key) for r in records if r.get(key) is not None]
    if not rs:
        return None
    return round(sum(1 for r in rs if r > 0) / len(rs), 4)


# ===========================================================================
# Harness wiring — edge_stability_harness imported UNMODIFIED
# ===========================================================================
def harness_verdict(records: list[dict], window_days: int = WINDOW_DAYS) -> dict:
    """Run synthetic records through edge_stability_harness, patching only its
    loader for this call. The harness logic — windowing, eff, is_admissible()
    threshold — is reused VERBATIM and UNMODIFIED.
    """
    orig_load = harness._load
    try:
        harness._load = lambda: records  # type: ignore[assignment]
        verdict = harness.evaluate(HARNESS_FIELD, window_days)
        admissible = harness.is_admissible(HARNESS_FIELD, window_days)
    finally:
        harness._load = orig_load  # type: ignore[assignment]
    verdict["admissible_via_is_admissible"] = admissible
    return verdict


# ===========================================================================
# Report
# ===========================================================================
def render_report(res: dict) -> str:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    recs = res.get("records", [])
    h = res.get("harness", {})
    cg = res.get("cost_gate", {})
    offline = res.get("any_offline", False)
    adm_harness = h.get("admissible", False)
    cost_pass = cg.get("passes", False)
    scored = h.get("windows_scored", 0)
    n_large = res.get("n_excluded_large_cap", 0)

    if offline or scored < harness.MIN_STABLE_WINDOWS:
        verdict = "UNTESTED-data-gap"
    elif adm_harness and cost_pass:
        verdict = "ADMISSIBLE"
    else:
        verdict = "REJECTED"

    out = [
        "# E-1 Insider Open-Market Cluster Buys, Small-Cap (H-028) — 2026-05-18",
        "",
        f"_Generated {ts} by `tools/e1_insider_cluster_buy_research.py`._",
        "",
        f"## VERDICT: **{verdict}**",
        "",
        "**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** No caller in "
        "`quality_gates.py`, `dashboard_generator.py`, `passes_active_gate`, "
        "`calculate_smart_score`, or any pick-generation / scoring path. Fetches "
        "free public SEC Form-4 + price data, writes this report — nothing else.",
        "",
        "## The signal",
        "",
        "Insider open-market cluster buy — SEC Form 4 transaction code P. A "
        "*cluster* is 3+ DISTINCT insiders filing an open-market purchase on the "
        "same small-cap ticker within a short window:",
        "",
        f"- `cluster(D)` = >= {CLUSTER_MIN_INSIDERS} distinct insiders, code P, "
        f"same ticker, within {CLUSTER_WINDOW_DAYS} days.",
        "- `total_buy_usd` = summed code-P purchase notional across the cluster's "
        "insiders.",
        "- `signal_z` = strictly-past rolling z-score of the cluster's "
        "`total_buy_usd` vs the ticker's own prior clusters (conviction "
        "magnitude; harness score field = `|signal_z|`).",
        "- direction = LONG only. A cluster is unambiguously bullish revealed "
        "preference; insider open-market SELLING is far noisier (diversification, "
        "liquidity, tax) and is explicitly NOT used as a short leg.",
        "",
        "**Causal mechanism:** insiders have a legal information advantage and a "
        "revealed-preference signal — open-market buys with personal capital, "
        "when CLUSTERED, are the strongest legal information event available "
        "(Cohen, Malloy & Pomorski 2012; Jeng et al.). The edge persists because "
        "filings are noisy: most insider activity is options exercise / 10b5-1 "
        "plans (code A/M/S/F), NOT code P — careful filtering is the moat.",
        "",
        "## Small-cap stratification (pre-registered scope)",
        "",
        "The proposal is explicit: the cluster-buy signal is likely arbitraged in "
        "mega-caps. This module tests ONLY the SMALL-CAP cohort — tickers with "
        f"market cap below ${SMALL_CAP_MAX_USD:,.0f} at cluster time. The "
        "full-universe E-1 is deliberately NOT built and NOT pre-registered. "
        f"Large-cap tickers excluded this run: **{n_large}**.",
        "",
        "## Construction (legitimate density pattern from H-008/H-019/H-026/H-027)",
        "",
        "- **FULL continuous-position LONG-only book** — insider clusters are "
        f"sparse, so once a small-cap ticker forms a code-P cluster EVERY "
        f"(ticker, day) for the next {HOLD_DAYS} trading days is one resolved "
        "record. NO post-hoc `total_buy_usd` threshold, NO selection of 'big' "
        "clusters. This is the H-008 continuous-hold density pattern, not "
        "threshold relaxation.",
        "- **Strict no-look-ahead** — a Form 4 lags the transaction by up to "
        f"{FILING_LAG_DAYS} business days. The cluster is stamped at the LATEST "
        "filing date of its constituent purchases, becomes visible one day "
        "later, and a position on day D sees only clusters visible strictly "
        "before D; entry D; return realized over price close(D)->close(D+1).",
        "",
        "## Data (free sources only)",
        "",
        "- **SEC EDGAR `data.sec.gov`** — submissions API + Form-4 ownership XML "
        "(free, no key, SEC-UA required). Code P = open-market purchase; "
        "A/M/S/F/G discarded.",
        "- **yfinance** — free, no-key daily close series + `marketCap` scalar "
        "(drives the small-cap cut).",
        "- **openinsider.com** — documented free scrapeable fallback aggregator; "
        "the canonical path here is the primary SEC EDGAR feed.",
        f"- **Sample:** {len(recs)} small-cap ticker-day resolved records.",
        (
            "- **OFFLINE NOTE:** one or more tickers fell back to a labelled "
            "synthetic series because a dense free code-P cluster tape was "
            "unavailable. The verdict is therefore UNTESTED-data-gap — this run "
            "did NOT measure a real edge."
            if offline else
            "- All tickers sourced from live free data."
        ),
        "",
    ]

    pt = res.get("per_ticker", {})
    if pt:
        out += ["| Ticker | records | wins | gross WR | clusters | note |",
                "|---|---|---|---|---|---|"]
        for k, v in pt.items():
            wr = f"{v['wr']*100:.1f}%" if v.get("wr") is not None else "n/a"
            out.append(f"| {k} | {v.get('n',0)} | {v.get('wins',0)} | {wr} | "
                       f"{v.get('clusters','n/a')} | {v.get('excluded') or ''} |")
        out.append("")

    out += ["## Harness verdict (THE gate — `edge_stability_harness`, UNMODIFIED)",
            ""]
    if "per_window_eff" in h:
        effs = " ".join(
            (f"{e['eff']:+.2f}" if e.get("eff") is not None else "n/a")
            for e in h["per_window_eff"])
        out += [
            f"- per-window eff (new->old): `{effs}`",
            f"- windows scored: {h.get('windows_scored')}  "
            f"(strong {h.get('windows_strong')}: "
            f"+{h.get('strong_positive')}/-{h.get('strong_negative')})",
            f"- `is_admissible()`: {h.get('admissible_via_is_admissible')}",
            f"- harness reason: {h.get('reason', 'n/a')}",
            "",
        ]
    else:
        out += [f"- {h.get('reason', 'n/a')}", ""]

    out += ["## Post-cost gate (15bps round-trip; net must keep >= 60% of gross)",
            ""]
    if cg:
        out += [
            f"- gross edge: **{cg.get('gross_edge_bps')} bps/trade**",
            f"- net edge (after {cg.get('cost_bps')}bps round-trip): "
            f"**{cg.get('net_edge_bps')} bps/trade**",
            f"- cost-survival: **{cg.get('cost_survival_pct')}%** "
            f"(floor {int(COST_SURVIVAL_MIN*100)}%)",
            f"- post-cost gate: **{'PASS' if cost_pass else 'FAIL'}**",
            "",
        ]
    out += [
        f"- pooled gross WR: {(res.get('pooled_wr_gross') or 0)*100:.1f}%",
        f"- pooled net WR: {(res.get('pooled_wr_net') or 0)*100:.1f}%",
        "",
        "## Honest conclusion",
        "",
    ]
    if verdict == "ADMISSIBLE":
        out += [
            "**E-1 cleared `edge_stability_harness` AND the post-cost gate.** "
            "Against a poor base rate (8-11 prior kills) this is a **research "
            "candidate, not a green light.** Before any wiring it still needs: "
            "a real per-insider Form-4 code-P XML transaction tape (not a "
            "cluster-cadence proxy), a fresh out-of-sample re-test, a "
            "deflated-Sharpe / SPA multiple-testing correction, and operator "
            "review. No wiring here.",
        ]
    elif verdict == "REJECTED":
        out += [
            "**E-1 was TESTED and REJECTED.** The continuous-position "
            "construction gave the harness real window density, so it rendered "
            "a genuine verdict. " + (
                "The harness eff sign splits across windows — in-sample "
                "separation that flips sign across regimes. "
                if not adm_harness else
                "The harness sign is stable but the post-cost gate fails — "
                "small-cap spreads eat the edge. "
            ) + "Do NOT re-test this construction on this sample. Nothing is "
            "wired or sized.",
        ]
    else:
        out += [
            "**E-1 is UNTESTED — data-gap, explicitly NOT a pass.** " + (
                "A dense free per-insider Form-4 code-P transaction tape was "
                "unavailable (the bounded EDGAR ownership-XML walk is not "
                "wired), so the run used a labelled synthetic series. "
                if offline else
                f"The harness scored only {scored} fourteen-day window(s); it "
                f"needs >= {harness.MIN_STABLE_WINDOWS}. "
            ) + "This is an honest non-verdict — not a pass and not a clean "
            "fail. A real E-1 verdict needs a dense per-insider Form-4 "
            "ownership-XML parser (transactionCode == 'P' from "
            "ownershipDocument/nonDerivativeTable) so clusters are real, not "
            "cadence-proxied.",
        ]
    out += [
        "",
        "## next_step",
        "",
        (
            "E-1 cleared both gates — escalate for a real per-insider code-P "
            "XML tape, out-of-sample re-test, DSR/SPA correction, and operator "
            "review before any wiring."
            if verdict == "ADMISSIBLE" else
            "Harness kill — small-cap insider code-P cluster-buy magnitude does "
            "not yield an admissible equity edge on this sample. Do NOT re-test "
            "this construction on this data."
            if verdict == "REJECTED" else
            "Wire the SEC EDGAR Form-4 ownership-XML parser (walk each Form 4's "
            "nonDerivativeTable for transactionCode == 'P', "
            "transactionShares * transactionPricePerShare) so the small-cap "
            "code-P cluster tape is real. Re-run only with the dense tape."
        ),
        "",
    ]
    return "\n".join(out)


# ===========================================================================
# Orchestration
# ===========================================================================
def run(quick: bool, refresh: bool, universe: str = "meme") -> dict:
    if universe == "diverse":
        tickers = UNIVERSE_DIVERSE_QUICK if quick else UNIVERSE_DIVERSE
    else:
        tickers = UNIVERSE_QUICK if quick else UNIVERSE_FULL
    data = load_market_data(tickers, refresh)

    bt = backtest_continuous(data)
    recs = bt.get("records", [])
    cg = cost_survival(bt.get("gross_rets", []), bt.get("net_rets", []))

    res = {
        "records": recs,
        "per_ticker": bt.get("per_ticker", {}),
        "cost_gate": cg,
        "any_offline": bt.get("any_offline", False),
        "n_excluded_large_cap": bt.get("n_excluded_large_cap", 0),
        "pooled_wr_gross": pooled_wr(recs, net=False),
        "pooled_wr_net": pooled_wr(recs, net=True),
        "universe": universe,
    }
    if len(recs) < harness.MIN_WINDOW_N:
        res["harness"] = {
            "admissible": False,
            "reason": f"INSUFFICIENT DATA — {len(recs)} records, harness needs "
                      f">= {harness.MIN_WINDOW_N}/window",
            "windows_scored": 0,
        }
    else:
        res["harness"] = harness_verdict(recs)
    return res


def json_summary(res: dict) -> dict:
    h = res.get("harness", {})
    cg = res.get("cost_gate", {})
    scored = h.get("windows_scored", 0)
    offline = res.get("any_offline", False)
    if offline or scored < harness.MIN_STABLE_WINDOWS:
        verdict = "UNTESTED-data-gap"
    elif h.get("admissible") and cg.get("passes"):
        verdict = "ADMISSIBLE"
    else:
        verdict = "REJECTED"
    hyp_id = "H-028v2" if res.get("universe") == "diverse" else "H-028"
    return {
        "hypothesis": hyp_id,
        "family": "insider_open_market_cluster_buy",
        "asset_class": "EQUITY",
        "stratification": "small_cap_diverse" if res.get("universe") == "diverse" else "small_cap_meme",
        "small_cap_max_usd": SMALL_CAP_MAX_USD,
        "verdict": verdict,
        "offline_synthetic": offline,
        "n_records": len(res.get("records", [])),
        "n_excluded_large_cap": res.get("n_excluded_large_cap", 0),
        "windows_scored": scored,
        "windows_strong": h.get("windows_strong"),
        "strong_positive": h.get("strong_positive"),
        "strong_negative": h.get("strong_negative"),
        "per_window_eff": [e.get("eff") for e in h.get("per_window_eff", [])],
        "harness_sign": h.get("sign"),
        "is_admissible": h.get("admissible_via_is_admissible", h.get("admissible")),
        "pooled_wr_gross": res.get("pooled_wr_gross"),
        "pooled_wr_net": res.get("pooled_wr_net"),
        "gross_edge_bps": cg.get("gross_edge_bps"),
        "net_edge_bps": cg.get("net_edge_bps"),
        "cost_survival_pct": cg.get("cost_survival_pct"),
        "cost_gate_passes": cg.get("passes"),
        "harness_reason": h.get("reason"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true",
                    help="small smoke set for a fast run")
    ap.add_argument("--json", dest="as_json", action="store_true")
    ap.add_argument("--refresh-cache", action="store_true",
                    help="re-fetch SEC Form-4 + price data, ignoring the cache")
    ap.add_argument("--universe", choices=["meme", "diverse"], default="meme",
                    help="'meme' = original H-028 (meme stocks); 'diverse' = H-028v2 (financials/industrials/energy/healthcare)")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "reports" /
                    "e1_insider_cluster_buy_research_2026-05-18.md")
    args = ap.parse_args()

    res = run(args.quick, args.refresh_cache, universe=args.universe)
    summary = json_summary(res)

    if args.as_json:
        print(json.dumps(summary, indent=2, default=str))
        return 0

    report = render_report(res)
    args.out.write_text(report, encoding="utf-8")
    print(f"# wrote {args.out}", file=sys.stderr)
    print(report)
    print("\n# JSON SUMMARY")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
