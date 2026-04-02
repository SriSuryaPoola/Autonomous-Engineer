"""
Task Pipeline — Decomposition, Assignment, Parallel Execution, Merging.

Provides the machinery for the Manager Agent to:
  1. Decompose user requests into a task graph
  2. Assign tasks to workers by role/capability
  3. Execute independent tasks concurrently
  4. Merge results into a single deliverable
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine, Optional

from config.settings import (
    TASK_CATEGORY_TO_ROLE,
    PARALLEL_WORKERS,
    WORKER_ROLES,
)
from core.message import AgentMessage, TaskSpec, TaskStatus, MessagePriority

logger = logging.getLogger(__name__)


# ─── Task Decomposer ─────────────────────────────────────────────────────────

class TaskDecomposer:
    """
    Breaks a high-level user request into structured TaskSpec items.

    Uses keyword analysis to categorize tasks and build a dependency graph.
    """

    # Patterns that suggest a specific task category
    CATEGORY_SIGNALS = {
        "test": ["test", "qa", "automat", "selenium", "playwright", "coverage",
                 "assert", "expect", "spec", "scenario"],
        "code": ["build", "implement", "create", "write code", "develop",
                 "function", "class", "module", "api", "endpoint", "feature"],
        "review": ["review", "audit", "check quality", "best practice",
                   "security", "performance", "lint", "validate code"],
        "deploy": ["deploy", "ci/cd", "pipeline", "docker", "container",
                   "kubernetes", "infrastructure", "config", "environment"],
        "research": ["research", "analyze", "investigate", "evaluate",
                     "compare", "feasibility", "study"],
    }

    def decompose(self, user_request: str) -> list[TaskSpec]:
        """
        Parse a user request and produce a list of TaskSpec items.
        """
        logger.info(f"Decomposing request: {user_request[:80]}...")
        request_lower = user_request.lower()

        # Detect which categories are relevant
        detected: dict[str, list[str]] = {}
        for category, signals in self.CATEGORY_SIGNALS.items():
            matching = [s for s in signals if s in request_lower]
            if matching:
                detected[category] = matching

        # If no specific signals, default to a code task
        if not detected:
            detected["code"] = ["general implementation"]

        # Build tasks
        tasks: list[TaskSpec] = []
        dependency_ids: list[str] = []

        # Code / implementation task(s) come first
        if "code" in detected:
            t = TaskSpec(
                title=f"Implementation: {user_request[:60]}",
                description=user_request,
                category="code",
                assigned_role=TASK_CATEGORY_TO_ROLE.get("code", "SOFTWARE_DEVELOPER"),
                priority=MessagePriority.HIGH,
            )
            tasks.append(t)
            dependency_ids.append(t.task_id)

        # QA / test tasks depend on code
        if "test" in detected:
            t = TaskSpec(
                title=f"QA/Testing: {user_request[:60]}",
                description=f"Design and implement tests for: {user_request}",
                category="test",
                assigned_role=TASK_CATEGORY_TO_ROLE.get("test", "QA_ENGINEER"),
                dependencies=list(dependency_ids),
                priority=MessagePriority.HIGH,
            )
            tasks.append(t)

        # Review task depends on code (and optionally test)
        if "review" in detected or len(tasks) >= 1:
            code_ids = [t.task_id for t in tasks if t.category == "code"]
            t = TaskSpec(
                title=f"Code Review: {user_request[:60]}",
                description=f"Review code quality and best practices for: {user_request}",
                category="review",
                assigned_role=TASK_CATEGORY_TO_ROLE.get("review", "CODE_REVIEWER"),
                dependencies=code_ids,
                priority=MessagePriority.NORMAL,
            )
            tasks.append(t)

        # Deployment task
        if "deploy" in detected:
            t = TaskSpec(
                title=f"Deployment: {user_request[:60]}",
                description=f"Create deployment configuration for: {user_request}",
                category="deploy",
                assigned_role=TASK_CATEGORY_TO_ROLE.get("deploy", "DEVOPS_ENGINEER"),
                dependencies=[t.task_id for t in tasks if t.category in ("code", "test")],
                priority=MessagePriority.NORMAL,
            )
            tasks.append(t)

        # Research task (if needed, runs in parallel)
        if "research" in detected:
            t = TaskSpec(
                title=f"Research: {user_request[:60]}",
                description=f"Research and analyze: {user_request}",
                category="research",
                assigned_role=TASK_CATEGORY_TO_ROLE.get("research", "SOFTWARE_DEVELOPER"),
                priority=MessagePriority.NORMAL,
            )
            tasks.insert(0, t)  # Research first

        logger.info(f"Decomposed into {len(tasks)} tasks: "
                     + ", ".join(t.title for t in tasks))
        return tasks


# ─── Task Assigner ────────────────────────────────────────────────────────────

class TaskAssigner:
    """
    Maps tasks to worker roles based on category and capabilities.
    """

    def assign(self, task: TaskSpec, available_roles: list[str]) -> str:
        """
        Determine the best role for a task.
        Returns the role name string.
        """
        # Use pre-assigned role if available and valid
        if task.assigned_role and task.assigned_role in available_roles:
            return task.assigned_role

        # Look up by category
        role = TASK_CATEGORY_TO_ROLE.get(task.category.lower())
        if role and role in available_roles:
            return role

        # Keyword matching fallback
        desc_lower = task.description.lower()
        for keyword, role_name in TASK_CATEGORY_TO_ROLE.items():
            if keyword in desc_lower and role_name in available_roles:
                task.assigned_role = role_name
                return role_name

        # Default to first available role
        if available_roles:
            task.assigned_role = available_roles[0]
            return available_roles[0]

        raise ValueError("No available workers to assign task")


# ─── Parallel Executor ────────────────────────────────────────────────────────

class ParallelExecutor:
    """
    Executes independent tasks concurrently using a DAG Priority Queue.
    """

    def __init__(self, max_concurrent: int = PARALLEL_WORKERS):
        self.max_concurrent = max_concurrent
        self._logger = logging.getLogger("pipeline.executor")

    async def execute(
        self,
        tasks: list[TaskSpec],
        execute_fn: Callable[[TaskSpec], Coroutine[Any, Any, AgentMessage]],
        on_completed_fn: Optional[Callable[[TaskSpec, AgentMessage], Coroutine[Any, Any, list[TaskSpec]]]] = None
    ) -> list[AgentMessage]:
        """
        Execute tasks respecting dependency order and priority.
        Maintains PENDING -> RUNNING -> FAILED / COMPLETED state.
        """
        completed_msgs: dict[str, AgentMessage] = {}
        results: list[AgentMessage] = []
        
        # Priority mapping: lower number = higher priority
        priority_map = {
            MessagePriority.CRITICAL: 0,
            MessagePriority.HIGH: 1,
            MessagePriority.NORMAL: 2,
            MessagePriority.LOW: 3
        }

        pending = {t.task_id: t for t in tasks}
        running = set()
        
        # Mark all pending explicitly
        for t in tasks:
            t.status = TaskStatus.PENDING

        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def run_task(task: TaskSpec) -> tuple[str, AgentMessage]:
            async with semaphore:
                try:
                    result = await execute_fn(task)
                    return task.task_id, result
                except Exception as e:
                    self._logger.error(f"Task {task.title} raised exception: {e}")
                    return task.task_id, AgentMessage(
                        agent_role="SYSTEM",
                        task_received=task.title,
                        issues=[str(e)],
                        status=TaskStatus.FAILED,
                    )

        # Execution loop
        active_tasks = []
        
        while pending or running:
            # Enqueue ready tasks
            ready_to_start = []
            for task_id, task in list(pending.items()):
                if all(dep in completed_msgs for dep in task.dependencies):
                    ready_to_start.append(task)
                    
            # Sort ready tasks by priority
            ready_to_start.sort(key=lambda t: priority_map.get(t.priority, 2))
            
            for task in ready_to_start:
                task.status = TaskStatus.IN_PROGRESS
                self._logger.info(f"▶ Scheduling: [{task.priority.name}] {task.title}")
                del pending[task.task_id]
                running.add(task.task_id)
                # create asyncio task
                coro = asyncio.create_task(run_task(task))
                active_tasks.append(coro)

            if not active_tasks:
                if pending:
                    self._logger.error("Deadlock detected! Unresolved dependencies.")
                    break
                break

            # Wait for at least one task to finish
            done, pending_coros = await asyncio.wait(
                active_tasks, return_when=asyncio.FIRST_COMPLETED
            )
            
            active_tasks = list(pending_coros)
            
            for finished in done:
                task_id, result = finished.result()
                running.remove(task_id)
                completed_msgs[task_id] = result
                results.append(result)
                
                # Update task status object explicitly
                orig_task = next((t for t in tasks if t.task_id == task_id), None)
                if orig_task:
                    orig_task.status = result.status
                    
                    # Phase 3 Expansion: Dynamic Task Creation (CI/CD Feedback Loop)
                    if on_completed_fn:
                        try:
                            new_tasks = await on_completed_fn(orig_task, result)
                            if new_tasks:
                                for nt in new_tasks:
                                    nt.status = TaskStatus.PENDING
                                    tasks.append(nt)
                                    pending[nt.task_id] = nt
                                    self._logger.info(f"⚡ Dynamically enqueued new task: {nt.title}")
                        except Exception as ec:
                            self._logger.error(f"Error in on_completed_fn: {ec}")

                self._logger.info(
                    f"{'✓' if result.status == TaskStatus.COMPLETED else '⚠'} "
                    f"Completed: {result.task_received}"
                )

        return results


# ─── Task Merger ──────────────────────────────────────────────────────────────

class TaskMerger:
    """
    Combines multiple worker outputs into a single consolidated deliverable.
    """

    def merge(self, results: list[AgentMessage]) -> AgentMessage:
        """Merge multiple agent outputs into one final message."""
        all_outputs = {}
        all_failures: list[str] = []
        all_plans: list[str] = []
        all_flow_summaries: list[str] = []

        for msg in results:
            section = msg.agent_role
            all_outputs[section] = msg.output
            if hasattr(msg, 'failures'):
                all_failures.extend(msg.failures)
            if msg.plan:
                all_plans.append(f"[{section}] {msg.plan}")
            if msg.claude_flow_summary:
                all_flow_summaries.append(f"[{section}]\n{msg.claude_flow_summary}")

        # Determine overall status
        statuses = [msg.status for msg in results]
        if all(s == TaskStatus.COMPLETED for s in statuses):
            overall_status = TaskStatus.COMPLETED
        elif any(s == TaskStatus.FAILED for s in statuses):
            overall_status = TaskStatus.FAILED
        else:
            overall_status = TaskStatus.NEEDS_REVIEW

        return AgentMessage(
            agent_role="MANAGER",
            task_received="Merged results from all workers",
            plan="\n".join(all_plans),
            claude_flow_summary="\n\n".join(all_flow_summaries),
            output=all_outputs,
            failures=list(set(all_failures)),
            next_action="Deliver to user" if overall_status == TaskStatus.COMPLETED
                        else "Review and reassign failed tasks",
            status=overall_status,
        )
