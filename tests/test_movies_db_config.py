import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
PHP = os.environ.get("PHP_BINARY") or shutil.which("php")
VERSIONS = ("MOVIESHOWS2", "MOVIESHOWS3")


@pytest.fixture(params=VERSIONS)
def config_path(request, tmp_path):
    target = tmp_path / "example.test" / request.param / "api" / "db-config.php"
    target.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "TORONTOEVENTS_ANTIGRAVITY" / request.param / "api" / "db-config.php", target)
    return target


def run_config(path, credentials=None, env=None, reject=False, protected=False):
    assert PHP, "PHP CLI is required; set PHP_BINARY if it is not on PATH"
    if credentials is not None:
        private = path.parents[3] / "movies-db-private.php"
        if protected:
            private = path.parents[2] / ".movies-db-private" / "credentials.php"
            private.parent.mkdir()
            (private.parent / ".htaccess").write_text("Deny from all\n")
        private.write_text("<?php return " + credentials + ";")
    script = """
    class PDO {
        const ATTR_ERRMODE = 3;
        const ERRMODE_EXCEPTION = 2;
        const ATTR_DEFAULT_FETCH_MODE = 19;
        const FETCH_ASSOC = 2;
        public $arguments;
        function __construct($dsn, $username, $password) {
            if (getenv('TEST_REJECT')) {
                throw new PDOException('Do not disclose supplied-secret', 1045);
            }
            $this->arguments = array($dsn, $username, $password);
        }
        function setAttribute($key, $value) {}
    }
    class PDOException extends Exception {}
    require $argv[1];
    $connection = getDbConnection();
    echo json_encode($connection === null ? null : $connection->arguments);
    """
    process_env = {
        key: value for key, value in os.environ.items()
        if not key.startswith("EJAGUIAR1_TVMOVIESTRAILERS_")
    }
    process_env.update(env or {})
    if reject:
        process_env["TEST_REJECT"] = "1"
    result = subprocess.run(
        [PHP, "-n", "-r", script, str(path)],
        env=process_env, capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout), result.stderr


def test_private_credentials_are_used(config_path):
    result, errors = run_config(
        config_path, "array('username' => 'site-user', 'password' => 'supplied-secret')"
    )
    assert result == [
        "mysql:host=localhost;dbname=ejaguiar1_tvmoviestrailers;charset=utf8mb4",
        "site-user", "supplied-secret",
    ]
    assert errors == ""


def test_environment_takes_priority(config_path):
    result, errors = run_config(
        config_path,
        "array('username' => 'file-user', 'password' => 'file-secret')",
        {
            "EJAGUIAR1_TVMOVIESTRAILERS_USER": "env-user",
            "EJAGUIAR1_TVMOVIESTRAILERS_PASS": "env-secret",
        },
    )
    assert result[1:] == ["env-user", "env-secret"]
    assert errors == ""


def test_protected_site_credentials_are_used_when_parent_is_unavailable(config_path):
    result, errors = run_config(
        config_path,
        "array('username' => 'site-user', 'password' => 'supplied-secret')",
        protected=True,
    )
    assert result[1:] == ["site-user", "supplied-secret"]
    assert errors == ""


def test_missing_configuration_fails_explicitly(config_path):
    result, errors = run_config(config_path)
    assert result is None
    assert "Movies DB credentials are not configured" in errors


@pytest.mark.parametrize("credentials", [
    "array('username' => 'site-user')",
    "array('username' => 'site-user', 'password' => '')",
    "array('username' => 'site-user', 'password' => 123)",
    "'not-an-array'",
])
def test_invalid_private_configuration_is_rejected(config_path, credentials):
    result, errors = run_config(config_path, credentials)
    assert result is None
    assert "Movies DB private configuration is invalid" in errors


def test_partial_environment_is_not_silently_ignored(config_path):
    result, errors = run_config(
        config_path,
        "array('username' => 'site-user', 'password' => 'supplied-secret')",
        {"EJAGUIAR1_TVMOVIESTRAILERS_USER": "env-user"},
    )
    assert result is None
    assert "Movies DB environment credentials are incomplete" in errors


def test_connection_failure_does_not_log_password(config_path):
    result, errors = run_config(
        config_path,
        "array('username' => 'site-user', 'password' => 'supplied-secret')",
        reject=True,
    )
    assert result is None
    assert "1045" in errors
    assert "supplied-secret" not in errors


def run_tmdb_config(path, credentials=None, env=None):
    if credentials is not None:
        (path.parents[3] / "movies-db-private.php").write_text(
            "<?php return " + credentials + ";"
        )
    process_env = {
        key: value for key, value in os.environ.items()
        if key != "TMDB_API_KEY"
    }
    process_env.update(env or {})
    result = subprocess.run(
        [PHP, "-n", "-r",
         "require $argv[1]; echo json_encode(getMoviesTmdbApiKey());", str(path)],
        env=process_env, capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout), result.stderr


def test_tmdb_environment_key_takes_priority(config_path):
    result, errors = run_tmdb_config(
        config_path,
        "array('tmdb_api_key' => 'private-key')",
        {"TMDB_API_KEY": "env-key"},
    )
    assert result == "env-key"
    assert errors == ""


def test_tmdb_private_key_is_used(config_path):
    result, errors = run_tmdb_config(
        config_path, "array('tmdb_api_key' => 'private-key')"
    )
    assert result == "private-key"
    assert errors == ""


def test_missing_tmdb_key_fails_explicitly(config_path):
    result, errors = run_tmdb_config(config_path)
    assert result is None
    assert "Movies TMDB API key is not configured" in errors


def test_refresh_log_works_without_json_pretty_print(tmp_path):
    source = (ROOT / "TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/fetch_new_content.php").read_text()
    log_code = source.split("$existingLog[] = $logEntry;", 1)[1].split("// ---- Output ----", 1)[0]
    log_file = tmp_path / "pull_log.json"
    script = r"""
    namespace LegacyJson;
    function defined($name) { return false; }
    function json_encode($value) {
        if (func_num_args() !== 1) {
            throw new \Exception('Legacy json_encode accepts exactly one argument');
        }
        return \json_encode($value);
    }
    $logFile = $argv[1];
    $existingLog = array(array('status' => 'success', 'movies_added' => 2));
    $summary = array('errors' => 0);
    $logEntry = array('status' => 'success', 'errors' => 0);
    """ + log_code
    subprocess.run(
        [PHP, "-n", "-r", script, str(log_file)],
        capture_output=True, text=True, check=True,
    )
    assert json.loads(log_file.read_text()) == [{"status": "success", "movies_added": 2}]
