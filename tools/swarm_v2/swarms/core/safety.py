"""Safety enforcement layer for the multi-agent swarm system.

Provides fine-grained access control, tool allowlisting, AST-based static
analysis of Python code, and a configurable read-only mode that is enabled by
default.
"""

from __future__ import annotations

import ast
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default policy constants
# ---------------------------------------------------------------------------

DEFAULT_ALLOWED_TOOLS: set[str] = {
    "read",
    "search",
    "grep",
    "find",
    "test",
    "pytest",
    "python -m pytest",
}

# Tools that are *always* blocked when read_only=True.
DEFAULT_BLOCKED_IN_READONLY: set[str] = {
    "write",
    "edit",
    "rm",
    "mv",
    "git push",
    "git merge",
    "chmod",
    "execute",
    "shell",
}

# Dangerous file-write modes for ``open()``.
_DANGEROUS_OPEN_MODES: set[str] = {"w", "a", "x", "wb", "ab", "xb", "w+", "a+", "x+"}

# ---------------------------------------------------------------------------
# AST visitor – detects dangerous Python idioms
# ---------------------------------------------------------------------------


class _DangerousPatternVisitor(ast.NodeVisitor):
    """AST visitor that flags file writes, subprocess calls, code execution."""

    def __init__(self) -> None:
        self.violations: list[str] = []

    # -- open() with write mode ---------------------------------------------

    def visit_Call(self, node: ast.Call) -> None:  # noqa: D102
        self._check_open_call(node)
        self._check_os_calls(node)
        self._check_shutil_calls(node)
        self._check_subprocess_calls(node)
        self._check_code_execution(node)
        self.generic_visit(node)

    def _check_open_call(self, node: ast.Call) -> None:
        """Detect ``open(..., mode='<write-mode>')``."""
        func = node.func
        if not isinstance(func, ast.Name) or func.id != "open":
            return
        if len(node.args) < 2:
            # open(path) defaults to 'r' — safe
            return
        mode_arg = node.args[1]
        if isinstance(mode_arg, ast.Constant) and isinstance(mode_arg.value, str):
            if mode_arg.value in _DANGEROUS_OPEN_MODES:
                self.violations.append(
                    f"open() with write mode '{mode_arg.value}' detected (line {node.lineno})"
                )
        elif isinstance(mode_arg, ast.Str):  # Python < 3.8 compat
            if mode_arg.s in _DANGEROUS_OPEN_MODES:
                self.violations.append(
                    f"open() with write mode '{mode_arg.s}' detected (line {node.lineno})"
                )

    # -- os.* dangerous calls -----------------------------------------------

    def _check_os_calls(self, node: ast.Call) -> None:
        """Detect ``os.remove``, ``os.rename``, ``os.chmod``, etc."""
        func = node.func
        if not isinstance(func, ast.Attribute):
            return
        if isinstance(func.value, ast.Name) and func.value.id == "os":
            if func.attr in ("remove", "rename", "chmod", "unlink", "rmdir", "mkdir", "makedirs"):
                self.violations.append(
                    f"os.{func.attr}() detected (line {node.lineno})"
                )

    # -- shutil.* dangerous calls -------------------------------------------

    def _check_shutil_calls(self, node: ast.Call) -> None:
        """Detect ``shutil.rmtree``, ``shutil.move``, etc."""
        func = node.func
        if not isinstance(func, ast.Attribute):
            return
        if isinstance(func.value, ast.Name) and func.value.id == "shutil":
            if func.attr in ("rmtree", "move", "copytree", "copy2"):
                self.violations.append(
                    f"shutil.{func.attr}() detected (line {node.lineno})"
                )

    # -- subprocess calls ---------------------------------------------------

    def _check_subprocess_calls(self, node: ast.Call) -> None:
        """Detect ``subprocess.call``, ``subprocess.run``, etc."""
        func = node.func
        if not isinstance(func, ast.Attribute):
            return
        if isinstance(func.value, ast.Name) and func.value.id == "subprocess":
            if func.attr in ("call", "run", "Popen", "check_output", "check_call"):
                self.violations.append(
                    f"subprocess.{func.attr}() detected (line {node.lineno})"
                )

    # -- eval / exec / compile ----------------------------------------------

    def _check_code_execution(self, node: ast.Call) -> None:
        """Detect ``eval``, ``exec``, ``compile`` calls."""
        func = node.func
        if isinstance(func, ast.Name) and func.id in ("eval", "exec", "compile"):
            self.violations.append(
                f"{func.id}() detected (line {node.lineno})"
            )

    # -- os.system attribute access -----------------------------------------

    def visit_Attribute(self, node: ast.Attribute) -> None:  # noqa: D102
        if isinstance(node.value, ast.Name) and node.value.id == "os":
            if node.attr == "system":
                self.violations.append(
                    f"os.system access detected (line {node.lineno})"
                )
        self.generic_visit(node)

    # -- bare 'exec' / 'eval' as Name (legacy, should be caught above) -----

    def visit_Name(self, node: ast.Name) -> None:  # noqa: D102
        if node.id in ("eval", "exec", "compile"):
            # Only flag if not a Call (Call is handled in visit_Call)
            # This catches cases like `f = eval; f(code)`
            self.violations.append(
                f"Dangerous name reference '{node.id}' detected (line {node.lineno})"
            )
        self.generic_visit(node)


# ---------------------------------------------------------------------------
# SafetyEnforcer
# ---------------------------------------------------------------------------


