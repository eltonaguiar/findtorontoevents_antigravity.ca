"""Tests for alpha_engine.asset_class — canonical asset-class normalization.

Covers: USDT/USDC→crypto, =X→forex, =F→futures, known ETF/equity symbols,
6-char forex pairs, conflicting signals, missing fields, edge cases.
"""
import pytest
from alpha_engine.asset_class import (
    normalize_asset_class,
    classify_pick_asset_class_upper,
    is_crypto,
    is_non_crypto,
    asset_class_from_symbol,
    normalize_symbol,
    FOREX_CODES,
    BOND_SYMBOLS,
    ETF_SYMBOLS,
    EQUITY_SYMBOLS,
    COMMODITY_SYMBOLS,
)

# ═══════════════════════════════════════════════════════════════════════════
# normalize_symbol
# ═══════════════════════════════════════════════════════════════════════════


class TestNormalizeSymbol:
    def test_uppercase(self):
        assert normalize_symbol("btcusdt") == "BTCUSDT"

    def test_strip_dashes(self):
        assert normalize_symbol("EUR-USD") == "EURUSD"

    def test_strip_slashes(self):
        assert normalize_symbol("EUR/USD") == "EURUSD"

    def test_strip_underscores(self):
        assert normalize_symbol("eur_usd") == "EURUSD"

    def test_combined_separators(self):
        assert normalize_symbol("btc-usdt_futures/1") == "BTCUSDTFUTURES1"

    def test_none_input(self):
        assert normalize_symbol(None) == ""

    def test_empty_string(self):
        assert normalize_symbol("") == ""


# ═══════════════════════════════════════════════════════════════════════════
# asset_class_from_symbol
# ═══════════════════════════════════════════════════════════════════════════


class TestAssetClassFromSymbol:
    # ── Crypto ──
    def test_usdt_suffix(self):
        assert asset_class_from_symbol("BTCUSDT") == "crypto"

    def test_usdc_suffix(self):
        assert asset_class_from_symbol("ETHUSDC") == "crypto"

    def test_busd_suffix(self):
        assert asset_class_from_symbol("BNBBUSD") == "crypto"

    def test_dai_suffix(self):
        assert asset_class_from_symbol("ETHDAI") == "crypto"  # DAI as quote currency

    def test_lowercase_usdt(self):
        assert asset_class_from_symbol("btcusdt") == "crypto"

    # ── Forex ──
    def test_forex_suffix(self):
        assert asset_class_from_symbol("EURUSD=X") == "forex"

    def test_forex_suffix_with_separator(self):
        assert asset_class_from_symbol("EUR-USD=X") == "forex"

    def test_six_char_forex_pair(self):
        assert asset_class_from_symbol("EURUSD") == "forex"

    def test_six_char_gbpjpy(self):
        assert asset_class_from_symbol("GBPJPY") == "forex"

    def test_six_char_non_forex(self):
        """6 chars but not valid forex codes → unknown."""
        assert asset_class_from_symbol("ABCDEF") == "unknown"

    def test_forex_exotic_pair(self):
        assert asset_class_from_symbol("USDTRY") == "forex"

    # ── Futures ──
    def test_futures_suffix(self):
        assert asset_class_from_symbol("GC=F") == "futures"

    def test_futures_suffix_crude(self):
        assert asset_class_from_symbol("CL=F") == "futures"

    # ── ETF ──
    def test_known_etf_spy(self):
        assert asset_class_from_symbol("SPY") == "etf"

    def test_known_etf_qqq(self):
        assert asset_class_from_symbol("QQQ") == "etf"

    def test_known_etf_gld(self):
        assert asset_class_from_symbol("GLD") == "etf"

    def test_known_etf_tqqq(self):
        assert asset_class_from_symbol("TQQQ") == "etf"

    # ── Bond (symbol-based — bond ETFs classify as bond, not etf) ──
    def test_known_bond_tlt(self):
        assert asset_class_from_symbol("TLT") == "bond"

    def test_known_bond_ief(self):
        assert asset_class_from_symbol("IEF") == "bond"

    def test_known_bond_agg(self):
        assert asset_class_from_symbol("AGG") == "bond"

    def test_known_bond_lqd(self):
        assert asset_class_from_symbol("LQD") == "bond"

    def test_known_bond_shy(self):
        assert asset_class_from_symbol("SHY") == "bond"

    def test_known_bond_hyg(self):
        assert asset_class_from_symbol("HYG") == "bond"

    def test_known_bond_bnd(self):
        assert asset_class_from_symbol("BND") == "bond"

    def test_known_bond_emb(self):
        assert asset_class_from_symbol("EMB") == "bond"

    # ── Equity ──
    def test_known_equity_aapl(self):
        assert asset_class_from_symbol("AAPL") == "equity"

    def test_known_equity_tsla(self):
        assert asset_class_from_symbol("TSLA") == "equity"

    def test_known_equity_nvda(self):
        assert asset_class_from_symbol("NVDA") == "equity"

    # ── Unknown ──
    def test_unknown_symbol(self):
        assert asset_class_from_symbol("UNKNOWNXYZ") == "unknown"

    def test_empty_symbol(self):
        assert asset_class_from_symbol("") == "unknown"

    def test_none_symbol(self):
        assert asset_class_from_symbol(None) == "unknown"


