#!/usr/bin/env python3
"""
VT baby strategy adapters (baby_strategies/vt_*.py) for scanner.run_strategies.

Each function matches the standard signature: (data, context=None) -> list[dict].
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

_repo = Path(__file__).resolve().parent.parent
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

try:
    from antigravity_strategies import _signal_to_dict
except ImportError:  # package import path
    from alpha_engine.antigravity_strategies import _signal_to_dict


def _lower_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize yfinance columns to lowercase open/high/low/close/volume."""
    if df is None or df.empty:
        return df
    rename = {
        c: str(c).lower()
        for c in df.columns
        if str(c).lower() in ("open", "high", "low", "close", "volume", "adj close")
    }
    out = df.rename(columns=rename) if rename else df
    return out


def _yf_forex_pair_key(plain6: str) -> str:
    """EURUSD -> EURUSD=X for yfinance keys in scanner data."""
    p = (plain6 or "").upper().replace("/", "")
    if len(p) == 6 and p.isalpha():
        return f"{p}=X"
    return p


def _last_close(data: dict, symbol_keys: list[str]) -> Optional[float]:
    for k in symbol_keys:
        if k not in data:
            continue
        df = data[k]
        if not isinstance(df, pd.DataFrame) or df.empty:
            continue
        if "Close" in df.columns:
            v = float(df["Close"].iloc[-1])
            if v > 0:
                return v
        if "close" in df.columns:
            v = float(df["close"].iloc[-1])
            if v > 0:
                return v
    return None


def vt_adx_rsi2_etf(data: dict, context: dict | None = None) -> list[dict]:
    try:
        from baby_strategies.vt_adx_rsi2_etf import SYMBOLS, VTADXRsi2ETFStrategy
    except ImportError:
        return []

    strat = VTADXRsi2ETFStrategy()
    out: list[dict] = []
    for sym in SYMBOLS:
        raw = data.get(sym)
        if raw is None or len(raw) < 80:
            continue
        df = _lower_ohlcv(raw)
        try:
            for sig in strat.generate_signals(df, symbol=sym):
                d = _signal_to_dict(sig, "vt_adx_rsi2_etf", "equity")
                if d:
                    out.append(d)
        except Exception:
            continue
    return out


def vt_adx_rsi2_equity(data: dict, context: dict | None = None) -> list[dict]:
    try:
        from baby_strategies.vt_adx_rsi2_equity import SYMBOLS, VTADXRsi2EquityStrategy
    except ImportError:
        return []

    strat = VTADXRsi2EquityStrategy()
    out: list[dict] = []
    for sym in SYMBOLS:
        raw = data.get(sym)
        if raw is None or len(raw) < 80:
            continue
        df = _lower_ohlcv(raw)
        try:
            for sig in strat.generate_signals(df, symbol=sym):
                d = _signal_to_dict(sig, "vt_adx_rsi2_equity", "equity")
                if d:
                    out.append(d)
        except Exception:
            continue
    return out


def vt_thematic_etf_momentum(data: dict, context: dict | None = None) -> list[dict]:
    try:
        from baby_strategies.vt_thematic_etf_momentum import UNIVERSE, VTThematicETFMomentumStrategy
    except ImportError:
        return []

    md: Dict[str, pd.DataFrame] = {}
    for sym in UNIVERSE:
        if sym not in data:
            continue
        md[sym] = _lower_ohlcv(data[sym])
    if len(md) < 3:
        return []

    strat = VTThematicETFMomentumStrategy()
    try:
        sigs = strat.generate_signals(md)
    except Exception:
        return []

    out: list[dict] = []
    for sig in sigs:
        d = _signal_to_dict(sig, "vt_thematic_etf_momentum", "etf")
        if d:
            d["source"] = "vt_baby"
            try:
                from .antigravity_strategies import _infer_asset_class
                d["asset_class"] = _infer_asset_class(sig.symbol or "XBI")
            except Exception:
                d["asset_class"] = "ETF"
            out.append(d)
    return out


