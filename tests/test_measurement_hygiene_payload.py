def test_measurement_hygiene_payload_shape(monkeypatch):
    """With MEASUREMENT_HYGIENE_V1=1 and fresh data, emit the full block.

    Task 11 added a DB freshness gate to the ``measurement_hygiene`` payload
    block. When the underlying sources are stale it correctly forces
    ``enabled=false`` plus a ``freshness_warning``. This test pins the SHAPE
    for the fresh-data case, so it forces the freshness gate healthy to keep
    the assertions deterministic regardless of live data age.
    """
    import importlib
    import os

    os.environ["MEASUREMENT_HYGIENE_V1"] = "1"
    import audit_trail.dashboard_generator as dg
    dg = importlib.reload(dg)  # re-evaluate the module-level flag constant
    # Force the DB freshness gate to report fresh data (deterministic).
    monkeypatch.setattr(dg, "_check_data_freshness", lambda *a, **k: (True, ""))
    payload = dg.generate()
    assert "measurement_hygiene" in payload
    mh = payload["measurement_hygiene"]
    assert mh["enabled"] is True
    assert "banner_text" in mh
    assert mh["banner_text"] == "Measurement ≠ permission — only ledgers passing n≥100, PF≥1.5, CI-LB≥1.2, MDD≤20% are shown."
    assert "excluded_ledgers" in mh
    assert "gate_definitions" in mh