# ═══════════════════════════════════════════════════════════════════════════
# normalize_asset_class (full pick dict)
# ═══════════════════════════════════════════════════════════════════════════


class TestNormalizeAssetClass:
    # ── Symbol-based detection ──
    def test_crypto_usdt(self):
        pick = {"symbol": "BTCUSDT"}
        assert normalize_asset_class(pick) == "crypto"

    def test_forex_suffix(self):
        pick = {"symbol": "EURUSD=X"}
        assert normalize_asset_class(pick) == "forex"

    def test_futures_suffix(self):
        pick = {"symbol": "GC=F"}
        assert normalize_asset_class(pick) == "futures"

    def test_etf_symbol(self):
        pick = {"symbol": "SPY"}
        assert normalize_asset_class(pick) == "etf"

    def test_equity_symbol(self):
        pick = {"symbol": "AAPL"}
        assert normalize_asset_class(pick) == "equity"

    # ── Category-based detection ──
    def test_category_crypto(self):
        pick = {"category": "crypto", "symbol": "XYZ123"}
        assert normalize_asset_class(pick) == "crypto"

    def test_category_meme(self):
        pick = {"category": "meme", "symbol": "DOGEUSDT"}
        assert normalize_asset_class(pick) == "crypto"

    def test_category_forex(self):
        pick = {"category": "forex", "symbol": "XYZABC"}
        assert normalize_asset_class(pick) == "forex"

    def test_category_fx(self):
        pick = {"category": "fx", "symbol": "XYZABC"}
        assert normalize_asset_class(pick) == "forex"

    def test_category_etf(self):
        pick = {"category": "etf", "symbol": "XYZABC"}
        assert normalize_asset_class(pick) == "etf"

    def test_category_bond(self):
        pick = {"category": "bond", "symbol": "XYZABC"}
        assert normalize_asset_class(pick) == "bond"

    def test_category_commodity(self):
        pick = {"category": "commodity", "symbol": "XYZABC"}
        assert normalize_asset_class(pick) == "commodity"

    def test_category_futures(self):
        pick = {"category": "futures", "symbol": "XYZABC"}
        assert normalize_asset_class(pick) == "futures"

    def test_category_equity(self):
        pick = {"category": "equity", "symbol": "XYZABC"}
        assert normalize_asset_class(pick) == "equity"

    def test_category_stock(self):
        pick = {"category": "stock", "symbol": "XYZABC"}
        assert normalize_asset_class(pick) == "equity"

    def test_category_stocks(self):
        pick = {"category": "stocks", "symbol": "XYZABC"}
        assert normalize_asset_class(pick) == "equity"

    def test_category_penny(self):
        pick = {"category": "penny", "symbol": "XYZABC"}
        assert normalize_asset_class(pick) == "equity"

    # ── Source/strategy hints ──
    def test_source_binance(self):
        pick = {"source_system": "binance_scanner", "symbol": "XYZABC"}
        assert normalize_asset_class(pick) == "crypto"

    def test_source_bybit(self):
        pick = {"source_system": "bybit_signals", "symbol": "XYZABC"}
        assert normalize_asset_class(pick) == "crypto"

    def test_source_hyperliquid(self):
        pick = {"source_system": "hyperliquid_copy", "symbol": "XYZABC"}
        assert normalize_asset_class(pick) == "crypto"

    def test_strategy_copy_hl(self):
        pick = {"strategy": "copy_hl_whale_tracker", "symbol": "XYZABC"}
        assert normalize_asset_class(pick) == "crypto"

    def test_strategy_funding(self):
        pick = {"strategy": "funding_rate_carry", "symbol": "XYZABC"}
        assert normalize_asset_class(pick) == "crypto"

    def test_strategy_onchain(self):
        pick = {"strategy": "onchain_flow_signal", "symbol": "XYZABC"}
        assert normalize_asset_class(pick) == "crypto"

    # ── Asset_class field (alternative to category) ──
    def test_asset_class_field_equity(self):
        pick = {"asset_class": "EQUITY", "symbol": "XYZABC"}
        assert normalize_asset_class(pick) == "equity"

    def test_asset_class_field_forex(self):
        pick = {"asset_class": "FOREX", "symbol": "XYZABC"}
        assert normalize_asset_class(pick) == "forex"

    # ── Default fallback ──
    def test_empty_pick_defaults_to_equity(self):
        pick = {}
        assert normalize_asset_class(pick) == "equity"

    def test_unknown_category_defaults_to_equity(self):
        pick = {"category": "something_weird", "symbol": "XYZABC"}
        assert normalize_asset_class(pick) == "equity"

    # ── Conflicting signals ──
    # ── Priority order: unambiguous suffixes > category > source hints > symbol frozensets ──

    def test_suffix_wins_over_category(self):
        """Unambiguous symbol suffix (=X) takes priority over conflicting category."""
        pick = {"symbol": "EURUSD=X", "category": "equity"}
        assert normalize_asset_class(pick) == "forex"

    def test_suffix_wins_over_source(self):
        """Unambiguous symbol suffix (=F) takes priority over crypto source hint."""
        pick = {"symbol": "GC=F", "source_system": "binance"}
        assert normalize_asset_class(pick) == "futures"

    def test_category_wins_over_source_hint(self):
        """Explicit category field beats source-system crypto hint."""
        pick = {"category": "equity", "source_system": "binance", "symbol": "XYZABC"}
        assert normalize_asset_class(pick) == "equity"

    def test_category_wins_over_symbol_frozenset(self):
        """Category='bond' beats IEF being in BOND_SYMBOLS frozenset."""
        pick = {"symbol": "IEF", "category": "bond"}
        assert normalize_asset_class(pick) == "bond"

    def test_bond_category_with_unknown_symbol(self):
        """category='bond' with symbol not in any frozenset → bond (category wins)."""
        pick = {"symbol": "UNKNOWN999", "category": "bond"}
        assert normalize_asset_class(pick) == "bond"

    def test_source_hint_wins_over_frozenset(self):
        """Source hint wins over symbol frozenset when no category."""
        pick = {"source_system": "binance", "symbol": "SPY"}
        assert normalize_asset_class(pick) == "crypto"

    # ── Bond classification (the bug this fix addresses) ──

    def test_bond_tlt_with_category(self):
        pick = {"symbol": "TLT", "category": "bond"}
        assert normalize_asset_class(pick) == "bond"

    def test_bond_ief_with_category(self):
        pick = {"symbol": "IEF", "category": "bond"}
        assert normalize_asset_class(pick) == "bond"

    def test_bond_shy_with_category(self):
        pick = {"symbol": "SHY", "category": "bond"}
        assert normalize_asset_class(pick) == "bond"

    def test_bond_agg_with_category(self):
        pick = {"symbol": "AGG", "category": "bond"}
        assert normalize_asset_class(pick) == "bond"

    def test_bond_lqd_with_category(self):
        pick = {"symbol": "LQD", "category": "bond"}
        assert normalize_asset_class(pick) == "bond"

    def test_bond_hyg_with_category(self):
        pick = {"symbol": "HYG", "category": "bond"}
        assert normalize_asset_class(pick) == "bond"

    def test_bond_bnd_with_category(self):
        pick = {"symbol": "BND", "category": "bond"}
        assert normalize_asset_class(pick) == "bond"

    def test_bond_emb_with_category(self):
        pick = {"symbol": "EMB", "category": "bond"}
        assert normalize_asset_class(pick) == "bond"

    def test_bond_tlt_no_category_uses_frozenset(self):
        """TLT without category should still classify as bond via BOND_SYMBOLS frozenset."""
        pick = {"symbol": "TLT"}
        assert normalize_asset_class(pick) == "bond"

    def test_bond_shy_no_category_uses_frozenset(self):
        """SHY without category should classify as bond via BOND_SYMBOLS frozenset."""
        pick = {"symbol": "SHY"}
        assert normalize_asset_class(pick) == "bond"

    def test_bond_agg_no_category_uses_frozenset(self):
        """AGG without category should classify as bond via BOND_SYMBOLS frozenset."""
        pick = {"symbol": "AGG"}
        assert normalize_asset_class(pick) == "bond"

    def test_mixed_case_category(self):
        pick = {"category": "CRYPTO", "symbol": "XYZABC"}
        assert normalize_asset_class(pick) == "crypto"

    # ── 6-char forex pair with separators ──
    def test_forex_pair_with_dash(self):
        pick = {"symbol": "EUR-USD"}
        assert normalize_asset_class(pick) == "forex"

    def test_forex_pair_with_slash(self):
        pick = {"symbol": "EUR/USD"}
        assert normalize_asset_class(pick) == "forex"


