"""
Agent Memory / Context Store.

Provides per-agent memory and global project memory:
  - AgentMemory: per-agent scratchpad, decisions, intermediate outputs.
  - ProjectMemory: persistent global state stored in memory/
"""

from __future__ import annotations

import json
import os
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class MemoryEntry:
    """A single entry in the agent's memory."""
    timestamp: datetime
    category: str           # "context" | "decision" | "output" | "error"
    content: Any
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "category": self.category,
            "content": self.content if isinstance(self.content, (str, int, float, bool, list, dict)) else str(self.content),
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryEntry":
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            category=data["category"],
            content=data["content"],
            tags=data.get("tags", []),
        )


class AgentMemory:
    """
    Per-agent memory store.
    """
    def __init__(self, agent_id: str, max_context: int = 50, base_dir: Optional[str] = None):
        self.agent_id = agent_id
        self.base_dir = base_dir
        self._context: deque[MemoryEntry] = deque(maxlen=max_context)
        self._decisions: list[MemoryEntry] = []
        self._outputs: list[MemoryEntry] = []
        self._errors: list[MemoryEntry] = []

    def add_context(self, content: Any, tags: Optional[list[str]] = None) -> None:
        self._context.append(MemoryEntry(datetime.now(), "context", content, tags or []))

    def log_decision(self, decision: str, reasoning: str = "", tags: Optional[list[str]] = None) -> None:
        self._decisions.append(MemoryEntry(datetime.now(), "decision", {"decision": decision, "reasoning": reasoning}, tags or []))

    def store_output(self, label: str, output: Any, tags: Optional[list[str]] = None) -> None:
        self._outputs.append(MemoryEntry(datetime.now(), "output", {"label": label, "data": output}, tags or []))

    def log_error(self, error: str, details: str = "", tags: Optional[list[str]] = None) -> None:
        self._errors.append(MemoryEntry(datetime.now(), "error", {"error": error, "details": details}, tags or []))

    def get_context(self, last_n: Optional[int] = None) -> list[MemoryEntry]:
        entries = list(self._context)
        return entries[-last_n:] if last_n else entries

    def get_decisions(self) -> list[MemoryEntry]: return list(self._decisions)
    def get_outputs(self) -> list[MemoryEntry]: return list(self._outputs)
    def get_errors(self) -> list[MemoryEntry]: return list(self._errors)

    def get_latest_output(self, label: Optional[str] = None) -> Optional[Any]:
        for entry in reversed(self._outputs):
            if label is None or entry.content.get("label") == label:
                return entry.content.get("data")
        return None

    def search(self, keyword: str) -> list[MemoryEntry]:
        keyword_lower = keyword.lower()
        results: list[MemoryEntry] = []
        for store in (self._context, self._decisions, self._outputs, self._errors):
            for entry in store:
                content_str = str(entry.content).lower()
                if keyword_lower in content_str or any(keyword_lower in t.lower() for t in entry.tags):
                    results.append(entry)
        return results

    def clear(self) -> None:
        self._context.clear()
        self._decisions.clear()
        self._outputs.clear()
        self._errors.clear()


class ProjectMemory:
    """
    Global persistent memory storage managing project data in memory/
    """
    def __init__(self, base_dir: str = "memory"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.context_file = os.path.join(self.base_dir, "project_context.json")
        self.history_file = os.path.join(self.base_dir, "task_history.json")
        self.errors_file = os.path.join(self.base_dir, "error_patterns.json")
        self.index_file = os.path.join(self.base_dir, "codebase_index.json")
        
        # Phase 3 Enhancements
        self.fix_strategies_file = os.path.join(self.base_dir, "fix_strategies.json")
        self.deployment_history_file = os.path.join(self.base_dir, "deployment_history.json")
        self.test_failures_file = os.path.join(self.base_dir, "test_failures.json")

        self.context = self._load(self.context_file, {"goals": [], "requirements": []})
        self.history = self._load(self.history_file, {"tasks": []})
        self.errors = self._load(self.errors_file, {"patterns": []})
        self.index = self._load(self.index_file, {"files": {}})
        
        self.fix_strategies = self._load(self.fix_strategies_file, {"strategies": []})
        self.deployment_history = self._load(self.deployment_history_file, {"deployments": []})
        self.test_failures = self._load(self.test_failures_file, {"failures": []})

    def _load(self, filepath: str, default: dict) -> dict:
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        return default

    def _save(self, filepath: str, data: dict) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def update_context(self, key: str, value: Any) -> None:
        self.context[key] = value
        self._save(self.context_file, self.context)

    def add_task_history(self, task_record: dict) -> None:
        self.history["tasks"].append(task_record)
        self._save(self.history_file, self.history)

    def add_error_pattern(self, pattern: dict) -> None:
        self.errors["patterns"].append(pattern)
        self._save(self.errors_file, self.errors)

    def update_index(self, file_path: str, metadata: dict) -> None:
        self.index["files"][file_path] = metadata
        self._save(self.index_file, self.index)

    def add_fix_strategy(self, strategy: dict) -> None:
        self.fix_strategies["strategies"].append(strategy)
        self._save(self.fix_strategies_file, self.fix_strategies)

    def add_deployment_history(self, deployment: dict) -> None:
        self.deployment_history["deployments"].append(deployment)
        self._save(self.deployment_history_file, self.deployment_history)

    def add_test_failure(self, failure: dict) -> None:
        self.test_failures["failures"].append(failure)
        self._save(self.test_failures_file, self.test_failures)

    def mark_resolved(self, task_id: str, solution_summary: str) -> None:
        """
        Mark all failures for a task_id as resolved with the solution that worked.
        Used by the convergence loop to track self-healing journeys.
        """
        changed = False
        for failure in self.test_failures.get("failures", []):
            if failure.get("task_id") == task_id:
                failure["resolved"] = True
                failure["solution"] = solution_summary
                changed = True
        if changed:
            self._save(self.test_failures_file, self.test_failures)

    def get_similar_failures(self, diagnosis: str, limit: int = 3) -> list:
        """
        Return recent past failures matching the given diagnosis.
        Used by PatchEngine as few-shot examples for LLM patches.
        """
        matches = [
            f for f in self.test_failures.get("failures", [])
            if f.get("diagnosis") == diagnosis
        ]
        # Return most recent first, excluding already-resolved
        unresolved = [m for m in matches if not m.get("resolved")]
        return unresolved[-limit:]
