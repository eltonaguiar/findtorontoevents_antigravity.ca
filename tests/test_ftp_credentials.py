import ast
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import MagicMock

import pytest

from tools import ftp_credentials as credentials


def test_reads_only_value_immediately_after_requested_label(tmp_path):
    path = tmp_path/"credentials.txt"
    path.write_text("unrelated label\nunrelated value\n50WEBS_FTP pass\nfixture-ftp-secret\nother label\nother value\n")
    assert credentials.read_local_password(path) == "fixture-ftp-secret"


@pytest.mark.parametrize("text", ["different label\nvalue\n", "50WEBS_FTP pass\n", "50WEBS_FTP pass\n\n"])
def test_missing_or_empty_label_fails_without_secret_output(tmp_path, text):
    path = tmp_path/"credentials.txt"
    path.write_text(text)
    with pytest.raises(ValueError):
        credentials.read_local_password(path)


def test_local_file_defaults_to_correct_account_and_hides_password_repr(tmp_path):
    path = tmp_path/"credentials.txt"
    path.write_text("50WEBS_FTP pass\nfixture-ftp-secret\n")
    result = credentials.get_ftp_credentials({}, path)
    assert (result.host, result.user, result.password) == (
        "ftps2.50webs.com", "ejaguiar1", "fixture-ftp-secret")
    assert "fixture-ftp-secret" not in repr(result)


def test_explicit_environment_preserved_for_separate_account(tmp_path):
    result = credentials.get_ftp_credentials(
        {"FTP_SERVER": "separate.example", "FTP_USER": "other-user", "FTP_PASS": "runtime-secret"},
        tmp_path/"not-present",
    )
    assert (result.host, result.user, result.password) == ("separate.example", "other-user", "runtime-secret")


def test_rotated_local_value_supersedes_stale_50webs_environment(tmp_path):
    path = tmp_path/"credentials.txt"
    path.write_text("50WEBS_FTP pass\nrotated-fixture-secret\n")
    result = credentials.get_ftp_credentials(
        {"FTP_USER": "ejaguiar1", "FTP_PASS": "stale-fixture-secret"}, path)
    assert result.password == "rotated-fixture-secret"


def test_ci_environment_works_without_local_file(tmp_path):
    result = credentials.get_ftp_credentials(
        {"FTP_USER": "ejaguiar1", "FTP_PASS": "runtime-secret"}, tmp_path/"absent")
    assert result.password == "runtime-secret"


def test_conflicting_host_aliases_fail_before_loading_password(tmp_path):
    with pytest.raises(ValueError, match="disagree"):
        credentials.get_ftp_credentials(
            {"FTP_HOST": "separate.example", "FTP_SERVER": credentials.HOST, "FTP_PASS": "runtime-secret"},
            tmp_path/"unused")


@pytest.mark.parametrize("env", [
    {"FTP_HOST": "separate.example"},
    {"FTP_USER": "other-user"},
])
def test_never_send_local_50webs_password_to_another_account(tmp_path, env):
    path = tmp_path/"credentials.txt"
    path.write_text("50WEBS_FTP pass\nfixture-ftp-secret\n")
    with pytest.raises(ValueError, match="non-default account"):
        credentials.get_ftp_credentials(env, path)


def test_ftp_specific_aliases_not_os_login_or_generic_password(tmp_path):
    path = tmp_path/"credentials.txt"
    path.write_text("50WEBS_FTP pass\nfixture-ftp-secret\n")
    result = credentials.get_ftp_credentials({"USER": "linux-user", "PASSWORD": "unrelated"}, path)
    assert result.user == "ejaguiar1"
    assert result.password == "fixture-ftp-secret"
    result = credentials.get_ftp_credentials({"FTP_USERNAME": "explicit", "FTP_PASSWORD": "runtime-secret"}, path)
    assert result.user == "explicit" and result.password == "runtime-secret"


def test_control_characters_rejected(tmp_path):
    with pytest.raises(ValueError, match="control character"):
        credentials.get_ftp_credentials({"FTP_PASS": "value\ninjected"}, tmp_path/"unused")


def test_check_uses_tls_protected_data_and_never_uploads(monkeypatch, capsys):
    monkeypatch.setattr(credentials, "load_ftp_environment",
                        lambda: credentials.FTPCredentials(credentials.HOST, credentials.USER, "fixture-ftp-secret"))
    ftp = MagicMock()
    factory = MagicMock()
    factory.return_value.__enter__.return_value = ftp
    monkeypatch.setattr(credentials, "FTP_TLS", factory)
    monkeypatch.setattr(sys, "argv", ["ftp_credentials.py", "--check"])
    assert credentials.main() == 0
    ftp.login.assert_called_once_with("ejaguiar1", "fixture-ftp-secret")
    ftp.prot_p.assert_called_once()
    ftp.cwd.assert_called_once_with("/findtorontoevents.ca")
    ftp.storbinary.assert_not_called()
    assert factory.call_args.kwargs["context"].check_hostname
    assert "fixture-ftp-secret" not in capsys.readouterr().out


