"""
Tests for Claude Flow 6-step execution engine.
"""

import pytest
import asyncio

from core.claude_flow import ClaudeFlow, SubAgent, SubAgentResult
from core.message import TaskSpec, TaskStatus
from core.agent_base import WorkerAgent
from core.hiclaw_bridge import HiClawCoordinator


class MockWorker(WorkerAgent):
    """A mock worker for testing Claude Flow."""

    def __init__(self):
        super().__init__(
            agent_id="test-worker-001",
            role="TEST_WORKER",
            capabilities=["test"],
        )

    async def _process_task(self, task: TaskSpec) -> dict:
        return {
            "result": f"Processed: {task.title}",
            "status": "success",
        }


class TestSubAgent:
    """Tests for individual sub-agents."""

    @pytest.fixture
    def worker(self):
        return MockWorker()

    @pytest.fixture
    def task(self):
        return TaskSpec(
            title="Test Task",
            description="A test task for testing the sub-agent",
            category="test",
            assigned_role="TEST_WORKER",
        )

    @pytest.mark.asyncio
    async def test_understand_phase(self, worker, task):
        agent = SubAgent("Researcher", "understand", worker)
        result = await agent.run(task, {})
        assert result.phase == "understand"
        assert result.sub_agent == "Researcher"
        assert result.output is not None
        assert "task_title" in result.output

    @pytest.mark.asyncio
    async def test_decompose_phase(self, worker, task):
        context = {
            "understand": {
                "extracted_requirements": ["implement feature X"],
                "task_title": "Test Task",
            }
        }
        agent = SubAgent("Planner", "decompose", worker)
        result = await agent.run(task, context)
        assert result.output is not None
        assert "micro_tasks" in result.output
        assert result.output["total_steps"] > 0

    @pytest.mark.asyncio
    async def test_validate_phase(self, worker, task):
        context = {
            "execute": {
                "success_rate": 1.0,
                "execution_results": [
                    {"step": 1, "status": "completed"},
                ],
            }
        }
        agent = SubAgent("Tester", "validate", worker)
        result = await agent.run(task, context)
        assert result.output is not None
        assert "quality_score" in result.output
        assert "passed" in result.output


class TestClaudeFlow:
    """Tests for the full Claude Flow pipeline."""

    @pytest.fixture
    def worker(self):
        return MockWorker()

    @pytest.fixture
    def task(self):
        return TaskSpec(
            title="Test Claude Flow",
            description="Test the 6-step pipeline",
            category="code",
            assigned_role="TEST_WORKER",
        )

    @pytest.mark.asyncio
    async def test_full_pipeline(self, worker, task):
        flow = ClaudeFlow(worker=worker)
        result = await flow.run(task)

        assert "plan" in result
        assert "execution_log" in result
        assert "output" in result
        assert "quality_score" in result
        assert "passed" in result
        assert result["quality_score"] > 0

    @pytest.mark.asyncio
    async def test_phase_results_accessible(self, worker, task):
        flow = ClaudeFlow(worker=worker)
        await flow.run(task)

        phases = flow.phase_results
        assert "understand" in phases
        assert "decompose" in phases
        assert "execute" in phases
        assert "validate" in phases
        assert "refine" in phases
