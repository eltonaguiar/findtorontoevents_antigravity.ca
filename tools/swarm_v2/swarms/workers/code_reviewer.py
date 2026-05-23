"""Code review worker agent.

Reviews code artifacts for quality, security, correctness, and style.
Produces structured review reports with severity-graded comments and an
overall approval recommendation.
"""

from __future__ import annotations

import ast
import logging
import os
import re
from typing import Any, Optional

from swarms.core.models import (
    AgentConfig,
    AgentRole,
    CodeArtifact,
    MessageType,
    SwarmMessage,
    SwarmTask,
)
from swarms.core.messaging import MessageBus
from swarms.core.llm_client import LLMClient

logger = logging.getLogger(__name__)

# Valid severity levels for review comments — used to validate parsed LLM output.
_VALID_SEVERITIES: frozenset[str] = frozenset(
    {"critical", "warning", "info"}
)

# ---------------------------------------------------------------------------
# Security / quality heuristics
# ---------------------------------------------------------------------------

# Patterns that indicate potential security vulnerabilities
_SECURITY_PATTERNS: list[tuple[str, str, str]] = [
    (r"(?i)SELECT\s+.*\s+FROM\s+.*\+.*", "sql_injection", "Possible SQL injection — string concatenation in query"),
    (r"(?i)INSERT\s+INTO\s+.*\+.*", "sql_injection", "Possible SQL injection in INSERT"),
    (r"(?i)DELETE\s+FROM\s+.*\+.*", "sql_injection", "Possible SQL injection in DELETE"),
    (r"(?i)UPDATE\s+.*SET\s+.*\+.*", "sql_injection", "Possible SQL injection in UPDATE"),
    (r"(?i)execute\s*\(\s*['\"].*\+.*['\"]", "sql_injection", "Dynamic query construction detected"),
    (r"(?i)\.format\s*\(.*\)|%\s*\(.*\)\s*", "format_string", "Potential format-string vulnerability — use parameterized queries"),
    (r"(?i)innerHTML\s*[=:]", "xss", "innerHTML assignment — potential XSS vulnerability"),
    (r"(?i)document\.write\s*\(", "xss", "document.write — potential XSS vulnerability"),
    (r"(?i)eval\s*\(", "code_injection", "eval() detected — dangerous code execution"),
    (r"(?i)exec\s*\(", "code_injection", "exec() detected — dangerous code execution"),
    (r"(?i)subprocess\.\w+\s*\([^)]*shell\s*=\s*True", "command_injection", "subprocess with shell=True — command injection risk"),
    (r"(?i)os\.system\s*\(", "command_injection", "os.system() — command injection risk"),
    (r"(?i)pickle\.(loads|load)\s*\(", "deserialization", "Unsafe pickle deserialization — use json instead"),
    (r"(?i)yaml\.(load|unsafe_load)\s*\(", "deserialization", "Unsafe yaml.load — use safe_load()"),
    (r"(?i)input\s*\(\s*\)", "user_input", "Unvalidated user input — sanitize before processing"),
    (r"(?i)hardcoded|password\s*=\s*['\"][^'\"]+['\"]|secret\s*=\s*['\"][^'\"]+['\"]|api_key\s*=\s*['\"][^'\"]+['\"]|token\s*=\s*['\"][^'\"]+['\"]", "secrets", "Possible hardcoded secret/credential"),
]

# Style anti-patterns
_STYLE_PATTERNS: list[tuple[str, str]] = [
    (r"^\s*print\s*\(", "Use logging instead of print() for production code"),
    (r"^\s*except\s*:\s*$", "Bare 'except:' clause — use specific exception types"),
    (r"^\s*except\s+Exception\s*:\s*$", "Overly broad 'except Exception:' — be more specific"),
    (r";\s*$", "Avoid semicolons at end of lines"),
    (r"^\s*pass\s*$", "Empty pass statement — implement or remove"),
    (r"^\s*#\s*FIXME", "FIXME marker found — address before merging"),
    (r"^\s*#\s*HACK", "HACK marker found — consider cleaner implementation"),
    (r"^\s*import\s+\*", "Wildcard import — import only what you need"),
]


# ---------------------------------------------------------------------------
# CodeReviewerWorker
# ---------------------------------------------------------------------------


