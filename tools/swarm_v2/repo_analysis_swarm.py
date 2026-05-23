from __future__ import annotations

"""
Swarm-based codebase analyzer for the prediction repository.

Maps repository structure, identifies potential issues, extracts
import dependency graphs, finds dead code, TODOs/FIXMEs, and traces
the prediction pipeline data flow.
"""

import ast
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger: logging.Logger = logging.getLogger("swarm_v2.repo")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ModuleInfo:
    """Metadata for a single Python module."""

    path: str
    rel_path: str
    lines_of_code: int
    function_count: int
    class_count: int
    avg_function_length: float
    cyclomatic_complexity: float
    import_count: int
    todo_fixme_items: list[dict] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    called_by: list[str] = field(default_factory=list)  # modules that import this one


@dataclass
class PipelineStage:
    """A single stage in the prediction pipeline."""

    name: str
    description: str
    files: list[str] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    output_points: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# AST visitor helpers
# ---------------------------------------------------------------------------


class _ModuleAnalyzer(ast.NodeVisitor):
    """AST visitor that extracts metrics from a single Python module."""

    def __init__(self, source: str) -> None:
        self.source_lines: list[str] = source.splitlines()
        self.function_count: int = 0
        self.class_count: int = 0
        self.total_function_lines: int = 0
        self.cyclomatic_complexity: float = 0.0
        self.imports: list[str] = []
        self.classes: list[str] = []
        self.functions: list[str] = []
        self.todo_fixme_items: list[dict] = []

    def analyze(self) -> None:
        """Run the visitor over the parsed AST."""
        try:
            tree = ast.parse("\n".join(self.source_lines))
        except SyntaxError as exc:
            logger.warning("Syntax error parsing module: %s", exc)
            return
        self.visit(tree)
        self._extract_comments()

    # ---- visitor overrides ----

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self.function_count += 1
        self.functions.append(node.name)
        length = node.end_lineno - node.lineno if node.end_lineno else 1
        self.total_function_lines += length
        # Cyclomatic complexity: 1 + number of decision points
        complexity = 1
        for child in ast.walk(node):
            if isinstance(
                child,
                (
                    ast.If,
                    ast.While,
                    ast.For,
                    ast.ExceptHandler,
                    ast.With,
                    ast.Assert,
                    ast.comprehension,
                ),
            ):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        self.cyclomatic_complexity += complexity
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        # Treat async functions identically for metric purposes
        self.visit_FunctionDef(node)  # type: ignore[arg-type]

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self.class_count += 1
        self.classes.append(node.name)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        module = node.module or ""
        for alias in node.names:
            self.imports.append(f"{module}.{alias.name}" if module else alias.name)
        self.generic_visit(node)

    # ---- comment extraction ----

    def _extract_comments(self) -> None:
        pattern = re.compile(r"#.*?(TODO|FIXME|HACK)(.*?)$", re.IGNORECASE)
        for line_no, line in enumerate(self.source_lines, start=1):
            match = pattern.search(line)
            if match:
                tag = match.group(1).upper()
                text = match.group(2).strip()
                self.todo_fixme_items.append(
                    {
                        "line": line_no,
                        "tag": tag,
                        "text": text,
                    }
                )


# ---------------------------------------------------------------------------
# RepoAnalyzerSwarm
# ---------------------------------------------------------------------------