def vt_restatement_short(data: dict, context: dict | None = None) -> list[dict]:
    try:
        from baby_strategies.vt_restatement_short import VTRestatementShortStrategy
    except ImportError:
        return []

    strat = VTRestatementShortStrategy()
    out: list[dict] = []
    for sym, raw in data.items():
        if not isinstance(raw, pd.DataFrame) or len(raw) < 30:
            continue
        s = str(sym).upper()
        if "=X" in s or "=F" in s or "-USD" in s or "USDT" in s:
            continue
        df = _lower_ohlcv(raw)
        try:
            for sig in strat.generate_signals(df, symbol=sym):
                d = _signal_to_dict(sig, "vt_restatement_short", "equity")
                if d:
                    d["source"] = "vt_baby"
                    out.append(d)
        except Exception:
            continue
    return out


def vt_stat_arb_gdx_slv(data: dict, context: dict | None = None) -> list[dict]:
    try:
        from baby_strategies.vt_stat_arb_gdx_slv import VTStatArbGDXSLVStrategy
    except ImportError:
        return []

    gdx = data.get("GDX")
    slv = data.get("SLV")
    if gdx is None or slv is None:
        return []
    if len(gdx) < 320 or len(slv) < 320:
        return []

    strat = VTStatArbGDXSLVStrategy()
    try:
        sigs = strat.generate_signals(_lower_ohlcv(gdx), _lower_ohlcv(slv))
    except Exception:
        return []

    out: list[dict] = []
    for sig in sigs:
        d = _signal_to_dict(sig, "vt_stat_arb_gdx_slv", "etf")
        if d:
            d["source"] = "vt_baby"
            out.append(d)
    return out


def vt_myfxbook_sentiment_forex(data: dict, context: dict | None = None) -> list[dict]:
    try:
        from baby_strategies.vt_myfxbook_sentiment_forex import VTMyfxbookSentimentForexStrategy
    except ImportError:
        return []

    strat = VTMyfxbookSentimentForexStrategy()
    try:
        sigs = strat.generate_signals(data)
    except Exception:
        return []

    out: list[dict] = []
    for sig in sigs:
        plain = getattr(sig, "symbol", "") or ""
        yk = _yf_forex_pair_key(plain)
        fb = _last_close(data, [yk, plain])
        d = _signal_to_dict(
            sig,
            "vt_myfxbook_sentiment_forex",
            "forex",
            fallback_price=fb,
        )
        if d:
            d["symbol"] = yk
            d["source"] = "vt_baby"
            meta = getattr(sig, "metadata", None)
            if meta and isinstance(meta, dict):
                d.setdefault("extra", {}).update(meta)
            out.append(d)
    return out


def vt_edgar_insider_cluster(data: dict, context: dict | None = None) -> list[dict]:
    """EDGAR Form-4 insider cluster buying (v3: director-only cohort).

    Event-driven — depends on a cluster cache JSON produced by the research
    harness, NOT on OHLCV data alone.  The strategy loads events from disk
    at init time, then matches against the current bar date.
    """
    try:
        from baby_strategies.vt_edgar_insider_cluster import VTEdgarInsiderClusterStrategy
    except ImportError:
        return []

    # Director-only mode (v3 default) — only clusters with >=1 director fire.
    strat = VTEdgarInsiderClusterStrategy(params={"director_only": True})
    out: list[dict] = []
    for sym, raw in data.items():
        if not isinstance(raw, pd.DataFrame) or len(raw) < 20:
            continue
        s = str(sym).upper()
        # Skip forex/futures/crypto keys
        if "=X" in s or "=F" in s or "-USD" in s or "USDT" in s:
            continue
        df = _lower_ohlcv(raw)
        try:
            for sig in strat.generate_signals(df, symbol=sym):
                d = _signal_to_dict(sig, "vt_edgar_insider_cluster", "equity")
                if d:
                    d["source"] = "vt_baby"
                    out.append(d)
        except Exception:
            continue
    return out