class SafetyEnforcer:
    """Centralised safety policy enforcement for swarm agents.

    Operates in *read-only* mode by default and can be relaxed on a per-tool
    basis via the ``allowed_tools`` parameter.
    """

    def __init__(
        self,
        read_only: bool = True,
        allowed_tools: Optional[set[str]] = None,
    ) -> None:
        """Initialise the safety enforcer.

        Parameters
        ----------
        read_only:
            If ``True``, any tool that modifies the filesystem or executes
            arbitrary code is rejected regardless of the allow-list.
        allowed_tools:
            Override the default set of permitted tool names.  When
            ``read_only`` is also ``True``, the intersection with the safe
            subset is used.
        """
        self.read_only: bool = read_only
        self.allowed_tools: set[str] = set(allowed_tools) if allowed_tools is not None else DEFAULT_ALLOWED_TOOLS.copy()

    # -- tool gating --------------------------------------------------------

    def check_tool_call(self, tool_name: str, tool_args: dict) -> tuple[bool, str]:
        """Determine whether *tool_name* may be invoked.

        Returns
        -------
        tuple[bool, str]
            ``(allowed, reason)`` — when *allowed* is ``False``, *reason*
            contains a human-readable explanation.
        """
        _ = tool_args  # reserved for future fine-grained argument scanning

        # 1. Read-only block list (highest priority)
        if self.read_only and tool_name in DEFAULT_BLOCKED_IN_READONLY:
            return False, f"Tool '{tool_name}' is blocked in read-only mode."

        # 2. Prefix-based heuristic for compound dangerous tools
        if self.read_only:
            for blocked in DEFAULT_BLOCKED_IN_READONLY:
                if tool_name.startswith(blocked):
                    return (
                        False,
                        f"Tool '{tool_name}' matches blocked prefix '{blocked}' in read-only mode.",
                    )

        # 3. Allow-list membership
        if tool_name not in self.allowed_tools:
            return (
                False,
                f"Tool '{tool_name}' is not in the allowed tool set: {sorted(self.allowed_tools)}.",
            )

        logger.debug("SafetyEnforcer: tool '%s' allowed", tool_name)
        return True, ""

    # -- file-system gating -------------------------------------------------

    def check_file_access(self, filepath: str, mode: str) -> tuple[bool, str]:
        """Determine whether *filepath* may be accessed in *mode*.

        Parameters
        ----------
        filepath:
            Absolute or relative path to the target file.
        mode:
            One of ``"read"``, ``"write"``, or ``"execute"``.

        Returns
        -------
        tuple[bool, str]
            ``(allowed, reason)``.
        """
        if mode not in {"read", "write", "execute"}:
            return False, f"Invalid access mode '{mode}'."

        if self.read_only and mode == "write":
            return (
                False,
                f"Write access to '{filepath}' denied: read-only mode is active.",
            )

        if self.read_only and mode == "execute":
            return (
                False,
                f"Execute access to '{filepath}' denied: read-only mode is active.",
            )

        # Prevent traversal outside the project workspace.
        # Check the raw path with forward-slash normalisation so Unix-style
        # system paths are blocked even on Windows (where os.path.abspath
        # would rewrite "/etc/passwd" to "C:\etc\passwd" and defeat the
        # prefix check).
        abs_path = os.path.abspath(filepath)
        raw_path = filepath.replace("\\", "/")
        # Heuristic: block absolute paths that look like system directories
        blocked_prefixes = (
            "/etc/", "/usr/", "/bin/", "/sbin/", "/lib/",
            "/opt/", "/var/", "/sys/", "/proc/", "/dev/",
        )
        candidates = (abs_path.replace("\\", "/"), raw_path)
        if any(c.startswith(p) for p in blocked_prefixes for c in candidates):
            return (
                False,
                f"Access to system path '{filepath}' is forbidden.",
            )

        logger.debug("SafetyEnforcer: file '%s' mode '%s' allowed", filepath, mode)
        return True, ""

    # -- static analysis ----------------------------------------------------

    def enforce_read_only(self, code: str) -> tuple[bool, str]:
        """Statically analyse *code* for dangerous Python patterns.

        Parses *code* into an AST and walks it looking for:

        * ``open(..., 'w|a|x|wb|ab|...')``
        * ``os.remove``, ``os.rename``, ``os.chmod``, ``os.unlink`` …
        * ``shutil.rmtree``, ``shutil.move``, …
        * ``subprocess.call``, ``subprocess.run``, ``subprocess.Popen`` …
        * ``os.system``
        * ``eval``, ``exec``, ``compile``

        Returns
        -------
        tuple[bool, str]
            ``(safe, details)`` — *safe* is ``True`` when no dangerous
            constructs are found; otherwise *details* lists every violation.
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return False, f"Syntax error in provided code: {exc}"

        visitor = _DangerousPatternVisitor()
        visitor.visit(tree)

        if visitor.violations:
            report = "Read-only violation(s) detected:\n  - " + "\n  - ".join(
                visitor.violations
            )
            logger.warning("SafetyEnforcer: %s", report)
            return False, report

        return True, ""

    # -- introspection ------------------------------------------------------

    def get_policy(self) -> dict:
        """Return the full safety policy as a serialisable dictionary.

        The dictionary contains the current read-only setting, the allowed
        tool set, and the blocked-in-read-only set for auditing purposes.
        """
        return {
            "read_only": self.read_only,
            "allowed_tools": sorted(self.allowed_tools),
            "blocked_in_read_only": sorted(DEFAULT_BLOCKED_IN_READONLY),
            "dangerous_open_modes": sorted(_DANGEROUS_OPEN_MODES),
        }
