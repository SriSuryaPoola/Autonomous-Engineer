# Core framework package — HiClaw + Claude Flow
from .message import AgentMessage, TaskSpec, TaskStatus, MessagePriority
from .agent_base import BaseAgent, WorkerAgent, ManagerAgentBase
from .claude_flow import ClaudeFlow
from .task_pipeline import TaskDecomposer, TaskAssigner, TaskMerger, ParallelExecutor
from .memory import AgentMemory
from .hiclaw_bridge import HiClawCoordinator, HiClawRoom, HiClawMessenger, HiClawAgentRegistry