def vt_csv_edge_luxalgo_alts(data: dict, context: dict | None = None) -> list[dict]:
    """LuxAlgo probabilistic breakout filter on WIF/JUP/AVAX/SOL alt perps.

    Wraps baby_strategies/vt_csv_edge_luxalgo_alts.py which uses the
    LuxAlgo filter pipeline (BreakoutForecaster + StreakAnalyzer +
    VolatilityWaterfall) to filter low-quality breakout signals.
    +27pp WR improvement vs unfiltered on this universe.

    Symbol mapping: scanner data dict uses yfinance keys ("WIF-USD" etc)
    but the strategy outputs Binance-style keys ("WIFUSDT" etc).
    We look up both formats and emit signals with Binance keys (matching
    the production_scanner convention for crypto).
    """
    try:
        from baby_strategies.vt_csv_edge_luxalgo_alts import SYMBOLS, VTCsvEdgeLuxalgoAltsStrategy
    except ImportError:
        return []

    # Binance-style -> yfinance-style lookup map
    _binance_to_yf = {}
    for bsym in SYMBOLS:
        base = bsym.replace("USDT", "")
        _binance_to_yf[bsym] = f"{base}-USD"  # WIFUSDT -> WIF-USD

    strat = VTCsvEdgeLuxalgoAltsStrategy()
    out: list[dict] = []
    for bsym, yfkey in _binance_to_yf.items():
        raw = data.get(yfkey)
        if raw is None:
            raw = data.get(bsym)
        if raw is None or not isinstance(raw, pd.DataFrame) or len(raw) < 120:
            continue
        df = _lower_ohlcv(raw)
        try:
            for sig in strat.generate_signals(df, symbol=bsym):
                d = _signal_to_dict(sig, "vt_csv_edge_luxalgo_alts", "crypto")
                if d:
                    d["symbol"] = bsym  # Use Binance key (production convention)
                    d["source"] = "vt_baby"
                    d["extra"]["edge"] = "+27pp WR vs unfiltered"
                    d["extra"]["universe"] = ",".join(SYMBOLS)
                    out.append(d)
        except Exception:
            continue
    return out


def vt_sc13d_activist(data: dict, context: dict | None = None) -> list[dict]:
    """SEC Schedule 13D activist stake disclosures (v2: marquee whitelist).

    Event-driven — depends on a classified.json cache produced by the
    research harness.  Only fires for marquee activist filers (Elliott,
    Starboard, Icahn, etc.) when use_marquee_whitelist=True (default).
    """
    try:
        from baby_strategies.vt_sc13d_activist import VTSc13dActivistStrategy
    except ImportError:
        return []

    # Marquee-whitelist mode (v2 default) — only known activists fire.
    strat = VTSc13dActivistStrategy(params={"use_marquee_whitelist": True})
    out: list[dict] = []
    for sym, raw in data.items():
        if not isinstance(raw, pd.DataFrame) or len(raw) < 20:
            continue
        s = str(sym).upper()
        # Skip forex/futures/crypto keys
        if "=X" in s or "=F" in s or "-USD" in s or "USDT" in s:
            continue
        df = _lower_ohlcv(raw)
        try:
            for sig in strat.generate_signals(df, symbol=sym):
                d = _signal_to_dict(sig, "vt_sc13d_activist", "equity")
                if d:
                    d["source"] = "vt_baby"
                    out.append(d)
        except Exception:
            continue
    return out


