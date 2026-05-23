"""Tests for SafetyEnforcer in swarms.core.safety."""

from __future__ import annotations

import pytest

from swarms.core.safety import DEFAULT_ALLOWED_TOOLS, SafetyEnforcer


class TestSafetyEnforcerDefaults:
    def test_default_tool_allowlist(self):
        enforcer = SafetyEnforcer()
        assert enforcer.allowed_tools == DEFAULT_ALLOWED_TOOLS

    def test_default_read_only(self):
        enforcer = SafetyEnforcer()
        assert enforcer.read_only is True

    def test_custom_tools(self):
        enforcer = SafetyEnforcer(allowed_tools={"custom_tool", "read"})
        assert "custom_tool" in enforcer.allowed_tools
        assert "read" in enforcer.allowed_tools

    def test_read_only_false(self):
        enforcer = SafetyEnforcer(read_only=False)
        assert enforcer.read_only is False


class TestCheckToolCall:
    def test_allows_read_tools(self):
        enforcer = SafetyEnforcer()
        for tool in ["read", "search", "grep", "find", "test", "pytest"]:
            allowed, reason = enforcer.check_tool_call(tool, {})
            assert allowed is True, f"Tool {tool} should be allowed, got: {reason}"

    def test_blocks_write_tools(self):
        enforcer = SafetyEnforcer()
        for tool in ["write", "edit", "rm", "mv", "git push", "git merge", "chmod"]:
            allowed, reason = enforcer.check_tool_call(tool, {})
            assert allowed is False, f"Tool {tool} should be blocked"
            assert "read-only" in reason.lower() or "blocked" in reason.lower()

    def test_blocks_unknown_tool(self):
        enforcer = SafetyEnforcer()
        allowed, reason = enforcer.check_tool_call("unknown_tool_xyz", {})
        assert allowed is False
        assert "not in the allowed tool set" in reason

    def test_allows_when_read_only_false(self):
        enforcer = SafetyEnforcer(read_only=False, allowed_tools={"write", "edit"})
        allowed, _ = enforcer.check_tool_call("write", {})
        assert allowed is True

    def test_prefix_blocking(self):
        enforcer = SafetyEnforcer()
        allowed, _ = enforcer.check_tool_call("git push origin main", {})
        assert allowed is False

    def test_python_m_pytest_allowed(self):
        enforcer = SafetyEnforcer()
        allowed, _ = enforcer.check_tool_call("python -m pytest", {})
        assert allowed is True


class TestCheckFileAccess:
    def test_allows_read(self):
        enforcer = SafetyEnforcer()
        allowed, _ = enforcer.check_file_access("/path/to/file", "read")
        assert allowed is True

    def test_blocks_write_in_read_only(self):
        enforcer = SafetyEnforcer()
        allowed, reason = enforcer.check_file_access("/tmp/file", "write")
        assert allowed is False
        assert "read-only" in reason.lower()

    def test_blocks_execute_in_read_only(self):
        enforcer = SafetyEnforcer()
        allowed, reason = enforcer.check_file_access("/tmp/script.sh", "execute")
        assert allowed is False
        assert "read-only" in reason.lower()

    def test_allows_write_when_not_read_only(self):
        enforcer = SafetyEnforcer(read_only=False)
        allowed, _ = enforcer.check_file_access("/tmp/file", "write")
        assert allowed is True

    def test_blocks_system_paths(self):
        enforcer = SafetyEnforcer(read_only=False)
        for path in ["/etc/passwd", "/usr/bin/python", "/bin/sh", "/dev/null"]:
            allowed, reason = enforcer.check_file_access(path, "read")
            assert allowed is False, f"Path {path} should be blocked"
            assert "system path" in reason.lower() or "forbidden" in reason.lower()

    def test_invalid_mode(self):
        enforcer = SafetyEnforcer()
        allowed, reason = enforcer.check_file_access("file", "invalid")
        assert allowed is False
        assert "Invalid access mode" in reason


