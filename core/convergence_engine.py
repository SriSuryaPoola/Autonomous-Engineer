"""
Convergence Engine — Evaluates whether a QA cycle has fully converged.

Convergence criteria (ALL must be satisfied):
  1. All test suites exit with code 0
  2. Test coverage >= COVERAGE_THRESHOLD (default 70%)
  3. No unresolved critical failures in ProjectMemory
  4. CI pipeline result is 'success' (if configured)

Emits ConvergenceState objects that are broadcast via WebSocket
to the live dashboard.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

COVERAGE_THRESHOLD = 70.0  # matches qa_engineer.py default


class ConvergenceState(str, Enum):
    AWAITING    = "AWAITING"    # No task submitted
    RUNNING     = "RUNNING"     # Tests executing
    PARTIAL     = "PARTIAL"     # Tests pass but coverage below threshold
    CONVERGED   = "CONVERGED"   # All criteria met
    ESCALATED   = "ESCALATED"   # Max retries exceeded, human review needed
    CI_PENDING  = "CI_PENDING"  # Local converged, waiting for CI


@dataclass
class ConvergenceReport:
    project_id: str
    state: ConvergenceState
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Test metrics
    tests_passed: bool = False
    iterations: int = 0
    self_heals: int = 0
    
    # Coverage metrics
    coverage_percentage: float = 0.0
    coverage_threshold: float = COVERAGE_THRESHOLD
    coverage_met: bool = False
    
    # CI metrics
    ci_enabled: bool = False
    ci_success: Optional[bool] = None
    ci_url: str = ""
    
    # Readable summary
    summary: str = ""
    unresolved_issues: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "state": self.state.value,
            "timestamp": self.timestamp,
            "tests_passed": self.tests_passed,
            "iterations": self.iterations,
            "self_heals": self.self_heals,
            "coverage": {
                "percentage": self.coverage_percentage,
                "threshold": self.coverage_threshold,
                "met": self.coverage_met
            },
            "ci": {
                "enabled": self.ci_enabled,
                "success": self.ci_success,
                "url": self.ci_url
            },
            "summary": self.summary,
            "unresolved_issues": self.unresolved_issues
        }


class ConvergenceEngine:
    """
    Evaluates convergence criterion and generates structured reports.
    Stores the latest report in memory/{project_id}/convergence.json.
    """

    def __init__(self, memory_dir: str = "memory"):
        self.memory_dir = memory_dir

    def evaluate(
        self,
        project_id: str,
        qa_result: dict,
        ci_result=None
    ) -> ConvergenceReport:
        """
        Evaluate a QA result against convergence criteria.
        
        Args:
            project_id: Project being evaluated
            qa_result: Output dict from QAEngineer._process_task()
            ci_result: Optional CIResult from CIFeedbackLoop
            
        Returns:
            ConvergenceReport — the full convergence assessment
        """
        tests_passed = qa_result.get("converged", False)
        iterations = qa_result.get("iterations", 0)
        self_heals = qa_result.get("self_heals", 0)
        coverage = qa_result.get("coverage", {})
        coverage_pct = coverage.get("percentage") or 0.0
        coverage_met = coverage_pct >= COVERAGE_THRESHOLD if coverage_pct else False

        # Check for unresolved issues in memory
        unresolved = self._get_unresolved_failures(project_id)

        # Determine state
        if not tests_passed:
            state = ConvergenceState.ESCALATED
        elif ci_result and not ci_result.success:
            state = ConvergenceState.ESCALATED
        elif ci_result and ci_result.status == "timeout":
            state = ConvergenceState.CI_PENDING
        elif tests_passed and not coverage_met and coverage_pct > 0:
            state = ConvergenceState.PARTIAL
        elif tests_passed and (coverage_met or coverage_pct == 0):
            state = ConvergenceState.CONVERGED
        else:
            state = ConvergenceState.RUNNING

        # Build summary
        summary = self._build_summary(state, iterations, self_heals, coverage_pct, ci_result)

        report = ConvergenceReport(
            project_id=project_id,
            state=state,
            tests_passed=tests_passed,
            iterations=iterations,
            self_heals=self_heals,
            coverage_percentage=round(coverage_pct, 2),
            coverage_threshold=COVERAGE_THRESHOLD,
            coverage_met=coverage_met,
            ci_enabled=ci_result is not None,
            ci_success=ci_result.success if ci_result else None,
            ci_url=ci_result.run_url if ci_result else "",
            summary=summary,
            unresolved_issues=unresolved
        )

        # Persist to disk
        self._save_report(project_id, report)
        logger.info(f"[Convergence] Project {project_id}: {state.value} | Coverage: {coverage_pct:.1f}%")
        return report

    def get_latest(self, project_id: str) -> Optional[ConvergenceReport]:
        """Load the latest convergence report from disk."""
        path = self._report_path(project_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            report = ConvergenceReport(
                project_id=data["project_id"],
                state=ConvergenceState(data["state"]),
                timestamp=data.get("timestamp", ""),
                tests_passed=data.get("tests_passed", False),
                iterations=data.get("iterations", 0),
                self_heals=data.get("self_heals", 0),
                coverage_percentage=data.get("coverage", {}).get("percentage", 0.0),
                coverage_met=data.get("coverage", {}).get("met", False),
                ci_enabled=data.get("ci", {}).get("enabled", False),
                ci_success=data.get("ci", {}).get("success"),
                ci_url=data.get("ci", {}).get("url", ""),
                summary=data.get("summary", ""),
                unresolved_issues=data.get("unresolved_issues", [])
            )
            return report
        except Exception as e:
            logger.error(f"[Convergence] Failed to load report: {e}")
            return None

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _report_path(self, project_id: str) -> str:
        proj_dir = os.path.join(self.memory_dir, project_id)
        os.makedirs(proj_dir, exist_ok=True)
        return os.path.join(proj_dir, "convergence.json")

    def _save_report(self, project_id: str, report: ConvergenceReport):
        try:
            with open(self._report_path(project_id), "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"[Convergence] Failed to save report: {e}")

    def _get_unresolved_failures(self, project_id: str) -> list:
        failure_file = os.path.join(self.memory_dir, project_id, "test_failures.json")
        if not os.path.exists(failure_file):
            return []
        try:
            with open(failure_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            failures = data.get("failures", [])
            return [f for f in failures if not f.get("resolved", False)]
        except Exception:
            return []

    def _build_summary(
        self, state: ConvergenceState, iterations: int,
        self_heals: int, coverage: float, ci_result
    ) -> str:
        base = f"Completed {iterations} iteration(s) with {self_heals} self-heal(s). "
        if state == ConvergenceState.CONVERGED:
            return base + f"✅ Fully converged. Coverage: {coverage:.1f}%."
        elif state == ConvergenceState.PARTIAL:
            return base + f"⚠️ Tests pass but coverage {coverage:.1f}% < {COVERAGE_THRESHOLD}% threshold."
        elif state == ConvergenceState.ESCALATED:
            ci_msg = f" CI failed: {ci_result.conclusion}" if ci_result and not ci_result.success else ""
            return base + f"❌ Could not converge.{ci_msg} Human review required."
        elif state == ConvergenceState.CI_PENDING:
            return base + "⏳ Local tests converged. CI pipeline still running."
        return base + "🔄 In progress..."
