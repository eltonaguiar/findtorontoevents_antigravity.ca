"""FIX-L unit tests: non-crypto TIER1/TIER2 symbol sets in market_cap_tier_score.

Covers:
1. Non-crypto blue-chip symbols receive +10/+5 (previously 0).
2. Untiered non-crypto remains 0 (no crypto-specific micro-cap penalty).
3. Crypto tier behaviour unchanged (+10 / +5 / -5).
4. Symbol normalization (hyphens, Yahoo '=X' suffix, slashes, dots).
5. Forex heuristics still fire when category missing.
"""

import unittest

from alpha_engine.elite_scorer import (
    TIER1_COINS,
    TIER1_COMMODITY,
    TIER1_EQUITY,
    TIER1_ETF,
    TIER1_FOREX,
    TIER1_FUTURES,
    TIER2_COINS,
    TIER2_COMMODITY,
    TIER2_EQUITY,
    TIER2_ETF,
    TIER2_FOREX,
    TIER2_FUTURES,
    _normalize_non_crypto_symbol,
    market_cap_tier_score,
)


class CryptoTierBehaviourUnchangedTests(unittest.TestCase):
    def test_tier1_crypto_returns_ten(self) -> None:
        self.assertEqual(market_cap_tier_score("BTCUSDT"), 10)
        self.assertEqual(market_cap_tier_score("ETHUSDT", "crypto"), 10)

    def test_tier2_crypto_returns_five(self) -> None:
        self.assertEqual(market_cap_tier_score("AAVEUSDT"), 5)

    def test_untiered_crypto_still_penalised(self) -> None:
        # FIX-L must NOT remove the crypto micro-cap penalty.
        self.assertEqual(market_cap_tier_score("REZUSDT"), -5)
        self.assertEqual(market_cap_tier_score("RESOLVUSDT", "crypto"), -5)


class EquityTierTests(unittest.TestCase):
    def test_tier1_equity_returns_ten(self) -> None:
        self.assertEqual(market_cap_tier_score("AAPL", "equity"), 10)
        self.assertEqual(market_cap_tier_score("NVDA", "stock"), 10)
        self.assertEqual(market_cap_tier_score("MSFT", "EQUITY"), 10)  # case-insensitive

    def test_tier2_equity_returns_five(self) -> None:
        self.assertEqual(market_cap_tier_score("ORCL", "equity"), 5)
        self.assertEqual(market_cap_tier_score("NFLX", "stock"), 5)

    def test_untiered_equity_returns_zero_not_negative(self) -> None:
        # Must NOT inherit the crypto -5 penalty.
        self.assertEqual(market_cap_tier_score("RANDOMPENNY", "equity"), 0)
        self.assertEqual(market_cap_tier_score("SMALLCAP", "stock"), 0)

    def test_hyphenated_equity_normalizes(self) -> None:
        # 'BRK-B' should normalize to 'BRKB' which is in TIER1_EQUITY.
        self.assertEqual(market_cap_tier_score("BRK-B", "equity"), 10)


class ForexTierTests(unittest.TestCase):
    def test_tier1_forex_returns_ten(self) -> None:
        self.assertEqual(market_cap_tier_score("EURUSD", "forex"), 10)
        self.assertEqual(market_cap_tier_score("USDJPY", "forex"), 10)

    def test_tier1_forex_via_yahoo_suffix_without_category(self) -> None:
        # Forex heuristic should still fire when category is empty.
        self.assertEqual(market_cap_tier_score("EURUSD=X"), 10)
        self.assertEqual(market_cap_tier_score("GBPJPY=X"), 10)

    def test_tier1_forex_via_slash_without_category(self) -> None:
        self.assertEqual(market_cap_tier_score("EUR/USD"), 10)

    def test_tier2_forex_returns_five(self) -> None:
        self.assertEqual(market_cap_tier_score("EURAUD", "forex"), 5)
        self.assertEqual(market_cap_tier_score("CADJPY=X"), 5)

    def test_exotic_forex_returns_zero(self) -> None:
        self.assertEqual(market_cap_tier_score("USDTRY", "forex"), 0)
        self.assertEqual(market_cap_tier_score("USDZAR=X"), 0)


class CommodityTierTests(unittest.TestCase):
    def test_tier1_commodity_returns_ten(self) -> None:
        self.assertEqual(market_cap_tier_score("GC", "commodity"), 10)
        self.assertEqual(market_cap_tier_score("XAUUSD", "commodity"), 10)
        self.assertEqual(market_cap_tier_score("CL", "commodity"), 10)

    def test_tier2_commodity_returns_five(self) -> None:
        self.assertEqual(market_cap_tier_score("ZC", "commodity"), 5)
        self.assertEqual(market_cap_tier_score("KC", "commodity"), 5)

    def test_untiered_commodity_returns_zero(self) -> None:
        self.assertEqual(market_cap_tier_score("XYZ", "commodity"), 0)


