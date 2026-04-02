"""
Structured Agent Communication Protocol — HiClaw Compatible.

All agents communicate via AgentMessage instances that conform to the
HiClaw mandated communication format (Phase 3 13-field strict protocol):

    [AGENT ROLE]
    [TASK ID]
    [TASK TYPE]
    [TASK RECEIVED]
    [DEPENDENCIES]
    [PLAN]
    [CLAUDE FLOW SUMMARY]
    [TOOLS USED]
    [OUTPUT]
    [FAILURES]
    [RETRY COUNT]
    [MEMORY UPDATE]
    [NEXT ACTION]
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class MessagePriority(Enum):
    """Priority levels for inter-agent messages."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(Enum):
    """Lifecycle status of a task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"
    REASSIGNED = "reassigned"


@dataclass
class AgentMessage:
    """
    Structured communication message used by ALL HiClaw agents.
    """

    # HiClaw mandated fields
    agent_role: str                                     # [AGENT ROLE]
    task_id: str = ""                                   # [TASK ID]
    task_type: str = ""                                 # [TASK TYPE]
    task_received: str = ""                             # [TASK RECEIVED]
    dependencies: list[str] = field(default_factory=list) # [DEPENDENCIES]
    plan: str = ""                                      # [PLAN]
    claude_flow_summary: str = ""                       # [CLAUDE FLOW SUMMARY]
    tools_used: list[str] = field(default_factory=list) # [TOOLS USED]
    output: Any = None                                  # [OUTPUT]
    failures: list[str] = field(default_factory=list)   # [FAILURES]
    retry_count: int = 0                                # [RETRY COUNT]
    memory_update: str = ""                             # [MEMORY UPDATE]
    next_action: str = ""                               # [NEXT ACTION]

    # Internal tracking
    status: TaskStatus = TaskStatus.PENDING
    priority: MessagePriority = MessagePriority.NORMAL
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)

    # ── Serialization ──────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dictionary."""
        data = asdict(self)
        data["status"] = self.status.value
        data["priority"] = self.priority.value
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "AgentMessage":
        """Deserialize from a dictionary."""
        data = dict(data)
        data["status"] = TaskStatus(data.get("status", "pending"))
        data["priority"] = MessagePriority(data.get("priority", "normal"))
        ts = data.get("timestamp")
        if isinstance(ts, str):
            data["timestamp"] = datetime.fromisoformat(ts)
        return cls(**data)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_json(cls, json_str: str) -> "AgentMessage":
        return cls.from_dict(json.loads(json_str))

    # ── HiClaw Format Display ─────────────────────────────────────────────

    def to_hiclaw_format(self) -> str:
        """
        Format message in the strict HiClaw communication format.
        This is the format used when sending via HiClaw rooms.
        """
        divider = "─" * 60
        deps_str = "\n".join(f"  • {d}" for d in self.dependencies) if self.dependencies else "  (none)"
        tools_str = "\n".join(f"  • {t}" for t in self.tools_used) if self.tools_used else "  (none)"
        failures_str = "\n".join(f"  • {f}" for f in self.failures) if self.failures else "  (none)"
        output_str = json.dumps(self.output, indent=2, default=str) if self.output else "(none)"

        return f"""
╔{'═' * 58}╗
║  HiClaw Message — {self.message_id[:8]}
╚{'═' * 58}╝
{divider}
  [AGENT ROLE]
    {self.agent_role}

  [TASK ID]
    {self.task_id or '(none)'}

  [TASK TYPE]
    {self.task_type or '(none)'}

  [TASK RECEIVED]
    {self.task_received or '(none)'}

  [DEPENDENCIES]
{deps_str}

  [PLAN]
    {self.plan or '(not yet planned)'}

  [CLAUDE FLOW SUMMARY]
    {self.claude_flow_summary or '(not yet executed)'}

  [TOOLS USED]
{tools_str}

  [OUTPUT]
    {output_str}

  [FAILURES]
{failures_str}

  [RETRY COUNT]
    {self.retry_count}

  [MEMORY UPDATE]
    {self.memory_update or '(none)'}

  [NEXT ACTION]
    {self.next_action or '(awaiting instructions)'}
{divider}
  Status: {self.status.value.upper()} | Priority: {self.priority.value.upper()}
  Timestamp: {self.timestamp.isoformat()}
""".strip()

    def __str__(self) -> str:
        return self.to_hiclaw_format()


@dataclass
class TaskSpec:
    """
    A lightweight task specification for decomposition and assignment.
    Routed through HiClaw rooms to workers.
    """

    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    category: str = ""              # e.g. "code", "test", "review"
    assigned_role: str = ""         # e.g. "SOFTWARE_DEVELOPER"
    dependencies: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    priority: MessagePriority = MessagePriority.NORMAL
    output: Any = None
    feedback: str = ""              # Manager feedback for reassignment
    attempt: int = 1                # Current attempt number
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        data["priority"] = self.priority.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "TaskSpec":
        data = dict(data)
        data["status"] = TaskStatus(data.get("status", "pending"))
        data["priority"] = MessagePriority(data.get("priority", "normal"))
        return cls(**data)

    def __str__(self) -> str:
        return (
            f"TaskSpec[{self.task_id[:8]}] "
            f"title={self.title!r} role={self.assigned_role} "
            f"status={self.status.value} attempt={self.attempt}"
        )