class TestEnforceReadOnly:
    def test_allows_safe_code(self):
        enforcer = SafetyEnforcer()
        code = "\n".join([
            "def hello():",
            "    return 'world'",
            "",
            "x = 1 + 2",
            "data = [1, 2, 3]",
        ])
        safe, details = enforcer.enforce_read_only(code)
        assert safe is True
        assert details == ""

    def test_catches_open_write_mode(self):
        enforcer = SafetyEnforcer()
        for mode in ["w", "a", "x", "wb", "ab", "xb", "w+", "a+", "x+"]:
            code = f"with open('file.txt', '{mode}') as f: f.write('data')"
            safe, details = enforcer.enforce_read_only(code)
            assert safe is False, f"Mode '{mode}' should be caught"
            assert "open()" in details

    def test_allows_open_read_mode(self):
        enforcer = SafetyEnforcer()
        code = "with open('file.txt', 'r') as f: data = f.read()"
        safe, _ = enforcer.enforce_read_only(code)
        assert safe is True

    def test_allows_open_default_mode(self):
        enforcer = SafetyEnforcer()
        code = "with open('file.txt') as f: data = f.read()"
        safe, _ = enforcer.enforce_read_only(code)
        assert safe is True

    def test_catches_os_remove(self):
        enforcer = SafetyEnforcer()
        code = "import os\nos.remove('file.txt')"
        safe, details = enforcer.enforce_read_only(code)
        assert safe is False
        assert "os.remove" in details

    def test_catches_os_rename(self):
        enforcer = SafetyEnforcer()
        code = "import os\nos.rename('a', 'b')"
        safe, details = enforcer.enforce_read_only(code)
        assert safe is False
        assert "os.rename" in details

    def test_catches_os_chmod(self):
        enforcer = SafetyEnforcer()
        code = "import os\nos.chmod('file', 0o777)"
        safe, details = enforcer.enforce_read_only(code)
        assert safe is False
        assert "os.chmod" in details

    def test_catches_os_unlink(self):
        enforcer = SafetyEnforcer()
        code = "import os\nos.unlink('file.txt')"
        safe, details = enforcer.enforce_read_only(code)
        assert safe is False
        assert "os.unlink" in details

    def test_catches_os_rmdir(self):
        enforcer = SafetyEnforcer()
        code = "import os\nos.rmdir('dir')"
        safe, details = enforcer.enforce_read_only(code)
        assert safe is False
        assert "os.rmdir" in details

    def test_catches_os_mkdir(self):
        enforcer = SafetyEnforcer()
        code = "import os\nos.mkdir('newdir')"
        safe, details = enforcer.enforce_read_only(code)
        assert safe is False
        assert "os.mkdir" in details

    def test_catches_os_makedirs(self):
        enforcer = SafetyEnforcer()
        code = "import os\nos.makedirs('a/b/c')"
        safe, details = enforcer.enforce_read_only(code)
        assert safe is False
        assert "os.makedirs" in details

    def test_catches_subprocess_run(self):
        enforcer = SafetyEnforcer()
        code = "import subprocess\nsubprocess.run(['ls', '-la'])"
        safe, details = enforcer.enforce_read_only(code)
        assert safe is False
        assert "subprocess.run" in details

    def test_catches_subprocess_call(self):
        enforcer = SafetyEnforcer()
        code = "import subprocess\nsubprocess.call(['echo', 'hi'])"
        safe, details = enforcer.enforce_read_only(code)
        assert safe is False
        assert "subprocess.call" in details

    def test_catches_subprocess_popen(self):
        enforcer = SafetyEnforcer()
        code = "import subprocess\nsubprocess.Popen(['cat', 'file'])"
        safe, details = enforcer.enforce_read_only(code)
        assert safe is False
        assert "subprocess.Popen" in details

    def test_catches_subprocess_check_output(self):
        enforcer = SafetyEnforcer()
        code = "import subprocess\nsubprocess.check_output(['ls'])"
        safe, details = enforcer.enforce_read_only(code)
        assert safe is False
        assert "subprocess.check_output" in details

    def test_catches_subprocess_check_call(self):
        enforcer = SafetyEnforcer()
        code = "import subprocess\nsubprocess.check_call(['true'])"
        safe, details = enforcer.enforce_read_only(code)
        assert safe is False
        assert "subprocess.check_call" in details

    def test_catches_eval(self):
        enforcer = SafetyEnforcer()
        code = "eval('1 + 1')"
        safe, details = enforcer.enforce_read_only(code)
        assert safe is False
        assert "eval()" in details

    def test_catches_exec(self):
        enforcer = SafetyEnforcer()
        code = "exec('print(1)')"
        safe, details = enforcer.enforce_read_only(code)
        assert safe is False
        assert "exec()" in details

    def test_catches_compile(self):
        enforcer = SafetyEnforcer()
        code = "compile('pass', '', 'exec')"
        safe, details = enforcer.enforce_read_only(code)
        assert safe is False
        assert "compile()" in details

    def test_catches_shutil_rmtree(self):
        enforcer = SafetyEnforcer()
        code = "import shutil\nshutil.rmtree('dir')"
        safe, details = enforcer.enforce_read_only(code)
        assert safe is False
        assert "shutil.rmtree" in details

    def test_catches_shutil_move(self):
        enforcer = SafetyEnforcer()
        code = "import shutil\nshutil.move('a', 'b')"
        safe, details = enforcer.enforce_read_only(code)
        assert safe is False
        assert "shutil.move" in details

    def test_catches_os_system(self):
        enforcer = SafetyEnforcer()
        code = "import os\nos.system('ls')"
        safe, details = enforcer.enforce_read_only(code)
        assert safe is False
        assert "os.system" in details

    def test_catches_dangerous_name_reference(self):
        enforcer = SafetyEnforcer()
        code = "f = eval\nf('1')"
        safe, details = enforcer.enforce_read_only(code)
        assert safe is False
        assert "Dangerous name reference 'eval'" in details

    def test_syntax_error_handling(self):
        enforcer = SafetyEnforcer()
        code = "def broken(\n  pass"
        safe, details = enforcer.enforce_read_only(code)
        assert safe is False
        assert "Syntax error" in details

    def test_multiple_violations_reported(self):
        enforcer = SafetyEnforcer()
        code = "\n".join([
            "import os",
            "os.remove('a')",
            "eval('1')",
            "open('f', 'w')",
        ])
        safe, details = enforcer.enforce_read_only(code)
        assert safe is False
        lines = details.split("\n  - ")
        assert len(lines) >= 3  # multiple violations


class TestGetPolicy:
    def test_policy_structure(self):
        enforcer = SafetyEnforcer()
        policy = enforcer.get_policy()
        assert "read_only" in policy
        assert "allowed_tools" in policy
        assert "blocked_in_read_only" in policy
        assert "dangerous_open_modes" in policy

    def test_policy_values(self):
        enforcer = SafetyEnforcer(read_only=True)
        policy = enforcer.get_policy()
        assert policy["read_only"] is True
        assert "read" in policy["allowed_tools"]
        assert "write" in policy["blocked_in_read_only"]
        assert "w" in policy["dangerous_open_modes"]

    def test_policy_read_only_false(self):
        enforcer = SafetyEnforcer(read_only=False)
        policy = enforcer.get_policy()
        assert policy["read_only"] is False

    def test_allowed_tools_is_sorted_list(self):
        enforcer = SafetyEnforcer()
        policy = enforcer.get_policy()
        assert isinstance(policy["allowed_tools"], list)
        assert policy["allowed_tools"] == sorted(policy["allowed_tools"])
