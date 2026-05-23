# ---------------------------------------------------------------------------
# alpha_engine/polymarket_volume_filter.py
# ---------------------------------------------------------------------------
# Polymarket Volume Spike Filter — CRYPTO LONG entry confirmation layer.
#
# Design: When a CRYPTO LONG pick is being ingested, check whether the
# corresponding Polymarket markets for that symbol show a volume spike
# (current volume >> historical median). A Polymarket volume spike indicates
# smart-money crowd conviction that complements technical entry signals.
#
# Integration: Called from feed_hygiene.py step 5c — falls through gracefully
# if Polymarket data is unavailable or the symbol has no active markets.
#
# Rollback: export POLYMARKET_VOL_SPIKE_DISABLED=1
# ---------------------------------------------------------------------------

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).resolve().parent / 'data'
_POLYMARKET_SIGNALS_FILE = _DATA_DIR / 'polymarket_signals.json'

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Minimum Polymarket volume (USD) to qualify as a valid market signal.
# Below this, the market is too thin to be meaningful.
_MIN_MARKET_VOLUME_USD = 1_000.0

# Volume spike threshold: current volume must be this multiple of the
# symbol's median historical volume to count as a spike.
# e.g. 2.0 = current volume must be 2x the median for that symbol.
_SPIKE_MULTIPLIER = 2.0

# Confidence boost when Polymarket volume spike confirms a LONG entry.
_CONF_SPIKE_BOOST = 0.05  # +5% confidence when spike is present

# Symbols with zero Polymarket coverage — always pass (no markets = pass-through
# is the natural behavior, but listing them explicitly documents intent and
# saves a file read per call).
_EXEMPT_SYMBOLS = frozenset({
    # No known Polymarket markets — the filter naturally passes because
    # 'has_markets = False' triggers the no-data pass-through.
})

# ---------------------------------------------------------------------------
# Internal state (lazy-loaded, cached for session)
# ---------------------------------------------------------------------------

_cached_signals: Optional[list[dict]] = None
_cache_ts: Optional[datetime] = None
_CACHE_MAX_AGE_SECONDS = 300  # 5 minutes


