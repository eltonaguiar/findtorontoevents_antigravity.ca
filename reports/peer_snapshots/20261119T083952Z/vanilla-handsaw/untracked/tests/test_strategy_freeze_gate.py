import json

from tools.strategy_freeze_gate import main


def _write_manifest(tmp_path, frozen):
    path = tmp_path / "freeze.json"
    path.write_text(json.dumps({
        "frozen": frozen,
        "rule": "no new strategy may be generated while a P0 item is open",
        "p0": ["E11", "E13", "E14"],
        "p0_detail": {"E11": "backfill fx"},
    }))
    return path


def test_frozen_manifest_blocks(tmp_path, capsys):
    manifest = _write_manifest(tmp_path, True)
    assert main(["--manifest", str(manifest)]) == 1
    err = capsys.readouterr().err
    assert "E11" in err and "FROZEN" in err


def test_unfrozen_manifest_passes(tmp_path, capsys):
    manifest = _write_manifest(tmp_path, False)
    assert main(["--manifest", str(manifest)]) == 0
    assert "not frozen" in capsys.readouterr().out


def test_missing_manifest_errors(tmp_path):
    assert main(["--manifest", str(tmp_path / "nope.json")]) == 2


def test_json_output_reports_state(tmp_path, capsys):
    manifest = _write_manifest(tmp_path, True)
    assert main(["--manifest", str(manifest), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["frozen"] is True
    assert payload["p0"] == ["E11", "E13", "E14"]