class FuturesTierTests(unittest.TestCase):
    def test_tier1_futures_returns_ten(self) -> None:
        self.assertEqual(market_cap_tier_score("ES", "futures"), 10)
        self.assertEqual(market_cap_tier_score("NQ", "futures"), 10)
        self.assertEqual(market_cap_tier_score("ZN", "futures"), 10)

    def test_tier2_futures_returns_five(self) -> None:
        self.assertEqual(market_cap_tier_score("ZF", "futures"), 5)
        self.assertEqual(market_cap_tier_score("6A", "futures"), 5)

    def test_bond_category_routes_to_futures_tiers(self) -> None:
        # Bond futures share the same tier set as other futures.
        self.assertEqual(market_cap_tier_score("ZB", "bond"), 10)
        self.assertEqual(market_cap_tier_score("ZT", "bond"), 5)


class ETFTierTests(unittest.TestCase):
    def test_tier1_etf_returns_ten(self) -> None:
        self.assertEqual(market_cap_tier_score("SPY", "etf"), 10)
        self.assertEqual(market_cap_tier_score("QQQ", "etf"), 10)
        self.assertEqual(market_cap_tier_score("GLD", "etf"), 10)

    def test_tier2_etf_returns_five(self) -> None:
        self.assertEqual(market_cap_tier_score("XLP", "etf"), 5)
        self.assertEqual(market_cap_tier_score("ARKK", "etf"), 5)

    def test_untiered_etf_returns_zero(self) -> None:
        self.assertEqual(market_cap_tier_score("RANDOMETF", "etf"), 0)


class SymbolNormalizationTests(unittest.TestCase):
    def test_normalize_strips_hyphens(self) -> None:
        self.assertEqual(_normalize_non_crypto_symbol("BRK-B"), "BRKB")

    def test_normalize_strips_yahoo_suffix(self) -> None:
        self.assertEqual(_normalize_non_crypto_symbol("EURUSD=X"), "EURUSD")

    def test_normalize_strips_slashes(self) -> None:
        self.assertEqual(_normalize_non_crypto_symbol("EUR/USD"), "EURUSD")

    def test_normalize_strips_dots(self) -> None:
        self.assertEqual(_normalize_non_crypto_symbol("BRK.B"), "BRKB")

    def test_normalize_uppercases(self) -> None:
        self.assertEqual(_normalize_non_crypto_symbol("aapl"), "AAPL")

    def test_normalize_handles_empty(self) -> None:
        self.assertEqual(_normalize_non_crypto_symbol(""), "")
        self.assertEqual(_normalize_non_crypto_symbol(None), "")  # type: ignore[arg-type]


class TierSetDisjointnessTests(unittest.TestCase):
    """A symbol must not be in both TIER1 and TIER2 of the same asset class."""

    def test_equity_tiers_disjoint(self) -> None:
        self.assertEqual(TIER1_EQUITY & TIER2_EQUITY, set())

    def test_forex_tiers_disjoint(self) -> None:
        self.assertEqual(TIER1_FOREX & TIER2_FOREX, set())

    def test_commodity_tiers_disjoint(self) -> None:
        self.assertEqual(TIER1_COMMODITY & TIER2_COMMODITY, set())

    def test_futures_tiers_disjoint(self) -> None:
        self.assertEqual(TIER1_FUTURES & TIER2_FUTURES, set())

    def test_etf_tiers_disjoint(self) -> None:
        self.assertEqual(TIER1_ETF & TIER2_ETF, set())

    def test_crypto_tiers_disjoint(self) -> None:
        self.assertEqual(TIER1_COINS & TIER2_COINS, set())


class RegressionTests(unittest.TestCase):
    """Guard against the pre-FIX-L behaviour creeping back in."""

    def test_blue_chip_equity_no_longer_returns_zero(self) -> None:
        self.assertNotEqual(market_cap_tier_score("AAPL", "equity"), 0)

    def test_major_forex_no_longer_returns_zero(self) -> None:
        self.assertNotEqual(market_cap_tier_score("EURUSD", "forex"), 0)

    def test_gold_no_longer_returns_zero(self) -> None:
        self.assertNotEqual(market_cap_tier_score("XAUUSD", "commodity"), 0)

    def test_spy_no_longer_returns_zero(self) -> None:
        self.assertNotEqual(market_cap_tier_score("SPY", "etf"), 0)


if __name__ == "__main__":
    unittest.main()
