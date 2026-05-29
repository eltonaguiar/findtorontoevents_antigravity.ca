import json

import tools.ai_tournament.build_model_diagnostics as diagnostics
import tools.populate_picks as populate_picks


def test_build_prompt_tasks_and_collect_api_picks_are_deterministic(monkeypatch):
    models = {
        "beta": {
            "api_key_env": "BETA_KEY",
            "assignments": {"CRYPTO": ["p2", "p1"]},
        },
        "alpha": {
            "api_key_env": "ALPHA_KEY",
            "assignments": {"EQUITY": ["p1"]},
        },
    }
    universe = {"CRYPTO": ["BTCUSDT"], "EQUITY": ["AAPL"]}
    tasks = populate_picks.build_prompt_tasks(models, universe)

    monkeypatch.setattr(populate_picks, "MAX_WORKERS", 4)
    monkeypatch.setattr(populate_picks, "MAX_WORKERS_PER_KEY", 1)

    def fake_try_prompt_model(model_id, model_cfg, asset_class, ac_universe, persona_id=""):
        return [{"model_id": model_id, "persona_id": persona_id, "asset_class": asset_class}], "api_success"

    monkeypatch.setattr(populate_picks, "try_prompt_model", fake_try_prompt_model)
    picks, model_status_counts, coverage_fallback_count = populate_picks.collect_api_and_coverage_picks(tasks, {})

    assert model_status_counts["api_success"] == 3
    assert coverage_fallback_count == 0
    assert [(pick["model_id"], pick["persona_id"]) for pick in picks] == [
        ("beta", "p2"),
        ("beta", "p1"),
        ("alpha", "p1"),
    ]


def test_build_model_diagnostics_classifies_models(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    (repo / "config").mkdir(parents=True)
    (repo / "data" / "ai_tournament" / "submissions").mkdir(parents=True)
    (repo / "audit_dashboard" / "data").mkdir(parents=True)

    config = {
        "models": {
            "active_model": {
                "provider": "X",
                "api_key_env": "ACTIVE_KEY",
                "model_name": "x-1",
                "assignments": {"CRYPTO": ["p1", "p2"]},
            },
            "missing_key_model": {
                "provider": "Y",
                "api_key_env": "MISSING_KEY",
                "model_name": "y-1",
                "assignments": {"EQUITY": ["p1"]},
            },
            "no_pick_model": {
                "provider": "Z",
                "api_key_env": "NO_PICK_KEY",
                "model_name": "z-1",
                "assignments": {"ETF": ["p1"]},
            },
        }
    }
    (repo / "config" / "model_persona_mapping.json").write_text(json.dumps(config))
    (repo / "audit_dashboard" / "data" / "ai_tournament_model_summary.json").write_text(
        json.dumps(
            {
                "models": [
                    {"model_id": "active_model", "total_picks": 4, "resolved": 1, "last_pick": "2026-05-28T00:00:00+00:00"},
                    {"model_id": "missing_key_model", "total_picks": 2, "resolved": 1, "last_pick": "2026-05-27T00:00:00+00:00"},
                ]
            }
        )
    )
    today = diagnostics._today_str()
    (repo / "data" / "ai_tournament" / "submissions" / f"active_model_{today}.json").write_text(
        json.dumps(
            {
                "model_id": "active_model",
                "status": "OPEN",
                "submitted_at": "2026-05-28T01:00:00+00:00",
                "picks": [{"symbol": "BTCUSDT"}],
            }
        )
    )
    (repo / "data" / "ai_tournament" / "submissions" / f"no_pick_model_{today}.json").write_text(
        json.dumps(
            {
                "model_id": "no_pick_model",
                "status": "no_picks_generated",
                "submitted_at": "2026-05-28T01:05:00+00:00",
                "reason": "API call failed",
                "picks": [],
            }
        )
    )

    monkeypatch.setattr(diagnostics, "REPO", repo)
    monkeypatch.setattr(diagnostics, "CONFIG", repo / "config" / "model_persona_mapping.json")
    monkeypatch.setattr(diagnostics, "SUBMISSIONS", repo / "data" / "ai_tournament" / "submissions")
    monkeypatch.setattr(diagnostics, "MODEL_SUMMARY", repo / "audit_dashboard" / "data" / "ai_tournament_model_summary.json")
    monkeypatch.setattr(diagnostics, "OUT", repo / "audit_dashboard" / "data" / "ai_tournament_model_diagnostics.json")
    monkeypatch.setenv("ACTIVE_KEY", "x")
    monkeypatch.setenv("NO_PICK_KEY", "z")

    built = diagnostics.build()
    by_model = {model["model_id"]: model for model in built["models"]}

    assert built["counts"]["configured_total"] == 3
    assert built["counts"]["active_today"] == 1
    assert built["counts"]["configured_no_picks"] == 1
    assert built["counts"]["blocked_missing_key"] == 0
    assert built["counts"]["historical_only"] == 1
    assert by_model["active_model"]["status"] == "active_today"
    assert by_model["no_pick_model"]["status"] == "configured_no_picks"
    assert by_model["missing_key_model"]["status"] == "historical_only"