def _load_recent_earnings_surprise(symbol: str, earnings_dir: Path, max_age_days: int = 7) -> Optional[float]:
    """Read latest real earnings surprise from cache if recent enough."""
    p = earnings_dir / symbol / "latest.json"
    if not p.exists():
        return None
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    history = payload.get("history")
    if not isinstance(history, list):
        return None
    today = datetime.now(timezone.utc).date()
    for row in history:
        if not isinstance(row, dict):
            continue
        surprise = row.get("surprise_pct")
        date_s = row.get("date")
        if surprise is None or not date_s:
            continue
        try:
            earn_date = datetime.fromisoformat(str(date_s)).date()
            val = float(surprise)
        except Exception:
            continue
        age = (today - earn_date).days
        if 1 <= age <= max_age_days:
            return val
    return None


def vt_equity_earnings_drift_pead(data: dict, context: dict | None = None) -> list[dict]:
    """PEAD adapter using real earnings cache; gated by UEPS_ENABLE_PEAD."""
    if os.getenv("UEPS_ENABLE_PEAD", "0").strip().lower() not in ("1", "true", "yes", "on"):
        return []
    try:
        from baby_strategies.equity_earnings_drift_pead import EquityEarningsDriftPEAD
    except ImportError:
        return []

    repo_root = Path(__file__).resolve().parent.parent
    earnings_dir = repo_root / "data" / "earnings"
    if context and isinstance(context.get("earnings_dir"), (str, Path)):
        earnings_dir = Path(context["earnings_dir"])
    if not earnings_dir.exists():
        return []

    strat = EquityEarningsDriftPEAD()
    out: list[dict] = []
    for sym, raw in data.items():
        if not isinstance(raw, pd.DataFrame) or len(raw) < 30:
            continue
        s = str(sym).upper()
        if "=X" in s or "=F" in s or "-USD" in s or "USDT" in s:
            continue
        surprise = _load_recent_earnings_surprise(s, earnings_dir, max_age_days=7)
        if surprise is None:
            continue
        df = _lower_ohlcv(raw)
        try:
            for sig in strat.generate_signals(df, symbol=s, earnings_surprise_pct=surprise):
                d = _signal_to_dict(sig, "vt_earnings_pead", "equity")
                if d:
                    d["symbol"] = s
                    d["source"] = "vt_baby"
                    d.setdefault("extra", {})["surprise_pct"] = round(float(surprise), 3)
                    out.append(d)
        except Exception:
            continue
    return out


def vt_equity_two_day_rsi_reversal(data: dict, context: dict | None = None) -> list[dict]:
    try:
        from baby_strategies.equity_two_day_rsi_reversal import EquityTwoDayRsiReversalStrategy
    except ImportError:
        return []

    strat = EquityTwoDayRsiReversalStrategy()
    out: list[dict] = []
    for sym, raw in data.items():
        if not isinstance(raw, pd.DataFrame) or len(raw) < 220:
            continue
        s = str(sym).upper()
        if "=X" in s or "=F" in s or "-USD" in s or "USDT" in s:
            continue
        df = _lower_ohlcv(raw)
        try:
            for sig in strat.generate_signals(df, symbol=sym):
                d = _signal_to_dict(sig, "vt_equity_two_day_rsi_reversal", "equity")
                if d:
                    d["symbol"] = sym
                    out.append(d)
        except Exception:
            continue
    return out


def vt_commodity_trend_pullback_rsi(data: dict, context: dict | None = None) -> list[dict]:
    try:
        from baby_strategies.commodity_trend_pullback_rsi import (
            CommodityTrendPullbackRsiStrategy,
            SYMBOL_PRESETS,
        )
    except ImportError:
        return []

    strat = CommodityTrendPullbackRsiStrategy()
    out: list[dict] = []
    for sym in SYMBOL_PRESETS.keys():  # GLD, SLV, DBC, USO
        raw = data.get(sym)
        if raw is None or len(raw) < 220:
            continue
        df = _lower_ohlcv(raw)
        try:
            for sig in strat.generate_signals(df, symbol=sym):
                d = _signal_to_dict(sig, "vt_commodity_trend_pullback_rsi", "etf")
                if d:
                    d["symbol"] = sym
                    out.append(d)
        except Exception:
            continue
    return out


