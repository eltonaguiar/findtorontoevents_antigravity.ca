"""
Tests for commodity_seasonal strategy + usda fetcher.

Refs: reports/edge_research_synthesis_2026_05_12.md
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest import mock

import pytest

from alpha_engine import commodity_seasonal as cs
from tools import usda_data_fetcher as usda


# ---------- USDA fetcher ----------

def test_usda_graceful_failure_on_network_error(tmp_path, monkeypatch):
    """Fetcher must return empty-rows dict (not raise) when API down."""
    monkeypatch.setattr(usda, "CACHE_DIR", tmp_path)

    def _bad_query(_params):
        return {}

    monkeypatch.setattr(usda, "_query", _bad_query)
    out = usda.fetch_planting_progress("CORN")
    assert isinstance(out, dict)
    assert out.get("row_count", -1) == 0
    assert out.get("rows") == []


def test_usda_unsupported_crop_returns_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(usda, "CACHE_DIR", tmp_path)
    out = usda.fetch_inventory("LITHIUM")
    assert out == {}


# ---------- Seasonal window detection ----------

def test_detect_window_pre_planting_long():
    # CORN planting_peak = week 19 -> weeks 17,18 should LONG
    dt = datetime.fromisocalendar(2026, 18, 3).replace(tzinfo=timezone.utc)
    assert cs.detect_window("CORN", dt) == "LONG"


def test_detect_window_pre_harvest_short():
    # CORN harvest_peak = week 41 -> weeks 39,40 should SHORT
    dt = datetime.fromisocalendar(2026, 40, 3).replace(tzinfo=timezone.utc)
    assert cs.detect_window("CORN", dt) == "SHORT"


def test_detect_window_outside_returns_none():
    dt = datetime.fromisocalendar(2026, 1, 3).replace(tzinfo=timezone.utc)
    assert cs.detect_window("CORN", dt) is None


# ---------- Pick generation ----------

def test_generate_picks_disabled_by_default(monkeypatch):
    monkeypatch.delenv("COMMODITY_SEASONAL_ENABLED", raising=False)
    assert cs.generate_picks() == []


def test_build_pick_shape_and_asset_class():
    now = datetime.fromisocalendar(2026, 18, 3).replace(tzinfo=timezone.utc)
    pick = cs.build_pick("CORN", "LONG", price=450.0, atr=5.0, now=now)
    required = {
        "strategy", "asset_class", "symbol", "direction",
        "entry_price", "take_profit", "stop_loss", "confidence",
    }
    assert required.issubset(pick.keys())
    assert pick["asset_class"] == "COMMODITY"
    assert pick["strategy"] == "commodity_seasonal_planting_harvest"
    assert pick["symbol"] == "ZC=F"
    assert pick["direction"] == "LONG"
    assert pick["take_profit"] > pick["entry_price"] > pick["stop_loss"]
    assert 0.55 <= pick["confidence"] <= 0.75


def test_generate_picks_enabled_emits_when_in_window(monkeypatch):
    monkeypatch.setenv("COMMODITY_SEASONAL_ENABLED", "1")
    monkeypatch.setenv("COMMODITY_SEASONAL_CROPS", "ALL")
    fake_now = datetime.fromisocalendar(2026, 18, 3).replace(tzinfo=timezone.utc)
    monkeypatch.setattr(cs, "_fetch_price_atr", lambda _s: (450.0, 5.0))
    picks = cs.generate_picks(now=fake_now)
    assert len(picks) >= 1
    for p in picks:
        assert p["asset_class"] == "COMMODITY"
        assert p["strategy"] == "commodity_seasonal_planting_harvest"
        assert p["direction"] in ("LONG", "SHORT")
        assert p["take_profit"] != p["entry_price"]
        assert p["stop_loss"] != p["entry_price"]


# ---------- Per-crop allowlist (env COMMODITY_SEASONAL_CROPS) ----------

def test_enabled_crops_default_is_wheat_cotton(monkeypatch):
    monkeypatch.delenv("COMMODITY_SEASONAL_CROPS", raising=False)
    assert cs._get_enabled_crops() == {"WHEAT", "COTTON"}


def test_enabled_crops_all_is_full_set(monkeypatch):
    monkeypatch.setenv("COMMODITY_SEASONAL_CROPS", "ALL")
    assert cs._get_enabled_crops() == set(cs.CROP_TO_SYMBOL.keys())


def test_enabled_crops_singleton_wheat(monkeypatch):
    monkeypatch.setenv("COMMODITY_SEASONAL_CROPS", "WHEAT")
    assert cs._get_enabled_crops() == {"WHEAT"}
