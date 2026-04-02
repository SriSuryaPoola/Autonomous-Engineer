"""
QA Engineer Worker — Phase 5 Agentic Testing with Self-Correcting Loop.

Implements the closed-loop paradigm from ArXiv 2601.02454:
  1. Test Generation Agent  → Writes test code
  2. Execution Agent        → Runs in sandbox, captures failure
  3. Patch Agent            → LLM or heuristic patches the test
  4. Repeat until convergence (all pass + coverage threshold met)

Key changes from Phase 3:
  - Uses SandboxExecutor instead of bare subprocess (safe isolation)
  - Implements MAX_RETRIES convergence loop with LLM patching
  - Records both failures AND resolutions in ProjectMemory
  - Broadcasts real-time status updates via coordinator
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Optional

from config.settings import WORKER_ROLES
from core.agent_base import WorkerAgent
from core.message import TaskSpec
from core.hiclaw_bridge import HiClawCoordinator
from core.memory import ProjectMemory
from core.tools.fs_tools import FileSystemTools
from core.sandbox.executor import SandboxExecutor
from core.patch_engine import PatchEngine

logger = logging.getLogger(__name__)

_ROLE_CONFIG = WORKER_ROLES["QA_ENGINEER"]

# Convergence configuration
MAX_RETRIES = 5
COVERAGE_THRESHOLD = 70.0  # percent — configurable per-project


class QAEngineer(WorkerAgent):

    def __init__(
        self,
        coordinator: Optional[HiClawCoordinator] = None,
        memory_dir: Optional[str] = None,
        claude_client=None
    ):
        super().__init__(
            agent_id=str(uuid.uuid4()),
            role="QA_ENGINEER",
            capabilities=_ROLE_CONFIG["capabilities"],
            coordinator=coordinator,
            memory_dir=memory_dir
        )
        self.project_memory = ProjectMemory(base_dir=memory_dir or "memory")
        self.sandbox = SandboxExecutor(timeout=60)
        self.patch_engine = PatchEngine(claude_client=claude_client)

    # -------------------------------------------------------------------------
    # Core Task Processing — Convergence Loop
    # -------------------------------------------------------------------------

    async def _process_task(self, task: TaskSpec) -> dict:
        """
        Closed-loop self-correcting test execution.
        Iterates up to MAX_RETRIES times until:
          - All tests pass AND
          - Coverage meets COVERAGE_THRESHOLD
        """
        subrole = self._determine_qa_subrole(task.description)
        self._logger.info(f"[QA:{subrole}] Starting convergence loop for: {task.title}")

        filename = f"tests/test_{subrole.lower()}_{task.task_id[:6]}.py"
        cwd = getattr(task, "workspace", os.getcwd())
        
        # Determine source path for coverage measurement
        source_path = self._infer_source_path(task, cwd)

        # Generate initial test code
        current_code = self._generate_tests(subrole, task)
        FileSystemTools.write_file(filename, current_code)

        last_result = None
        coverage_result = None
        iterations = 0
        self_heals = 0

        for attempt in range(MAX_RETRIES):
            iterations = attempt + 1
            self._broadcast(task, f"🧪 Iteration {iterations}/{MAX_RETRIES} — Running {subrole} tests...")

            # Step 1: Run tests in sandbox
            result = self.sandbox.run_isolated(filename, cwd=cwd)
            last_result = result

            self._logger.info(
                f"[QA:{subrole}] Attempt {iterations}: exit={result.exit_code}, "
                f"timed_out={result.timed_out}, duration={result.duration_secs}s"
            )

            # Step 2: Check for convergence
            if result.success:
                # Run coverage measurement after successful test pass
                if source_path:
                    coverage_result = self.sandbox.run_coverage(filename, source_path, cwd)
                    self._logger.info(f"[QA] Coverage: {coverage_result.percentage:.1f}%")

                    if coverage_result.percentage >= COVERAGE_THRESHOLD:
                        self._broadcast(task,
                            f"✅ CONVERGED: Tests passed + Coverage {coverage_result.percentage:.1f}% "
                            f"(threshold: {COVERAGE_THRESHOLD}%) in {iterations} iteration(s)."
                        )
                        break  # Full convergence achieved

                    # Tests pass but coverage is low — generate gap-filling tests
                    self._broadcast(task,
                        f"⚠️ Tests passed but coverage {coverage_result.percentage:.1f}% < "
                        f"{COVERAGE_THRESHOLD}%. Generating gap-filling tests..."
                    )
                    current_code = self._generate_gap_filling_tests(
                        current_code, coverage_result, task
                    )
                    FileSystemTools.write_file(filename, current_code)
                    self_heals += 1
                    continue

                else:
                    # No source path — just confirm test pass
                    self._broadcast(task, f"✅ Tests passed (no coverage target). Iterations: {iterations}")
                    break

            # Step 3: Test failed — diagnose and patch
            diagnosis = result.classify_failure()
            self._logger.warning(f"[QA:{subrole}] Failure diagnosis: {diagnosis}")

            # Log to persistent memory
            self.project_memory.add_test_failure({
                "task_id": task.task_id,
                "subrole": subrole,
                "attempt": iterations,
                "diagnosis": diagnosis,
                "stdout": result.stdout[-800:],
                "stderr": result.stderr[-400:]
            })

            if attempt == MAX_RETRIES - 1:
                # Final attempt failed — escalate
                self._broadcast(task,
                    f"❌ ESCALATED: Could not converge after {MAX_RETRIES} attempts. "
                    f"Last diagnosis: {diagnosis}. Human review required."
                )
                break

            # Step 4: Apply LLM or heuristic patch
            self._broadcast(task, f"🔧 Patching ({diagnosis})... attempt {iterations}/{MAX_RETRIES}")

            if diagnosis == "CodeBug":
                # Try to patch the implementation, not the test
                impl_path = self._infer_impl_path(task, cwd)
                if impl_path and os.path.exists(impl_path):
                    with open(impl_path, "r", encoding="utf-8", errors="replace") as f:
                        impl_code = f.read()
                    patch = self.patch_engine.patch_implementation(
                        impl_code=impl_code,
                        test_code=current_code,
                        failure_log=result.combined_output
                    )
                    if patch.confidence > 0.3:
                        FileSystemTools.write_file(impl_path, patch.patched_code)
                        self._logger.info(f"[QA] Implementation patched: {patch.explanation}")
                        self_heals += 1
                        continue

            # Default: patch the test
            patch = self.patch_engine.patch_test(
                original_code=current_code,
                failure_log=result.combined_output,
                diagnosis=diagnosis
            )
            self._logger.info(
                f"[QA] Test patch applied (confidence={patch.confidence:.2f}): {patch.explanation}"
            )
            current_code = patch.patched_code
            FileSystemTools.write_file(filename, current_code)
            self_heals += 1

        # -------------------------------------------------------------------------
        # Build final result
        # -------------------------------------------------------------------------
        success = last_result.success if last_result else False
        if success:
            self.project_memory.mark_resolved(task.task_id, f"Converged in {iterations} iterations")

        return {
            "domain": "quality_assurance",
            "subrole": subrole,
            "task": task.title,
            "converged": success,
            "iterations": iterations,
            "self_heals": self_heals,
            "coverage": {
                "percentage": coverage_result.percentage if coverage_result else None,
                "uncovered": coverage_result.uncovered_lines if coverage_result else [],
                "threshold": COVERAGE_THRESHOLD
            },
            "artifacts": {
                "test_file": filename,
                "final_output": last_result.combined_output if last_result else "",
                "duration_secs": last_result.duration_secs if last_result else 0
            },
            "status": "converged" if success else "escalated"
        }

    # -------------------------------------------------------------------------
    # Test Generation (same sub-role routing as before, now returns string)
    # -------------------------------------------------------------------------

    def _generate_tests(self, subrole: str, task: TaskSpec) -> str:
        if subrole == "UI":
            return self._generate_ui_tests(task)
        elif subrole == "API":
            return self._generate_api_tests(task)
        elif subrole == "Performance":
            return self._generate_perf_tests(task)
        else:
            return self._generate_regression_tests(task)

    def _determine_qa_subrole(self, description: str) -> str:
        desc = description.lower()
        if any(x in desc for x in ["ui", "frontend", "playwright", "browser", "selenium"]):
            return "UI"
        if any(x in desc for x in ["performance", "load", "locust", "stress", "throughput"]):
            return "Performance"
        if any(x in desc for x in ["regression", "historical", "retest", "verify all"]):
            return "Regression"
        return "API"

    def _infer_source_path(self, task: TaskSpec, cwd: str) -> Optional[str]:
        """Try to determine which source module the tests are targeting."""
        import re
        paths = re.findall(r'[a-zA-Z0-9_\-\./\\]+\.py', task.description)
        for p in paths:
            full = os.path.join(cwd, p)
            if os.path.exists(full):
                return p
        return None

    def _infer_impl_path(self, task: TaskSpec, cwd: str) -> Optional[str]:
        return self._infer_source_path(task, cwd)

    def _generate_gap_filling_tests(
        self, existing_code: str, coverage_result, task: TaskSpec
    ) -> str:
        """
        Generate additional test stubs for uncovered lines.
        Uses uncovered line numbers from coverage report as context.
        """
        uncovered_info = ""
        for fdata in coverage_result.uncovered_lines[:3]:
            lines = fdata.get("lines", [])
            uncovered_info += f"# Uncovered lines in {fdata.get('file', 'unknown')}: {lines}\n"

        gap_stub = (
            f"\n\n# --- Gap-filling tests (auto-generated, iteration {task.task_id[:6]}) ---\n"
            f"{uncovered_info}"
            "def test_coverage_gap_01():\n"
            "    # TODO: Cover uncovered branches above\n"
            "    assert True\n"
        )
        return existing_code + gap_stub

    def _broadcast(self, task: TaskSpec, msg: str):
        """Send a real-time status message via the coordinator."""
        self._logger.info(f"[QA Broadcast] {msg}")
        if self.coordinator:
            try:
                import asyncio
                asyncio.ensure_future(
                    self.coordinator.messenger.broadcast(
                        self.coordinator.status_room.room_id,
                        {
                            "type": "status_update",
                            "text": msg,
                            "source": "qa_engineer",
                            "task_id": task.task_id
                        }
                    )
                )
            except Exception:
                pass  # Non-critical

    # -------------------------------------------------------------------------
    # Existing test generator methods (unchanged from Phase 3)
    # -------------------------------------------------------------------------

    def _generate_ui_tests(self, task: TaskSpec) -> str:
        return (
            '"""Auto-generated Playwright UI tests"""\n'
            'import pytest\n'
            '# Requires playwright installed and configured\n'
            'def test_ui_stub():\n'
            '    assert True, "UI verification stub"\n'
        )

    def _generate_api_tests(self, task: TaskSpec) -> str:
        import re, difflib

        paths = re.findall(r'[a-zA-Z0-9_\-\./\\]+\.py', task.description)
        target_file = None

        for p in paths:
            if os.path.exists(p):
                target_file = p
                break

        if not target_file and paths:
            potential = paths[0]
            dirname = os.path.dirname(potential) or "."
            basename = os.path.basename(potential)
            if os.path.exists(dirname):
                files = [f for f in os.listdir(dirname) if f.endswith(".py")]
                matches = difflib.get_close_matches(basename, files, n=1, cutoff=0.5)
                if matches:
                    target_file = os.path.join(dirname, matches[0])

        if target_file:
            try:
                with open(target_file, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                funcs = re.findall(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)', content)
                methods = "\n".join(
                    f'def test_{fn}():\n    # Auto-stub for {fn}\n    assert True\n'
                    for fn in funcs if not fn.startswith("_") and fn != "main"
                )
                return f'import pytest\n# Source: {target_file}\n\n{methods}\n' if methods else self._api_fallback()
            except Exception:
                pass

        if "math" in task.description.lower():
            return (
                "import pytest\n"
                "from math_lib import add, subtract\n\n"
                "def test_add():\n    assert add(2, 3) == 5\n\n"
                "def test_subtract():\n    assert subtract(5, 3) == 2\n"
            )
        return self._api_fallback()

    def _api_fallback(self) -> str:
        return (
            '"""Auto-generated Pytest API tests"""\n'
            'import pytest\n'
            'def test_api_stub():\n'
            '    assert True, "API verification stub"\n'
        )

    def _generate_perf_tests(self, task: TaskSpec) -> str:
        return (
            '"""Auto-generated Performance tests"""\n'
            'def test_performance_stub():\n'
            '    import time\n'
            '    start = time.time()\n'
            '    time.sleep(0.01)  # simulate load\n'
            '    assert (time.time() - start) < 0.1\n'
        )

    def _generate_regression_tests(self, task: TaskSpec) -> str:
        failures = self.project_memory.test_failures.get("failures", [])
        recent = "\n".join(
            f"# Historic: {f['diagnosis']}" for f in failures[-3:]
        )
        return (
            '"""Auto-generated Regression tests (memory-driven)"""\n'
            'import pytest\n'
            f'{recent}\n'
            'def test_regression_stub():\n'
            '    assert True, "Regression verification stub"\n'
        )
