"""
Integration test — Full end-to-end pipeline.

Tests the complete flow:
  USER → HiClaw Manager → Workers (Claude Flow) → Review → Merge → Deliver
"""

import pytest
import asyncio

from orchestrator import Orchestrator
from core.message import TaskStatus


class TestIntegration:
    """End-to-end integration tests."""

    @pytest.fixture
    def orchestrator(self):
        return Orchestrator(log_level="WARNING")

    @pytest.mark.asyncio
    async def test_playwright_task_flow(self, orchestrator):
        """
        Test the example from the spec:
        'Build Playwright automation for login and dashboard'
        """
        result = await orchestrator.run(
            "Build Playwright automation for login and dashboard"
        )

        # Should produce a merged result
        assert result.agent_role == "MANAGER"
        assert result.output is not None
        assert result.status in (TaskStatus.COMPLETED, TaskStatus.NEEDS_REVIEW)

    @pytest.mark.asyncio
    async def test_simple_code_task(self, orchestrator):
        """Test a simple code implementation task."""
        result = await orchestrator.run(
            "Implement a user registration module"
        )

        assert result.agent_role == "MANAGER"
        assert result.output is not None

    @pytest.mark.asyncio
    async def test_hiclaw_messaging(self, orchestrator):
        """Verify HiClaw rooms and messaging are working."""
        coordinator = orchestrator.coordinator

        # All agents should be registered
        agents = coordinator.registry.all_agents
        assert len(agents) == 5  # 1 manager + 4 workers

        # Rooms should be created
        rooms = coordinator.messenger._rooms
        assert len(rooms) >= 5  # broadcast + status + review + 4 direct

    @pytest.mark.asyncio
    async def test_system_status(self, orchestrator):
        """Test system status reporting."""
        status = orchestrator.system_status()
        assert "MANAGER" in status
        assert "SOFTWARE_DEVELOPER" in status
        assert "QA_ENGINEER" in status
        assert "CODE_REVIEWER" in status
        assert "DEVOPS_ENGINEER" in status

    @pytest.mark.asyncio
    async def test_hiclaw_format_in_output(self, orchestrator):
        """Verify output follows HiClaw communication format."""
        result = await orchestrator.run("Build a simple API")
        formatted = result.to_hiclaw_format()

        required_fields = [
            "[AGENT ROLE]",
            "[TASK RECEIVED]",
            "[PLAN]",
            "[CLAUDE FLOW EXECUTION SUMMARY]",
            "[OUTPUT]",
            "[ISSUES]",
            "[NEXT ACTION]",
        ]
        for field in required_fields:
            assert field in formatted, f"Missing HiClaw field: {field}"
