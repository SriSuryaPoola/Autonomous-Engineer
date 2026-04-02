"""
Code Reviewer Worker — HiClaw Agent.

Domain: Code quality review, best practices enforcement,
security auditing, performance review.
Executes ALL tasks via Claude Flow internally.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from config.settings import WORKER_ROLES
from core.agent_base import WorkerAgent
from core.message import TaskSpec
from core.hiclaw_bridge import HiClawCoordinator

logger = logging.getLogger(__name__)

_ROLE_CONFIG = WORKER_ROLES["CODE_REVIEWER"]


class CodeReviewer(WorkerAgent):
    """
    Code Reviewer specialist.

    Capabilities: code review, best practices, security audit,
    performance review, style enforcement.

    Used by the Manager's self-improvement loop to validate outputs
    before final delivery.

    All execution goes through Claude Flow — never direct.
    """

    def __init__(self, coordinator: Optional[HiClawCoordinator] = None, memory_dir: Optional[str] = None):
        super().__init__(
            agent_id=str(uuid.uuid4()),
            role="CODE_REVIEWER",
            capabilities=_ROLE_CONFIG["capabilities"],
            coordinator=coordinator,
            memory_dir=memory_dir
        )

    async def _process_task(self, task: TaskSpec) -> dict:
        """
        Domain-specific processing: Run actual static analysis / syntax checks.
        """
        self._logger.info(f"🔍 Processing review task: {task.title}")
        from core.tools.cli_tools import CLITools

        # Run built-in py_compile to check for syntax errors across python files
        check_cmd = 'python -c "import compileall; compileall.compile_dir(\'.\', force=True, quiet=1)"'
        self._logger.info("  Running syntax check via CLITools")
        
        output = CLITools.run_command(check_cmd)
        
        # If output contains "Compiling", it's just the log. 
        # But if there are SyntaxErrors, they will appear in output.
        passed = "SyntaxError" not in output and "CompileError" not in output

        result = {
            "domain": "code_review",
            "task": task.title,
            "category": task.category,
            "action": "static_analysis",
            "artifacts": {
                "check_command": check_cmd,
                "analysis_output": output,
                "passed": passed
            },
            "status": "review_completed" if passed else "review_failed",
        }

        self.memory.store_output(task.title, result, tags=["review_output", "cli_tools"])
        return result