class CodeReviewerWorker:
    """Reviews code for quality, security, correctness, and style.

    Checks
    ------
    * Code quality and readability.
    * Security vulnerabilities (SQL injection, XSS, unsafe deserialization, …).
    * Test coverage adequacy.
    * Adherence to task requirements.
    * Potential bugs or edge cases.

    Parameters
    ----------
    agent_id :
        Unique identifier for this worker instance.
    config :
        Agent configuration (role, model, temperature, …).
    bus :
        Shared :class:`MessageBus` for inter-agent communication.
    llm :
        Optional :class:`LLMClient`.  When supplied *and* available the worker
        reviews code via a real LLM; otherwise it falls back to the
        deterministic static-analysis path.  ``None`` (the default) keeps the
        worker fully hermetic — no network access.
    """

    def __init__(
        self,
        agent_id: str,
        config: AgentConfig,
        bus: MessageBus,
        llm: Optional[LLMClient] = None,
    ) -> None:
        self.agent_id: str = agent_id
        self.config: AgentConfig = config
        self.bus: MessageBus = bus
        self.llm: Optional[LLMClient] = llm

    # -- public API ------------------------------------------------------------

    async def review(self, artifact: CodeArtifact, task: SwarmTask) -> dict:
        """Review a :class:`CodeArtifact`.

        Performs static analysis, security scanning, style checking, and
        test-coverage validation.  Returns a structured review dict.

        Parameters
        ----------
        artifact :
            The code artifact to review.
        task :
            The original task (for requirement-adherence checking).

        Returns
        -------
        dict
            Structured review with keys:

            * ``approved`` (*bool*) — ``True`` when score >= 80 and no critical issues.
            * ``score`` (*float*) — aggregate quality score 0-100.
            * ``comments`` (*list[dict]*) — each with ``line``, ``severity``,
              ``message``, ``suggestion``.
            * ``issues_found`` (*int*) — total number of issues detected.
        """
        logger.info(
            "CodeReviewerWorker[%s]: reviewing artifact %s (%s)",
            self.agent_id,
            artifact.filepath,
            artifact.language,
        )

        # Prefer a real LLM when one is wired in and available; on any
        # failure (no LLM, unavailable, network error, unparsable response)
        # fall back to the deterministic static-analysis path.
        all_comments = self._collect_comments(artifact, task)

        # 6. Aggregate score
        score = self._calculate_score(all_comments, artifact)
        critical_count = sum(1 for c in all_comments if c.get("severity") == "critical")
        approved = score >= 80.0 and critical_count == 0

        result = {
            "approved": approved,
            "score": round(score, 1),
            "comments": all_comments,
            "issues_found": len(all_comments),
        }

        logger.info(
            "CodeReviewerWorker[%s]: review complete — score=%.1f issues=%d approved=%s",
            self.agent_id,
            score,
            len(all_comments),
            approved,
        )

        # Broadcast review result
        await self.bus.broadcast(
            payload={
                "agent_id": self.agent_id,
                "filepath": artifact.filepath,
                "review": result,
            },
            sender=self.agent_id,
            msg_type=MessageType.CODE_REVIEW,
        )

        return result

    async def review_pr(self, pr_data: dict) -> dict:
        """Review a Pull Request.

        Analyses the diff, files changed, and overall impact to produce a
        structured PR review.

        Parameters
        ----------
        pr_data :
            Dictionary with keys such as ``pr_number``, ``title``,
            ``description``, ``files_changed`` (list of dicts with ``filename``,
            ``patch``, ``status``), and ``author``.

        Returns
        -------
        dict
            Structured PR review with keys:

            * ``approved`` (*bool*)
            * ``score`` (*float*) — 0-100
            * ``comments`` (*list[dict]*)
            * ``issues_found`` (*int*)
            * ``summary`` (*str*) — human-readable summary
        """
        logger.info(
            "CodeReviewerWorker[%s]: reviewing PR #%s — %s",
            self.agent_id,
            pr_data.get("pr_number", "?"),
            pr_data.get("title", "Untitled"),
        )

        all_comments: list[dict] = []
        files = pr_data.get("files_changed", [])

        for file_info in files:
            filename = file_info.get("filename", "")
            patch = file_info.get("patch", "")
            status = file_info.get("status", "modified")

            # Simulate per-file review
            if status == "removed":
                continue

            dummy_artifact = CodeArtifact(
                filepath=filename,
                language=self._detect_language(filename),
                source_code=patch,
            )
            sec = self._scan_security(dummy_artifact)
            sty = self._scan_style(dummy_artifact)
            bug = self._scan_correctness(dummy_artifact)
            for c in sec + sty + bug:
                c["file"] = filename
                all_comments.append(c)

        # PR-specific heuristics
            # Large PR penalty
        total_lines = sum(
            len(f.get("patch", "").splitlines()) for f in files
        )
        if total_lines > 500:
            all_comments.append(
                {
                    "severity": "warning",
                    "message": f"Large PR: {total_lines} lines changed — consider splitting",
                    "suggestion": "Break into smaller, focused PRs for easier review",
                    "file": "PR",
                }
            )

        # Missing tests for new files
        test_files = [f for f in files if "test" in f.get("filename", "").lower()]
        source_files = [
            f for f in files
            if "test" not in f.get("filename", "").lower()
            and f.get("status") != "removed"
        ]
        if source_files and not test_files:
            all_comments.append(
                {
                    "severity": "warning",
                    "message": "No test files detected in this PR",
                    "suggestion": "Add unit tests for new/modified code",
                    "file": "PR",
                }
            )

        score = self._calculate_score(all_comments, dummy_artifact if files else None)
        critical_count = sum(1 for c in all_comments if c.get("severity") == "critical")
        approved = score >= 75.0 and critical_count == 0

        result = {
            "approved": approved,
            "score": round(score, 1),
            "comments": all_comments,
            "issues_found": len(all_comments),
            "summary": (
                f"PR review: {len(all_comments)} issue(s) found, "
                f"score={score:.1f}/100, {'APPROVED' if approved else 'NEEDS_WORK'}"
            ),
        }

        await self.bus.broadcast(
            payload={
                "agent_id": self.agent_id,
                "pr_number": pr_data.get("pr_number"),
                "review": result,
            },
            sender=self.agent_id,
            msg_type=MessageType.CODE_REVIEW,
        )

        return result

    async def handle_message(self, message: SwarmMessage) -> Optional[SwarmMessage]:
        """Process incoming messages relevant to code review.

        Supported message types:

        * ``CODE_GENERATION`` — triggers a review of the generated artifact.
        * ``TASK_ASSIGNMENT`` with ``task_type=pr_review`` — triggers PR review.

        Parameters
        ----------
        message :
            The incoming swarm message.

        Returns
        -------
        SwarmMessage or None
            A response message containing the review result.
        """
        if message.msg_type == MessageType.CODE_GENERATION:
            payload = message.payload
            artifact_data = payload.get("artifact", {})
            artifact = CodeArtifact(**artifact_data)

            # Derive a minimal SwarmTask from the payload
            task = SwarmTask(
                task_type="coding",
                description=artifact_data.get("description", artifact.filepath),
                inputs=artifact_data,
            )
            review = await self.review(artifact, task)
            return SwarmMessage(
                msg_type=MessageType.CODE_REVIEW,
                sender=self.agent_id,
                recipients=[message.sender],
                payload={
                    "artifact_filepath": artifact.filepath,
                    "review": review,
                },
            )

        if message.msg_type == MessageType.TASK_ASSIGNMENT:
            task_data = message.payload.get("task", {})
            if task_data.get("task_type") == "pr_review":
                pr_data = task_data.get("inputs", {})
                review = await self.review_pr(pr_data)
                return SwarmMessage(
                    msg_type=MessageType.CODE_REVIEW,
                    sender=self.agent_id,
                    recipients=[message.sender],
                    payload={"pr_number": pr_data.get("pr_number"), "review": review},
                )

        return None

    # -- review dispatch -------------------------------------------------------

    def _collect_comments(self, artifact: CodeArtifact, task: SwarmTask) -> list[dict]:
        """Produce the list of review comments for *artifact*.

        Uses a real LLM when :attr:`llm` is wired in and available; on any
        failure (no LLM, unavailable, completion error, unparsable response)
        falls back to the deterministic static-analysis path.

        Parameters
        ----------
        artifact :
            The code artifact to review.
        task :
            The original task (for requirement-adherence checking).

        Returns
        -------
        list[dict]
            Review comments, each with ``line``, ``severity``, ``message``,
            and ``suggestion`` keys.
        """
        if self.llm is not None and self.llm.available:
            comments = self._llm_review(artifact)
            if comments is not None:
                logger.info(
                    "CodeReviewerWorker[%s]: LLM path (provider=%s, %d comment(s))",
                    self.agent_id,
                    self.llm.provider_name,
                    len(comments),
                )
                return comments

        logger.info(
            "CodeReviewerWorker[%s]: deterministic fallback", self.agent_id
        )
        return self._deterministic_review(artifact, task)

    def _deterministic_review(
        self, artifact: CodeArtifact, task: SwarmTask
    ) -> list[dict]:
        """Run the deterministic static-analysis review pipeline.

        Parameters
        ----------
        artifact :
            The code artifact to review.
        task :
            The original task (for requirement-adherence checking).

        Returns
        -------
        list[dict]
            Aggregated comments from the security, style, correctness,
            test-adequacy, and requirement-adherence scanners.
        """
        all_comments: list[dict] = []

        # 1. Security scan
        all_comments.extend(self._scan_security(artifact))

        # 2. Style scan
        all_comments.extend(self._scan_style(artifact))

        # 3. Correctness / bug scan
        all_comments.extend(self._scan_correctness(artifact))

        # 4. Test coverage check
        all_comments.extend(self._check_test_adequacy(artifact))

        # 5. Requirement adherence
        all_comments.extend(self._check_requirements(artifact, task))

        return all_comments

    def _llm_review(self, artifact: CodeArtifact) -> Optional[list[dict]]:
        """Review *artifact*'s source code via the wired-in :class:`LLMClient`.

        The model is asked to return one finding per line in a strict
        ``severity | message | suggestion`` pipe-delimited format, which is
        then parsed into the same list-of-dict shape the deterministic
        reviewer returns.

        Parameters
        ----------
        artifact :
            The code artifact whose source code is reviewed.

        Returns
        -------
        list[dict] or None
            Parsed review comments on success — an empty list is a valid
            result (the model found no issues).  Returns ``None`` when the
            completion failed or produced no parsable findings (caller then
            uses the deterministic path).
        """
        system = (
            "You are a meticulous senior code reviewer. Report only real, "
            "actionable issues — security, correctness, style, missing tests."
        )
        prompt = (
            f"Review the following {artifact.language} source file "
            f"({artifact.filepath}) and report findings.\n\n"
            "Output ONE finding per line and NOTHING else. Each line MUST use "
            "exactly this pipe-delimited format:\n"
            "severity | message | suggestion\n"
            "where severity is one of: critical, warning, info.\n"
            "If there are no issues, output the single line: NONE\n\n"
            f"```{artifact.language}\n{artifact.source_code}\n```"
        )
        text = self.llm.complete(prompt, system=system)
        if text is None:
            return None
        return self._parse_llm_review(text)

    def _parse_llm_review(self, text: str) -> Optional[list[dict]]:
        """Parse an LLM review response into review-comment dicts.

        Parameters
        ----------
        text :
            Raw LLM response text — one ``severity | message | suggestion``
            finding per line, or the sentinel ``NONE``.

        Returns
        -------
        list[dict] or None
            Parsed comments, each with ``line``, ``severity``, ``message``,
            and ``suggestion`` keys.  An empty list when the model reported
            ``NONE``.  ``None`` when no line could be parsed (caller then
            falls back to the deterministic path).
        """
        comments: list[dict] = []
        saw_none = False

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            # Strip leading list markers / fence noise.
            line = line.lstrip("-*0123456789.) \t")
            if not line:
                continue
            if line.upper() == "NONE":
                saw_none = True
                continue
            if line.startswith("```"):
                continue

            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 2:
                continue

            severity = parts[0].lower()
            if severity not in _VALID_SEVERITIES:
                continue

            message = parts[1]
            if not message:
                continue
            suggestion = parts[2] if len(parts) >= 3 else ""

            comments.append(
                {
                    "line": 1,
                    "severity": severity,
                    "message": message,
                    "suggestion": suggestion,
                }
            )

        if comments:
            return comments
        if saw_none:
            return []
        # Nothing parsable — signal the caller to use the deterministic path.
        return None

    # -- internal scanners -----------------------------------------------------

    def _scan_security(self, artifact: CodeArtifact) -> list[dict]:
        """Scan source code for known security vulnerabilities.

        Returns a list of comment dicts with ``severity`` set to ``critical``
        for confirmed vulnerabilities or ``warning`` for suspicious patterns.
        """
        comments: list[dict] = []
        source = artifact.source_code
        lines = source.splitlines()

        for lineno, line in enumerate(lines, start=1):
            for pattern, vuln_type, message in _SECURITY_PATTERNS:
                if re.search(pattern, line):
                    comments.append(
                        {
                            "line": lineno,
                            "severity": "critical",
                            "message": f"[{vuln_type.upper()}] {message}",
                            "suggestion": self._security_remediation(vuln_type),
                        }
                    )

        return comments

    def _scan_style(self, artifact: CodeArtifact) -> list[dict]:
        """Check code style and readability.

        Returns a list of comment dicts with ``severity`` set to ``info`` or
        ``warning`` depending on the anti-pattern.
        """
        comments: list[dict] = []
        source = artifact.source_code
        lines = source.splitlines()

        for lineno, line in enumerate(lines, start=1):
            for pattern, message in _STYLE_PATTERNS:
                if re.search(pattern, line):
                    comments.append(
                        {
                            "line": lineno,
                            "severity": "warning" if "FIXME" in line or "HACK" in line else "info",
                            "message": message,
                            "suggestion": "Refactor according to project style guide",
                        }
                    )

        # Check line length
        for lineno, line in enumerate(lines, start=1):
            if len(line) > 100:
                comments.append(
                    {
                        "line": lineno,
                        "severity": "info",
                        "message": f"Line exceeds 100 characters ({len(line)})",
                        "suggestion": "Break into multiple lines",
                    }
                )

        return comments

    def _scan_correctness(self, artifact: CodeArtifact) -> list[dict]:
        """Look for potential bugs and edge-case issues.

        Uses lightweight AST parsing (when the language is Python) and
        heuristic pattern matching.
        """
        comments: list[dict] = []
        source = artifact.source_code

        if artifact.language == "python":
            try:
                tree = ast.parse(source)
            except SyntaxError as exc:
                return [
                    {
                        "line": getattr(exc, "lineno", 1),
                        "severity": "critical",
                        "message": f"Syntax error: {exc}",
                        "suggestion": "Fix syntax before review",
                    }
                ]

            for node in ast.walk(tree):
                # Check for mutable default arguments
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for default in node.args.defaults:
                        if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                            comments.append(
                                {
                                    "line": getattr(node, "lineno", 1),
                                    "severity": "critical",
                                    "message": (
                                        f"Mutable default argument in '{node.name}' — "
                                        "shared state across calls"
                                    ),
                                    "suggestion": "Use None as default and initialise inside function",
                                }
                            )

                # Check for bare except
                if isinstance(node, ast.Try):
                    for handler in node.handlers:
                        if handler.type is None:
                            comments.append(
                                {
                                    "line": getattr(handler, "lineno", 1),
                                    "severity": "warning",
                                    "message": "Bare 'except' clause catches all exceptions including SystemExit",
                                    "suggestion": "Use 'except Exception:' or more specific types",
                                }
                            )

                # Check for unclosed resources
                if isinstance(node, ast.With):
                    context_names = [
                        isinstance(item.context_expr, ast.Call)
                        and isinstance(item.context_expr.func, ast.Name)
                        and item.context_expr.func.id
                        for item in node.items
                    ]
                    if "open" in [str(c) for c in context_names if c]:
                        pass  # open() in with-statement is fine

        # Language-agnostic checks
        if "return None" not in source and "return" not in source:
            comments.append(
                {
                    "line": 1,
                    "severity": "info",
                    "message": "No explicit return statements found",
                    "suggestion": "Ensure all code paths have appropriate return values",
                }
            )

        return comments

    def _check_test_adequacy(self, artifact: CodeArtifact) -> list[dict]:
        """Validate that the artifact has adequate tests."""
        comments: list[dict] = []

        if not artifact.tests:
            comments.append(
                {
                    "line": 1,
                    "severity": "critical",
                    "message": "No tests included — tests are mandatory",
                    "suggestion": "Add comprehensive unit tests",
                }
            )
            return comments

        test_lines = [
            ln for ln in artifact.tests.splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        if len(test_lines) < 10:
            comments.append(
                {
                    "line": 1,
                    "severity": "warning",
                    "message": f"Test suite appears thin ({len(test_lines)} meaningful lines)",
                    "suggestion": "Add more test cases including edge cases",
                }
            )

        # Check test results if available
        if artifact.test_results:
            coverage = artifact.test_results.get("coverage", 0.0)
            if coverage < 80.0:
                comments.append(
                    {
                        "line": 1,
                        "severity": "warning",
                        "message": f"Test coverage {coverage:.1f}% is below the 80% threshold",
                        "suggestion": "Add tests to cover uncovered branches",
                    }
                )
            failed = artifact.test_results.get("failed", 0)
            if failed > 0:
                comments.append(
                    {
                        "line": 1,
                        "severity": "critical",
                        "message": f"{failed} test(s) failing",
                        "suggestion": "Fix failing tests before submission",
                    }
                )

        return comments

    def _check_requirements(self, artifact: CodeArtifact, task: SwarmTask) -> list[dict]:
        """Check adherence to task requirements."""
        comments: list[dict] = []
        req_language = task.inputs.get("language", "python").lower()
        if req_language and artifact.language != req_language:
            comments.append(
                {
                    "line": 1,
                    "severity": "warning",
                    "message": (
                        f"Artifact language ({artifact.language}) does not match "
                        f"requested language ({req_language})"
                    ),
                    "suggestion": "Generate code in the requested language",
                }
            )

        # Check that description keywords appear in the code
        desc_words = set(task.description.lower().split())
        code_words = set(artifact.source_code.lower().split())
        # Simple keyword overlap heuristic
        important_words = {w for w in desc_words if len(w) > 5 and w.isalpha()}
        if important_words and not important_words & code_words:
            comments.append(
                {
                    "line": 1,
                    "severity": "info",
                    "message": "Code may not fully address task description keywords",
                    "suggestion": "Ensure the implementation covers all described functionality",
                }
            )

        return comments

    # -- scoring ---------------------------------------------------------------

    def _calculate_score(self, comments: list[dict], artifact: Optional[CodeArtifact]) -> float:
        """Compute an aggregate quality score from 0 to 100.

        Scoring formula::

            base = 100
            -3 per critical issue
            -2 per warning
            -1 per info
            -5 if no tests
            -5 if coverage < 80%
        """
        score = 100.0
        for c in comments:
            sev = c.get("severity", "info")
            if sev == "critical":
                score -= 3.0
            elif sev == "warning":
                score -= 2.0
            else:
                score -= 1.0

        if artifact is not None:
            if not artifact.tests:
                score -= 5.0
            if artifact.test_results and artifact.test_results.get("coverage", 100.0) < 80.0:
                score -= 5.0

        return max(0.0, min(100.0, score))

    # -- helpers ---------------------------------------------------------------

    def _security_remediation(self, vuln_type: str) -> str:
        """Return a remediation suggestion for a given vulnerability type."""
        remediations: dict[str, str] = {
            "sql_injection": "Use parameterized queries or an ORM — never concatenate SQL",
            "xss": "Use textContent instead of innerHTML; sanitize all user input",
            "code_injection": "Avoid eval/exec; use ast.literal_eval for safe parsing",
            "command_injection": "Use subprocess with argument lists instead of shell=True",
            "deserialization": "Use json.loads() or yaml.safe_load() instead of unsafe loaders",
            "user_input": "Validate and sanitize all external input with a schema library",
            "secrets": "Use environment variables or a secrets manager — never hardcode credentials",
            "format_string": "Use f-strings or .format() with explicit, validated values",
        }
        return remediations.get(vuln_type, "Review and fix the security issue")

    def _detect_language(self, filename: str) -> str:
        """Infer programming language from a file extension."""
        ext_map: dict[str, str] = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".rb": "ruby",
            ".sh": "bash",
        }
        _, ext = os.path.splitext(filename.lower())
        return ext_map.get(ext, "unknown")