def vt_equity_vix_regime_momentum(data: dict, context: dict | None = None) -> list[dict]:
    try:
        from baby_strategies.equity_vix_regime_momentum import EquityVIXRegimeMomentum
    except ImportError:
        return []

    vix_raw = data.get("^VIX") or data.get("VIX")
    vix3m_raw = data.get("^VIX3M") or data.get("VIX3M")
    if vix_raw is None or vix3m_raw is None:
        return []
    try:
        vix_df = _lower_ohlcv(vix_raw)
        vix3m_df = _lower_ohlcv(vix3m_raw)
        vix = float(vix_df["close"].iloc[-1])
        vix3m = float(vix3m_df["close"].iloc[-1])
    except Exception:
        return []

    strat = EquityVIXRegimeMomentum()
    out: list[dict] = []
    for sym in ("SPY", "QQQ", "IWM"):
        raw = data.get(sym)
        if raw is None or len(raw) < 55:
            continue
        df = _lower_ohlcv(raw)
        try:
            for sig in strat.generate_signals(df, vix=vix, vix3m=vix3m, symbol=sym):
                d = _signal_to_dict(sig, "vt_equity_vix_regime_momentum", "equity")
                if d:
                    out.append(d)
        except Exception:
            continue
    return out


def vt_equity_sector_rotation_momentum(data: dict, context: dict | None = None) -> list[dict]:
    try:
        from baby_strategies.equity_sector_rotation_momentum import (
            EquitySectorRotationMomentum,
            SECTOR_ETFS,
        )
    except ImportError:
        return []

    sector_data: Dict[str, pd.DataFrame] = {}
    for sym in SECTOR_ETFS:
        raw = data.get(sym)
        if raw is not None and len(raw) >= 65:
            sector_data[sym] = _lower_ohlcv(raw)

    if len(sector_data) < 3:
        return []

    spy_raw = data.get("SPY")
    spy_df = _lower_ohlcv(spy_raw) if spy_raw is not None and len(spy_raw) >= 200 else None

    strat = EquitySectorRotationMomentum()
    try:
        signals = strat.generate_signals(sector_data, spy_data=spy_df)
    except Exception:
        return []

    out: list[dict] = []
    for sig in signals:
        d = _signal_to_dict(sig, "vt_equity_sector_rotation_momentum", "etf")
        if d:
            out.append(d)
    return out


# ETF symbols where OOS backtest (unwired_non_crypto_backtest_results.json 2026-05-14)
# showed WR 70-78%, PF 2.41-3.99, n 34-44 — all above Tier-2 thresholds.
# Strategy: Fade false Bollinger Band breakouts with below-average volume (exhaustion signal).
# Wire-Up Rule: WIRED — registered in VT_BABY_STRATEGIES below; scanner.py merges on every
#   equity/all run. OOS evidence: SPY WR=70.6% PF=2.51 n=34; QQQ WR=71.4% PF=2.41 n=35;
#   IWM WR=75.0% PF=3.25 n=44; XLK WR=77.8% PF=3.99 n=36; XLF WR=76.7% PF=3.29 n=43.
_VPCR_ETF_SYMBOLS = ["SPY", "QQQ", "IWM", "XLK", "XLF", "XLE", "XLV"]


def vt_volume_price_confirmation_reversal(data: dict, context: dict | None = None) -> list[dict]:
    try:
        from baby_strategies.volume_price_confirmation_reversal import (
            VolumePriceConfirmationReversalStrategy,
        )
    except ImportError:
        return []

    strat = VolumePriceConfirmationReversalStrategy()
    out: list[dict] = []
    for sym in _VPCR_ETF_SYMBOLS:
        raw = data.get(sym)
        if raw is None or len(raw) < 60:
            continue
        df = _lower_ohlcv(raw)
        try:
            for sig in strat.generate_signals(df, symbol=sym):
                d = _signal_to_dict(sig, "vt_volume_price_confirmation_reversal", "etf")
                if d:
                    d["symbol"] = sym
                    d["asset_class"] = "ETF"
                    out.append(d)
        except Exception:
            continue
    return out


