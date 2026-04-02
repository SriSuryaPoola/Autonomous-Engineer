"""
Tests for the structured message protocol.
"""

import pytest
import json
from datetime import datetime

from core.message import AgentMessage, TaskSpec, TaskStatus, MessagePriority


class TestAgentMessage:
    """Tests for AgentMessage dataclass."""

    def test_create_message(self):
        msg = AgentMessage(
            agent_role="QA_ENGINEER",
            task_received="Build login tests",
        )
        assert msg.agent_role == "QA_ENGINEER"
        assert msg.task_received == "Build login tests"
        assert msg.status == TaskStatus.PENDING
        assert msg.priority == MessagePriority.NORMAL
        assert msg.message_id  # UUID generated

    def test_serialization_roundtrip(self):
        msg = AgentMessage(
            agent_role="SOFTWARE_DEVELOPER",
            task_received="Implement API",
            plan="Build REST endpoints",
            output={"code": "print('hello')"},
            failures=["missing auth"],
            next_action="Add JWT support",
            status=TaskStatus.COMPLETED,
            priority=MessagePriority.HIGH,
        )
        data = msg.to_dict()
        restored = AgentMessage.from_dict(data)

        assert restored.agent_role == msg.agent_role
        assert restored.task_received == msg.task_received
        assert restored.plan == msg.plan
        assert restored.output == msg.output
        assert restored.issues == msg.issues
        assert restored.status == TaskStatus.COMPLETED
        assert restored.priority == MessagePriority.HIGH

    def test_json_roundtrip(self):
        msg = AgentMessage(
            agent_role="MANAGER",
            task_received="Deploy app",
            output={"status": "ready"},
        )
        json_str = msg.to_json()
        restored = AgentMessage.from_json(json_str)
        assert restored.agent_role == msg.agent_role
        assert restored.output == msg.output

    def test_hiclaw_format(self):
        msg = AgentMessage(
            agent_role="CODE_REVIEWER",
            task_received="Review login module",
            plan="Check security patterns",
            claude_flow_summary="5 phases completed",
            output="APPROVED",
            failures=["Minor: add type hints"],
            next_action="Merge to main",
        )
        formatted = msg.to_hiclaw_format()
        assert "[AGENT ROLE]" in formatted
        assert "CODE_REVIEWER" in formatted
        assert "[TASK RECEIVED]" in formatted
        assert "[CLAUDE FLOW EXECUTION SUMMARY]" in formatted
        assert "[OUTPUT]" in formatted
        assert "[ISSUES]" in formatted
        assert "[NEXT ACTION]" in formatted


class TestTaskSpec:
    """Tests for TaskSpec dataclass."""

    def test_create_task(self):
        task = TaskSpec(
            title="Build API",
            description="Create REST API",
            category="code",
            assigned_role="SOFTWARE_DEVELOPER",
        )
        assert task.title == "Build API"
        assert task.status == TaskStatus.PENDING

    def test_task_serialization(self):
        task = TaskSpec(
            title="Run tests",
            category="test",
            dependencies=["task-1", "task-2"],
        )
        data = task.to_dict()
        restored = TaskSpec.from_dict(data)
        assert restored.title == task.title
        assert restored.dependencies == task.dependencies
