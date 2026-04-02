"""
Coverage Tracker — Per-project test coverage history and trend analysis.

Stores coverage data in: memory/{project_id}/coverage_history.json
Provides trend calculation and uncovered line summaries for agent consumption.
"""

import json
import logging
import os
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)

COVERAGE_HISTORY_FILE = "coverage_history.json"


class CoverageTracker:
    """
    Manages per-project coverage history.
    
    Usage:
        tracker = CoverageTracker(base_dir="memory")
        tracker.record("proj-123", "tests/test_foo.py", coverage_result)
        trend = tracker.get_trend("proj-123")
        current = tracker.get_current("proj-123")
    """

    def __init__(self, base_dir: str = "memory"):
        self.base_dir = base_dir

    def _project_dir(self, project_id: str) -> str:
        path = os.path.join(self.base_dir, project_id)
        os.makedirs(path, exist_ok=True)
        return path

    def _history_path(self, project_id: str) -> str:
        return os.path.join(self._project_dir(project_id), COVERAGE_HISTORY_FILE)

    def _load(self, project_id: str) -> List[dict]:
        path = self._history_path(project_id)
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[CoverageTracker] Failed to load history: {e}")
            return []

    def _save(self, project_id: str, history: List[dict]):
        path = self._history_path(project_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.error(f"[CoverageTracker] Failed to save history: {e}")

    def record(self, project_id: str, test_file: str, coverage_result) -> None:
        """
        Record a new coverage measurement for a project.
        
        Args:
            project_id: Unique project identifier
            test_file: Path to the test file that was run
            coverage_result: CoverageResult from SandboxExecutor.run_coverage()
        """
        history = self._load(project_id)
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "test_file": test_file,
            "percentage": coverage_result.percentage,
            "covered_lines": coverage_result.covered_lines,
            "total_lines": coverage_result.total_lines,
            "uncovered_count": sum(len(f.get("lines", [])) for f in coverage_result.uncovered_lines),
            "error": coverage_result.error
        }
        history.append(entry)
        # Keep only last 50 records
        if len(history) > 50:
            history = history[-50:]
        self._save(project_id, history)
        logger.info(f"[CoverageTracker] Recorded {coverage_result.percentage:.1f}% for {project_id}")

    def get_current(self, project_id: str) -> float:
        """Returns the latest coverage percentage, or 0.0 if no history."""
        history = self._load(project_id)
        if not history:
            return 0.0
        return history[-1].get("percentage", 0.0)

    def get_trend(self, project_id: str, window: int = 5) -> dict:
        """
        Calculate coverage trend over the last N runs.
        
        Returns:
            {
              "current": 78.5,
              "previous": 66.2,
              "delta": 12.3,
              "trend": "+12.3%",
              "direction": "up" | "down" | "flat",
              "runs": 5
            }
        """
        history = self._load(project_id)
        if len(history) < 2:
            current = history[-1]["percentage"] if history else 0.0
            return {
                "current": current,
                "previous": current,
                "delta": 0.0,
                "trend": "—",
                "direction": "flat",
                "runs": len(history)
            }

        window_data = history[-window:]
        current = window_data[-1]["percentage"]
        previous = window_data[0]["percentage"]
        delta = round(current - previous, 2)

        return {
            "current": current,
            "previous": previous,
            "delta": delta,
            "trend": f"+{delta}%" if delta >= 0 else f"{delta}%",
            "direction": "up" if delta > 0.5 else ("down" if delta < -0.5 else "flat"),
            "runs": len(window_data)
        }

    def get_uncovered_summary(self, project_id: str) -> List[str]:
        """
        Returns human-readable uncovered line summaries from the latest run.
        Useful for prompting the LLM to generate targeted gap-filling tests.
        """
        history = self._load(project_id)
        if not history:
            return []
        latest = history[-1]
        count = latest.get("uncovered_count", 0)
        if count == 0:
            return ["No uncovered lines — full coverage achieved."]
        return [f"{count} line(s) remain uncovered. Run targeted tests to improve coverage."]

    def get_history_summary(self, project_id: str) -> List[dict]:
        """Returns the last 10 coverage records for dashboard display."""
        history = self._load(project_id)
        return history[-10:]
