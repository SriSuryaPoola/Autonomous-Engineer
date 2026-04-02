"""
Tests for the task pipeline — decomposer, assigner, merger, executor.
"""

import pytest
import asyncio

from core.message import AgentMessage, TaskSpec, TaskStatus, MessagePriority
from core.task_pipeline import TaskDecomposer, TaskAssigner, TaskMerger, ParallelExecutor


class TestTaskDecomposer:
    """Tests for task decomposition."""

    @pytest.fixture
    def decomposer(self):
        return TaskDecomposer()

    def test_code_task_detection(self, decomposer):
        tasks = decomposer.decompose("Build a REST API with authentication")
        assert len(tasks) >= 2  # At least code + review
        roles = [t.assigned_role for t in tasks]
        assert "SOFTWARE_DEVELOPER" in roles

    def test_test_task_detection(self, decomposer):
        tasks = decomposer.decompose("Write automated tests for login feature")
        roles = [t.assigned_role for t in tasks]
        assert "QA_ENGINEER" in roles

    def test_playwright_task(self, decomposer):
        tasks = decomposer.decompose(
            "Build Playwright automation for login and dashboard"
        )
        assert len(tasks) >= 2
        categories = [t.category for t in tasks]
        assert "test" in categories or "code" in categories

    def test_always_includes_review(self, decomposer):
        tasks = decomposer.decompose("Implement user registration")
        categories = [t.category for t in tasks]
        assert "review" in categories


class TestTaskAssigner:
    """Tests for task assignment."""

    @pytest.fixture
    def assigner(self):
        return TaskAssigner()

    def test_assign_code_task(self, assigner):
        task = TaskSpec(category="code")
        role = assigner.assign(task, ["SOFTWARE_DEVELOPER", "QA_ENGINEER"])
        assert role == "SOFTWARE_DEVELOPER"

    def test_assign_test_task(self, assigner):
        task = TaskSpec(category="test")
        role = assigner.assign(task, ["SOFTWARE_DEVELOPER", "QA_ENGINEER"])
        assert role == "QA_ENGINEER"

    def test_assign_preassigned(self, assigner):
        task = TaskSpec(category="code", assigned_role="DEVOPS_ENGINEER")
        role = assigner.assign(task, ["SOFTWARE_DEVELOPER", "DEVOPS_ENGINEER"])
        assert role == "DEVOPS_ENGINEER"

    def test_assign_fallback(self, assigner):
        task = TaskSpec(category="unknown")
        role = assigner.assign(task, ["SOFTWARE_DEVELOPER"])
        assert role == "SOFTWARE_DEVELOPER"


class TestTaskMerger:
    """Tests for result merging."""

    @pytest.fixture
    def merger(self):
        return TaskMerger()

    def test_merge_completed(self, merger):
        results = [
            AgentMessage(
                agent_role="SOFTWARE_DEVELOPER",
                task_received="Build API",
                output={"code": "done"},
                status=TaskStatus.COMPLETED,
            ),
            AgentMessage(
                agent_role="QA_ENGINEER",
                task_received="Test API",
                output={"tests": "5 passed"},
                status=TaskStatus.COMPLETED,
            ),
        ]
        merged = merger.merge(results)
        assert merged.status == TaskStatus.COMPLETED
        assert "SOFTWARE_DEVELOPER" in merged.output
        assert "QA_ENGINEER" in merged.output

    def test_merge_with_failure(self, merger):
        results = [
            AgentMessage(
                agent_role="SOFTWARE_DEVELOPER",
                task_received="Build API",
                output={"code": "done"},
                status=TaskStatus.COMPLETED,
            ),
            AgentMessage(
                agent_role="QA_ENGINEER",
                task_received="Test API",
                failures=["Tests failed"],
                status=TaskStatus.FAILED,
            ),
        ]
        merged = merger.merge(results)
        assert merged.status == TaskStatus.FAILED


class TestParallelExecutor:
    """Tests for parallel task execution."""

    @pytest.fixture
    def executor(self):
        return ParallelExecutor(max_concurrent=2)

    @pytest.mark.asyncio
    async def test_execute_independent_tasks(self, executor):
        tasks = [
            TaskSpec(title="Task A", category="code"),
            TaskSpec(title="Task B", category="test"),
        ]

        async def mock_execute(task: TaskSpec) -> AgentMessage:
            return AgentMessage(
                agent_role="TEST",
                task_received=task.title,
                status=TaskStatus.COMPLETED,
            )

        results = await executor.execute(tasks, mock_execute)
        assert len(results) == 2
        assert all(r.status == TaskStatus.COMPLETED for r in results)

    @pytest.mark.asyncio
    async def test_execute_with_dependencies(self, executor):
        task_a = TaskSpec(title="Task A", category="code")
        task_b = TaskSpec(
            title="Task B", category="test",
            dependencies=[task_a.task_id],
        )

        execution_order = []

        async def mock_execute(task: TaskSpec) -> AgentMessage:
            execution_order.append(task.title)
            return AgentMessage(
                agent_role="TEST",
                task_received=task.title,
                status=TaskStatus.COMPLETED,
            )

        results = await executor.execute([task_a, task_b], mock_execute)
        assert len(results) == 2
        assert execution_order.index("Task A") < execution_order.index("Task B")
