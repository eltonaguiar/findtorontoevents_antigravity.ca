"""
Fundamentals Data Loader

Fetches quarterly/annual fundamental data: income statement, balance sheet,
cash flow, key ratios. Uses yfinance as primary source.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class FundamentalsLoader:
    """Load fundamental data for quality, growth, and valuation factors."""

    def __init__(self):
        self._cache: Dict[str, Dict] = {}

    def load(self, tickers: List[str]) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Load fundamentals for all tickers.

        Returns dict of ticker -> {
            'income': DataFrame (quarterly income statement),
            'balance': DataFrame (quarterly balance sheet),
            'cashflow': DataFrame (quarterly cash flow),
            'info': dict (company info + key stats),
        }
        """
        import yfinance as yf

        result = {}
        for ticker in tickers:
            if ticker in self._cache:
                result[ticker] = self._cache[ticker]
                continue
            try:
                stock = yf.Ticker(ticker)
                data = {
                    "income": self._safe_get(stock, "quarterly_financials"),
                    "balance": self._safe_get(stock, "quarterly_balance_sheet"),
                    "cashflow": self._safe_get(stock, "quarterly_cashflow"),
                    "info": stock.info if hasattr(stock, "info") else {},
                }
                result[ticker] = data
                self._cache[ticker] = data
            except Exception as e:
                logger.warning(f"Failed to load fundamentals for {ticker}: {e}")
                result[ticker] = {"income": pd.DataFrame(), "balance": pd.DataFrame(),
                                  "cashflow": pd.DataFrame(), "info": {}}
        return result

    def _safe_get(self, stock, attr: str) -> pd.DataFrame:
        """Safely get a DataFrame attribute from yfinance Ticker."""
        try:
            df = getattr(stock, attr, pd.DataFrame())
            return df if df is not None else pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    def get_key_ratios(self, tickers: List[str]) -> pd.DataFrame:
        """
        Compute key fundamental ratios for the universe.

        Returns DataFrame with columns:
        - roe, roic, roa
        - gross_margin, operating_margin, net_margin
        - debt_to_equity, current_ratio
        - fcf_yield, earnings_yield
        - revenue_growth, earnings_growth
        - dividend_yield, payout_ratio
        - pe_ratio, pb_ratio, ps_ratio
        - market_cap
        """
        data = self.load(tickers)
        rows = []

        for ticker in tickers:
            d = data.get(ticker, {})
            info = d.get("info", {})
            income = d.get("income", pd.DataFrame())
            balance = d.get("balance", pd.DataFrame())
            cashflow = d.get("cashflow", pd.DataFrame())

            row = {"ticker": ticker}

            # From info dict (most recent)
            row["market_cap"] = info.get("marketCap", np.nan)
            row["pe_ratio"] = info.get("trailingPE", info.get("forwardPE", np.nan))
            row["pb_ratio"] = info.get("priceToBook", np.nan)
            row["ps_ratio"] = info.get("priceToSalesTrailing12Months", np.nan)
            row["dividend_yield"] = info.get("dividendYield", 0) or 0
            row["payout_ratio"] = info.get("payoutRatio", np.nan)
            row["roe"] = info.get("returnOnEquity", np.nan)
            row["roa"] = info.get("returnOnAssets", np.nan)
            row["debt_to_equity"] = info.get("debtToEquity", np.nan)
            row["current_ratio"] = info.get("currentRatio", np.nan)
            row["gross_margin"] = info.get("grossMargins", np.nan)
            row["operating_margin"] = info.get("operatingMargins", np.nan)
            row["net_margin"] = info.get("profitMargins", np.nan)
            row["revenue_growth"] = info.get("revenueGrowth", np.nan)
            row["earnings_growth"] = info.get("earningsGrowth", np.nan)
            row["beta"] = info.get("beta", np.nan)
            row["shares_outstanding"] = info.get("sharesOutstanding", np.nan)
            row["float_shares"] = info.get("floatShares", np.nan)
            row["sector"] = info.get("sector", "Unknown")
            row["industry"] = info.get("industry", "Unknown")

            # Compute ROIC from financials if available
            row["roic"] = self._compute_roic(income, balance)

            # FCF yield
            row["fcf_yield"] = self._compute_fcf_yield(cashflow, info)

            # Earnings yield (inverse of P/E)
            pe = row["pe_ratio"]
            row["earnings_yield"] = (1.0 / pe) if pe and pe > 0 else np.nan

            # Accruals quality
            row["accruals_ratio"] = self._compute_accruals(income, cashflow, balance)

            rows.append(row)

        return pd.DataFrame(rows).set_index("ticker")

    def _compute_roic(self, income: pd.DataFrame, balance: pd.DataFrame) -> float:
        """ROIC = NOPAT / Invested Capital."""
        try:
            if income.empty or balance.empty:
                return np.nan
            # Get most recent quarter
            ebit = self._get_row_value(income, ["EBIT", "Operating Income"])
            tax_rate = 0.21  # Approximate corporate tax rate
            nopat = ebit * (1 - tax_rate)

            total_debt = self._get_row_value(balance, ["Total Debt", "Long Term Debt"])
            equity = self._get_row_value(balance, ["Total Stockholder Equity", "Stockholders Equity"])
            cash = self._get_row_value(balance, ["Cash", "Cash And Cash Equivalents"])

            invested_capital = total_debt + equity - cash
            if invested_capital <= 0:
                return np.nan
            return nopat / invested_capital
        except Exception:
            return np.nan

    def _compute_fcf_yield(self, cashflow: pd.DataFrame, info: dict) -> float:
        """FCF Yield = Free Cash Flow / Market Cap."""
        try:
            if cashflow.empty:
                return np.nan
            fcf = self._get_row_value(cashflow, ["Free Cash Flow"])
            if np.isnan(fcf):
                operating_cf = self._get_row_value(cashflow, ["Total Cash From Operating Activities", "Operating Cash Flow"])
                capex = abs(self._get_row_value(cashflow, ["Capital Expenditures", "Capital Expenditure"]))
                fcf = operating_cf - capex
            mcap = info.get("marketCap", 0)
            if mcap <= 0:
                return np.nan
            return fcf / mcap
        except Exception:
            return np.nan

    def _compute_accruals(self, income: pd.DataFrame, cashflow: pd.DataFrame, balance: pd.DataFrame) -> float:
        """
        Accruals ratio = (Net Income - Operating Cash Flow) / Total Assets.
        High accruals = lower earnings quality.
        """
        try:
            if income.empty or cashflow.empty or balance.empty:
                return np.nan
            net_income = self._get_row_value(income, ["Net Income"])
            op_cf = self._get_row_value(cashflow, ["Total Cash From Operating Activities", "Operating Cash Flow"])
            total_assets = self._get_row_value(balance, ["Total Assets"])
            if total_assets <= 0:
                return np.nan
            return (net_income - op_cf) / total_assets
        except Exception:
            return np.nan

    def _get_row_value(self, df: pd.DataFrame, row_names: List[str]) -> float:
        """Get the most recent value for a row, trying multiple possible names."""
        if df.empty:
            return np.nan
        for name in row_names:
            if name in df.index:
                vals = df.loc[name].dropna()
                if len(vals) > 0:
                    return float(vals.iloc[0])
        return np.nan

    def get_sector_map(self, tickers: List[str]) -> Dict[str, str]:
        """Get sector classification for each ticker."""
        ratios = self.get_key_ratios(tickers)
        return ratios["sector"].to_dict()

    def get_industry_map(self, tickers: List[str]) -> Dict[str, str]:
        """Get industry classification for each ticker."""
        ratios = self.get_key_ratios(tickers)
        return ratios["industry"].to_dict()

    def get_buyback_yield(self, tickers: List[str]) -> pd.Series:
        """
        Compute share buyback yield: (shares_prev - shares_current) / shares_prev.
        Positive = company is buying back shares.
        """
        data = self.load(tickers)
        yields = {}
        for ticker in tickers:
            try:
                balance = data[ticker].get("balance", pd.DataFrame())
                if balance.empty:
                    yields[ticker] = 0.0
                    continue
                shares_row = None
                for name in ["Share Issued", "Common Stock Shares Outstanding", "Ordinary Shares Number"]:
                    if name in balance.index:
                        shares_row = balance.loc[name].dropna()
                        break
                if shares_row is not None and len(shares_row) >= 2:
                    current = float(shares_row.iloc[0])
                    previous = float(shares_row.iloc[1])
                    if previous > 0:
                        yields[ticker] = (previous - current) / previous
                    else:
                        yields[ticker] = 0.0
                else:
                    yields[ticker] = 0.0
            except Exception:
                yields[ticker] = 0.0
        return pd.Series(yields, name="buyback_yield")
