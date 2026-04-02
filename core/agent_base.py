"""
Abstract Base Classes for all HiClaw agents.

Hierarchy:
    BaseAgent              — universal HiClaw-aware interface
    ├── ManagerAgentBase   — coordination ONLY via HiClaw (never executes)
    └── WorkerAgent        — receives via HiClaw, executes via Claude Flow
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from core.memory import AgentMemory
from core.message import AgentMessage, TaskSpec, TaskStatus, MessagePriority
from core.hiclaw_bridge import HiClawCoordinator


logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Universal HiClaw agent interface.

    Every agent registers with the HiClaw system and communicates
    exclusively through HiClaw rooms.
    """

    def __init__(self, agent_id: str, role: str,
                 coordinator: Optional[HiClawCoordinator] = None,
                 memory_dir: Optional[str] = None):
        self.agent_id = agent_id
        self.role = role
        # Initialize Memory (Phase 4: with optional project-level directory)
        self.memory = AgentMemory(agent_id, base_dir=memory_dir)
        self.coordinator = coordinator
        self._logger = logging.getLogger(f"agent.{role}.{agent_id[:8]}")

        # Register with HiClaw if coordinator is available
        if self.coordinator:
            self.coordinator.registry.register(
                agent_id=agent_id,
                role=role,
                capabilities=self._get_capabilities(),
            )

    def _get_capabilities(self) -> list[str]:
        """Override in subclasses to declare capabilities."""
        return []

    # ── HiClaw Communication ─────────────────────────────────────────────

    async def send_to_room(self, room_id: str, message: AgentMessage) -> dict:
        """Send a structured message via HiClaw room."""
        if not self.coordinator:
            raise RuntimeError("No HiClaw coordinator available")
        return await self.coordinator.messenger.send_message(
            sender_id=self.agent_id,
            room_id=room_id,
            content=message.to_dict(),
        )

    async def send_direct(self, target_agent_id: str, message: AgentMessage) -> dict:
        """Send a direct message to another agent via HiClaw."""
        if not self.coordinator:
            raise RuntimeError("No HiClaw coordinator available")
        room = self.coordinator.get_direct_room(self.agent_id, target_agent_id)
        if not room:
            raise ValueError(f"No direct room between {self.agent_id[:8]} and {target_agent_id[:8]}")
        return await self.coordinator.messenger.send_message(
            sender_id=self.agent_id,
            room_id=room.room_id,
            content=message.to_dict(),
        )

    async def post_status(self, status_text: str) -> None:
        """Post a status update to the HiClaw status room."""
        if self.coordinator:
            await self.coordinator.post_status(self.agent_id, status_text)

    # ── Core Lifecycle ────────────────────────────────────────────────────

    @abstractmethod
    async def receive_task(self, task: TaskSpec,
                           context: Optional[AgentMessage] = None) -> None:
        """Accept an incoming task via HiClaw messaging."""
        ...

    @abstractmethod
    async def execute(self) -> AgentMessage:
        """Execute the current task and return a structured result."""
        ...

    @abstractmethod
    async def report(self) -> AgentMessage:
        """Produce the final report for the completed task."""
        ...

    # ── Helpers ───────────────────────────────────────────────────────────

    def _create_message(
        self,
        task_received: str,
        plan: str = "",
        claude_flow_summary: str = "",
        output: Any = None,
        failures: Optional[list[str]] = None,
        next_action: str = "",
        status: TaskStatus = TaskStatus.PENDING,
        priority: MessagePriority = MessagePriority.NORMAL,
        parent_id: Optional[str] = None,
    ) -> AgentMessage:
        """Create a HiClaw-format message stamped with this agent's role."""
        return AgentMessage(
            agent_role=self.role,
            task_received=task_received,
            plan=plan,
            claude_flow_summary=claude_flow_summary,
            output=output,
            failures=failures or [],
            next_action=next_action,
            status=status,
            priority=priority,
            parent_id=parent_id,
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.agent_id[:8]} role={self.role}>"


