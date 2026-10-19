"""Fetch historical daily closes/returns for the combined-book ETF universe."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

UNIVERSE = {
    "SPY": "trend_stock", "EFA": "trend_stock", "EEM": "trend_stock",
    "IWM": "trend_stock",
    "TLT": "trend_bond", "IEF": "trend_bond", "SHY": "trend_bond",
    "LQD": "trend_bond", "HYG": "trend_bond", "TIP": "trend_bond",
    "GLD": "trend_comm", "DBC": "trend_comm", "USO": "trend_comm",
    "SLV": "trend_comm",
    "VNQ": "trend_re",
    "QUAL": "quality", "VLUE": "quality", "MTUM": "quality", "USMV": "quality",
    "XYLD": "put_proxy", "PUT": "put_index",
}


def _default_cache_dir() -> Path:
    return Path(os.environ.get("COMBINED_BOOK_CACHE", "combined_book/data"))


def _write_cache(closes: dict, cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    for sym, series in closes.items():
        series.to_frame(name="close").to_csv(cache_dir / f"{sym}.csv")


def _read_cache(sym: str, cache_dir: Path) -> pd.Series | None:
    path = cache_dir / f"{sym}.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    return df["close"].dropna()


def _download(symbol: str) -> pd.Series:
    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover - env dependent
        raise RuntimeError("yfinance is required to download missing data") from exc
    df = yf.download(symbol, auto_adjust=True, progress=False, period="max")
    close = df["Close"].squeeze()
    close.index = pd.to_datetime(close.index)
    return close.dropna()


def get_daily_closes(
    symbols: list[str], cache_dir: Path | None = None
) -> dict[str, pd.Series]:
    cache_dir = cache_dir or _default_cache_dir()
    out: dict[str, pd.Series] = {}
    missing: list[str] = []
    for sym in symbols:
        cached = _read_cache(sym, cache_dir)
        if cached is not None and not cached.empty:
            out[sym] = cached
        else:
            missing.append(sym)
    if missing:
        fetched = {sym: _download(sym) for sym in missing}
        _write_cache(fetched, cache_dir)
        out.update(fetched)
    return out


def monthly_returns(series: pd.Series) -> pd.Series:
    monthly = series.resample("ME").last().dropna()
    if len(monthly) < 2:
        return pd.Series(dtype=float)
    # First month's return is measured against the first available close so
    # the series includes the opening month rather than dropping it.
    first_close = float(series.dropna().iloc[0])
    rets = monthly.pct_change(fill_method=None)
    if first_close > 0:
        rets.iloc[0] = monthly.iloc[0] / first_close - 1.0
    return rets.dropna()


# --- Research dataset (extended history, separate from raw-ETF pilot data) ---
# Splicing map: extend each ETF backward with an older mutual-fund proxy whose
# returns are used only before the ETF's own history begins (mirrors the
# reference grokbot run's SPL map).
SPLICE_MAP = {
    "SPY": "VFINX",
    "TLT": "VUSTX",
    "IEF": "VBMFX",
    "LQD": "VBMFX",
    "SHY": "FGOVX",
    "HYG": "VWEHX",
    "GLD": "FSAGX",
    "VNQ": "VGSIX",
    "DBC": "PCRIX",
}

# Mutual-fund proxies needed for splicing.
RESEARCH_PROXIES = tuple(dict.fromkeys(SPLICE_MAP.values()))

RESEARCH_TREND_UNIVERSE = (
    "SPY", "EFA", "EEM", "IWM", "TLT", "IEF", "SHY", "LQD", "HYG",
    "TIP", "GLD", "DBC", "USO", "SLV", "VNQ",
)

KF_DATA_DIR = Path(__file__).resolve().parent / "data" / "kfrench"
KF_OP_FILE = KF_DATA_DIR / "Portfolios_Formed_on_OP.txt"
KF_BEME_FILE = KF_DATA_DIR / "Portfolios_Formed_on_BE-ME.txt"


def _column_ranges(header_line: str) -> list[tuple[int, int]]:
    """Return (start, end) char ranges of each fixed-width column label.

    Columns are separated by runs of 2+ spaces; a label may itself contain a
    single interior space (e.g. 'Hi 30') so we only split on runs of 2+ spaces.
    """
    ranges: list[tuple[int, int]] = []
    i = 0
    n = len(header_line)
    while i < n:
        if header_line[i] == " ":
            i += 1
            continue
        start = i
        while i < n and not (
            header_line[i] == " " and i + 1 < n and header_line[i + 1] == " "
        ):
            i += 1
        ranges.append((start, i))
    return ranges


def _parse_kfrench_monthly(path: Path, column: str) -> pd.Series:
    """Parse Ken French 'Value Weight Returns -- Monthly' section.

    Returns monthly percent returns converted to fractions indexed by month-end.
    Header column labels are extracted positionally (multi-word labels like
    'Hi 30', and file-specific extra columns like '<= 0'); data rows are
    whitespace-split so value ``i`` after the date maps to label ``i``.
    """
    text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    marker = next(
        i for i, line in enumerate(text) if "Value Weight Returns -- Monthly" in line
    )
    header_line = text[marker + 1]
    labels = [header_line[s:e].strip() for s, e in _column_ranges(header_line)]
    col_idx = labels.index(column)
    data: dict[str, float] = {}
    for line in text[marker + 2:]:
        toks = line.split()
        if not toks:
            continue
        date_token = toks[0]
        # monthly rows are YYYYMM; the trailing annual summary rows are 4-digit
        if not (len(date_token) == 6 and date_token.isdigit()):
            break
        if len(toks) < col_idx + 2:
            break
        data[date_token] = float(toks[col_idx + 1])
    index = pd.to_datetime(list(data.keys()), format="%Y%m") + pd.offsets.MonthEnd(0)
    series = pd.Series(list(data.values()), index=index) / 100.0
    series = series[~series.index.duplicated(keep="last")].sort_index()
    return series


def load_kfrench_quality_value_monthly() -> pd.Series:
    """Quality/value series = 0.5*FF(OP Hi 30) + 0.5*FF(BE-ME Hi 30) - 10bp/mo.

    Matches the reference run: the French series is sliced to start 1986-01
    (the reference used ``qv['1986-01':]``), so the pre-1986 history does not
    distort the backtest.
    """
    op = _parse_kfrench_monthly(KF_OP_FILE, "Hi 30")
    beme = _parse_kfrench_monthly(KF_BEME_FILE, "Hi 30")
    qv = 0.5 * op.add(beme, fill_value=0.0) - 0.002 / 12.0
    qv = qv["1986-01":]
    return qv.sort_index().dropna()


def get_research_daily_closes(
    cache_dir: Path | None = None,
) -> dict[str, pd.Series]:
    """Download + cache spliced daily closes for the research trend universe.

    Each ETF is extended backward with its mutual-fund proxy's closes. The raw
    (un-spliced) ETF data remains available for the live paper pilot.
    """
    cache_dir = cache_dir or _default_cache_dir()
    symbols = list(RESEARCH_TREND_UNIVERSE) + list(RESEARCH_PROXIES)
    closes = get_daily_closes(symbols, cache_dir=cache_dir)
    spliced: dict[str, pd.Series] = {}
    for sym in RESEARCH_TREND_UNIVERSE:
        series = closes.get(sym)
        if series is None:
            continue
        proxy = SPLICE_MAP.get(sym)
        if proxy and proxy in closes:
            proxy_series = closes[proxy]
            # Only where the ETF itself is missing (proxy fills earlier gaps).
            series = series.combine_first(
                proxy_series.where(series.isna())
            )
        spliced[sym] = series.sort_index().dropna()
    return spliced


def get_put_index_daily_closes(cache_dir: Path | None = None) -> pd.Series:
    """Fetch the CBOE PUT index (^PUT) daily closes (research put-write series)."""
    cache_dir = cache_dir or _default_cache_dir()
    cached = _read_cache("PUT", cache_dir)
    if cached is not None and not cached.empty:
        return cached
    fetched = _download("^PUT")
    _write_cache({"PUT": fetched}, cache_dir)
    return fetched