class RepoAnalyzerSwarm:
    """
    Swarm-based codebase analyzer.

    Crawls the repository, maps Python files, extracts import dependency
    graphs, locates dead code, surfaces TODO/FIXME/HACK comments, and
    computes code-quality metrics.
    """

    def __init__(self, repo_root: str) -> None:
        """
        Parameters
        ----------
        repo_root:
            Absolute or relative path to the repository root.
        """
        self.repo_root: Path = Path(repo_root).resolve()
        self.modules: dict[str, ModuleInfo] = {}
        self._python_files: list[Path] = []
        logger.info("RepoAnalyzerSwarm initialised for %s", self.repo_root)

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def crawl_directory_structure(self) -> dict[str, Any]:
        """
        Discover all Python files under *repo_root* and compute LOC per module.

        Returns
        -------
        dict
            Keys: ``total_files``, ``total_loc``, ``modules`` (mapping of
            relative path to LOC count).
        """
        logger.info("Crawling directory structure …")
        self._python_files = list(self.repo_root.rglob("*.py"))
        total_loc = 0
        module_map: dict[str, int] = {}

        for py_file in self._python_files:
            rel = str(py_file.relative_to(self.repo_root))
            loc = self._count_loc(py_file)
            module_map[rel] = loc
            total_loc += loc

        result = {
            "total_files": len(self._python_files),
            "total_loc": total_loc,
            "modules": module_map,
        }
        logger.info(
            "Found %d Python files with %d total LOC",
            result["total_files"],
            result["total_loc"],
        )
        return result

    def extract_import_graph(self) -> dict[str, Any]:
        """
        Build a bidirectional dependency graph between modules.

        Returns
        -------
        dict
            ``nodes`` — list of module relative paths.  
            ``edges`` — list of ``{from, to}`` dicts.  
            ``reverse_edges`` — dict mapping module to its importers.
        """
        logger.info("Extracting import graph …")
        self._ensure_modules_analysed()

        nodes: list[str] = []
        edges: list[dict[str, str]] = []
        reverse_edges: dict[str, list[str]] = {}

        for mod in self.modules.values():
            nodes.append(mod.rel_path)
            if mod.rel_path not in reverse_edges:
                reverse_edges[mod.rel_path] = []

            for imp in mod.imports:
                # Heuristic: match import to a local module
                target = self._resolve_import_to_module(imp)
                if target and target != mod.rel_path:
                    edges.append({"from": mod.rel_path, "to": target})
                    reverse_edges.setdefault(target, []).append(mod.rel_path)
                    if target not in nodes:
                        nodes.append(target)

        return {
            "nodes": nodes,
            "edges": edges,
            "reverse_edges": reverse_edges,
        }

    def find_dead_code(self) -> list[str]:
        """
        Identify files that are not imported by any other module.

        Returns
        -------
        list[str]
            Relative paths of potentially dead modules.
        """
        logger.info("Searching for dead code …")
        self._ensure_modules_analysed()
        graph = self.extract_import_graph()
        reverse_edges: dict[str, list[str]] = graph["reverse_edges"]

        dead: list[str] = []
        for mod_path in graph["nodes"]:
            importers = reverse_edges.get(mod_path, [])
            # A file is "dead" if nothing imports it and it is not a top-level script
            if not importers and not self._is_likely_entry_point(mod_path):
                dead.append(mod_path)

        logger.info("Found %d potentially dead modules", len(dead))
        return dead

    def find_todo_fixme(self) -> list[dict[str, Any]]:
        """
        Extract every TODO / FIXME / HACK comment with file and line number.

        Returns
        -------
        list[dict]
            Each dict has keys ``file``, ``line``, ``tag``, ``text``.
        """
        logger.info("Scanning for TODO/FIXME/HACK comments …")
        self._ensure_modules_analysed()

        results: list[dict[str, Any]] = []
        for mod in self.modules.values():
            for item in mod.todo_fixme_items:
                results.append(
                    {
                        "file": mod.rel_path,
                        "line": item["line"],
                        "tag": item["tag"],
                        "text": item["text"],
                    }
                )

        logger.info("Found %d TODO/FIXME/HACK items", len(results))
        return results

    def analyze_code_quality(self) -> dict[str, Any]:
        """
        Compute aggregate code-quality metrics across the repository.

        Returns
        -------
        dict
            ``avg_function_length``, ``avg_cyclomatic_complexity``,
            ``total_functions``, ``total_classes``, ``test_coverage_estimate``,
            ``per_module`` breakdown.
        """
        logger.info("Analysing code quality …")
        self._ensure_modules_analysed()

        total_functions = 0
        total_classes = 0
        total_function_lines = 0
        total_complexity = 0.0
        per_module: dict[str, dict[str, Any]] = {}

        for mod in self.modules.values():
            total_functions += mod.function_count
            total_classes += mod.class_count
            total_function_lines += mod.avg_function_length * mod.function_count
            total_complexity += mod.cyclomatic_complexity

            per_module[mod.rel_path] = {
                "loc": mod.lines_of_code,
                "functions": mod.function_count,
                "classes": mod.class_count,
                "avg_function_length": round(mod.avg_function_length, 2),
                "cyclomatic_complexity": round(mod.cyclomatic_complexity, 2),
                "import_count": mod.import_count,
            }

        avg_function_length = (
            total_function_lines / total_functions if total_functions else 0.0
        )
        avg_complexity = (
            total_complexity / total_functions if total_functions else 0.0
        )

        # Simple heuristic: if a module has a corresponding test file, count it
        test_files = [
            f for f in self._python_files if "test" in f.name.lower() or f.name.startswith("test_")
        ]
        coverage_estimate = min(
            100.0, len(test_files) * 15.0
        )  # rough heuristic: ~15% coverage per test file

        result = {
            "avg_function_length": round(avg_function_length, 2),
            "avg_cyclomatic_complexity": round(avg_complexity, 2),
            "total_functions": total_functions,
            "total_classes": total_classes,
            "test_coverage_estimate": round(coverage_estimate, 2),
            "per_module": per_module,
        }
        logger.info("Code quality analysis complete: %s", result)
        return result

    def generate_repo_report(self) -> str:
        """
        Generate a full Markdown report of the repository analysis.

        Returns
        -------
        str
            Markdown-formatted report.
        """
        logger.info("Generating repository report …")
        structure = self.crawl_directory_structure()
        quality = self.analyze_code_quality()
        dead_code = self.find_dead_code()
        todos = self.find_todo_fixme()
        import_graph = self.extract_import_graph()

        lines: list[str] = []
        lines.append("# Repository Analysis Report\n")
        lines.append(f"**Root:** `{self.repo_root}`  ")
        lines.append(
            f"**Generated:** {__import__('datetime').datetime.now().isoformat()}\n"
        )

        # Summary
        lines.append("## Summary\n")
        lines.append(f"- **Total Python files:** {structure['total_files']}")
        lines.append(f"- **Total LOC:** {structure['total_loc']:,}")
        lines.append(f"- **Total functions:** {quality['total_functions']}")
        lines.append(f"- **Total classes:** {quality['total_classes']}")
        lines.append(f"- **Avg function length:** {quality['avg_function_length']} lines")
        lines.append(
            f"- **Avg cyclomatic complexity:** {quality['avg_cyclomatic_complexity']}"
        )
        lines.append(
            f"- **Test coverage estimate:** {quality['test_coverage_estimate']}%"
        )
        lines.append(f"- **Dead modules:** {len(dead_code)}")
        lines.append(f"- **TODO/FIXME/HACK items:** {len(todos)}\n")

        # Directory structure
        lines.append("## Directory Structure\n")
        lines.append("```")
        dir_tree = self._build_dir_tree()
        lines.extend(dir_tree)
        lines.append("```\n")

        # Import graph
        lines.append("## Import Graph\n")
        lines.append(f"- **Nodes:** {len(import_graph['nodes'])}")
        lines.append(f"- **Edges:** {len(import_graph['edges'])}\n")
        if import_graph["edges"]:
            lines.append("| From | To |")
            lines.append("|------|----|")
            for edge in import_graph["edges"]:
                lines.append(f"| `{edge['from']}` | `{edge['to']}` |")
            lines.append("")

        # Dead code
        if dead_code:
            lines.append("## Dead Code (Potentially Unused Modules)\n")
            for mod in dead_code:
                lines.append(f"- `{mod}`")
            lines.append("")

        # TODO/FIXME
        if todos:
            lines.append("## TODO / FIXME / HACK\n")
            lines.append("| File | Line | Tag | Text |")
            lines.append("|------|------|-----|------|")
            for item in todos:
                text = item["text"].replace("|", "\\|")
                lines.append(
                    f"| `{item['file']}` | {item['line']} | {item['tag']} | {text} |"
                )
            lines.append("")

        # Per-module quality
        lines.append("## Per-Module Quality\n")
        lines.append(
            "| Module | LOC | Functions | Classes | Avg Fn Length | Complexity | Imports |"
        )
        lines.append(
            "|--------|-----|-----------|---------|---------------|------------|---------|"
        )
        for mod_path, metrics in quality["per_module"].items():
            lines.append(
                f"| `{mod_path}` | {metrics['loc']} | {metrics['functions']} | "
                f"{metrics['classes']} | {metrics['avg_function_length']} | "
                f"{metrics['cyclomatic_complexity']} | {metrics['import_count']} |"
            )
        lines.append("")

        logger.info("Repository report generated (%d lines)", len(lines))
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    def _count_loc(self, path: Path) -> int:
        """Count non-blank, non-comment lines of code."""
        try:
            with open(path, "r", encoding="utf-8") as fh:
                lines = fh.readlines()
        except OSError as exc:
            logger.warning("Cannot read %s: %s", path, exc)
            return 0

        loc = 0
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                loc += 1
        return loc

    def _ensure_modules_analysed(self) -> None:
        """Lazily parse every Python file with the AST visitor."""
        if self.modules:
            return
        if not self._python_files:
            self.crawl_directory_structure()

        for py_file in self._python_files:
            rel = str(py_file.relative_to(self.repo_root))
            try:
                source = py_file.read_text(encoding="utf-8")
            except OSError as exc:
                logger.warning("Skipping %s: %s", py_file, exc)
                continue

            analyzer = _ModuleAnalyzer(source)
            analyzer.analyze()

            avg_fn_len = (
                analyzer.total_function_lines / analyzer.function_count
                if analyzer.function_count
                else 0.0
            )

            self.modules[rel] = ModuleInfo(
                path=str(py_file),
                rel_path=rel,
                lines_of_code=self._count_loc(py_file),
                function_count=analyzer.function_count,
                class_count=analyzer.class_count,
                avg_function_length=round(avg_fn_len, 2),
                cyclomatic_complexity=round(analyzer.cyclomatic_complexity, 2),
                import_count=len(analyzer.imports),
                todo_fixme_items=analyzer.todo_fixme_items,
                classes=analyzer.classes,
                functions=analyzer.functions,
                imports=analyzer.imports,
            )

    def _resolve_import_to_module(self, import_name: str) -> str | None:
        """
        Heuristic: map a fully-qualified import name back to a relative
        module path inside the repository.
        """
        # Try direct match: a.b.c -> a/b/c.py
        parts = import_name.split(".")
        candidate = "/".join(parts) + ".py"
        if candidate in self.modules:
            return candidate

        # Try package init: a.b -> a/b/__init__.py
        candidate_init = "/".join(parts) + "/__init__.py"
        if candidate_init in self.modules:
            return candidate_init

        # Try progressively shorter prefixes
        for i in range(len(parts) - 1, 0, -1):
            prefix = "/".join(parts[:i]) + ".py"
            if prefix in self.modules:
                return prefix
            prefix_init = "/".join(parts[:i]) + "/__init__.py"
            if prefix_init in self.modules:
                return prefix_init

        return None

    def _is_likely_entry_point(self, rel_path: str) -> bool:
        """Return *True* if the file looks like a top-level script."""
        lower = rel_path.lower()
        entry_indicators = [
            "__main__",
            "main.py",
            "run_",
            "entry_",
            "app.py",
            "server.py",
            "manage.py",
            "setup.py",
        ]
        return any(ind in lower for ind in entry_indicators)

    def _build_dir_tree(self) -> list[str]:
        """Build a textual directory tree of Python files."""
        if not self._python_files:
            self.crawl_directory_structure()

        dirs: dict[str, list[str]] = {}
        for py_file in self._python_files:
            rel = str(py_file.relative_to(self.repo_root))
            parent = str(py_file.parent.relative_to(self.repo_root))
            dirs.setdefault(parent, []).append(py_file.name)

        lines: list[str] = [str(self.repo_root)]
        for parent in sorted(dirs):
            depth = parent.count(os.sep) + 1 if parent != "." else 0
            indent = "    " * depth
            display = parent.split(os.sep)[-1] if parent != "." else "."
            lines.append(f"{indent}{display}/")
            sub_indent = "    " * (depth + 1)
            for name in sorted(dirs[parent]):
                lines.append(f"{sub_indent}{name}")
        return lines