# ═══════════════════════════════════════════════════════════════════════════
# is_crypto / is_non_crypto
# ═══════════════════════════════════════════════════════════════════════════


class TestIsCrypto:
    def test_crypto_true(self):
        assert is_crypto({"symbol": "BTCUSDT"}) is True

    def test_crypto_false_forex(self):
        assert is_crypto({"symbol": "EURUSD=X"}) is False

    def test_crypto_false_equity(self):
        assert is_crypto({"symbol": "AAPL"}) is False

    def test_crypto_meme_category(self):
        assert is_crypto({"category": "meme", "symbol": "DOGEUSDT"}) is True


class TestIsNonCrypto:
    def test_non_crypto_forex(self):
        assert is_non_crypto({"symbol": "EURUSD=X"}) is True

    def test_non_crypto_equity(self):
        assert is_non_crypto({"symbol": "AAPL"}) is True

    def test_non_crypto_etf(self):
        assert is_non_crypto({"symbol": "SPY"}) is True

    def test_non_crypto_futures(self):
        assert is_non_crypto({"symbol": "GC=F"}) is True

    def test_crypto_is_not_non_crypto(self):
        assert is_non_crypto({"symbol": "BTCUSDT"}) is False


# ═══════════════════════════════════════════════════════════════════════════
# Constants integrity
# ═══════════════════════════════════════════════════════════════════════════


