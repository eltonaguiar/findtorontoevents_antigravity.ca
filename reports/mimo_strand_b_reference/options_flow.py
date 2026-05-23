"""
MiMo (Xiaomi) reference delivery — options-flow signals. 2026-05-18.
REFERENCE ONLY — unvalidated by MiMo (could not run the harness, no repo access).
Vet before reuse. Known gaps: Deribit free API is current-snapshot only (no
history → cannot backtest without a paid vendor); no post-cost gate; harness
wiring is a TODO. Good parts: real Deribit API, clean BS greeks, pure signal math.

Options-implied signal generators for the findtorontoevents quant system.

Four genuinely-new input signals derived from options market microstructure:
  1. put_call_ratio      — volume-weighted P/C ratio
  2. iv_skew_25d         — 25-delta put IV minus call IV
  3. dealer_gamma_proxy  — aggregate dealer gamma exposure (short-gamma assumption)
  4. unusual_volume      — current options volume vs 20-day trailing mean

Data source: Deribit public API v2 (BTC + ETH options, no auth required).
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import requests

logger = logging.getLogger(__name__)

DERIBIT_BASE = "https://www.deribit.com/api/v2/public"
RATE_LIMIT_SLEEP = 0.12
MIN_EXPIRY_DAYS = 1
MAX_EXPIRY_DAYS = 365
TRAILING_WINDOW = 20
RISK_FREE_RATE = 0.05

SIGNAL_NAMES = [
    "put_call_ratio",
    "iv_skew_25d",
    "dealer_gamma_proxy",
    "unusual_volume",
]


@dataclass(frozen=True)
class OptionRecord:
    """Parsed option from Deribit book summary."""
    underlying: str
    expiry: datetime
    strike: float
    is_put: bool
    mark_iv: float            # decimal, e.g. 0.60
    volume_usd: float
    open_interest_usd: float
    mark_price: float


def _deribit_get(endpoint: str, params: dict | None = None,
                 max_retries: int = 3) -> dict:
    url = f"{DERIBIT_BASE}/{endpoint}"
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params or {}, timeout=15)
            resp.raise_for_status()
            body = resp.json()
            return body.get("result", body)
        except requests.RequestException as exc:
            logger.warning("Deribit %s attempt %d failed: %s",
                           endpoint, attempt + 1, exc)
            if attempt < max_retries - 1:
                time.sleep(RATE_LIMIT_SLEEP * (attempt + 1))
    return {}


def fetch_spot_price(currency: str = "BTC") -> float:
    raw = _deribit_get("get_index_price",
                       {"index_name": f"{currency.lower()}_usd"})
    if raw and "index_price" in raw:
        return float(raw["index_price"])
    raise ValueError(f"Cannot fetch {currency} spot from Deribit")


def fetch_option_chain(currency: str = "BTC") -> list[OptionRecord]:
    raw = _deribit_get("get_book_summary_by_currency",
                       {"currency": currency, "kind": "option"})
    if not raw:
        return []
    now = datetime.now(timezone.utc)
    records: list[OptionRecord] = []
    for item in raw:
        try:
            name = item.get("instrument_name", "")
            parts = name.split("-")
            if len(parts) != 4:
                continue
            expiry = datetime.strptime(parts[1], "%d%b%y").replace(
                tzinfo=timezone.utc)
            dte = (expiry - now).days
            if dte < MIN_EXPIRY_DAYS or dte > MAX_EXPIRY_DAYS:
                continue
            iv_raw = item.get("mark_iv")
            if iv_raw is None or iv_raw <= 0:
                continue
            records.append(OptionRecord(
                underlying=parts[0],
                expiry=expiry,
                strike=float(parts[2]),
                is_put=(parts[3] == "P"),
                mark_iv=iv_raw / 100.0,
                volume_usd=float(item.get("volume_usd", 0)),
                open_interest_usd=float(item.get("open_interest_usd", 0)),
                mark_price=float(item.get("mark_price", 0)),
            ))
        except (ValueError, TypeError, KeyError):
            continue
    return records


def _norm_cdf(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def bs_delta(S: float, K: float, T: float, sigma: float, r: float,
             is_put: bool) -> float:
    """European option delta.  Call in (0,1), put in (-1,0)."""
    if T <= 0 or sigma <= 0:
        return 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (
        sigma * math.sqrt(T))
    return _norm_cdf(d1) - 1.0 if is_put else _norm_cdf(d1)


def bs_gamma(S: float, K: float, T: float, sigma: float, r: float) -> float:
    """European option gamma (identical for calls and puts)."""
    if T <= 0 or sigma <= 0:
        return 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (
        sigma * math.sqrt(T))
    return _norm_pdf(d1) / (S * sigma * math.sqrt(T))


def compute_put_call_ratio(records: list[OptionRecord],
                           use_oi: bool = False) -> float:
    """P/C ratio.  >1 -> puts dominate (bearish lean).  NaN if no data."""
    key = "open_interest_usd" if use_oi else "volume_usd"
    put_tot = sum(getattr(r, key) for r in records if r.is_put)
    call_tot = sum(getattr(r, key) for r in records if not r.is_put)
    return float("nan") if call_tot <= 0 else put_tot / call_tot


def compute_iv_skew_25d(records: list[OptionRecord], spot: float,
                        r: float = RISK_FREE_RATE) -> float:
    """25-delta IV skew: IV(25d put) - IV(25d call).
    Positive -> put protection expensive -> bearish positioning."""
    now = datetime.now(timezone.utc)
    best_put: tuple[float, float] | None = None
    best_call: tuple[float, float] | None = None
    for rec in records:
        T = max((rec.expiry - now).total_seconds() / (365.25 * 86400), 1e-6)
        delta = bs_delta(spot, rec.strike, T, rec.mark_iv, r, rec.is_put)
        diff = abs(abs(delta) - 0.25)
        if diff > 0.15:
            continue
        if rec.is_put:
            if best_put is None or diff < best_put[0]:
                best_put = (diff, rec.mark_iv)
        else:
            if best_call is None or diff < best_call[0]:
                best_call = (diff, rec.mark_iv)
    if best_put is None or best_call is None:
        return float("nan")
    return best_put[1] - best_call[1]


def compute_dealer_gamma_proxy(records: list[OptionRecord], spot: float,
                                r: float = RISK_FREE_RATE) -> float:
    """Aggregate dealer gamma (dealers assumed net-short).
    More negative -> short-gamma trending regime.  Normalised by total OI."""
    now = datetime.now(timezone.utc)
    total_gamma = 0.0
    total_oi = 0.0
    for rec in records:
        T = max((rec.expiry - now).total_seconds() / (365.25 * 86400), 1e-6)
        g = bs_gamma(spot, rec.strike, T, rec.mark_iv, r)
        total_gamma += -g * rec.open_interest_usd
        total_oi += rec.open_interest_usd
    return float("nan") if total_oi <= 0 else total_gamma / total_oi


def compute_unusual_volume(records: list[OptionRecord],
                           historical_volumes: pd.Series | None = None,
                           trailing_window: int = TRAILING_WINDOW) -> float:
    """Today's total options volume / trailing-window mean.  >1 -> elevated."""
    current = sum(r.volume_usd for r in records)
    if historical_volumes is None or len(historical_volumes) < trailing_window:
        return float("nan")
    avg = historical_volumes.iloc[-trailing_window:].mean()
    return float("nan") if avg <= 0 else current / avg


