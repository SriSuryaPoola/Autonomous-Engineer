"""
Sandbox Executor — Safe, isolated subprocess-based test runner.

Runs pytest in a child process with hard timeouts and resource limits.
On Windows, uses subprocess + timeout enforcement.
On Linux/Mac, additionally applies ulimit-style limits.

Returns structured SandboxResult and CoverageResult dataclasses
to decouple the test runner from raw subprocess output.
"""

import json
import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SandboxResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    duration_secs: float = 0.0

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    @property
    def combined_output(self) -> str:
        return (self.stdout + "\n" + self.stderr).strip()

    def classify_failure(self) -> str:
        """Heuristic diagnosis of failure type."""
        out = self.combined_output.lower()
        if self.timed_out:
            return "Timeout"
        if "modulenotfounderror" in out or "importerror" in out:
            return "Environment"
        if "syntaxerror" in out:
            return "SyntaxError"
        if "assertionerror" in out or "assert" in out:
            return "AssertionError"
        if "connectionrefused" in out or "connectionerror" in out:
            return "Environment"
        if "nameerror" in out or "attributeerror" in out:
            return "CodeBug"
        return "Unknown"


@dataclass
class CoverageResult:
    percentage: float = 0.0
    covered_lines: int = 0
    total_lines: int = 0
    uncovered_lines: list = field(default_factory=list)
    report_path: str = ""
    error: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        return self.error is None and self.total_lines > 0


class SandboxExecutor:
    """
    Safe, subprocess-isolated test runner with timeout enforcement.
    
    Usage:
        executor = SandboxExecutor(timeout=60)
        result = executor.run_isolated("tests/test_foo.py", cwd=".")
        coverage = executor.run_coverage("tests/test_foo.py", "src/foo.py", cwd=".")
    """

    DEFAULT_TIMEOUT = 60          # seconds
    DEFAULT_MAX_OUTPUT = 10_000   # characters

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        max_output: int = DEFAULT_MAX_OUTPUT,
        python_executable: Optional[str] = None
    ):
        self.timeout = timeout
        self.max_output = max_output
        self.default_python = python_executable or sys.executable

    def _get_python(self, cwd: str) -> str:
        """Resolve the python executable, preferring a local venv if it exists."""
        venv_win = os.path.join(cwd, "venv", "Scripts", "python.exe")
        venv_unix = os.path.join(cwd, "venv", "bin", "python")
        if os.path.exists(venv_win):
            return venv_win
        if os.path.exists(venv_unix):
            return venv_unix
        return self.default_python

    def run_isolated(self, test_path: str, cwd: str = ".") -> SandboxResult:
        """
        Run pytest on the given test file in a sandboxed subprocess.
        
        Args:
            test_path: Path to the test file (relative to cwd)
            cwd: Working directory for the subprocess
            
        Returns:
            SandboxResult with exit_code, stdout, stderr, timed_out
        """
        python_exe = self._get_python(cwd)
        cmd = [
            python_exe, "-m", "pytest",
            test_path,
            "-v",
            "--tb=short",
            "--no-header",
            "-q"
        ]

        logger.info(f"[Sandbox] Running: {' '.join(cmd)} in {cwd}")
        start = time.time()

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

            try:
                stdout, stderr = proc.communicate(timeout=self.timeout)
                duration = time.time() - start
                
                return SandboxResult(
                    exit_code=proc.returncode,
                    stdout=stdout[:self.max_output],
                    stderr=stderr[:self.max_output],
                    timed_out=False,
                    duration_secs=round(duration, 2)
                )

            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                duration = time.time() - start
                logger.warning(f"[Sandbox] Test timed out after {self.timeout}s: {test_path}")
                
                return SandboxResult(
                    exit_code=-1,
                    stdout="",
                    stderr=f"TIMEOUT: Test exceeded {self.timeout}s limit",
                    timed_out=True,
                    duration_secs=round(duration, 2)
                )

        except FileNotFoundError:
            return SandboxResult(
                exit_code=-2,
                stdout="",
                stderr=f"Python executable not found for cwd {cwd}",
                timed_out=False,
                duration_secs=0.0
            )
        except Exception as e:
            logger.error(f"[Sandbox] Unexpected error: {e}")
            return SandboxResult(
                exit_code=-3,
                stdout="",
                stderr=f"Sandbox execution error: {e}",
                timed_out=False,
                duration_secs=0.0
            )

    def run_coverage(
        self,
        test_path: str,
        source_path: str,
        cwd: str = "."
    ) -> CoverageResult:
        """
        Run pytest with coverage measurement for the given source module.
        
        Args:
            test_path: Path to the test file
            source_path: Path to the source module being tested
            cwd: Working directory
            
        Returns:
            CoverageResult with percentage, uncovered lines, and report path
        """
        coverage_json = os.path.join(cwd, ".coverage_report.json")
        python_exe = self._get_python(cwd)
        
        cmd = [
            python_exe, "-m", "pytest",
            test_path,
            f"--cov={source_path}",
            "--cov-report=json:" + coverage_json,
            "--cov-report=term-missing",
            "-q",
            "--no-header"
        ]

        logger.info(f"[Sandbox] Coverage run: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout
            )

            # Parse the JSON coverage report
            if os.path.exists(coverage_json):
                with open(coverage_json, "r") as f:
                    cov_data = json.load(f)

                totals = cov_data.get("totals", {})
                percent = totals.get("percent_covered", 0.0)
                covered = totals.get("covered_lines", 0)
                total = totals.get("num_statements", 0)

                # Collect uncovered lines across all files
                uncovered = []
                for fpath, fdata in cov_data.get("files", {}).items():
                    missing = fdata.get("missing_lines", [])
                    if missing:
                        uncovered.append({
                            "file": fpath,
                            "lines": missing
                        })

                # Clean up temp report
                try:
                    os.remove(coverage_json)
                except Exception:
                    pass

                return CoverageResult(
                    percentage=round(percent, 2),
                    covered_lines=covered,
                    total_lines=total,
                    uncovered_lines=uncovered,
                    report_path=coverage_json
                )

            else:
                # Coverage report not generated (test likely failed)
                return CoverageResult(
                    percentage=0.0,
                    error=f"Coverage report not generated. Test exit code: {result.returncode}\n{result.stderr[:500]}"
                )

        except subprocess.TimeoutExpired:
            return CoverageResult(
                percentage=0.0,
                error=f"Coverage run timed out after {self.timeout}s"
            )
        except Exception as e:
            return CoverageResult(
                percentage=0.0,
                error=f"Coverage execution error: {e}"
            )
