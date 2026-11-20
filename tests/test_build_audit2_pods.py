import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_projection_shape(tmp_path):
    manifest = {"pods": [
        {"id": "POD-A", "status": "observe", "hypothesis_id": "H-1",
         "asset_classes": ["CRYPTO", "EQUITY"], "directions": ["LONG"],
         "strategies": ["s1", "s2"], "thesis": "t",
         "acceptance_criteria": "n>=100"},
        {"id": "POD-B", "status": "declined", "strategies": []},
    ]}
    src = tmp_path / "m.json"
    src.write_text(json.dumps(manifest))
    out = tmp_path / "pods.json"
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "build_audit2_pods.py"),
                        "--manifest", str(src), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    d = json.loads(out.read_text())
    assert d["n_pods"] == 2
    a = d["pods"][0]
    assert a["id"] == "POD-A" and a["hypothesis"] == "H-1"
    assert a["klass"] == "CRYPTO / EQUITY" and a["dir"] == "LONG"
    assert a["strategies"] == ["s1", "s2"] and a["gate"] == "n>=100"
    b = d["pods"][1]
    assert b["klass"] == "" and b["strategies"] == []
