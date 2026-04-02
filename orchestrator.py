"""
Orchestrator — HiClaw ↔ Claude Flow Integration.

Top-level system that wires together:
  - HiClaw Coordinator (rooms, messaging, registry)
  - Manager Agent (CEO)
  - Worker Agents (specialists)

Handles the full lifecycle:
  1. Initialize HiClaw environment
  2. Register all agents
  3. Accept user request
  4. Run the Manager pipeline (decompose → assign → execute → review → merge)
  5. Deliver final output
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from config.settings import LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT
from core.hiclaw_bridge import HiClawCoordinator
from core.message import AgentMessage, TaskSpec, TaskStatus
from core.dashboard import Dashboard
from agents.manager import ManagerAgent
from agents.workers.software_developer import SoftwareDeveloper
from agents.workers.qa_engineer import QAEngineer
from agents.workers.code_reviewer import CodeReviewer
from agents.workers.devops_engineer import DevOpsEngineer

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Top-level orchestrator for the Autonomous Engineering Team.

    Ties together HiClaw (coordination) + Claude Flow (execution)
    into a single unified system.
    """

    def __init__(self, log_level: Optional[str] = None, memory_dir: Optional[str] = None):
        self._setup_logging(log_level or LOG_LEVEL)
        self._logger = logging.getLogger("orchestrator")
        self.memory_dir = memory_dir

        # Initialize HiClaw Coordinator
        self.coordinator = HiClawCoordinator()

        # Create agents with optional memory isolation
        self.manager = ManagerAgent(coordinator=self.coordinator, memory_dir=memory_dir)
        self.workers = {
            "SOFTWARE_DEVELOPER": SoftwareDeveloper(coordinator=self.coordinator, memory_dir=memory_dir),
            "QA_ENGINEER": QAEngineer(coordinator=self.coordinator, memory_dir=memory_dir),
            "CODE_REVIEWER": CodeReviewer(coordinator=self.coordinator, memory_dir=memory_dir),
            "DEVOPS_ENGINEER": DevOpsEngineer(coordinator=self.coordinator, memory_dir=memory_dir),
        }

        # Register workers with manager
        for worker in self.workers.values():
            self.manager.register_worker(worker)

        # Initialize HiClaw environment
        worker_ids = [w.agent_id for w in self.workers.values()]
        self.coordinator.initialize(self.manager.agent_id, worker_ids)

        self._logger.info("=" * 60)
        self._logger.info("Autonomous Engineering Team — READY")
        self._logger.info(f"  Manager: {self.manager.agent_id[:8]}")
        for role, worker in self.workers.items():
            self._logger.info(f"  {role}: {worker.agent_id[:8]}")
        self._logger.info(f"  HiClaw Rooms: {len(self.coordinator.messenger._rooms)}")
        self._logger.info("=" * 60)

    def _setup_logging(self, level: str) -> None:
        """Configure logging for the entire system."""
        logging.basicConfig(
            level=getattr(logging, level.upper(), logging.INFO),
            format=LOG_FORMAT,
            datefmt=LOG_DATE_FORMAT,
        )

    async def run(self, user_request: str, use_dashboard: bool = False) -> AgentMessage:
        """
        Execute a user request through the full pipeline.

        Flow:
          USER → HiClaw Manager → Workers (Claude Flow) → Review → Merge → Deliver
        """
        dashboard = None
        if use_dashboard:
            dashboard = Dashboard(self)
            dashboard.start()

        self._logger.info("=" * 60)
        self._logger.info(f"📥 USER REQUEST: {user_request}")
        self._logger.info("=" * 60)

        # Post initial status to HiClaw
        await self.coordinator.post_status(
            self.manager.agent_id,
            f"New request received: {user_request[:60]}..."
        )

        # Create top-level task
        top_task = TaskSpec(
            title="User Request",
            description=user_request,
            category="code",
            assigned_role="MANAGER",
        )

        # Manager receives and processes
        await self.manager.receive_task(top_task)
        result = await self.manager.execute()

        # Print final output
        self._logger.info("=" * 60)
        self._logger.info("📤 FINAL DELIVERY")
        self._logger.info("=" * 60)
        print("\n" + result.to_hiclaw_format() + "\n")
        
        if dashboard:
            dashboard.stop()

        return result

    async def interactive(self, use_dashboard: bool = False) -> None:
        """
        Interactive REPL mode.

        Enter requests and get results in a loop.
        """
        print("\n" + "=" * 60)
        print("🤖 Autonomous Engineering Team — Interactive Mode")
        print("=" * 60)
        print("Type your request and press Enter. Type 'exit' to quit.\n")

        while True:
            try:
                request = input("📝 Request > ").strip()
                if not request:
                    continue
                if request.lower() in ("exit", "quit", "q"):
                    print("\n👋 Shutting down. Goodbye!")
                    break

                result = await self.run(request, use_dashboard=use_dashboard)

                # Show HiClaw system summary
                print(f"\n{self.coordinator.summary()}\n")

            except KeyboardInterrupt:
                print("\n\n👋 Interrupted. Goodbye!")
                break
            except Exception as exc:
                self._logger.error(f"Error: {exc}", exc_info=True)
                print(f"\n❌ Error: {exc}\n")

    def system_status(self) -> str:
        """Get the current system status."""
        return self.coordinator.summary()
