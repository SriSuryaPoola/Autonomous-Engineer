"""
Manager Agent (CEO) — HiClaw Coordinator.

The Manager Agent:
  ❗ NEVER executes tasks directly
  ❗ ONLY coordinates through HiClaw messaging

Responsibilities:
  1. Interpret user goals
  2. Decompose goals into structured tasks
  3. Assign tasks to workers via HiClaw rooms
  4. Track task progress
  5. Review outputs from workers
  6. Reassign or refine tasks if needed (self-improvement loop)
  7. Merge final outputs
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Optional

from config.settings import MAX_RETRIES, QUALITY_THRESHOLD
from core.agent_base import ManagerAgentBase, WorkerAgent
from core.message import AgentMessage, TaskSpec, TaskStatus, MessagePriority
from core.task_pipeline import TaskDecomposer, TaskAssigner, TaskMerger, ParallelExecutor
from core.hiclaw_bridge import HiClawCoordinator

logger = logging.getLogger(__name__)


class ManagerAgent(ManagerAgentBase):
    """
    Level 1 — CEO Agent.

    Operates exclusively through HiClaw coordination.
    Delegates ALL execution to workers. Uses the self-improvement loop
    to ensure quality before delivery.
    """

    def __init__(self, coordinator: Optional[HiClawCoordinator] = None, memory_dir: Optional[str] = None):
        super().__init__(
            agent_id=str(uuid.uuid4()),
            coordinator=coordinator,
            memory_dir=memory_dir
        )
        self._decomposer = TaskDecomposer()
        self._assigner = TaskAssigner()
        self._merger = TaskMerger()
        self._executor = ParallelExecutor()
        self._current_request: str = ""
        self._task_results: dict[str, AgentMessage] = {}

    # ── Core Lifecycle ────────────────────────────────────────────────────

    async def receive_task(self, task: TaskSpec,
                           context: Optional[AgentMessage] = None) -> None:
        """Manager receives the top-level user request."""
        self._current_request = task.description
        self.memory.add_context(
            {"user_request": task.description},
            tags=["user_request"],
        )
        self._logger.info(f"📥 Received user request: {task.description[:80]}")
        await self.post_status(f"MANAGER received request: {task.description[:60]}")

    async def execute(self) -> AgentMessage:
        """
        Full execution pipeline:
          1. Decompose → 2. Assign → 3. Workers execute via Claude Flow
          → 4. Review → 5. Reassign if needed → 6. Merge → 7. Deliver
        """
        self._logger.info("=" * 60)
        self._logger.info("MANAGER: Starting execution pipeline")
        self._logger.info("=" * 60)

        # Step 1: Decompose
        tasks = await self.decompose(self._current_request)

        # Dynamic Hook for CI/CD Self-Healing
        async def check_ci_status(completed_task: TaskSpec, result: AgentMessage) -> list[TaskSpec]:
            if completed_task.category == "deploy" and result.status.value == "completed":
                self._logger.info(f"CI hook activated for {completed_task.title}. Checking GitHub Actions...")
                from core.tools.ci_tools import CITools
                
                # We would get the workflow dynamically, assuming "ci.yml" for integration test
                status = CITools.get_latest_run_status("ci.yml")
                if status.get("conclusion") == "failure":
                    self._logger.warning("CI Failure detected! Spawning debugging task...")
                    logs = CITools.get_run_logs(status.get("databaseId", ""))
                    debug_task = TaskSpec(
                        title=f"CI Failure Debug: {completed_task.title}",
                        description=f"Fix the CI failure. Logs: {logs}",
                        category="code",
                        assigned_role="SOFTWARE_DEVELOPER",
                        priority=MessagePriority.CRITICAL,
                    )
                    return [debug_task]
            return []

        # Step 2+3: Assign and execute via HiClaw
        results = await self._executor.execute(tasks, self.assign_task, on_completed_fn=check_ci_status)

        # Step 4+5: Review loop (self-improvement)
        final_results = []
        for i, (task, result) in enumerate(zip(tasks, results)):
            reviewed_result = await self._review_loop(task, result)
            final_results.append(reviewed_result)

        # Step 6: Merge
        merged = await self.merge_results(final_results)

        # Step 7: Log and return
        self.memory.store_output("final_delivery", merged.to_dict())
        await self.post_status("MANAGER: Delivery ready")

        return merged

    async def report(self) -> AgentMessage:
        latest = self.memory.get_latest_output("final_delivery")
        return self._create_message(
            task_received=self._current_request,
            output=latest,
            status=TaskStatus.COMPLETED,
            next_action="Delivered to user",
        )

    # ── Decomposition ─────────────────────────────────────────────────────

    async def decompose(self, user_request: str) -> list[TaskSpec]:
        """Break user request into structured tasks."""
        self._logger.info("📋 Decomposing request into tasks...")
        await self.post_status("MANAGER: Decomposing request into tasks")

        tasks = self._decomposer.decompose(user_request)

        # Assign roles
        for task in tasks:
            role = self._assigner.assign(task, self.available_roles)
            task.assigned_role = role
            self._logger.info(f"  → {task.title} → {role}")

        self.memory.log_decision(
            f"Decomposed into {len(tasks)} tasks",
            reasoning="; ".join(f"{t.title}→{t.assigned_role}" for t in tasks),
        )

        return tasks

    # ── Assignment (via HiClaw) ───────────────────────────────────────────

    async def assign_task(self, task: TaskSpec) -> AgentMessage:
        """
        Assign a task to a worker via HiClaw messaging.

        ❗ Manager delegates — NEVER executes directly.
        """
        worker = self.get_worker(task.assigned_role)
        if not worker:
            self._logger.error(f"No worker for role: {task.assigned_role}")
            return self._create_message(
                task_received=task.title,
                issues=[f"No worker available for role: {task.assigned_role}"],
                status=TaskStatus.FAILED,
            )

        self._logger.info(
            f"📨 Assigning via HiClaw: {task.title} → {worker.role}"
        )
        await self.post_status(f"MANAGER: Assigning '{task.title}' to {worker.role}")

        # Send assignment via HiClaw
        assignment_msg = self._create_message(
            task_received=task.title,
            plan=f"Assigned to {worker.role} for execution via Claude Flow",
            next_action=f"{worker.role} should invoke Claude Flow",
            status=TaskStatus.IN_PROGRESS,
        )

        # Send via HiClaw direct room if available
        if self.coordinator:
            try:
                await self.send_direct(worker.agent_id, assignment_msg)
            except (ValueError, RuntimeError):
                self._logger.warning("Direct HiClaw room not available, using direct call")

        # Worker receives and executes (via Claude Flow internally)
        await worker.receive_task(task, context=assignment_msg)
        result = await worker.execute()

        # Store result
        self._task_results[task.task_id] = result

        # Post result to HiClaw status
        await self.post_status(
            f"MANAGER: {worker.role} completed '{task.title}' "
            f"[{result.status.value}]"
        )

        return result

    # ── Review (Quality Gate) ─────────────────────────────────────────────

    async def review_output(self, message: AgentMessage) -> tuple[bool, str]:
        """
        Review a worker's output for quality.

        Uses the Code Reviewer worker if available, otherwise does a
        basic quality check.
        """
        # Try to use Code Reviewer agent
        reviewer = self.get_worker("CODE_REVIEWER")
        if reviewer and message.agent_role != "CODE_REVIEWER":
            self._logger.info("🔍 Sending output to CODE_REVIEWER for review")

            review_task = TaskSpec(
                title=f"Review: {message.task_received}",
                description=f"Review the following output for quality, "
                            f"correctness, and best practices:\n{message.output}",
                category="review",
                assigned_role="CODE_REVIEWER",
            )
            await reviewer.receive_task(review_task)
            review_result = await reviewer.execute()

            # Post review to HiClaw review room
            if self.coordinator:
                await self.coordinator.post_review(
                    self.agent_id, review_result.to_dict()
                )

            has_issues = bool(review_result.failures)
            feedback = (
                "; ".join(review_result.failures) if has_issues
                else "Quality check passed"
            )
            return (not has_issues, feedback)

        # Basic quality check if no reviewer available
        if message.status == TaskStatus.FAILED:
            return (False, "Task failed — needs re-execution")
        if message.issues:
            return (False, f"Issues found: {'; '.join(message.issues)}")
        return (True, "Output accepted")

    async def _review_loop(self, task: TaskSpec, result: AgentMessage) -> AgentMessage:
        """
        Self-improvement loop:
          1. Review output
          2. If issues → reassign with feedback
          3. Repeat until quality passes or max retries
        """
        current_result = result

        for attempt in range(1, MAX_RETRIES + 1):
            passed, feedback = await self.review_output(current_result)

            if passed:
                self._logger.info(
                    f"✅ Review passed for '{task.title}' on attempt {attempt}"
                )
                return current_result

            self._logger.warning(
                f"❌ Review failed for '{task.title}': {feedback}. "
                f"Reassigning (attempt {attempt}/{MAX_RETRIES})"
            )
            self.memory.log_decision(
                f"Reassigning {task.title}",
                reasoning=feedback,
                tags=["reassignment"],
            )

            # Reassign with feedback
            task.feedback = feedback
            task.attempt = attempt + 1
            task.status = TaskStatus.REASSIGNED

            await self.post_status(
                f"MANAGER: Reassigning '{task.title}' (attempt {task.attempt})"
            )

            current_result = await self.assign_task(task)

        self._logger.warning(
            f"⚠ Max retries reached for '{task.title}'. Accepting current result."
        )
        return current_result

    # ── Merge ─────────────────────────────────────────────────────────────

    async def merge_results(self, results: list[AgentMessage]) -> AgentMessage:
        """Combine all worker outputs into a single deliverable."""
        self._logger.info("🔗 Merging results from all workers...")
        await self.post_status("MANAGER: Merging final results")

        merged = self._merger.merge(results)
        merged.next_action = "Final delivery to user"

        self.memory.store_output("merged_results", merged.to_dict())
        return merged