def test_check_failure_is_nonzero_and_does_not_echo_server_message(monkeypatch, capsys):
    monkeypatch.setattr(credentials, "load_ftp_environment",
                        lambda: credentials.FTPCredentials(credentials.HOST, credentials.USER, "fixture-ftp-secret"))
    monkeypatch.setattr(credentials, "FTP_TLS", MagicMock(side_effect=OSError("fixture-ftp-secret")))
    monkeypatch.setattr(sys, "argv", ["ftp_credentials.py", "--check"])
    assert credentials.main() == 2
    assert "fixture-ftp-secret" not in capsys.readouterr().err


def test_wrapper_direct_invocation_passes_secret_in_environment_not_arguments(tmp_path):
    path = tmp_path/"credentials.txt"
    path.write_text("50WEBS_FTP pass\nfixture-ftp-secret\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith("FTP_")}
    env["FTP_CREDENTIAL_FILE"] = str(path)
    script = Path(credentials.__file__)
    result = subprocess.run(
        [sys.executable, str(script), "--", sys.executable, "-c",
         "import os; assert os.environ['FTP_USER']=='ejaguiar1'; "
         "assert os.environ['FTP_PASS']=='fixture-ftp-secret'; print('child verified')"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "child verified"
    assert "fixture-ftp-secret" not in result.stdout + result.stderr


def test_supplements_has_no_literal_password_default():
    tree = ast.parse((Path(credentials.__file__).parent/"deploy_supplements.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"get", "getenv"}:
            if len(node.args) > 1 and isinstance(node.args[0], ast.Constant) and node.args[0].value == "FTP_PASS":
                assert not isinstance(node.args[1], ast.Constant) or not node.args[1].value


def test_sports_wrapper_uses_tls_and_canonical_loader():
    text = (Path(credentials.__file__).parent/"deploy_sports_files.sh").read_text()
    assert 'exec python3 tools/ftp_credentials.py -- bash "$0" "$@"' in text
    assert "curl --config - --ssl-reqd" in text
    assert '--user "$FTP_USER:$FTP_PASS"' not in text
    assert "windows_env_backup" not in text


def test_shared_connection_verifies_tls_and_protects_data(monkeypatch):
    monkeypatch.setattr(credentials, "get_ftp_credentials",
                        lambda: credentials.FTPCredentials(credentials.HOST, credentials.USER, "fixture-secret"))
    ftp = MagicMock()
    factory = MagicMock(return_value=ftp)
    monkeypatch.setattr(credentials, "FTP_TLS", factory)
    assert credentials.connect_ftp() is ftp
    ftp.connect.assert_called_once_with(credentials.HOST, 21)
    ftp.login.assert_called_once_with(credentials.USER, "fixture-secret")
    ftp.prot_p.assert_called_once()
    assert factory.call_args.kwargs["context"].check_hostname


def test_shared_connection_closes_failed_login(monkeypatch):
    monkeypatch.setattr(credentials, "get_ftp_credentials",
                        lambda: credentials.FTPCredentials(credentials.HOST, credentials.USER, "fixture-secret"))
    ftp = MagicMock()
    ftp.login.side_effect = OSError("connection failed")
    monkeypatch.setattr(credentials, "FTP_TLS", MagicMock(return_value=ftp))
    with pytest.raises(OSError):
        credentials.connect_ftp()
    ftp.close.assert_called_once()
    ftp.prot_p.assert_not_called()


def test_tracked_deployers_do_not_restore_ftp_password_literal_defaults():
    root = Path(credentials.__file__).resolve().parents[1]
    listed = subprocess.run(
        ["git", "ls-files", "*.py"], cwd=root, check=True, capture_output=True, text=True)
    for name in listed.stdout.splitlines():
        if "deploy" not in name.lower():
            continue
        path = root/name
        if not path.is_file():
            continue
        source = path.read_text(encoding="utf-8")
        if "FTP" not in source:
            continue
        tree = ast.parse(source, filename=name)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in {"get", "getenv"} or len(node.args) < 2:
                continue
            key, default = node.args[:2]
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                continue
            if "FTP" in key.value.upper() and any(word in key.value.upper() for word in ["PASS", "PWD"]):
                assert not isinstance(default, ast.Constant) or not default.value, (
                    f"{name}:{node.lineno}: nonempty FTP password literal default")