# ---------------------------------------------------------------------------
# PredictionPipelineMapper
# ---------------------------------------------------------------------------


class PredictionPipelineMapper:
    """
    Maps the data flow through the prediction pipeline.

    Identifies entry points (raw-data ingestion) and output points
    (published predictions / tracked outcomes) by scanning the repository
    for characteristic module names, class names, and function names.
    """

    # Stage keywords used to heuristic-match files to pipeline stages
    STAGE_KEYWORDS: dict[str, list[str]] = {
        "data_ingestion": [
            "fetch",
            "download",
            "scrape",
            "ingest",
            "collect",
            "api",
            "client",
            "source",
        ],
        "feature_engineering": [
            "feature",
            "transform",
            "preprocess",
            "indicator",
            "signal",
            "engineering",
            "extract",
        ],
        "model_training": [
            "train",
            "fit",
            "model",
            "learner",
            "classifier",
            "regressor",
            "backtest",
        ],
        "prediction_generation": [
            "predict",
            "forecast",
            "inference",
            "score",
            "generate",
            "pick",
            "swarm_pick",
        ],
        "outcome_tracking": [
            "outcome",
            "resolve",
            "track",
            "result",
            "evaluate",
            "performance",
            "leaderboard",
            "review",
        ],
    }

    def __init__(self, repo_analyzer: RepoAnalyzerSwarm) -> None:
        """
        Parameters
        ----------
        repo_analyzer:
            An already-initialised :class:`RepoAnalyzerSwarm`.
        """
        self.repo_analyzer = repo_analyzer
        self.repo_analyzer._ensure_modules_analysed()
        logger.info("PredictionPipelineMapper initialised")

    def trace_prediction_flow(self) -> dict[str, Any]:
        """
        Trace the prediction pipeline stages and associate files with each.

        Returns
        -------
        dict
            ``stages`` — ordered list of pipeline stages.  
            ``entry_points`` — files that ingest raw data.  
            ``output_points`` — files that emit or track predictions.
        """
        logger.info("Tracing prediction pipeline flow …")
        modules = self.repo_analyzer.modules

        stages: dict[str, PipelineStage] = {
            name: PipelineStage(
                name=name,
                description=self._stage_description(name),
            )
            for name in self.STAGE_KEYWORDS
        }

        for rel_path, mod in modules.items():
            lower_path = rel_path.lower()
            all_names = " ".join(mod.classes + mod.functions).lower()

            for stage_name, keywords in self.STAGE_KEYWORDS.items():
                if any(kw in lower_path for kw in keywords) or any(
                    kw in all_names for kw in keywords
                ):
                    stages[stage_name].files.append(rel_path)

        # Detect entry / output points
        entry_points: list[str] = []
        output_points: list[str] = []

        for rel_path, mod in modules.items():
            lower = rel_path.lower()
            if any(kw in lower for kw in ("main", "run", "entry", "app", "server")):
                entry_points.append(rel_path)
            if any(
                kw in lower
                for kw in (
                    "output",
                    "publish",
                    "predict",
                    "pick",
                    "resolve",
                    "leaderboard",
                )
            ):
                output_points.append(rel_path)

        # Populate entry/output into stages
        stages["data_ingestion"].entry_points = entry_points
        stages["outcome_tracking"].output_points = output_points

        result = {
            "stages": [
                {
                    "name": s.name,
                    "description": s.description,
                    "files": s.files,
                    "entry_points": s.entry_points,
                    "output_points": s.output_points,
                }
                for s in stages.values()
            ],
            "entry_points": entry_points,
            "output_points": output_points,
        }
        logger.info("Pipeline flow traced: %d stages identified", len(stages))
        return result

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _stage_description(stage_name: str) -> str:
        descriptions: dict[str, str] = {
            "data_ingestion": "Raw market and alternative data ingestion",
            "feature_engineering": "Feature extraction, transformation, and technical-indicator generation",
            "model_training": "Model fitting, hyper-parameter tuning, and backtesting",
            "prediction_generation": "Inference-time prediction and swarm-pick generation",
            "outcome_tracking": "Post-trade outcome resolution and performance tracking",
        }
        return descriptions.get(stage_name, "")


# ---------------------------------------------------------------------------
# Convenience entry-point
# ---------------------------------------------------------------------------


def main() -> None:  # pragma: no cover
    """CLI convenience runner."""
    import argparse

    parser = argparse.ArgumentParser(description="Repository analysis swarm")
    parser.add_argument("repo_root", help="Path to repository root")
    parser.add_argument("--report", action="store_true", help="Generate markdown report")
    parser.add_argument("--pipeline", action="store_true", help="Trace prediction pipeline")
    args = parser.parse_args()

    analyzer = RepoAnalyzerSwarm(args.repo_root)

    if args.report:
        print(analyzer.generate_repo_report())

    if args.pipeline:
        mapper = PredictionPipelineMapper(analyzer)
        import json

        print(json.dumps(mapper.trace_prediction_flow(), indent=2))

    if not args.report and not args.pipeline:
        # Default: quick summary
        struct = analyzer.crawl_directory_structure()
        print(f"Files: {struct['total_files']}, LOC: {struct['total_loc']}")


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    main()
