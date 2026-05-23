"""Universe-scale fundamentals fetcher with failover and on-disk cache.

Opt-in sidecar (per CLAUDE.md Wire-Up Rule). No production caller in this commit.
Wiring plan: Phase 6 `value_screener.py` will call `FundamentalsFetcher.fetch_batch`
on the screening universe each weekly run.

Design (per findings/SYNTHESIS.md §1-2):
  Primary:   SEC EDGAR `data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json`
  Fallback:  yfinance with cache (TSX gap-fill + EDGAR misses)
  Cache:     JSON at data/fundamentals/{ticker}/latest.json, TTL 168h (weekly)

All EDGAR requests use a polite User-Agent header (SEC fair-use rule).
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError

logger = logging.getLogger(__name__)

EDGAR_COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
EDGAR_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
DEFAULT_USER_AGENT = (
    "FindTorontoEvents Antigravity research/long-term-value-pipeline "
    "(zerounderscore@gmail.com)"
)
DEFAULT_CACHE_DIR = Path("data/fundamentals")
DEFAULT_TTL_HOURS = 168

GAAP_TAG_MAP: dict[str, list[str]] = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "operating_income": ["OperatingIncomeLoss", "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"],
    "ebit": ["OperatingIncomeLoss"],
    "ebitda_proxy_da": ["DepreciationAndAmortization", "DepreciationDepletionAndAmortization"],
    "interest_expense": ["InterestExpense"],
    "income_tax_expense": ["IncomeTaxExpenseBenefit"],
    "total_assets": ["Assets"],
    "total_liabilities": ["Liabilities"],
    "stockholders_equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "current_assets": ["AssetsCurrent"],
    "current_liabilities": ["LiabilitiesCurrent"],
    "long_term_debt": ["LongTermDebt", "LongTermDebtNoncurrent"],
    "cash_and_equivalents": ["CashAndCashEquivalentsAtCarryingValue"],
    "shares_outstanding": ["CommonStockSharesOutstanding", "EntityCommonStockSharesOutstanding"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "dividends_paid": ["PaymentsOfDividends", "PaymentsOfDividendsCommonStock"],
}


@dataclass
class FundamentalsRecord:
    """Standardized fundamentals snapshot for one ticker."""
    ticker: str
    cik: str | None = None
    period: str = ""
    fetched_at: str = ""
    source: str = ""
    cache_hit: bool = False
    income_statement: dict[str, float | None] = field(default_factory=dict)
    balance_sheet: dict[str, float | None] = field(default_factory=dict)
    cash_flow: dict[str, float | None] = field(default_factory=dict)
    ratios: dict[str, float | None] = field(default_factory=dict)

    def is_complete(self) -> bool:
        required = ["revenue", "net_income", "total_assets", "stockholders_equity"]
        return all(self.income_statement.get(k) is not None
                   or self.balance_sheet.get(k) is not None
                   for k in required)


class EdgarAdapter:
    """Pulls fundamentals from SEC EDGAR companyfacts JSON per ticker."""

    def __init__(self, user_agent: str = DEFAULT_USER_AGENT, request_delay_s: float = 0.12):
        self.user_agent = user_agent
        self.request_delay_s = request_delay_s
        self._ticker_cik_map: dict[str, int] | None = None
        self._http_get = _stdlib_http_get

    def _load_ticker_cik_map(self) -> dict[str, int]:
        if self._ticker_cik_map is not None:
            return self._ticker_cik_map
        try:
            raw = self._http_get(EDGAR_TICKERS_URL, self.user_agent)
            data = json.loads(raw)
            mapping: dict[str, int] = {}
            for entry in data.values():
                ticker = entry.get("ticker")
                cik = entry.get("cik_str")
                if ticker and cik is not None:
                    mapping[ticker.upper()] = int(cik)
            self._ticker_cik_map = mapping
            return mapping
        except (HTTPError, URLError, json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load EDGAR ticker→CIK map: %s", e)
            self._ticker_cik_map = {}
            return {}

    def fetch(self, ticker: str) -> FundamentalsRecord | None:
        ticker_u = ticker.upper().strip()
        cik_map = self._load_ticker_cik_map()
        cik = cik_map.get(ticker_u)
        if cik is None:
            logger.debug("EDGAR no CIK for %s", ticker_u)
            return None

        url = EDGAR_COMPANYFACTS_URL.format(cik=cik)
        try:
            time.sleep(self.request_delay_s)
            raw = self._http_get(url, self.user_agent)
            data = json.loads(raw)
        except (HTTPError, URLError, json.JSONDecodeError, OSError) as e:
            logger.warning("EDGAR fetch failed for %s (CIK %d): %s", ticker_u, cik, e)
            return None

        return self._parse_companyfacts(ticker_u, str(cik), data)

    def _parse_companyfacts(
        self, ticker: str, cik: str, data: dict[str, Any]
    ) -> FundamentalsRecord:
        record = FundamentalsRecord(
            ticker=ticker, cik=cik,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            source="edgar",
        )
        gaap = data.get("facts", {}).get("us-gaap", {})
        latest_period_end = ""
        for canonical, tag_candidates in GAAP_TAG_MAP.items():
            value, period_end = self._latest_value_for_tags(gaap, tag_candidates)
            target = self._statement_for(canonical, record)
            target[canonical] = value
            if period_end > latest_period_end:
                latest_period_end = period_end
        record.period = self._period_label(latest_period_end)
        return record

    @staticmethod
    def _latest_value_for_tags(gaap: dict[str, Any], tags: list[str]) -> tuple[float | None, str]:
        best_value: float | None = None
        best_end = ""
        best_is_fy = False
        for tag in tags:
            tag_data = gaap.get(tag)
            if not tag_data:
                continue
            units = tag_data.get("units", {})
            for unit_key in ("USD", "shares", "USD/shares"):
                items = units.get(unit_key)
                if not items:
                    continue
                for item in items:
                    val = item.get("val")
                    end = item.get("end", "")
                    fp = item.get("fp", "")
                    if val is None or not end:
                        continue
                    is_fy = (fp == "FY")
                    if is_fy and not best_is_fy:
                        best_value, best_end, best_is_fy = float(val), end, True
                    elif is_fy == best_is_fy and end > best_end:
                        best_value, best_end = float(val), end
                if best_value is not None:
                    break
            if best_value is not None:
                break
        return best_value, best_end

    @staticmethod
    def _prior_value_for_tags(gaap: dict[str, Any], tags: list[str]) -> tuple[float | None, str]:
        """Return the second-most-recent annual (FY) value for the first matching tag.

        Used for Piotroski tests 5-9 and Beneish M-score which require prior-year comparisons.
        Returns (None, "") when only one or zero FY entries exist.
        """
        for tag in tags:
            tag_data = gaap.get(tag)
            if not tag_data:
                continue
            units = tag_data.get("units", {})
            for unit_key in ("USD", "shares", "USD/shares"):
                items = units.get(unit_key)
                if not items:
                    continue
                fy_items = sorted(
                    [i for i in items
                     if i.get("fp") == "FY" and i.get("end") and i.get("val") is not None],
                    key=lambda x: x["end"],
                    reverse=True,
                )
                if len(fy_items) >= 2:
                    item = fy_items[1]
                    return float(item["val"]), item["end"]
                # Only one or zero FY entries — no prior available for this tag.
                break
            break
        return None, ""

    def fetch_prior(self, ticker: str) -> "FundamentalsRecord | None":
        """Fetch prior fiscal year fundamentals (for Piotroski / Beneish M).

        Re-uses the same companyfacts JSON endpoint; the EDGAR CDN response is
        the same document as for `fetch()`, parsed a second time to extract the
        second-most-recent FY values for each GAAP tag.
        """
        ticker_u = ticker.upper().strip()
        cik_map = self._load_ticker_cik_map()
        cik = cik_map.get(ticker_u)
        if cik is None:
            logger.debug("EDGAR no CIK for prior fetch: %s", ticker_u)
            return None
        url = EDGAR_COMPANYFACTS_URL.format(cik=cik)
        try:
            time.sleep(self.request_delay_s)
            raw = self._http_get(url, self.user_agent)
            data = json.loads(raw)
        except (HTTPError, URLError, json.JSONDecodeError, OSError) as e:
            logger.warning("EDGAR prior-year fetch failed for %s: %s", ticker_u, e)
            return None
        return self._parse_companyfacts_prior(ticker_u, str(cik), data)

    def _parse_companyfacts_prior(
        self, ticker: str, cik: str, data: dict[str, Any]
    ) -> "FundamentalsRecord":
        """Parse prior fiscal year values from an EDGAR companyfacts payload."""
        record = FundamentalsRecord(
            ticker=ticker, cik=cik,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            source="edgar_prior",
        )
        gaap = data.get("facts", {}).get("us-gaap", {})
        prior_period_end = ""
        for canonical, tag_candidates in GAAP_TAG_MAP.items():
            value, period_end = self._prior_value_for_tags(gaap, tag_candidates)
            target = self._statement_for(canonical, record)
            target[canonical] = value
            if period_end > prior_period_end:
                prior_period_end = period_end
        record.period = self._period_label(prior_period_end) + "_prior"
        return record

    @staticmethod
    def _statement_for(canonical: str, record: FundamentalsRecord) -> dict[str, float | None]:
        income_keys = {"revenue", "net_income", "operating_income", "ebit",
                       "ebitda_proxy_da", "interest_expense", "income_tax_expense"}
        balance_keys = {"total_assets", "total_liabilities", "stockholders_equity",
                        "current_assets", "current_liabilities", "long_term_debt",
                        "cash_and_equivalents", "shares_outstanding"}
        cashflow_keys = {"operating_cash_flow", "capex", "dividends_paid"}
        if canonical in income_keys:
            return record.income_statement
        if canonical in balance_keys:
            return record.balance_sheet
        if canonical in cashflow_keys:
            return record.cash_flow
        return record.income_statement

    @staticmethod
    def _period_label(end_date: str) -> str:
        if not end_date or len(end_date) < 7:
            return ""
        try:
            year = end_date[0:4]
            month = int(end_date[5:7])
            quarter = (month - 1) // 3 + 1
            return f"{year}-Q{quarter}"
        except (ValueError, IndexError):
            return ""


class YFinanceFallbackAdapter:
    """Fallback for non-US issuers and EDGAR misses."""

    def fetch(self, ticker: str) -> FundamentalsRecord | None:
        try:
            import yfinance as yf
        except ImportError:
            logger.warning("yfinance not installed — fallback unavailable")
            return None

        try:
            t = yf.Ticker(ticker)
            info = t.info or {}
        except Exception as e:
            logger.warning("yfinance fetch failed for %s: %s", ticker, e)
            return None

        record = FundamentalsRecord(
            ticker=ticker.upper(),
            fetched_at=datetime.now(timezone.utc).isoformat(),
            source="yfinance",
        )
        record.income_statement["revenue"] = info.get("totalRevenue")
        record.income_statement["net_income"] = info.get("netIncomeToCommon")
        record.balance_sheet["total_assets"] = info.get("totalAssets")
        record.balance_sheet["total_liabilities"] = info.get("totalLiab") or info.get("totalDebt")
        record.balance_sheet["stockholders_equity"] = info.get("bookValue")
        record.balance_sheet["cash_and_equivalents"] = info.get("totalCash")
        record.balance_sheet["shares_outstanding"] = info.get("sharesOutstanding")
        record.cash_flow["operating_cash_flow"] = info.get("operatingCashflow")
        record.period = datetime.now(timezone.utc).strftime("%Y-Q%q")
        return record


class ParquetCache:
    """On-disk JSON cache with TTL."""

    def __init__(self, cache_dir: Path | str = DEFAULT_CACHE_DIR, ttl_hours: int = DEFAULT_TTL_HOURS):
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_hours * 3600

    def _path_for(self, ticker: str, prior: bool = False) -> Path:
        filename = "prior.json" if prior else "latest.json"
        return self.cache_dir / ticker.upper() / filename

    def get(self, ticker: str) -> FundamentalsRecord | None:
        path = self._path_for(ticker)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Cache read failed for %s: %s", ticker, e)
            return None
        fetched_at = data.get("fetched_at", "")
        if fetched_at:
            try:
                fetched_dt = datetime.fromisoformat(fetched_at)
                age = (datetime.now(timezone.utc) - fetched_dt).total_seconds()
                if age > self.ttl_seconds:
                    return None
            except ValueError:
                pass
        record = FundamentalsRecord(**data)
        record.cache_hit = True
        return record

    def put(self, record: FundamentalsRecord) -> None:
        path = self._path_for(record.ticker)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(json.dumps(asdict(record), indent=2, default=str), encoding="utf-8")
        except OSError as e:
            logger.warning("Cache write failed for %s: %s", record.ticker, e)

    def get_prior(self, ticker: str) -> FundamentalsRecord | None:
        path = self._path_for(ticker, prior=True)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Prior cache read failed for %s: %s", ticker, e)
            return None
        fetched_at = data.get("fetched_at", "")
        if fetched_at:
            try:
                fetched_dt = datetime.fromisoformat(fetched_at)
                age = (datetime.now(timezone.utc) - fetched_dt).total_seconds()
                if age > self.ttl_seconds:
                    return None
            except ValueError:
                pass
        record = FundamentalsRecord(**data)
        record.cache_hit = True
        return record

    def put_prior(self, record: FundamentalsRecord) -> None:
        path = self._path_for(record.ticker, prior=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(json.dumps(asdict(record), indent=2, default=str), encoding="utf-8")
        except OSError as e:
            logger.warning("Prior cache write failed for %s: %s", record.ticker, e)


def compute_ratios(record: FundamentalsRecord, market_cap: float | None = None,
                   share_price: float | None = None) -> dict[str, float | None]:
    """Compute value/quality ratios needed by Phase 6 value_screener."""
    inc = record.income_statement
    bs = record.balance_sheet
    cf = record.cash_flow

    def safe_div(a, b):
        if a is None or b is None or b == 0:
            return None
        return a / b

    revenue = inc.get("revenue")
    net_income = inc.get("net_income")
    operating_income = inc.get("operating_income")
    ebit = inc.get("ebit") or operating_income
    da = inc.get("ebitda_proxy_da")
    interest_expense = inc.get("interest_expense")
    total_assets = bs.get("total_assets")
    total_liabilities = bs.get("total_liabilities")
    equity = bs.get("stockholders_equity")
    current_assets = bs.get("current_assets")
    current_liabilities = bs.get("current_liabilities")
    cash = bs.get("cash_and_equivalents")
    long_term_debt = bs.get("long_term_debt") or 0.0
    op_cf = cf.get("operating_cash_flow")
    capex = cf.get("capex") or 0.0

    free_cash_flow = (op_cf - abs(capex)) if op_cf is not None else None
    ebitda = (ebit + da) if (ebit is not None and da is not None) else None
    debt = (long_term_debt or 0.0) + (current_liabilities or 0.0) - (cash or 0.0)
    enterprise_value = market_cap + debt if market_cap is not None else None

    return {
        "pe": safe_div(market_cap, net_income) if market_cap is not None else None,
        "pb": safe_div(market_cap, equity) if market_cap is not None else None,
        "ev_ebitda": safe_div(enterprise_value, ebitda),
        "fcf_yield": safe_div(free_cash_flow, enterprise_value),
        "earnings_yield": safe_div(ebit, enterprise_value),
        "acquirers_multiple": safe_div(enterprise_value, operating_income),
        "roic": safe_div(ebit, (total_assets - (current_liabilities or 0.0))) if total_assets is not None else None,
        "roe": safe_div(net_income, equity),
        "roa": safe_div(net_income, total_assets),
        "debt_to_equity": safe_div(total_liabilities, equity),
        "interest_coverage": safe_div(ebit, interest_expense),
        "current_ratio": safe_div(current_assets, current_liabilities),
        "altman_z_double_prime": _altman_z_double_prime(
            current_assets, current_liabilities, total_assets, ebit, equity, total_liabilities
        ),
    }


def _altman_z_double_prime(current_assets, current_liabilities, total_assets, ebit, equity, total_liabilities):
    if total_assets is None or total_assets == 0 or total_liabilities is None or total_liabilities == 0:
        return None
    if any(v is None for v in (current_assets, current_liabilities, ebit, equity)):
        return None
    wc = current_assets - current_liabilities
    re_proxy = equity
    return (
        6.56 * (wc / total_assets)
        + 3.26 * (re_proxy / total_assets)
        + 6.72 * (ebit / total_assets)
        + 1.05 * (equity / total_liabilities)
    )


class FundamentalsFetcher:
    """Public facade. Tries primary source then fallbacks with caching."""

    def __init__(self, cache_dir: Path | str = DEFAULT_CACHE_DIR,
                 user_agent: str = DEFAULT_USER_AGENT, ttl_hours: int = DEFAULT_TTL_HOURS):
        self.cache = ParquetCache(cache_dir, ttl_hours)
        self.edgar = EdgarAdapter(user_agent)
        self.yfinance = YFinanceFallbackAdapter()

    def fetch(self, ticker: str, *, force_refresh: bool = False) -> FundamentalsRecord:
        ticker_u = ticker.upper().strip()
        if not force_refresh:
            cached = self.cache.get(ticker_u)
            if cached is not None:
                return cached
        record = self.edgar.fetch(ticker_u)
        if record is None or not record.is_complete():
            yf_record = self.yfinance.fetch(ticker_u)
            if yf_record is not None and yf_record.is_complete():
                record = yf_record
        if record is None:
            record = FundamentalsRecord(
                ticker=ticker_u,
                fetched_at=datetime.now(timezone.utc).isoformat(),
                source="missing",
            )
            return record
        self.cache.put(record)
        return record

    def fetch_batch(self, tickers: list[str], *, force_refresh: bool = False) -> dict[str, FundamentalsRecord]:
        return {t: self.fetch(t, force_refresh=force_refresh) for t in tickers}

    def fetch_prior(self, ticker: str, *, force_refresh: bool = False) -> FundamentalsRecord | None:
        """Fetch prior fiscal year record for Piotroski tests 5-9 and Beneish M.

        Returns None when EDGAR has only one FY entry for the ticker (e.g., recently listed).
        yfinance does not provide prior-year structured data, so only EDGAR is tried.
        """
        ticker_u = ticker.upper().strip()
        if not force_refresh:
            cached = self.cache.get_prior(ticker_u)
            if cached is not None:
                return cached
        record = self.edgar.fetch_prior(ticker_u)
        if record is not None:
            # Only cache when the record has at least one field — otherwise an empty
            # prior record would mask a future successful fetch.
            has_data = any(
                bool(d) for d in (record.income_statement, record.balance_sheet, record.cash_flow)
            )
            if has_data:
                self.cache.put_prior(record)
        return record

    def fetch_batch_prior(
        self, tickers: list[str], *, force_refresh: bool = False
    ) -> dict[str, FundamentalsRecord]:
        """Return prior-year records for each ticker; missing tickers are omitted."""
        result: dict[str, FundamentalsRecord] = {}
        for t in tickers:
            rec = self.fetch_prior(t, force_refresh=force_refresh)
            if rec is not None:
                result[t.upper().strip()] = rec
        return result


def _stdlib_http_get(url: str, user_agent: str) -> str:
    from urllib.request import Request, urlopen
    req = Request(url, headers={"User-Agent": user_agent, "Accept": "application/json"})
    with urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")
