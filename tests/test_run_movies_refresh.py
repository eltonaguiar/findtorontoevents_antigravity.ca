import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "tools/run_movies_refresh.py"
spec = importlib.util.spec_from_file_location("run_movies_refresh", SCRIPT)
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)


def status(total=100):
    return {"success": True, "total_records": total}


def response(added=2, skipped=1):
    return {
        "success": True,
        "summary": {
            "movies_added": added, "tv_added": 0, "skipped": skipped,
            "errors": 0, "fetched_from_tmdb": added + skipped,
        },
        "log_entry": {
            "timestamp": "2026-10-12 07:00:00", "status": "success",
            "movies_added": added, "tv_added": 0, "skipped": skipped, "errors": 0,
        },
    }


def mock_host(monkeypatch, result=None, after=None, log=None):
    result = result if result is not None else response()
    replies = iter([
        status(), result, after if after is not None else status(102),
        log if log is not None else [result["log_entry"]],
    ])
    calls = []

    def request(url, timeout):
        calls.append(url)
        return next(replies)

    monkeypatch.setattr(refresh, "request_json", request)
    return calls


def test_valid_refresh_checks_counts_and_persisted_log(monkeypatch):
    calls = mock_host(monkeypatch)
    assert refresh.refresh_host("https://example.test", "secret", "both", 3, "trending") == {
        "total_records": 102, "added": 2, "skipped": 1, "fetched": 3,
    }
    assert "type=both" in calls[1] and "pages=3" in calls[1]
    assert "/MOVIESHOWS3/fetch_new_content.php" in calls[1]
    assert "/log/pull_log.json" in calls[3]


def test_duplicates_only_is_a_valid_refresh(monkeypatch):
    mock_host(monkeypatch, response(added=0, skipped=3), status())
    assert refresh.refresh_host("https://example.test", "secret", "both", 3, "trending")["added"] == 0


@pytest.mark.parametrize("result", [
    {"success": False, "error": "Database connection failed"},
    {"success": False, "error": "Unauthorized"},
    {"success": True, "summary": {"errors": 6, "fetched_from_tmdb": 0}},
    {"success": True, "summary": {"errors": 0, "fetched_from_tmdb": 0}},
])
def test_failed_or_empty_refresh_is_not_success(monkeypatch, result):
    monkeypatch.setattr(refresh, "request_json", lambda url, timeout: result if "fetch_new" in url else status())
    with pytest.raises(refresh.RefreshError):
        refresh.refresh_host("https://example.test", "secret", "both", 3, "trending")


def test_row_count_mismatch_fails(monkeypatch):
    mock_host(monkeypatch, after=status(100))
    with pytest.raises(refresh.RefreshError, match="row count"):
        refresh.refresh_host("https://example.test", "secret", "both", 3, "trending")


def test_missing_or_stale_log_fails(monkeypatch):
    mock_host(monkeypatch, log=[{"timestamp": "old", "status": "success"}])
    with pytest.raises(refresh.RefreshError, match="persisted log"):
        refresh.refresh_host("https://example.test", "secret", "both", 3, "trending")


def test_missing_sync_key_is_an_error(monkeypatch, capsys):
    monkeypatch.delenv("MS2_SYNC_KEY", raising=False)
    assert refresh.main([]) == 1
    assert "MS2_SYNC_KEY" in capsys.readouterr().err


@pytest.mark.parametrize("failure", [
    refresh.urllib.error.HTTPError("https://example.test/?key=secret", 403, "secret", {}, None),
    refresh.urllib.error.URLError("https://example.test/?key=secret"),
    ValueError("secret"),
    TimeoutError("secret"),
])
def test_transport_errors_do_not_disclose_authentication_url(monkeypatch, failure):
    def open_url(*args, **kwargs):
        raise failure

    monkeypatch.setattr(refresh.urllib.request, "urlopen", open_url)
    with pytest.raises(refresh.RefreshError) as error:
        refresh.request_json("https://example.test/?key=secret", 10)
    assert "secret" not in str(error.value)


def test_old_status_schema_is_rejected(monkeypatch):
    monkeypatch.setattr(refresh, "request_json", lambda url, timeout: {
        "success": True, "stats": {"total_titles": 100},
    })
    with pytest.raises(refresh.RefreshError, match="total_records"):
        refresh.refresh_host("https://example.test", "secret", "both", 3, "trending")


def test_both_database_hosts_run_even_when_one_fails(monkeypatch, capsys):
    monkeypatch.setenv("MS2_SYNC_KEY", "secret-value")
    calls = []

    def run(base, key, kind, pages, mode):
        calls.append(base)
        if len(calls) == 1:
            raise refresh.RefreshError("Database unavailable")
        return {"added": 0, "skipped": 20, "fetched": 20, "total_records": 100}

    monkeypatch.setattr(refresh, "refresh_host", run)
    assert refresh.main([]) == 1
    assert calls == ["https://findtorontoevents.ca", "https://torontoevent.net"]
    captured = capsys.readouterr()
    assert "secret-value" not in captured.out + captured.err


def test_only_one_daily_movie_database_schedule_remains():
    root = SCRIPT.parents[1]
    import yaml
    scheduled = []
    for name in ("fetch-movies-v3.yml", "fetch-movies.yml", "kimi-fetch-movies.yml"):
        document = yaml.safe_load((root / ".github/workflows" / name).read_text())
        triggers = document.get("on", document.get(True, {}))
        if triggers.get("schedule"):
            scheduled.append(name)
        text = (root / ".github/workflows" / name).read_text()
        assert "tools/run_movies_refresh.py" in text
        assert "deploy_movieshows" not in text
    assert scheduled == ["fetch-movies-v3.yml"]
