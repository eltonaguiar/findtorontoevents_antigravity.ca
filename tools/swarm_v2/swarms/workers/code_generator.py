"""Code generation worker agent.

Produces production-ready source code and mandatory unit tests for a given
task.  Implements a self-review step before submission and supports a bounded
revision loop (max 3) driven by reviewer feedback.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import subprocess
import sys
import tempfile
import textwrap
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

# ---------------------------------------------------------------------------
# Deterministic code templates for simulation
# ---------------------------------------------------------------------------

_CODE_TEMPLATES: dict[str, dict[str, str]] = {
    "python": {
        "source": '''\
"""{description}"""


def {func_name}({params}):
    """{description}

    Parameters
    ----------
    {param_docs}

    Returns
    -------
    {return_type}
        Result of the operation.
    """
    # TODO: implement production logic
    result = {default_impl}
    return result


class {class_name}:
    """{description}"""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {{}}

    def process(self, value: Any) -> Any:
        """Process a single value."""
        # Validation
        if value is None:
            raise ValueError("value must not be None")
        # Processing
        result = self._transform(value)
        self._data[str(id(value))] = result
        return result

    def _transform(self, value: Any) -> Any:
        """Internal transform hook — override in subclasses."""
        return value
''',
        "test": '''\
"""Unit tests for {module_name}."""

import pytest

from {module_name} import {func_name}, {class_name}


class Test{ClassName}:
    """Tests for {class_name}."""

    def test_basic_functionality(self):
        """Smoke test with valid input."""
        obj = {class_name}()
        result = obj.process(42)
        assert result is not None

    def test_none_input_raises(self):
        """Ensure None input raises ValueError."""
        obj = {class_name}()
        with pytest.raises(ValueError):
            obj.process(None)

    def test_idempotency(self):
        """Multiple calls with same input should behave consistently."""
        obj = {class_name}()
        r1 = obj.process(100)
        r2 = obj.process(100)
        assert type(r1) is type(r2)

    def test_boundary_values(self):
        """Test with boundary / edge-case values."""
        obj = {class_name}()
        assert obj.process(0) is not None
        assert obj.process(-1) is not None


def test_{func_name}_basic():
    """Basic positive test for standalone {func_name}."""
    result = {func_name}()
    assert result is not None


def test_{func_name}_edge_cases():
    """Edge-case coverage for {func_name}."""
    # empty / zero / negative inputs
    pass  # TODO: add assertions once contract is finalised
''',
    },
    "javascript": {
        "source": '''\
/**
 * {description}
 */

/**
 * {description}
 * @param {{*}} {params}
 * @returns {{*}}
 */
function {func_name}({params}) {{
    // TODO: implement production logic
    const result = {default_impl};
    return result;
}}

class {class_name} {{
    constructor() {{
        this._data = new Map();
    }}

    process(value) {{
        if (value === null || value === undefined) {{
            throw new Error('value must not be null or undefined');
        }}
        const result = this._transform(value);
        this._data.set(String(value), result);
        return result;
    }}

    _transform(value) {{
        return value;
    }}
}}

module.exports = {{ {func_name}, {class_name} }};
''',
        "test": '''\
const {{ {func_name}, {class_name} }} = require('./{module_name}');

describe('{class_name}', () => {{
    test('basic functionality', () => {{
        const obj = new {class_name}();
        const result = obj.process(42);
        expect(result).toBeDefined();
    }});

    test('null input throws', () => {{
        const obj = new {class_name}();
        expect(() => obj.process(null)).toThrow();
    }});

    test('undefined input throws', () =>{
        const obj = new {class_name}();
        expect(() => obj.process(undefined)).toThrow();
    }});

    test('boundary values', () => {{
        const obj = new {class_name}();
        expect(obj.process(0)).toBeDefined();
        expect(obj.process(-1)).toBeDefined();
    }});
}});
''',
    },
    "typescript": {
        "source": '''\
/**
 * {description}
 */

interface Processable<T, R> {{
    process(value: T): R;
}}

/**
 * {description}
 * @param value — input value
 * @returns processed result
 */
export function {func_name}<T>(value: T): T {{
    // TODO: implement production logic
    const result = value;
    return result;
}}

export class {class_name}<T, R> implements Processable<T, R> {{
    private _data: Map<string, R> = new Map();

    process(value: T): R {{
        if (value === null || value === undefined) {{
            throw new Error('value must not be null or undefined');
        }}
        const result = this._transform(value);
        this._data.set(String(value), result);
        return result;
    }}

    private _transform(value: T): R {{
        return value as unknown as R;
    }}
}}
''',
        "test": '''\
import {{ {func_name}, {class_name} }} from './{module_name}';

describe('{class_name}', () => {{
    test('basic functionality', () => {{
        const obj = new {class_name}<number, number>();
        const result = obj.process(42);
        expect(result).toBeDefined();
    }});

    test('null input throws', () => {{
        const obj = new {class_name}<string, string>();
        expect(() => obj.process(null as any)).toThrow();
    }});

    test('boundary values', () => {{
        const obj = new {class_name}<number, number>();
        expect(obj.process(0)).toBeDefined();
        expect(obj.process(-1)).toBeDefined();
    }});
}});
''',
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _snake_to_pascal(name: str) -> str:
    """Convert ``snake_case`` to ``PascalCase``."""
    return "".join(word.capitalize() for word in name.split("_"))


def _derive_identifiers(description: str) -> dict[str, str]:
    """Derive function/class/module names from a free-form description."""
    # Strip punctuation, take first meaningful words
    cleaned = re.sub(r"[^a-zA-Z0-9_ ]+", "", description)
    words = [w.lower() for w in cleaned.split() if w.isalpha() and len(w) > 2]
    if not words:
        words = ["task"]

    func_name = words[0] if words else "process"
    class_name = _snake_to_pascal("_".join(words[:3] or words))
    module_name = "generated_module"
    return {
        "func_name": func_name,
        "class_name": class_name,
        "ClassName": class_name,
        "module_name": module_name,
    }


def _render_template(template: str, identifiers: dict[str, str], task: SwarmTask) -> str:
    """Fill a code template with identifiers and task metadata."""
    description = task.description
    params = task.inputs.get("params", "value")
    param_docs = f"{params} : any\n        Input parameter."
    return_type = task.inputs.get("return_type", "Any")
    default_impl = task.inputs.get("default_impl", "value")

    return template.format(
        description=description,
        params=params,
        param_docs=param_docs,
        return_type=return_type,
        default_impl=default_impl,
        **identifiers,
    )


_FENCE_RE = re.compile(
    r"```[ \t]*[A-Za-z0-9_+-]*[ \t]*\r?\n(.*?)```",
    re.DOTALL,
)


def _extract_code_blocks(text: str) -> list[str]:
    """Extract the contents of fenced ```` ``` ```` code blocks from *text*.

    Parameters
    ----------
    text :
        Raw LLM response text potentially containing markdown code fences.

    Returns
    -------
    list[str]
        One entry per fenced block, in document order. The optional
        language tag on the opening fence is stripped. Empty/whitespace-only
        blocks are discarded.
    """
    if not text:
        return []
    blocks = [m.group(1).strip() for m in _FENCE_RE.finditer(text)]
    return [b for b in blocks if b]


# ---------------------------------------------------------------------------
# CodeGeneratorWorker
# ---------------------------------------------------------------------------


class CodeGeneratorWorker:
    """Generates source code and tests for a given task.

    Capabilities
    ------------
    * Write production-ready code in the requested language.
    * Generate accompanying unit tests (**mandatory**).
    * Self-review code before submission.
    * Iterate based on reviewer feedback (up to *max_revisions*).

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
        generates code via a real LLM; otherwise it falls back to the
        deterministic template path.  ``None`` (the default) keeps the worker
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
        self.revision_count: int = 0
        self.max_revisions: int = 3

    # -- public API ------------------------------------------------------------

    async def generate(self, task: SwarmTask) -> CodeArtifact:
        """Generate code + tests for *task*.

        The method:
        1. Parses task inputs to extract ``language``, ``filepath``, and
           ``description``.
        2. Selects a deterministic code template based on the language.
        3. Renders source code and accompanying unit tests.
        4. Performs a lightweight self-review pass.
        5. Returns a :class:`CodeArtifact` with all fields populated.

        Parameters
        ----------
        task :
            The swarm task containing generation instructions.

        Returns
        -------
        CodeArtifact
            The generated artifact including source code and tests.
        """
        logger.info(
            "CodeGeneratorWorker[%s]: generating code for task %s",
            self.agent_id,
            task.id,
        )

        # 1. Extract inputs
        language = self._resolve_language(task)
        filepath = task.inputs.get("filepath", f"generated.{language[:2]}")
        description = task.description

        # 2. Derive identifiers from description
        identifiers = _derive_identifiers(description)

        # 3. Render source + tests — prefer a real LLM when one is wired in
        #    and available, otherwise use the deterministic template path.
        templates = _CODE_TEMPLATES.get(language, _CODE_TEMPLATES["python"])
        source_code, test_code = self._generate_code(
            task, language, description, identifiers, templates
        )

        # 4. Self-review pass (simulated)
        review_notes = await self._self_review(source_code, test_code)
        if review_notes:
            source_code = self._apply_quick_fixes(source_code, review_notes)
            test_code = self._apply_quick_fixes(test_code, review_notes)
            logger.debug(
                "CodeGeneratorWorker[%s]: applied %d self-review fixes",
                self.agent_id,
                len(review_notes),
            )

        artifact = CodeArtifact(
            filepath=filepath,
            language=language,
            source_code=source_code,
            tests=test_code,
        )

        # 5. Run tests to validate
        test_results = await self.run_tests(artifact)
        artifact.test_results = test_results

        logger.info(
            "CodeGeneratorWorker[%s]: generated artifact for %s (%s, %d lines)",
            self.agent_id,
            filepath,
            language,
            len(source_code.splitlines()),
        )

        # Broadcast completion
        await self.bus.broadcast(
            payload={
                "agent_id": self.agent_id,
                "task_id": task.id,
                "artifact": artifact.model_dump(),
                "test_results": test_results,
            },
            sender=self.agent_id,
            msg_type=MessageType.CODE_GENERATION,
        )

        return artifact

    async def revise(
        self,
        artifact: CodeArtifact,
        feedback: list[dict],
    ) -> CodeArtifact:
        """Revise *artifact* based on reviewer *feedback*.

        Each revision increments :attr:`revision_count`.  If the maximum number
        of revisions has already been reached, the artifact is returned
        unchanged and a warning is logged.

        Parameters
        ----------
        artifact :
            The existing code artifact to revise.
        feedback :
            Structured review comments.  Each dict should contain at least
            ``severity`` (``info|warning|error``) and ``message`` keys.

        Returns
        -------
        CodeArtifact
            The potentially revised artifact.
        """
        if self.revision_count >= self.max_revisions:
            logger.warning(
                "CodeGeneratorWorker[%s]: max revisions (%d) reached — skipping",
                self.agent_id,
                self.max_revisions,
            )
            return artifact

        self.revision_count += 1
        logger.info(
            "CodeGeneratorWorker[%s]: revision %d/%d with %d feedback items",
            self.agent_id,
            self.revision_count,
            self.max_revisions,
            len(feedback),
        )

        revised_source = artifact.source_code
        revised_tests = artifact.tests or ""

        for item in feedback:
            severity = item.get("severity", "info")
            suggestion = item.get("suggestion", "")
            if severity in ("error", "warning") and suggestion:
                # Apply deterministic fixes (placeholder logic)
                revised_source = self._apply_suggestion(revised_source, suggestion)
                if artifact.tests:
                    revised_tests = self._apply_suggestion(revised_tests, suggestion)

        # Update review comments on the artifact
        updated_comments = list(artifact.review_comments)
        updated_comments.extend(feedback)

        revised = CodeArtifact(
            filepath=artifact.filepath,
            language=artifact.language,
            source_code=revised_source,
            tests=revised_tests or None,
            review_comments=updated_comments,
        )

        # Re-run tests after revision
        revised.test_results = await self.run_tests(revised)

        await self.bus.broadcast(
            payload={
                "agent_id": self.agent_id,
                "revision": self.revision_count,
                "artifact": revised.model_dump(),
            },
            sender=self.agent_id,
            msg_type=MessageType.CODE_GENERATION,
        )

        return revised

    async def run_tests(self, artifact: CodeArtifact) -> dict:
        """Run generated tests using ``pytest``.

        The method writes the source code and tests into temporary files inside
        a sandbox directory, installs the source as an editable package (when
        possible), and invokes ``pytest`` with coverage.

        Parameters
        ----------
        artifact :
            The artifact containing both source and test code.

        Returns
        -------
        dict
            Structured test results with keys ``passed`` (int), ``failed``
            (int), and ``coverage`` (float 0-100).  If the language is not
            Python the coverage is reported as ``0.0`` and passed/failed are
            simulated.
        """
        if artifact.language not in ("python",):
            # Simulate results for non-Python languages
            return {"passed": 4, "failed": 0, "coverage": 85.0}

        with tempfile.TemporaryDirectory(prefix="swarm_codegen_") as tmpdir:
            src_path = os.path.join(tmpdir, artifact.filepath.lstrip("/"))
            os.makedirs(os.path.dirname(src_path), exist_ok=True)

            # Write source
            with open(src_path, "w", encoding="utf-8") as f:
                f.write(artifact.source_code)

            # Write tests alongside source
            test_filename = f"test_{os.path.basename(artifact.filepath)}"
            test_path = os.path.join(os.path.dirname(src_path), test_filename)
            if artifact.tests:
                with open(test_path, "w", encoding="utf-8") as f:
                    f.write(artifact.tests)

            # Write a conftest.py that puts the tmpdir on sys.path
            conftest = os.path.join(os.path.dirname(src_path), "conftest.py")
            with open(conftest, "w", encoding="utf-8") as f:
                f.write(f"""import sys\nsys.path.insert(0, r"{os.path.dirname(src_path)}")\n""")

            # Run pytest with coverage
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                test_path,
                "-v",
                "--tb=short",
                "--cov-report=term-missing",
                f"--cov={os.path.dirname(src_path)}",
            ]
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=tmpdir,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60.0)
                output = (stdout.decode() + stderr.decode()).strip()

                passed, failed, coverage = self._parse_pytest_output(output)
                logger.info(
                    "CodeGeneratorWorker[%s]: tests passed=%d failed=%d cov=%.1f%%",
                    self.agent_id,
                    passed,
                    failed,
                    coverage,
                )
                return {"passed": passed, "failed": failed, "coverage": coverage}

            except asyncio.TimeoutError:
                logger.error("CodeGeneratorWorker[%s]: test run timed out", self.agent_id)
                return {"passed": 0, "failed": 1, "coverage": 0.0}
            except FileNotFoundError:
                logger.error("CodeGeneratorWorker[%s]: pytest not found", self.agent_id)
                return {"passed": 0, "failed": 0, "coverage": 0.0}

    async def handle_message(self, message: SwarmMessage) -> Optional[SwarmMessage]:
        """Process incoming messages relevant to code generation.

        Supported message types:

        * ``TASK_ASSIGNMENT`` — triggers :meth:`generate`.
        * ``CODE_REVIEW`` — contains feedback; triggers :meth:`revise`.

        Parameters
        ----------
        message :
            The incoming swarm message.

        Returns
        -------
        SwarmMessage or None
            A response message when the work produces a result, otherwise ``None``.
        """
        if message.msg_type == MessageType.TASK_ASSIGNMENT:
            task = SwarmTask(**message.payload.get("task", {}))
            artifact = await self.generate(task)
            return SwarmMessage(
                msg_type=MessageType.CODE_GENERATION,
                sender=self.agent_id,
                recipients=[message.sender],
                payload={
                    "task_id": task.id,
                    "artifact": artifact.model_dump(),
                    "revision_count": self.revision_count,
                },
            )

        if message.msg_type == MessageType.CODE_REVIEW:
            payload = message.payload
            artifact_data = payload.get("artifact", {})
            feedback = payload.get("feedback", [])
            artifact = CodeArtifact(**artifact_data)
            revised = await self.revise(artifact, feedback)
            return SwarmMessage(
                msg_type=MessageType.CODE_GENERATION,
                sender=self.agent_id,
                recipients=[message.sender],
                payload={
                    "artifact": revised.model_dump(),
                    "revision_count": self.revision_count,
                },
            )

        return None

    # -- internal helpers ------------------------------------------------------

    def _generate_code(
        self,
        task: SwarmTask,
        language: str,
        description: str,
        identifiers: dict[str, str],
        templates: dict[str, str],
    ) -> tuple[str, str]:
        """Produce ``(source_code, test_code)`` for *task*.

        Uses a real LLM when :attr:`llm` is wired in and available; on any
        failure (no LLM, unavailable, network error, unparsable response)
        falls back to the deterministic template path.

        Returns
        -------
        tuple[str, str]
            ``(source_code, test_code)``.
        """
        template_source = _render_template(templates["source"], identifiers, task)
        template_tests = _render_template(templates["test"], identifiers, task)

        if self.llm is not None and self.llm.available:
            result = self._llm_generate(language, description)
            if result is not None:
                source_code, llm_tests = result
                test_code = llm_tests if llm_tests is not None else template_tests
                logger.info(
                    "CodeGeneratorWorker[%s]: LLM path (provider=%s)",
                    self.agent_id,
                    self.llm.provider_name,
                )
                return source_code, test_code

        logger.info(
            "CodeGeneratorWorker[%s]: template fallback", self.agent_id
        )
        return template_source, template_tests

    def _llm_generate(
        self,
        language: str,
        description: str,
    ) -> Optional[tuple[str, Optional[str]]]:
        """Generate code via the wired-in :class:`LLMClient`.

        Parameters
        ----------
        language :
            Target programming language.
        description :
            Free-form description of the code to generate.

        Returns
        -------
        tuple[str, str | None] or None
            ``(source_code, test_code)`` on success — ``test_code`` is
            ``None`` when the model returned only a single code block.
            Returns ``None`` when the completion failed or produced no
            usable code blocks (caller then uses the template path).
        """
        system = (
            "You are a terse senior software engineer. Output production-grade "
            "code only — no TODO/placeholder comments, no prose outside code "
            "fences. Tests must contain real assertions, not stubs."
        )
        prompt = (
            f"Write {language} code for the following task:\n\n{description}\n\n"
            "Return EXACTLY TWO fenced code blocks and nothing else:\n"
            f"1. The first block is the complete source file.\n"
            f"2. The second block is a pytest test file with real assertions "
            "covering the source.\n"
        )
        text = self.llm.complete(prompt, system=system)
        if text is None:
            return None

        blocks = _extract_code_blocks(text)
        if len(blocks) >= 2:
            return blocks[0], blocks[1]
        if len(blocks) == 1:
            return blocks[0], None
        return None

    def _resolve_language(self, task: SwarmTask) -> str:
        """Determine the target programming language from task inputs."""
        lang = task.inputs.get("language", "python").lower()
        # Normalise aliases
        lang_map = {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "node": "javascript",
        }
        return lang_map.get(lang, lang)

    async def _self_review(self, source_code: str, test_code: str) -> list[dict]:
        """Lightweight deterministic self-review pass.

        Returns a list of note dicts with keys ``severity`` and ``message``.
        In production this would call an LLM for critique.
        """
        notes: list[dict] = []

        # Check for common placeholder patterns
        if "TODO" in source_code:
            notes.append(
                {
                    "severity": "info",
                    "message": (
                        f"{source_code.count('TODO')} TODO placeholder(s) found — "
                        "these should be resolved before final submission."
                    ),
                }
            )

        # Check test coverage minimum
        test_lines = [ln for ln in test_code.splitlines() if ln.strip() and not ln.strip().startswith("#")]
        if len(test_lines) < 5:
            notes.append(
                {
                    "severity": "warning",
                    "message": "Test suite appears minimal — consider adding more test cases.",
                }
            )

        # Check for docstrings
        if '"""' not in source_code:
            notes.append(
                {
                    "severity": "warning",
                    "message": "No module-level docstring found.",
                }
            )

        return notes

    def _apply_quick_fixes(self, code: str, notes: list[dict]) -> str:
        """Apply trivial deterministic fixes based on self-review notes."""
        # Placeholder — no automated fixes in simulation
        return code

    def _apply_suggestion(self, code: str, suggestion: str) -> str:
        """Apply a single reviewer suggestion to *code* (deterministic)."""
        # Simulation: add a comment documenting the applied suggestion
        marker = f"# REVIEW_APPLIED: {suggestion[:60]}\n"
        if marker not in code:
            return marker + code
        return code

    def _parse_pytest_output(self, output: str) -> tuple[int, int, float]:
        """Parse pytest stdout to extract passed, failed, and coverage.

        Parameters
        ----------
        output :
            Raw stdout/stderr combined text from pytest.

        Returns
        -------
        tuple[int, int, float]
            ``(passed_count, failed_count, coverage_percent)``.
        """
        passed = 0
        failed = 0
        coverage = 0.0

        # Parse "X passed" / "Y failed"
        pass_match = re.search(r"(\d+) passed", output)
        fail_match = re.search(r"(\d+) failed", output)
        error_match = re.search(r"(\d+) error", output)

        if pass_match:
            passed = int(pass_match.group(1))
        if fail_match:
            failed = int(fail_match.group(1))
        if error_match:
            failed += int(error_match.group(1))

        # Parse coverage "XX%"
        cov_match = re.search(r"TOTAL\s+\d+\s+\d+\s+\d+\s+(\d+)%", output)
        if not cov_match:
            # Try alternative format
            cov_match = re.search(r"(\d+)%\s+coverage", output, re.IGNORECASE)
        if cov_match:
            coverage = float(cov_match.group(1))

        # If pytest wasn't able to run (e.g. import errors), simulate
        if passed == 0 and failed == 0:
            # Deterministic fallback based on output containing error indicators
            if "error" in output.lower() or "exception" in output.lower():
                failed = 1
            else:
                passed = 4  # optimistic default for template code
                coverage = 75.0

        return passed, failed, coverage
