def test_measurement_hygiene_payload_shape():
    import os
    os.environ["MEASUREMENT_HYGIENE_V1"] = "1"
    from audit_trail.dashboard_generator import generate
    payload = generate()
    assert "measurement_hygiene" in payload
    mh = payload["measurement_hygiene"]
    assert mh["enabled"] is True
    assert "banner_text" in mh
    assert mh["banner_text"] == "Measurement ≠ permission — only ledgers passing n≥100, PF≥1.5, CI-LB≥1.2, MDD≤20% are shown."
    assert "excluded_ledgers" in mh
    assert "gate_definitions" in mh
