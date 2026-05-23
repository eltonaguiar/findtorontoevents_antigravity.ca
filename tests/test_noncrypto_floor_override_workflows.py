from pathlib import Path


REPO = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def test_noncrypto_floor_overrides_are_wired():
    bond = _read(".github/workflows/bond-agent.yml")
    etf = _read(".github/workflows/etf-agent.yml")
    fut = _read(".github/workflows/futures-agent.yml")

    assert "BOND_ELITE_FLOOR" in bond
    assert "ETF_ELITE_FLOOR" in etf
    assert "FUTURES_ELITE_FLOOR" in fut
    assert ">= _elite_floor" in bond
    assert ">= _elite_floor" in etf
    assert ">= _elite_floor" in fut


def test_crypto_workflows_do_not_use_noncrypto_floor_envs():
    wf_dir = REPO / ".github" / "workflows"
    env_keys = ("BOND_ELITE_FLOOR", "ETF_ELITE_FLOOR", "FUTURES_ELITE_FLOOR")
    for wf in wf_dir.glob("*crypto*.yml"):
        txt = wf.read_text(encoding="utf-8")
        for key in env_keys:
            assert key not in txt, f"{key} leaked into crypto workflow {wf.name}"