class ManagerAgentBase(BaseAgent):
    """
    Base class for the Manager (CEO) agent.

    ❗ NEVER executes tasks directly.
    ❗ ONLY coordinates through HiClaw messaging.

    Capabilities:
      - Worker registration
      - Task decomposition & assignment via HiClaw
      - Output review & quality gating
      - Result merging
      - Self-improvement loop (reassignment with feedback)
    """

    def __init__(self, agent_id: str,
                 coordinator: Optional[HiClawCoordinator] = None,
                 memory_dir: Optional[str] = None):
        super().__init__(agent_id, role="MANAGER", coordinator=coordinator, memory_dir=memory_dir)
        self._workers: dict[str, "WorkerAgent"] = {}

    def register_worker(self, worker: "WorkerAgent") -> None:
        """Register a specialist worker agent."""
        self._workers[worker.role] = worker
        self._logger.info(f"Registered worker: {worker.role} ({worker.agent_id[:8]})")
        self.memory.log_decision(
            f"Registered worker {worker.role}",
            reasoning=f"Worker {worker.agent_id[:8]} with role {worker.role}",
        )

    def get_worker(self, role: str) -> Optional["WorkerAgent"]:
        return self._workers.get(role)

    @property
    def available_roles(self) -> list[str]:
        return list(self._workers.keys())

    @abstractmethod
    async def decompose(self, user_request: str) -> list[TaskSpec]:
        """Break a high-level user request into structured tasks."""
        ...

    @abstractmethod
    async def assign_task(self, task: TaskSpec) -> AgentMessage:
        """Assign a task to the appropriate worker via HiClaw and return result."""
        ...

    @abstractmethod
    async def review_output(self, message: AgentMessage) -> tuple[bool, str]:
        """Review a worker's output. Returns (passed, feedback)."""
        ...

    @abstractmethod
    async def merge_results(self, results: list[AgentMessage]) -> AgentMessage:
        """Combine multiple worker outputs into a single deliverable."""
        ...


class WorkerAgent(BaseAgent):
    """
    Base class for all specialist Worker agents.

    Each worker:
      1. Receives tasks via HiClaw messaging
      2. ALWAYS invokes Claude Flow internally for execution
      3. Returns structured output through HiClaw

    ❗ Workers MUST NOT skip validation.
    ❗ Workers MUST use Claude Flow — no direct execution.
    """

    def __init__(self, agent_id: str, role: str,
                 capabilities: Optional[list[str]] = None,
                 coordinator: Optional[HiClawCoordinator] = None,
                 memory_dir: Optional[str] = None):
        self.capabilities: list[str] = capabilities or []
        super().__init__(agent_id, role, coordinator=coordinator, memory_dir=memory_dir)
        self._current_task: Optional[TaskSpec] = None

    def _get_capabilities(self) -> list[str]:
        return self.capabilities

    def has_capability(self, capability: str) -> bool:
        return capability in self.capabilities

    async def receive_task(self, task: TaskSpec,
                           context: Optional[AgentMessage] = None) -> None:
        """Receive a task from the Manager via HiClaw."""
        self._current_task = task
        self.memory.add_context(
            {
                "received_task": task.to_dict(),
                "context": context.to_dict() if context else None,
                "attempt": task.attempt,
                "feedback": task.feedback,
            },
            tags=["task_received", f"attempt_{task.attempt}"],
        )
        self._logger.info(
            f"Received task via HiClaw: {task.title} (attempt {task.attempt})"
        )

        # Post status to HiClaw
        await self.post_status(f"{self.role} received task: {task.title}")

    async def execute(self) -> AgentMessage:
        """
        Execute the current task using Claude Flow.

        ❗ All execution goes through Claude Flow — never direct.
        """
        if self._current_task is None:
            return self._create_message(
                task_received="No task assigned",
                failures=["No task has been received via HiClaw"],
                status=TaskStatus.FAILED,
            )

        task = self._current_task
        self._logger.info(f"Invoking Claude Flow for task: {task.title}")
        await self.post_status(f"{self.role} executing: {task.title} via Claude Flow")

        try:
            # MANDATORY: Use Claude Flow for execution
            from core.claude_flow import ClaudeFlow

            flow = ClaudeFlow(worker=self)
            result = await flow.run(task)

            self.memory.store_output(task.title, result, tags=["claude_flow_result"])

            return self._create_message(
                task_received=task.title,
                plan=result.get("plan", ""),
                claude_flow_summary=result.get("execution_log", ""),
                output=result.get("output"),
                failures=result.get("issues", []),
                next_action=result.get("next_action", ""),
                status=(TaskStatus.COMPLETED
                        if result.get("passed", False)
                        else TaskStatus.NEEDS_REVIEW),
            )
        except Exception as exc:
            self._logger.error(f"Claude Flow execution failed: {exc}", exc_info=True)
            self.memory.log_error(str(exc), details=f"Task: {task.title}")
            return self._create_message(
                task_received=task.title,
                failures=[str(exc)],
                status=TaskStatus.FAILED,
            )

    async def report(self) -> AgentMessage:
        latest = self.memory.get_latest_output()
        task_title = self._current_task.title if self._current_task else "Unknown"
        return self._create_message(
            task_received=task_title,
            output=latest,
            status=TaskStatus.COMPLETED,
        )

    @abstractmethod
    async def _process_task(self, task: TaskSpec) -> dict:
        """
        Domain-specific task processing.
        Called by Claude Flow's Coder sub-agent.
        """
        ...
