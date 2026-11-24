import json
import os
from pathlib import Path
import subprocess
import shlex
import sys
import types

import pytest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/api/tmdb-ratings.php"
PHP = os.environ.get("PHP_BINARY", "php")


def validate(data):
    script = """
    require $argv[1];
    try {
        echo json_encode(validateTmdbRating(json_decode($argv[2], true), 278143));
    } catch (Exception $error) {
        echo json_encode(array('error' => $error->getMessage()));
    }
    """
    result = subprocess.run(
        [PHP, "-n", "-r", script, str(HELPER), json.dumps(data)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


@pytest.mark.parametrize("score,votes,provisional", [
    (10, 1, True), (8.6, 14, True), (8.2, 49, True), (8.2, 50, False), (0, 0, True),
])
def test_current_score_is_preserved_with_vote_confidence(score, votes, provisional):
    assert HELPER.exists(), "Missing existing-title rating refresh implementation"
    assert validate({"id": 278143, "vote_average": score, "vote_count": votes}) == {
        "rating": score, "vote_count": votes, "provisional": provisional,
    }


@pytest.mark.parametrize("data", [
    {"id": 123, "vote_average": 8.6, "vote_count": 14},
    {"id": 278143, "vote_average": 11, "vote_count": 14},
    {"id": 278143, "vote_average": 8.6},
    {"id": 278143, "vote_average": 8.6, "vote_count": -1},
    {"id": 278143, "vote_average": 8.6, "vote_count": 1.5},
    {"id": 278143, "vote_average": "8.6", "vote_count": 14},
])
def test_invalid_rating_or_identity_fails_without_inventing_score(data):
    assert HELPER.exists(), "Missing existing-title rating refresh implementation"
    assert "error" in validate(data)


def test_daily_refresh_calls_ratings_mode():
    source = (ROOT / "tools/run_movies_refresh.py").read_text()
    assert 'refresh_ratings(base, key)' in source
    assert '"mode": "ratings"' in source


def test_new_rating_candidates_match_playable_movie_feed():
    source = HELPER.read_text()
    assert "m.imdb_rating >= 10 AND EXISTS" in source
    assert "t.is_active = TRUE" in source
    assert "t.youtube_id IS NOT NULL" in source
    assert "OR r.movie_id IS NOT NULL" in source


@pytest.mark.parametrize("fail_metadata", [False, True])
def test_rating_and_metadata_are_committed_together(fail_metadata):
    script = """
    define('CURLOPT_RETURNTRANSFER', 1); define('CURLOPT_TIMEOUT', 2);
    define('CURLOPT_SSL_VERIFYPEER', 3); define('CURLINFO_HTTP_CODE', 4);
    function curl_init($url) { return true; }
    function curl_setopt($ch, $option, $value) {}
    function curl_exec($ch) { return '{"id":278143,"vote_average":8.65,"vote_count":14}'; }
    function curl_getinfo($ch, $option) { return 200; }
    function curl_close($ch) {}
    class Rows {
        function fetchAll() {
            return array(array('id'=>7833,'title'=>'Love You Teacher','type'=>'tv',
                'tmdb_id'=>278143,'imdb_rating'=>10));
        }
    }
    class Statement {
        public $db; public $sql;
        function __construct($db, $sql) { $this->db=$db; $this->sql=$sql; }
        function execute($args) {
            $this->db->writes[]=$args;
            if (strpos($this->sql, 'INSERT INTO movie_rating_details') !== false && $this->db->fail) {
                throw new Exception('Simulated metadata write failure');
            }
        }
    }
    class Database {
        public $events=array(); public $writes=array(); public $fail=false;
        function exec($sql) { $this->events[]='migration'; }
        function query($sql) { return new Rows(); }
        function prepare($sql) { return new Statement($this,$sql); }
        function beginTransaction() { $this->events[]='begin'; }
        function commit() { $this->events[]='commit'; }
        function rollBack() { $this->events[]='rollback'; }
    }
    require $argv[1];
    $db=new Database(); $db->fail=$argv[2]==='1';
    $result=refreshTmdbRatings($db, 'test-key');
    echo json_encode(array('result'=>$result, 'events'=>$db->events, 'writes'=>$db->writes));
    """
    process = subprocess.run(
        [PHP, "-n", "-r", script, str(HELPER), "1" if fail_metadata else "0"],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(process.stdout)
    assert data["events"] == ["migration", "begin", "rollback" if fail_metadata else "commit"]
    assert data["result"]["success"] is not fail_metadata
    assert data["result"]["errors"] == int(fail_metadata)
    assert data["writes"][0] == [8.7, 7833, 278143]
    if not fail_metadata:
        assert data["result"]["ratings"][0]["vote_count"] == 14
        assert data["result"]["ratings"][0]["provisional"] is True


@pytest.mark.parametrize("initialization_fails", [False, True])
def test_deploy_initializes_schema_before_any_dependent_api(monkeypatch, initialization_fails):
    import ftplib
    import yaml
    workflow = yaml.safe_load((ROOT / ".github/workflows/deploy-movieshows-all.yml").read_text())
    step = workflow["jobs"]["deploy"]["steps"][1]
    uploads = []

    class FTP:
        def __init__(self, host):
            pass

        def login(self, user, password):
            pass

        def prot_p(self):
            pass

        def cwd(self, directory):
            pass

        def storbinary(self, command, file):
            uploads.append(command.removeprefix("STOR "))

        def quit(self):
            pass

    helper = types.ModuleType("tools.run_movies_refresh")

    def request(url, timeout):
        assert uploads == ["tmdb-ratings.php", "fetch_new_content.php"]
        if initialization_fails:
            raise RuntimeError("Initialization failed")
        return {"success": True, "errors": 0}

    helper.request_json = request
    helper.successful_object = lambda data, label: data
    helper.count = lambda data, key: data[key]
    monkeypatch.setitem(sys.modules, "tools.run_movies_refresh", helper)
    monkeypatch.setattr(ftplib, "FTP_TLS", FTP)
    for name in ("FTP_HOST", "FTP_USER", "FTP_PASS", "MS2_SYNC_KEY"):
        monkeypatch.setenv(name, "test-value")
    monkeypatch.chdir(ROOT)
    code = compile(shlex.split(step["run"])[2], "<deploy>", "exec")
    if initialization_fails:
        with pytest.raises(RuntimeError, match="Initialization failed"):
            exec(code, {})
        assert uploads == ["tmdb-ratings.php", "fetch_new_content.php"]
    else:
        exec(code, {})
        assert "get-movies.php" in uploads[2:]