VT_BABY_STRATEGIES: Dict[str, Any] = {
    "vt_adx_rsi2_etf": vt_adx_rsi2_etf,
    "vt_adx_rsi2_equity": vt_adx_rsi2_equity,
    "vt_thematic_etf_momentum": vt_thematic_etf_momentum,
    "vt_restatement_short": vt_restatement_short,
    "vt_stat_arb_gdx_slv": vt_stat_arb_gdx_slv,
    "vt_myfxbook_sentiment_forex": vt_myfxbook_sentiment_forex,
    "vt_edgar_insider_cluster": vt_edgar_insider_cluster,
    "vt_sc13d_activist": vt_sc13d_activist,
    "vt_csv_edge_luxalgo_alts": vt_csv_edge_luxalgo_alts,
    "vt_earnings_pead": vt_equity_earnings_drift_pead,
    "vt_equity_two_day_rsi_reversal": vt_equity_two_day_rsi_reversal,
    "vt_commodity_trend_pullback_rsi": vt_commodity_trend_pullback_rsi,
    "vt_equity_vix_regime_momentum": vt_equity_vix_regime_momentum,
    "vt_equity_sector_rotation_momentum": vt_equity_sector_rotation_momentum,
    "vt_volume_price_confirmation_reversal": vt_volume_price_confirmation_reversal,
}


def vt_copper_platinum_cot_momentum(data: dict, context: dict | None = None) -> list[dict]:
    try:
        from baby_strategies.copper_platinum_cot_momentum import (
            CopperPlatinumCotMomentumStrategy,
            SYMBOL_PRESETS,
        )
    except ImportError:
        return []

    strat = CopperPlatinumCotMomentumStrategy()
    out: list[dict] = []
    for sym in SYMBOL_PRESETS.keys():  # HG=F, PL=F
        raw = data.get(sym)
        if raw is None or len(raw) < 220:
            continue
        df = _lower_ohlcv(raw)
        try:
            for sig in strat.generate_signals(df, symbol=sym):
                d = _signal_to_dict(sig, "vt_copper_platinum_cot_momentum", "commodity")
                if d:
                    d["symbol"] = sym
                    d["asset_class"] = "COMMODITY"
                    out.append(d)
        except Exception:
            continue
    return out


def vt_bond_yield_curve_momentum(data: dict, context: dict | None = None) -> list[dict]:
    try:
        from baby_strategies.bond_yield_curve_momentum import (
            BondYieldCurveMomentumStrategy,
            SYMBOL_PRESETS,
        )
    except ImportError:
        return []

    strat = BondYieldCurveMomentumStrategy()
    # Build data_dict for multi-asset mode
    bond_data: Dict[str, pd.DataFrame] = {}
    for sym in SYMBOL_PRESETS.keys():  # TLT, IEF, SHY, BND
        raw = data.get(sym)
        if raw is not None and len(raw) >= 220:
            bond_data[sym] = _lower_ohlcv(raw)

    if "TLT" not in bond_data:
        return []  # TLT is the regime anchor — required

    out: list[dict] = []
    try:
        signals = strat.generate_signals(bond_data)
    except Exception:
        return []

    for sig in signals:
        d = _signal_to_dict(sig, "vt_bond_yield_curve_momentum", "etf")
        if d:
            d["asset_class"] = "BOND"
            out.append(d)
    return out


# Register after all adapters are defined
VT_BABY_STRATEGIES["vt_copper_platinum_cot_momentum"] = vt_copper_platinum_cot_momentum
VT_BABY_STRATEGIES["vt_bond_yield_curve_momentum"] = vt_bond_yield_curve_momentum