def zscore_series(series: pd.Series,
                  window: int = TRAILING_WINDOW) -> pd.Series:
    """Rolling z-score.  NaN for the initial burn-in window."""
    mu = series.rolling(window, min_periods=window).mean()
    sigma = series.rolling(window, min_periods=window).std().replace(0, np.nan)
    return (series - mu) / sigma


def load_historical_and_generate_signals(
    chain_history: dict[datetime, list[OptionRecord]],
    spot_history: pd.Series,
    signals: list[str] | None = None,
) -> pd.DataFrame:
    """Build signal DataFrame from historical option-chain snapshots."""
    if signals is None:
        signals = list(SIGNAL_NAMES)
    dates = sorted(chain_history)
    vol_hist = pd.Series(
        {d: sum(r.volume_usd for r in chain_history[d]) for d in dates},
        index=pd.DatetimeIndex(dates),
    )
    rows: list[dict] = []
    for date in dates:
        recs = chain_history[date]
        spot = spot_history.asof(date) if date not in spot_history.index \
            else spot_history.loc[date]
        if pd.isna(spot) or not recs:
            continue
        row: dict = {"date": date}
        if "put_call_ratio" in signals:
            row["put_call_ratio"] = compute_put_call_ratio(recs)
        if "iv_skew_25d" in signals:
            row["iv_skew_25d"] = compute_iv_skew_25d(recs, float(spot))
        if "dealer_gamma_proxy" in signals:
            row["dealer_gamma_proxy"] = compute_dealer_gamma_proxy(
                recs, float(spot))
        if "unusual_volume" in signals:
            hist = vol_hist.loc[:date].iloc[:-1]
            row["unusual_volume"] = compute_unusual_volume(recs, hist)
        rows.append(row)
    return pd.DataFrame(rows).set_index("date")
