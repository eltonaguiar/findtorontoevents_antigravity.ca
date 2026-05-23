"""Impact analysis worker agent — analyzes blast radius of changes.

Computes dependency graphs, detects breaking changes, estimates risk,
and identifies affected modules for PRs and CI/CD failures.
"""

from __future__ import annotations

import ast
import json
import logging
import os
import re
from typing import Any, Optional

from swarms.core.models import (
    AgentConfig,
    AgentRole,
    MessageType,
    SwarmMessage,
    SwarmTask,
)
from swarms.core.messaging import MessageBus
from swarms.core.llm_client import LLMClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Risk scoring heuristics
# ---------------------------------------------------------------------------

# Per-file risk weights
_FILE_RISK_WEIGHTS: dict[str, float] = {
    "__init__.py": 1.5,
    "setup.py": 2.0,
    "pyproject.toml": 2.0,
    "requirements": 1.8,
    "Dockerfile": 1.5,
    ".github/workflows": 2.0,
    "config": 1.5,
    "settings": 1.5,
    "models": 1.3,
    "schema": 1.3,
    "api": 1.4,
    "migration": 2.0,
    "alembic": 1.8,
}

# Breaking-change pattern indicators
_BREAKING_PATTERNS: list[tuple[str, str]] = [
    (r"class\s+\w+.*\(.*BaseModel.*\)", "Model schema change — may break deserialization"),
    (r"def\s+\w+.*\(.*\)\s*->", "Function signature change — API contract affected"),
    (r"raise\s+\w+Error", "New exception type — callers may not handle it"),
    (r"removed|deleted|dropped", "Removal of previously available functionality"),
    (r"rename[d]?\s+\w+", "Renamed symbols — breaking for importers"),
    (r"@abstractmethod|@abc\.abstractmethod", "New abstract method — subclasses must implement"),
    (r"@deprecated", "Deprecation — downstream should migrate"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_JSON_FENCE_RE = re.compile(
    r"```[ \t]*(?:json)?[ \t]*\r?\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)


def _extract_json_object(text: str) -> Optional[dict]:
    """Extract the first JSON object from an LLM response.

    Handles responses that wrap JSON in a markdown ```` ```json ```` fence as
    well as bare JSON. Returns the decoded object, or ``None`` when no valid
    JSON object could be found.

    Parameters
    ----------
    text :
        Raw LLM response text.

    Returns
    -------
    dict or None
        The decoded JSON object, or ``None`` on parse failure.
    """
    if not text:
        return None

    candidates: list[str] = []
    fenced = _JSON_FENCE_RE.findall(text)
    candidates.extend(block.strip() for block in fenced)

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])

    for candidate in candidates:
        try:
            obj = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(obj, dict):
            return obj
    return None


# ---------------------------------------------------------------------------
# ImpactAnalyzerWorker
# ---------------------------------------------------------------------------


class ImpactAnalyzerWorker:
    """Analyzes the impact of code changes, PRs, or failures.

    Capabilities
    ------------
    * Dependency graph analysis.
    * Breaking change detection.
    * Blast radius estimation.
    * Risk scoring (0-100).
    * Affected module identification.

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
        assesses PR impact via a real LLM; otherwise it falls back to the
        deterministic heuristic path.  ``None`` (the default) keeps the worker
        fully hermetic — no network access.
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

    async def analyze_pr_impact(self, pr_data: dict) -> dict:
        """Analyze PR impact.

        Parameters
        ----------
        pr_data :
            Dictionary containing ``files_changed`` (list of dicts with
            ``filename``, ``patch``, ``status``, ``additions``, ``deletions``),
            ``pr_number``, ``title``, and optionally ``base_branch``.

        Returns
        -------
        dict
            Structured impact assessment with keys:

            * ``affected_files`` (*list[str]*) — all files touched.
            * ``affected_modules`` (*list[str]*) — inferred module names.
            * ``breaking_changes`` (*list[str]*) — descriptions of breaking changes.
            * ``risk_score`` (*float*) — 0-100 aggregate risk.
            * ``risk_level`` (*str*) — ``low`` / ``medium`` / ``high`` / ``critical``.
            * ``dependencies_affected`` (*list[str]*) — downstream dependencies at risk.
        """
        logger.info(
            "ImpactAnalyzerWorker[%s]: analyzing PR #%s — %s",
            self.agent_id,
            pr_data.get("pr_number", "?"),
            pr_data.get("title", "Untitled"),
        )

        # Prefer a real LLM when one is wired in and available; on any
        # failure (no LLM, unavailable, network error, unparsable response)
        # fall through to the deterministic heuristic path below.
        if self.llm is not None and self.llm.available:
            llm_result = self._llm_analyze_pr_impact(pr_data)
            if llm_result is not None:
                logger.info(
                    "ImpactAnalyzerWorker[%s]: LLM path (provider=%s) — "
                    "PR #%s risk=%.1f (%s)",
                    self.agent_id,
                    self.llm.provider_name,
                    pr_data.get("pr_number", "?"),
                    llm_result["risk_score"],
                    llm_result["risk_level"],
                )
                await self.bus.broadcast(
                    payload={
                        "agent_id": self.agent_id,
                        "pr_number": pr_data.get("pr_number"),
                        "impact": llm_result,
                    },
                    sender=self.agent_id,
                    msg_type=MessageType.IMPACT_ANALYSIS,
                )
                return llm_result

        logger.info(
            "ImpactAnalyzerWorker[%s]: deterministic heuristic path",
            self.agent_id,
        )

        files_changed = pr_data.get("files_changed", [])
        affected_files: list[str] = []
        affected_modules: list[str] = []
        breaking_changes: list[str] = []
        dependencies_affected: list[str] = []

        for file_info in files_changed:
            filename = file_info.get("filename", "")
            status = file_info.get("status", "modified")
            patch = file_info.get("patch", "")
            additions = file_info.get("additions", 0)
            deletions = file_info.get("deletions", 0)

            affected_files.append(filename)

            # Derive module name
            module = self._file_to_module(filename)
            if module and module not in affected_modules:
                affected_modules.append(module)

            # Detect breaking changes from patch
            for pattern, description in _BREAKING_PATTERNS:
                if re.search(pattern, patch, re.IGNORECASE):
                    breaking_changes.append(f"[{filename}] {description}")

            # Large deletions suggest removal
            if deletions > additions * 2 and additions < 5:
                breaking_changes.append(
                    f"[{filename}] Significant deletions ({deletions} lines) — possible removal"
                )

            # Detect dependency changes
            if "requirements" in filename or "pyproject.toml" in filename or "setup.py" in filename:
                deps = self._extract_dependency_changes(patch)
                dependencies_affected.extend(deps)

        # Calculate risk score
        risk_score = self._calculate_risk_score(
            affected_files=affected_files,
            affected_modules=affected_modules,
            breaking_changes=breaking_changes,
            dependencies_affected=dependencies_affected,
        )
        risk_level = self._score_to_level(risk_score)

        result = {
            "affected_files": affected_files,
            "affected_modules": affected_modules,
            "breaking_changes": breaking_changes,
            "risk_score": round(risk_score, 1),
            "risk_level": risk_level,
            "dependencies_affected": dependencies_affected,
        }

        logger.info(
            "ImpactAnalyzerWorker[%s]: PR #%s — risk=%.1f (%s), "
            "%d files, %d breaking change(s)",
            self.agent_id,
            pr_data.get("pr_number", "?"),
            risk_score,
            risk_level,
            len(affected_files),
            len(breaking_changes),
        )

        await self.bus.broadcast(
            payload={
                "agent_id": self.agent_id,
                "pr_number": pr_data.get("pr_number"),
                "impact": result,
            },
            sender=self.agent_id,
            msg_type=MessageType.IMPACT_ANALYSIS,
        )

        return result

    async def analyze_failure_impact(self, job_data: dict, repo_data: dict) -> dict:
        """Analyze CI/CD failure impact.

        Parameters
        ----------
        job_data :
            Dictionary with ``job_name``, ``conclusion`` (failure/cancelled),
            ``workflow_name``, ``run_url``, and optionally ``failed_since``.
        repo_data :
            Dictionary with ``repo`` (owner/name), ``default_branch``,
            ``affected_workflows`` (list), and ``recent_commits`` (list).

        Returns
        -------
        dict
            Impact assessment with keys:

            * ``failure_type`` (*str*)
            * ``affected_workflows`` (*list[str]*)
            * ``blast_radius_modules`` (*list[str]*)
            * ``risk_score`` (*float*) — 0-100
            * ``risk_level`` (*str*)
            * ``recommendations`` (*list[str]*)
        """
        logger.info(
            "ImpactAnalyzerWorker[%s]: analyzing failure for job '%s' in %s",
            self.agent_id,
            job_data.get("job_name", "?"),
            repo_data.get("repo", "?"),
        )

        failure_type = self._classify_failure(job_data)
        affected_workflows = repo_data.get("affected_workflows", [])
        if job_data.get("workflow_name"):
            affected_workflows.append(job_data["workflow_name"])
        affected_workflows = list(dict.fromkeys(affected_workflows))  # dedupe

        # Estimate blast radius from job name
        blast_radius_modules = self._infer_modules_from_job_name(
            job_data.get("job_name", "")
        )

        # Risk is higher for failures on default branch or critical jobs
        risk_score = 30.0  # base
        if failure_type in ("consecutive_failure", "critical_path_failure"):
            risk_score += 30.0
        if job_data.get("workflow_name", "").lower() in ("ci", "cd", "deploy", "release"):
            risk_score += 25.0
        if repo_data.get("default_branch") == job_data.get("branch"):
            risk_score += 15.0

        risk_score = min(100.0, risk_score)
        risk_level = self._score_to_level(risk_score)

        recommendations = self._generate_failure_recommendations(failure_type, job_data)

        result = {
            "failure_type": failure_type,
            "affected_workflows": affected_workflows,
            "blast_radius_modules": blast_radius_modules,
            "risk_score": round(risk_score, 1),
            "risk_level": risk_level,
            "recommendations": recommendations,
        }

        await self.bus.broadcast(
            payload={
                "agent_id": self.agent_id,
                "job_name": job_data.get("job_name"),
                "failure_impact": result,
            },
            sender=self.agent_id,
            msg_type=MessageType.IMPACT_ANALYSIS,
        )

        return result

    async def generate_dependency_graph(self, repo_path: str) -> dict:
        """Generate a dependency graph for the repository at *repo_path*.

        Parses Python import statements to build a module-level dependency map.

        Parameters
        ----------
        repo_path :
            Absolute or relative path to the repository root.

        Returns
        -------
        dict
            Dictionary with keys:

            * ``nodes`` (*list[str]*) — module names.
            * ``edges`` (*list[tuple[str, str]]*) — (from_module, to_module).
            * ``in_degree`` (*dict[str, int]*) — how many modules import each node.
            * ``out_degree`` (*dict[str, int]*) — how many modules each node imports.
        """
        logger.info(
            "ImpactAnalyzerWorker[%s]: generating dependency graph for %s",
            self.agent_id,
            repo_path,
        )

        nodes: set[str] = set()
        edges: list[tuple[str, str]] = []
        in_degree: dict[str, int] = {}
        out_degree: dict[str, int] = {}

        if not os.path.isdir(repo_path):
            logger.warning("Repo path '%s' is not a directory", repo_path)
            return {
                "nodes": [],
                "edges": [],
                "in_degree": {},
                "out_degree": {},
            }

        for root, _dirs, files in os.walk(repo_path):
            # Skip hidden dirs and common non-source directories
            _dirs[:] = [d for d in _dirs if not d.startswith(".") and d not in (
                "node_modules", "venv", ".venv", "__pycache__", "dist", "build"
            )]

            for filename in files:
                if not filename.endswith(".py"):
                    continue

                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, repo_path)
                module_name = self._file_to_module(rel_path) or rel_path

                nodes.add(module_name)
                in_degree.setdefault(module_name, 0)
                out_degree.setdefault(module_name, 0)

                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        source = f.read()
                except OSError:
                    continue

                try:
                    tree = ast.parse(source)
                except SyntaxError:
                    continue

                for node in ast.walk(tree):
                    imported: Optional[str] = None
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imported = alias.name.split(".")[0]
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imported = node.module.split(".")[0]
                        elif node.level and node.level > 0:
                            # Relative import — resolve to local module
                            imported = self._resolve_relative_import(rel_path, node.level)

                    if imported and not self._is_stdlib(imported):
                        dep_module = self._find_local_module(repo_path, imported)
                        if dep_module:
                            edges.append((module_name, dep_module))
                            out_degree[module_name] = out_degree.get(module_name, 0) + 1
                            in_degree[dep_module] = in_degree.get(dep_module, 0) + 1
                            nodes.add(dep_module)

        return {
            "nodes": sorted(nodes),
            "edges": edges,
            "in_degree": in_degree,
            "out_degree": out_degree,
        }

    async def handle_message(self, message: SwarmMessage) -> Optional[SwarmMessage]:
        """Process incoming messages relevant to impact analysis.

        Supported message types:

        * ``TASK_ASSIGNMENT`` with ``task_type=pr_review`` — triggers PR impact analysis.
        * ``TASK_ASSIGNMENT`` with ``task_type=gh_actions`` — triggers failure analysis.

        Parameters
        ----------
        message :
            The incoming swarm message.

        Returns
        -------
        SwarmMessage or None
            A response message with the impact assessment.
        """
        if message.msg_type == MessageType.TASK_ASSIGNMENT:
            task = SwarmTask(**message.payload.get("task", {}))
            inputs = task.inputs

            if task.task_type == "pr_review":
                pr_data = inputs
                impact = await self.analyze_pr_impact(pr_data)
                return SwarmMessage(
                    msg_type=MessageType.IMPACT_ANALYSIS,
                    sender=self.agent_id,
                    recipients=[message.sender],
                    payload={
                        "pr_number": pr_data.get("pr_number"),
                        "impact": impact,
                    },
                )

            if task.task_type == "gh_actions":
                job_data = inputs.get("job_data", {})
                repo_data = inputs.get("repo_data", {})
                impact = await self.analyze_failure_impact(job_data, repo_data)
                return SwarmMessage(
                    msg_type=MessageType.IMPACT_ANALYSIS,
                    sender=self.agent_id,
                    recipients=[message.sender],
                    payload={
                        "job_name": job_data.get("job_name"),
                        "failure_impact": impact,
                    },
                )

        return None

    async def analyze_blast_radius(
        self, *, job_name: str, failure_pattern: str, repo: str
    ) -> dict:
        """Estimate blast radius of a flaky/failing CI job.

        Parameters
        ----------
        job_name :
            Name of the failing job (e.g. ``ci.yml/unit-tests``).
        failure_pattern :
            Human-readable description of the failure pattern.
        repo :
            Repository identifier (``owner/repo``).

        Returns
        -------
        dict
            Blast-radius assessment with ``recommendations`` list and
            ``risk_score``.
        """
        logger.info(
            "ImpactAnalyzerWorker[%s]: blast-radius for '%s' in %s — %s",
            self.agent_id,
            job_name,
            repo,
            failure_pattern,
        )

        recommendations = [
            f"Investigate blast radius for '{job_name}': {failure_pattern}",
            "Check downstream consumers that depend on this job's artifacts",
            "Run dependent workflow tests to verify no cascading failures",
        ]

        await self.bus.broadcast(
            payload={
                "agent_id": self.agent_id,
                "job_name": job_name,
                "failure_pattern": failure_pattern,
                "repo": repo,
            },
            sender=self.agent_id,
            msg_type=MessageType.IMPACT_ANALYSIS,
        )

        return {
            "job_name": job_name,
            "failure_pattern": failure_pattern,
            "repo": repo,
            "risk_score": 50.0,
            "recommendations": recommendations,
        }

    # -- internal helpers ------------------------------------------------------

    def _llm_analyze_pr_impact(self, pr_data: dict) -> Optional[dict]:
        """Assess PR impact via the wired-in :class:`LLMClient`.

        Parameters
        ----------
        pr_data :
            The PR payload (see :meth:`analyze_pr_impact`).

        Returns
        -------
        dict or None
            An impact assessment in the same shape returned by
            :meth:`analyze_pr_impact`; ``None`` when the completion failed or
            produced an unparsable response (caller then uses the
            deterministic heuristic path).
        """
        files_changed = pr_data.get("files_changed", [])
        file_summaries: list[str] = []
        for file_info in files_changed:
            file_summaries.append(
                "- {name} ({status}, +{add}/-{dele})".format(
                    name=file_info.get("filename", "?"),
                    status=file_info.get("status", "modified"),
                    add=file_info.get("additions", 0),
                    dele=file_info.get("deletions", 0),
                )
            )
        files_block = "\n".join(file_summaries) or "(no files listed)"

        system = (
            "You are a senior release engineer assessing change impact and "
            "blast radius. Output ONLY valid JSON — no prose outside the JSON."
        )
        prompt = (
            f"Assess the impact of PR #{pr_data.get('pr_number', '?')} "
            f"titled '{pr_data.get('title', 'Untitled')}'.\n\n"
            f"Files changed:\n{files_block}\n\n"
            "Return EXACTLY a JSON object and nothing else with these keys:\n"
            '  "affected_files"         : array of strings,\n'
            '  "affected_modules"       : array of strings,\n'
            '  "breaking_changes"       : array of strings,\n'
            '  "risk_score"             : number in [0, 100],\n'
            '  "risk_level"             : one of "low"/"medium"/"high"/"critical",\n'
            '  "dependencies_affected"  : array of strings.\n'
        )
        text = self.llm.complete(prompt, system=system)
        if text is None:
            return None

        parsed = _extract_json_object(text)
        if parsed is None:
            return None

        try:
            risk_score = float(parsed.get("risk_score", 0.0))
        except (TypeError, ValueError):
            return None
        risk_score = round(min(100.0, max(0.0, risk_score)), 1)

        def _str_list(value: Any) -> list[str]:
            if not isinstance(value, list):
                return []
            return [str(v) for v in value if isinstance(v, (str, int, float))]

        risk_level = parsed.get("risk_level")
        if not isinstance(risk_level, str) or risk_level.lower() not in (
            "low",
            "medium",
            "high",
            "critical",
        ):
            risk_level = self._score_to_level(risk_score)
        else:
            risk_level = risk_level.lower()

        return {
            "affected_files": _str_list(parsed.get("affected_files")),
            "affected_modules": _str_list(parsed.get("affected_modules")),
            "breaking_changes": _str_list(parsed.get("breaking_changes")),
            "risk_score": risk_score,
            "risk_level": risk_level,
            "dependencies_affected": _str_list(
                parsed.get("dependencies_affected")
            ),
        }

    def _file_to_module(self, filename: str) -> Optional[str]:
        """Convert a file path to a Python module name."""
        if filename.endswith(".py"):
            return filename[:-3].replace(os.sep, ".").replace("/", ".")
        return None

    def _calculate_risk_score(
        self,
        affected_files: list[str],
        affected_modules: list[str],
        breaking_changes: list[str],
        dependencies_affected: list[str],
    ) -> float:
        """Compute an aggregate risk score from 0 to 100.

        Factors:

        * Number of files changed (diminishing returns after 20).
        * Number of modules affected.
        * File-specific risk weights.
        * Breaking change count (heavily weighted).
        * Dependency change count.
        """
        score = 0.0

        # Files changed — cap at 30 points
        score += min(30.0, len(affected_files) * 1.5)

        # Modules affected — cap at 15 points
        score += min(15.0, len(affected_modules) * 2.0)

        # File risk weights
        for filepath in affected_files:
            for keyword, weight in _FILE_RISK_WEIGHTS.items():
                if keyword in filepath.lower():
                    score += weight * 2.0
                    break

        # Breaking changes — heavily weighted
        score += len(breaking_changes) * 8.0

        # Dependency changes
        score += len(dependencies_affected) * 5.0

        return min(100.0, max(0.0, score))

    def _score_to_level(self, score: float) -> str:
        """Convert a numeric risk score to a qualitative level."""
        if score >= 80.0:
            return "critical"
        if score >= 50.0:
            return "high"
        if score >= 25.0:
            return "medium"
        return "low"

    def _extract_dependency_changes(self, patch: str) -> list[str]:
        """Extract dependency names from a requirements/setup patch."""
        deps: list[str] = []
        for line in patch.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                # Match package name before any version specifier
                m = re.match(r"\+\s*([a-zA-Z0-9_\-]+)", line)
                if m:
                    dep_name = m.group(1).lower()
                    if dep_name not in ("import", "from", "if", "try", "except"):
                        deps.append(dep_name)
        return list(dict.fromkeys(deps))

    def _classify_failure(self, job_data: dict) -> str:
        """Classify the type of CI/CD failure."""
        conclusion = job_data.get("conclusion", "").lower()
        failed_since = job_data.get("failed_since")

        if conclusion == "cancelled":
            return "cancelled"
        if conclusion == "timed_out":
            return "timeout"
        if failed_since and failed_since > 1:
            return "consecutive_failure"

        workflow = job_data.get("workflow_name", "").lower()
        if workflow in ("deploy", "release", "cd"):
            return "critical_path_failure"

        return "test_failure"

    def _infer_modules_from_job_name(self, job_name: str) -> list[str]:
        """Infer potentially affected modules from a CI job name."""
        modules: list[str] = []
        job_lower = job_name.lower()

        # Common naming conventions
        if "test" in job_lower:
            modules.append("tests")
        if "lint" in job_lower or "format" in job_lower:
            modules.append("dev_tools")
        if "build" in job_lower or "compile" in job_lower:
            modules.append("build")
        if "deploy" in job_lower:
            modules.append("deployment")
        if "api" in job_lower:
            modules.append("api")
        if "db" in job_lower or "migrate" in job_lower:
            modules.append("database")
        if "auth" in job_lower:
            modules.append("auth")
        if "core" in job_lower:
            modules.append("core")

        if not modules:
            modules.append("unknown")

        return modules

    def _generate_failure_recommendations(
        self, failure_type: str, job_data: dict
    ) -> list[str]:
        """Produce actionable recommendations based on failure classification."""
        recommendations: list[str] = []

        if failure_type == "consecutive_failure":
            recommendations.append(
                "This job has failed multiple times in a row — investigate immediately"
            )
            recommendations.append(
                "Check for recent dependency updates or infrastructure changes"
            )
        elif failure_type == "cancelled":
            recommendations.append(
                "Job was cancelled — check for resource limits or timeout settings"
            )
            recommendations.append(
                f"Consider increasing timeout for job '{job_data.get('job_name')}'"
            )
        elif failure_type == "timeout":
            recommendations.append(
                "Job timed out — investigate for deadlocks or slow external dependencies"
            )
            recommendations.append(
                "Check network latency and third-party service health"
            )
        elif failure_type == "critical_path_failure":
            recommendations.append(
                "CRITICAL: Deployment/release pipeline is blocked"
            )
            recommendations.append(
                "Consider rollback procedures if this affects production"
            )
        else:
            recommendations.append(
                "Check test logs for specific failure details"
            )
            recommendations.append(
                "Run tests locally to reproduce the failure"
            )

        recommendations.append(
            "Review recent commits for potential causes"
        )

        return recommendations

    def _resolve_relative_import(self, current_file: str, level: int) -> Optional[str]:
        """Resolve a relative import level to a module path."""
        parts = current_file.replace("/", ".").replace(os.sep, ".").split(".")
        if parts[-1] == "py":
            parts = parts[:-1]

        if level > len(parts):
            return None

        base = parts[:-level] if level > 0 else parts
        if not base:
            return None
        return ".".join(base)

    def _is_stdlib(self, module_name: str) -> bool:
        """Heuristically check whether *module_name* is from the Python stdlib."""
        stdlib_modules = {
            "abc", "argparse", "ast", "asyncio", "base64", "bisect", "builtins",
            "collections", "concurrent", "contextlib", "copy", "csv", "datetime",
            "decimal", "enum", "fnmatch", "functools", "glob", "hashlib", "heapq",
            "importlib", "inspect", "io", "itertools", "json", "logging", "math",
            "multiprocessing", "operator", "os", "pathlib", "pickle", "platform",
            "random", "re", "shutil", "signal", "socket", "sqlite3", "statistics",
            "string", "struct", "subprocess", "sys", "tempfile", "threading",
            "time", "traceback", "typing", "unittest", "urllib", "uuid", "warnings",
            "xml", "zipfile", "zlib", "http", "email", "html", "ftplib", "gettext",
        }
        return module_name in stdlib_modules

    def _find_local_module(self, repo_path: str, module_name: str) -> Optional[str]:
        """Check whether *module_name* maps to a local file in *repo_path*."""
        candidate = module_name.replace(".", os.sep) + ".py"
        candidate_path = os.path.join(repo_path, candidate)
        if os.path.isfile(candidate_path):
            return module_name

        # Check for package (__init__.py)
        pkg_init = os.path.join(repo_path, module_name.replace(".", os.sep), "__init__.py")
        if os.path.isfile(pkg_init):
            return module_name

        return None