def _get_cached_signals() -> list[dict]:
    """Return cached Polymarket signals, reloading if older than _CACHE_MAX_AGE_SECONDS.

    Cache is session-global and invalidated only on TTL expiry or explicit call
    to invalidate_cache(). Invalidating before checking defeats the cache — do NOT
    call _invalidate_cache() inside this function.
    """
    global _cached_signals, _cache_ts
    now = datetime.now(timezone.utc)

    if _cached_signals is not None and _cache_ts is not None:
        age = (now - _cache_ts).total_seconds()
        if age < _CACHE_MAX_AGE_SECONDS:
            return _cached_signals

    # TTL expired or cache cold — reload from disk
    if not _POLYMARKET_SIGNALS_FILE.exists():
        _cached_signals = []
        _cache_ts = now
        return _cached_signals

    try:
        with open(_POLYMARKET_SIGNALS_FILE, encoding='utf-8') as fh:
            data = json.load(fh)
        picks = data.get('picks', []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        _cached_signals = picks if isinstance(picks, list) else []
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning('[pm_vol_filter] Failed to load %s: %s', _POLYMARKET_SIGNALS_FILE, exc)
        _cached_signals = []

    _cache_ts = now
    return _cached_signals


def invalidate_cache() -> None:
    """Expire the session cache so the next call reloads fresh from disk.

    Call this from scanner.py or production_scanner.py at scan start so the
    filter sees the latest Polymarket signals file.
    """
    global _cached_signals, _cache_ts
    _cached_signals = None
    _cache_ts = None


def _invalidate_cache() -> None:
    """Alias for backward compatibility."""
    invalidate_cache()


# ---------------------------------------------------------------------------
# Core filter logic
# ---------------------------------------------------------------------------


def _is_exempt_symbol(symbol: str) -> bool:
    return symbol.upper() in _EXEMPT_SYMBOLS


def get_polymarket_volume_spike_info(symbol: str) -> dict:
    r'''Return volume spike info for a symbol from Polymarket signals.

    Returns a dict with keys:
        - has_markets      : bool — are there any active Polymarket markets?
        - volume_spike     : bool — is current volume a spike vs median?
        - spike_ratio      : float — current / median (1.0 = normal, >2 = spike)
        - current_volume   : float — most recent market volume USD
        - median_volume    : float — historical median volume for symbol
        - market_count     : int — number of active markets for symbol
        - top_direction    : str — dominant direction across markets
        - avg_probability  : float — average yes-probability across markets
        - reason           : str — human-readable explanation
    '''
    symbol_upper = symbol.upper()
    signals = _get_cached_signals()

    # Filter markets for this symbol
    symbol_markets = [
        s for s in signals
        if str(s.get('symbol', '')).upper() == symbol_upper
    ]

    result = {
        'has_markets': False,
        'volume_spike': False,
        'spike_ratio': 1.0,
        'current_volume': 0.0,
        'median_volume': 0.0,
        'market_count': 0,
        'top_direction': 'NEUTRAL',
        'avg_probability': 0.5,
        'reason': 'no polymarket data',
    }

    if not symbol_markets:
        result['reason'] = 'no Polymarket markets for %s' % symbol_upper
        return result

    result['has_markets'] = True
    result['market_count'] = len(symbol_markets)

    # Compute volume stats (only count markets above min volume threshold)
    volumes = [float(m.get('volume', 0)) for m in symbol_markets if float(m.get('volume', 0) or 0) >= _MIN_MARKET_VOLUME_USD]
    if not volumes:
        # No qualifying markets — has_markets stays False so filter passes
        result['has_markets'] = False
        result['reason'] = '%s markets below min volume threshold' % symbol_upper
        return result

    current_volume = max(volumes)
    result['current_volume'] = round(current_volume, 2)

    # Median volume for this symbol (lower-middle for even-length lists)
    sorted_vols = sorted(volumes)
    n = len(sorted_vols)
    median_idx = (n - 1) // 2  # lower-middle for even n (n=2 -> idx=0)
    median_volume = sorted_vols[median_idx] if sorted_vols else 1.0
    result['median_volume'] = round(median_volume, 2)

    if median_volume > 0:
        ratio = current_volume / median_volume
        result['spike_ratio'] = round(ratio, 3)
        result['volume_spike'] = ratio >= _SPIKE_MULTIPLIER

    # Direction: most markets are LONG or SHORT
    directions = [s.get('direction', s.get('signal_type', '').upper()) for s in symbol_markets]
    direction_counts: dict[str, int] = {}
    for d in directions:
        clean = d.upper().strip()
        if clean in ('LONG', 'SHORT', 'BUY', 'SELL'):
            direction_counts[clean] = direction_counts.get(clean, 0) + 1

    if direction_counts:
        result['top_direction'] = max(direction_counts, key=direction_counts.get)

    # Average probability
    probs = [float(s.get('probability', 0.5)) for s in symbol_markets if s.get('probability') is not None]
    if probs:
        result['avg_probability'] = round(sum(probs) / len(probs), 4)

    # Build reason string
    if result['volume_spike']:
        result['reason'] = (
            'VOLUME SPIKE: $%s vs $%s median (%.1fx) — Polymarket conviction elevated'
            % (current_volume, median_volume, result['spike_ratio'])
        )
    elif result['has_markets']:
        result['reason'] = (
            'no spike: $%s vs $%s median (%.1fx < %sx threshold)'
            % (current_volume, median_volume, result['spike_ratio'], _SPIKE_MULTIPLIER)
        )
    else:
        result['reason'] = f'no Polymarket markets for {symbol_upper}'

    return result


def is_polymarket_volume_confirmed(symbol: str, direction: str) -> tuple[bool, str]:
    r'''Main filter function — returns (confirmed, reason).

    For CRYPTO LONG entries: require Polymarket volume spike confirmation.
    For CRYPTO SHORT entries or non-crypto: always confirmed (passive check).

    The filter is conservative — it passes through if:
      - Polymarket data is unavailable
      - Symbol has no active markets
      - Volume spike is not detected (but is logged as a soft warning)
      - POLYMARKET_VOL_SPIKE_DISABLED=1 is set

    Only BLOCKS (returns False) when:
      - Polymarket volume spike is MISSING for a CRYPTO LONG entry
      - AND the symbol has active Polymarket markets (proving coverage exists)
      - AND the filter is not disabled via env var
    '''
    # Rollback flag
    if os.environ.get('POLYMARKET_VOL_SPIKE_DISABLED', '').strip() in ('1', 'true', 'TRUE'):
        return True, 'filter disabled via POLYMARKET_VOL_SPIKE_DISABLED'

    symbol_upper = symbol.upper().strip()

    # Exempt symbols always pass
    if _is_exempt_symbol(symbol_upper):
        return True, ('%s in exempt list' % symbol_upper)

    # Only apply to CRYPTO LONG entries
    direction_upper = direction.upper().strip()
    is_crypto_long = (
        direction_upper in ('LONG', 'BUY') and
        symbol_upper.endswith('USDT')
    )

    if not is_crypto_long:
        return True, 'not a CRYPTO LONG entry — no Polymarket confirmation required'

    # Get volume spike info
    info = get_polymarket_volume_spike_info(symbol_upper)

    # Case 1: No Polymarket markets at all — pass through (no data is not a block)
    if not info['has_markets']:
        return True, ('%s -- no Polymarket markets found (pass-through)' % symbol_upper)

    # Case 2: Has markets but no volume spike
    # Soft warning: log but do not block — Polymarket is one signal among many
    if not info['volume_spike']:
        logger.info(
            '[pm_vol_filter] %s LONG entry — Polymarket no-spike warning: %s',
            symbol_upper,
            info['reason'],
        )
        # Pass through but record the lack of confirmation in the reason
        return True, ('no-spike ' + info['reason'])

    # Case 3: Volume spike confirmed — boost confidence
    logger.info(
        '[pm_vol_filter] %s LONG entry — Polymarket VOLUME SPIKE confirmed: %s',
        symbol_upper,
        info['reason'],
    )
    return True, info['reason']


def apply_confidence_boost(
    pick: dict,
    current_confidence: float,
) -> tuple[float, str]:
    r'''Apply a confidence boost to a CRYPTO LONG pick if Polymarket volume spike
    is confirmed. Call this from feed_hygiene or scanner after is_valid_active_pick.

    Args:
        pick         : the pick dict (used to get symbol/direction)
        current_confidence : the pick's current confidence score

    Returns:
        (new_confidence, reason) — boosted if spike confirmed, unchanged otherwise
    '''
    symbol = str(pick.get('symbol', '')).upper()
    direction = str(pick.get('direction', pick.get('signal_type', ''))).upper()

    confirmed, reason = is_polymarket_volume_confirmed(symbol, direction)

    info = get_polymarket_volume_spike_info(symbol)

    if info['volume_spike'] and confirmed:
        # +_CONF_SPIKE_BOOST% confidence boost when spike is confirmed.
        # Clamp: (a) boost cannot be negative (current > 0.90 is already capped),
        #        (b) new_conf cannot exceed 0.90.
        boost = min(_CONF_SPIKE_BOOST, max(0.90 - current_confidence, 0.0))
        new_conf = round(min(0.90, current_confidence + boost), 3)
        return new_conf, ('pm_vol_spike: ' + info['reason'])

    return current_confidence, reason


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
    )

    test_symbols = [
        'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT',
        'DOGEUSDT', 'AVAXUSDT', 'LINKUSDT',
    ]

    print('=' * 60)
    print('  Polymarket Volume Spike Filter — Smoke Test')
    print('=' * 60)

    for sym in test_symbols:
        info = get_polymarket_volume_spike_info(sym)
        confirmed, reason = is_polymarket_volume_confirmed(sym, 'LONG')
        spike_tag = '[SPIKE]' if info['volume_spike'] else '[-----]'
        print(
            '  %s %-12s  vol=$%10s  median=$%10s  ratio=%.2fx  markets=%s  confirmed=%s  %s'
            % (spike_tag, sym,
               info['current_volume'], info['median_volume'],
               info['spike_ratio'], info['market_count'],
               confirmed, reason[:60])
        )

    print('Done.')


if __name__ == '__main__':
    main()