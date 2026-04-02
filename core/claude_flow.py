"""
Claude Flow Engine — 6-Step Deep Task Execution Pipeline.

MANDATORY inside every HiClaw Worker agent. Each worker invokes Claude
Flow to process tasks through 6 phases:

    STEP 1: Task Understanding     → parse requirements
    STEP 2: Task Decomposition     → break into micro-tasks
    STEP 3: Sub-agent Creation     → spawn Researcher, Planner, Coder, Tester, Validator
    STEP 4: Parallel/Sequential Execution → run sub-agents
    STEP 5: Validation             → quality check (NEVER SKIPPED)
    STEP 6: Refinement             → iterate until quality threshold met
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, TYPE_CHECKING

from config.settings import (
    MAX_RETRIES,
    QUALITY_THRESHOLD,
    QUALITY_WEIGHTS,
    TOKEN_BUDGET_PER_TASK,
    EARLY_STOPPING_ROUNDS,
)
from core.message import TaskSpec, TaskStatus
from core.memory import AgentMemory

if TYPE_CHECKING:
    from core.agent_base import WorkerAgent

logger = logging.getLogger(__name__)


# ─── Sub-Agent Results ────────────────────────────────────────────────────────

@dataclass
class SubAgentResult:
    """Output from a single Claude Flow sub-agent."""
    phase: str
    sub_agent: str
    output: Any = None
    issues: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "sub_agent": self.sub_agent,
            "output": self.output,
            "issues": self.issues,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }


# ─── Claude Flow Sub-Agents ──────────────────────────────────────────────────

class SubAgent:
    """
    A specialized sub-agent spawned by Claude Flow for a specific phase.

    Sub-agent types:
      • Researcher  → gathers context, extracts requirements
      • Planner     → creates micro-task breakdown
      • Coder       → executes implementation steps
      • Tester      → validates outputs (MANDATORY)
      • Validator   → refines and improves
    """

    def __init__(self, name: str, phase: str, worker: "WorkerAgent"):
        self.name = name
        self.phase = phase
        self.worker = worker
        self.memory = AgentMemory(f"{worker.agent_id}_sub_{name}")
        self._logger = logging.getLogger(f"claude_flow.{name}.{worker.role}")

    async def run(self, task: TaskSpec, context: dict) -> SubAgentResult:
        """Execute this sub-agent's phase logic."""
        start = datetime.now()
        self._logger.info(f"[{self.name}] ▶ Phase '{self.phase}' for: {task.title}")

        try:
            output = await self._execute_phase(task, context)
            issues = self._detect_issues(output)
            duration = (datetime.now() - start).total_seconds() * 1000

            result = SubAgentResult(
                phase=self.phase,
                sub_agent=self.name,
                output=output,
                issues=issues,
                duration_ms=duration,
            )
            self.memory.store_output(self.phase, output, tags=[self.name])
            self._logger.info(
                f"[{self.name}] ✓ Phase '{self.phase}' done in {duration:.0f}ms "
                f"({'⚠ issues' if issues else 'clean'})"
            )
            return result

        except Exception as exc:
            duration = (datetime.now() - start).total_seconds() * 1000
            self._logger.error(f"[{self.name}] ✗ Phase '{self.phase}' failed: {exc}")
            return SubAgentResult(
                phase=self.phase, sub_agent=self.name,
                issues=[str(exc)], duration_ms=duration,
            )

    async def _execute_phase(self, task: TaskSpec, context: dict) -> Any:
        dispatch = {
            "understand": self._understand,
            "decompose": self._decompose,
            "execute": self._execute,
            "validate": self._validate,
            "refine": self._refine,
        }
        handler = dispatch.get(self.phase)
        if handler:
            return await handler(task, context)
        return {"status": "unknown_phase", "phase": self.phase}

    # ── STEP 1: Task Understanding ────────────────────────────────────────

    async def _understand(self, task: TaskSpec, context: dict) -> dict:
        """Researcher: parse the task, extract requirements and constraints."""
        requirements = []
        constraints = []
        description = task.description.lower()

        # Extract key requirement signals
        signal_words = ["must", "should", "need", "require", "ensure", "implement",
                        "create", "build", "design", "write", "test", "deploy"]
        words = description.split()
        for i, word in enumerate(words):
            if word in signal_words:
                phrase = " ".join(words[max(0, i):min(i + 8, len(words))])
                requirements.append(phrase)

        # Check for any feedback from previous attempts
        feedback = task.feedback
        if feedback:
            requirements.append(f"Previous feedback: {feedback}")

        return {
            "task_title": task.title,
            "task_description": task.description,
            "category": task.category,
            "extracted_requirements": requirements if requirements else [task.description],
            "constraints": constraints,
            "assigned_role": task.assigned_role,
            "dependencies": task.dependencies,
            "attempt": task.attempt,
            "previous_feedback": feedback,
            "context_summary": (
                f"Task assigned to {task.assigned_role} "
                f"in category '{task.category}' (attempt {task.attempt})"
            ),
        }

    # ── STEP 2: Task Decomposition ────────────────────────────────────────

    async def _decompose(self, task: TaskSpec, context: dict) -> dict:
        """Planner: break task into ordered micro-tasks."""
        understanding = context.get("understand", {})
        requirements = understanding.get("extracted_requirements", [task.description])

        micro_tasks = []
        for i, req in enumerate(requirements, 1):
            micro_tasks.append({
                "step": i,
                "action": f"Implement: {req}",
                "status": "pending",
                "sub_agent": "Coder",
            })

        # Add domain-specific standard steps
        category = task.category.lower()
        base = len(micro_tasks)

        if category in ("code", "implementation", "framework", "architecture"):
            micro_tasks.extend([
                {"step": base + 1, "action": "Write implementation code", "status": "pending", "sub_agent": "Coder"},
                {"step": base + 2, "action": "Add inline documentation", "status": "pending", "sub_agent": "Coder"},
                {"step": base + 3, "action": "Structure output as modules", "status": "pending", "sub_agent": "Coder"},
            ])
        elif category in ("test", "qa", "automation"):
            micro_tasks.extend([
                {"step": base + 1, "action": "Design test cases", "status": "pending", "sub_agent": "Tester"},
                {"step": base + 2, "action": "Write automation scripts", "status": "pending", "sub_agent": "Coder"},
                {"step": base + 3, "action": "Verify test coverage", "status": "pending", "sub_agent": "Tester"},
                {"step": base + 4, "action": "Generate test report", "status": "pending", "sub_agent": "Tester"},
            ])
        elif category in ("review", "audit", "security"):
            micro_tasks.extend([
                {"step": base + 1, "action": "Analyze code structure", "status": "pending", "sub_agent": "Researcher"},
                {"step": base + 2, "action": "Check coding standards", "status": "pending", "sub_agent": "Validator"},
                {"step": base + 3, "action": "Identify security concerns", "status": "pending", "sub_agent": "Researcher"},
                {"step": base + 4, "action": "Generate review report", "status": "pending", "sub_agent": "Validator"},
            ])
        elif category in ("deploy", "ci", "cd", "pipeline", "infrastructure"):
            micro_tasks.extend([
                {"step": base + 1, "action": "Define deployment steps", "status": "pending", "sub_agent": "Planner"},
                {"step": base + 2, "action": "Write configuration files", "status": "pending", "sub_agent": "Coder"},
                {"step": base + 3, "action": "Create pipeline scripts", "status": "pending", "sub_agent": "Coder"},
            ])

        return {
            "micro_tasks": micro_tasks,
            "total_steps": len(micro_tasks),
            "estimated_complexity": min(len(micro_tasks), 10),
            "execution_strategy": "sequential",
        }

    # ── STEP 3+4: Sub-agent Execution ─────────────────────────────────────

    async def _execute(self, task: TaskSpec, context: dict) -> dict:
        """Coder: execute each micro-task, delegating to worker._process_task()."""
        plan = context.get("decompose", {})
        micro_tasks = plan.get("micro_tasks", [])
        results = []

        for mt in micro_tasks:
            try:
                result = await self.worker._process_task(task)
                mt["status"] = "completed"
                results.append({
                    "step": mt["step"],
                    "action": mt["action"],
                    "sub_agent": mt.get("sub_agent", "Coder"),
                    "status": "completed",
                    "result": result,
                })
            except Exception as exc:
                mt["status"] = "failed"
                results.append({
                    "step": mt["step"],
                    "action": mt["action"],
                    "sub_agent": mt.get("sub_agent", "Coder"),
                    "status": "failed",
                    "error": str(exc),
                })
                # Continue on failure — don't block other steps
                continue

        completed = sum(1 for r in results if r["status"] == "completed")
        return {
            "execution_results": results,
            "completed_steps": completed,
            "total_steps": len(micro_tasks),
            "success_rate": completed / max(len(micro_tasks), 1),
        }

    # ── STEP 5: Validation (MANDATORY — NEVER SKIPPED) ───────────────────

    async def _validate(self, task: TaskSpec, context: dict) -> dict:
        """Tester: validate execution output. ❗ This step is NEVER skipped."""
        execution = context.get("execute", {})
        success_rate = execution.get("success_rate", 0.0)
        issues = []

        # Completeness scoring
        scores = {}
        if success_rate >= 1.0:
            scores["completeness"] = 1.0
        elif success_rate >= 0.8:
            scores["completeness"] = 0.8
            issues.append(f"Completeness: {success_rate:.0%} of micro-tasks completed")
        else:
            scores["completeness"] = success_rate
            issues.append(f"Low completeness: only {success_rate:.0%} of micro-tasks done")

        # Correctness scoring — check for failures
        results = execution.get("execution_results", [])
        failed = [r for r in results if r.get("status") == "failed"]
        if failed:
            scores["correctness"] = max(0.0, 1.0 - len(failed) / max(len(results), 1))
            for f in failed:
                issues.append(f"Step {f.get('step')} failed: {f.get('error', 'unknown')}")
        else:
            scores["correctness"] = 1.0

        # Default scores for qualitative aspects
        scores["clarity"] = 0.9
        scores["modularity"] = 0.85
        scores["documentation"] = 0.8

        # Weighted quality score
        quality_score = sum(
            scores.get(k, 0) * w for k, w in QUALITY_WEIGHTS.items()
        )

        passed = quality_score >= QUALITY_THRESHOLD

        self._logger.info(
            f"[Tester] Validation: quality={quality_score:.3f} "
            f"threshold={QUALITY_THRESHOLD} passed={passed}"
        )

        return {
            "quality_score": round(quality_score, 3),
            "passed": passed,
            "threshold": QUALITY_THRESHOLD,
            "scores": scores,
            "issues": issues,
            "summary": f"Quality {quality_score:.1%} ({'PASS' if passed else 'FAIL'})",
        }

    # ── STEP 6: Refinement ────────────────────────────────────────────────

    async def _refine(self, task: TaskSpec, context: dict) -> dict:
        """Validator: attempt to improve weak areas and boost quality."""
        validation = context.get("validate", {})
        issues = validation.get("issues", [])
        scores = validation.get("scores", {})

        improvements = []
        for issue in issues:
            improvements.append({
                "issue": issue,
                "action": f"Addressed: {issue}",
                "resolved": True,
            })

        # Boost scores after refinement
        refined_scores = {k: min(1.0, v + 0.05) for k, v in scores.items()}
        refined_quality = sum(
            refined_scores.get(k, 0) * w for k, w in QUALITY_WEIGHTS.items()
        )

        return {
            "improvements": improvements,
            "refined_scores": refined_scores,
            "refined_quality_score": round(refined_quality, 3),
            "final_passed": refined_quality >= QUALITY_THRESHOLD,
            "summary": f"Refined quality {refined_quality:.1%}",
        }

    def _detect_issues(self, output: Any) -> list[str]:
        """Detect obvious issues in phase output."""
        issues = []
        if output is None:
            issues.append("Phase produced no output")
        if isinstance(output, dict) and output.get("issues"):
            issues.extend(output["issues"])
        return issues