class TestConstants:
    def test_forex_codes_has_major_pairs(self):
        for code in ("EUR", "GBP", "USD", "JPY", "AUD", "CAD", "CHF", "NZD"):
            assert code in FOREX_CODES

    def test_etf_symbols_has_spys(self):
        for sym in ("SPY", "QQQ", "IWM", "GLD"):
            assert sym in ETF_SYMBOLS

    def test_bond_symbols_has_tlt_ief(self):
        for sym in ("TLT", "IEF", "SHY", "AGG", "LQD", "HYG", "BND", "EMB"):
            assert sym in BOND_SYMBOLS

    def test_tlt_ief_not_in_etf_symbols(self):
        """TLT and IEF are bond ETFs, NOT equity ETFs."""
        assert "TLT" not in ETF_SYMBOLS
        assert "IEF" not in ETF_SYMBOLS

    def test_no_overlap_between_bond_and_etf(self):
        overlap = BOND_SYMBOLS & ETF_SYMBOLS
        assert len(overlap) == 0, f"Bond and ETF sets overlap: {overlap}"

    def test_equity_symbols_has_faang(self):
        for sym in ("AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA"):
            assert sym in EQUITY_SYMBOLS

    def test_no_overlap_between_etf_and_equity(elf):
        overlap = ETF_SYMBOLS & EQUITY_SYMBOLS
        assert len(overlap) == 0, f"ETF and Equity sets overlap: {overlap}"

    def test_forex_codes_are_3chars(self):
        for code in FOREX_CODES:
            assert len(code) == 3, f"Forex code '{code}' is not 3 characters"


# ═══════════════════════════════════════════════════════════════════════════
# pf_registry UNKNOWN cohort regression (audit_surface_truth 2026-06-06)
# ═══════════════════════════════════════════════════════════════════════════


class TestPfRegistryUnknownRegression:
    """Picks from alpha_engine closed ledger that were landing in UNKNOWN."""

    @pytest.mark.parametrize(
        "symbol,strategy,expected",
        [
            ("PA", "commodity_rsi_divergence", "COMMODITY"),
            ("PL", "metals_mean_reversion", "COMMODITY"),
            ("QQQ", "cta_golden_cross", "ETF"),
            ("AMD", "momentum_rider_base", "EQUITY"),
            ("LCID", "momentum_rider_base", "EQUITY"),
            ("AAPL", "vt_equity_two_day_rsi_reversal", "EQUITY"),
        ],
    )
    def test_alpha_engine_missing_asset_class_derives_upper(self, symbol, strategy, expected):
        pick = {
            "symbol": symbol,
            "strategy": strategy,
            "source_system": "alpha_engine",
        }
        assert classify_pick_asset_class_upper(pick) == expected

    def test_unknown_stamped_category_is_rederived(self):
        pick = {
            "symbol": "SPY",
            "strategy": "etf_risk_parity_rotation",
            "asset_class": "UNKNOWN",
            "source_system": "etf_all_strategies",
        }
        assert classify_pick_asset_class_upper(pick) == "ETF"

    def test_build_pf_registry_asset_class_helper(self):
        from tools.build_pf_registry import _asset_class

        row = {"symbol": "AAPL", "strategy": "vt_equity_two_day_rsi_reversal"}
        assert _asset_class(row) == "EQUITY"