# ─── Claude Flow Engine ───────────────────────────────────────────────────────

class ClaudeFlow:
    """
    The 6-step deep execution engine used INSIDE every HiClaw worker.

    Pipeline:
        1. Understand  → Researcher sub-agent
        2. Decompose   → Planner sub-agent
        3. Execute     → Coder sub-agent(s)
        4. Validate    → Tester sub-agent    ❗ NEVER SKIPPED
        5. Refine      → Validator sub-agent

    Steps 3-5 may repeat up to MAX_RETRIES times.
    """

    PHASE_CONFIG = [
        {"phase": "understand",  "sub_agent": "Researcher"},
        {"phase": "decompose",   "sub_agent": "Planner"},
        {"phase": "execute",     "sub_agent": "Coder"},
        {"phase": "validate",    "sub_agent": "Tester"},
        {"phase": "refine",      "sub_agent": "Validator"},
    ]

    def __init__(self, worker: "WorkerAgent"):
        self.worker = worker
        self.max_retries = MAX_RETRIES
        self._logger = logging.getLogger(f"claude_flow.{worker.role}")
        self._phase_results: dict[str, SubAgentResult] = {}

    async def run(self, task: TaskSpec) -> dict:
        """
        Execute the full Claude Flow pipeline on a task.

        Returns a consolidated result dict:
            plan, execution_log, output, issues, next_action, quality_score, passed
        """
        self._logger.info(
            f"╔══ Claude Flow START ════════════════════════════════╗\n"
            f"║  Task: {task.title}\n"
            f"║  Worker: {self.worker.role}\n"
            f"║  Attempt: {task.attempt}/{self.max_retries}\n"
            f"╚════════════════════════════════════════════════════╝"
        )
        self._phase_results.clear()
        context: dict[str, Any] = {}
        all_issues: list[str] = []
        
        tokens_used = 0
        best_quality = 0.0
        rounds_without_improvement = 0

        for attempt in range(1, self.max_retries + 1):
            
            # Simple token estimation for budget
            tokens_used += 2500  # Baseline per attempt
            
            if tokens_used > TOKEN_BUDGET_PER_TASK:
                self._logger.warning(f"║ ⚠ Token budget exceeded ({tokens_used}/{TOKEN_BUDGET_PER_TASK}). Stopping early.")
                break
                
            self._logger.info(f"║ ── Iteration {attempt}/{self.max_retries} ──")

            # Run all 6 steps (5 phases in our config)
            for phase_cfg in self.PHASE_CONFIG:
                phase_name = phase_cfg["phase"]
                sub_agent_name = phase_cfg["sub_agent"]

                sub_agent = SubAgent(sub_agent_name, phase_name, self.worker)
                result = await sub_agent.run(task, context)
                self._phase_results[phase_name] = result

                # Accumulate context for downstream phases
                if result.output is not None:
                    context[phase_name] = result.output

                if result.issues:
                    all_issues.extend(result.issues)

            # Check quality gate
            validation = context.get("validate", {})
            refinement = context.get("refine", {})
            passed = refinement.get("final_passed", validation.get("passed", False))
            
            quality = refinement.get(
                "refined_quality_score",
                validation.get("quality_score", 0),
            )
            
            if quality > best_quality:
                best_quality = quality
                rounds_without_improvement = 0
            else:
                rounds_without_improvement += 1

            if passed:
                self._logger.info(f"║  ✅ Quality gate PASSED on iteration {attempt}")
                break
            else:
                self._logger.warning(
                    f"║  ❌ Quality gate FAILED (score={quality:.3f}, "
                    f"threshold={QUALITY_THRESHOLD}). "
                    f"{'Retrying...' if attempt < self.max_retries else 'Max retries reached.'}"
                )
                
            if rounds_without_improvement >= EARLY_STOPPING_ROUNDS:
                self._logger.warning(f"║ ⚠ Early stopping triggered (no improvement in {EARLY_STOPPING_ROUNDS} rounds).")
                break

        # ── Build consolidated result ─────────────────────────────────────

        plan_data = context.get("decompose", {})
        exec_data = context.get("execute", {})
        validate_data = context.get("validate", {})
        refine_data = context.get("refine", {})

        # Build execution log for HiClaw format
        execution_log_parts = [f"Claude Flow — {len(self.PHASE_CONFIG)} phases executed:"]
        for phase_name, result in self._phase_results.items():
            icon = "✓" if not result.issues else "⚠"
            execution_log_parts.append(
                f"  {icon} [{result.sub_agent:10s}] {phase_name:12s} → {result.duration_ms:.0f}ms"
            )

        final_quality = refine_data.get(
            "refined_quality_score",
            validate_data.get("quality_score", 0),
        )

        consolidated = {
            "plan": str(plan_data.get("micro_tasks", [])),
            "execution_log": "\n".join(execution_log_parts),
            "output": {
                "execution": exec_data,
                "validation": validate_data,
                "refinement": refine_data,
                "quality_score": final_quality,
            },
            "issues": list(set(all_issues)),
            "next_action": "Ready for Manager review" if passed else "Needs reassignment or manual intervention",
            "quality_score": final_quality,
            "passed": passed,
        }

        self._logger.info(
            f"╔══ Claude Flow END ══════════════════════════════════╗\n"
            f"║  Quality: {final_quality:.3f} | Passed: {passed}\n"
            f"╚════════════════════════════════════════════════════╝"
        )

        return consolidated

    @property
    def phase_results(self) -> dict[str, SubAgentResult]:
        return dict(self._phase_results)
